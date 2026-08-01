"""
Progression math: Epley e1RM, double progression targets, and
pattern-level normalized strength trends.
"""
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.staple import StapleExercise
from app.models.training_session import (
    TrainingSession, SupersetRound, RoundEntry, EntrySet, SessionState,
)
from app.services.history_service import exercise_set_history

DEFAULT_REP_MIN = 8
DEFAULT_REP_MAX = 12
DEFAULT_INCREMENT = 5.0
DEFAULT_SETS = 3


def estimate_1rm(weight: float, reps: int) -> float:
    """Epley estimated one-rep max."""
    return weight * (1 + reps / 30)


def _fmt_weight(weight: float) -> str:
    return f"{weight:g}"


def next_target(
    last_sets: list[tuple[float | None, int | None]],
    rep_min: int = DEFAULT_REP_MIN,
    rep_max: int = DEFAULT_REP_MAX,
    increment: float = DEFAULT_INCREMENT,
) -> dict:
    """Double progression: add a rep until every set hits rep_max, then add load.

    last_sets is the most recent completed session's sets as (weight, reps).
    """
    if not last_sets:
        return {"weight": None, "reps": rep_min, "sets": DEFAULT_SETS, "last_summary": None}

    weights = [w for w, _r in last_sets if w is not None]
    reps = [r for _w, r in last_sets if r is not None]
    top_weight = max(weights) if weights else None
    min_reps = min(reps) if reps else rep_min

    if reps and weights and len(set(weights)) == 1 and len(set(reps)) == 1:
        last_summary = f"{len(last_sets)}x{reps[0]} @ {_fmt_weight(weights[0])}"
    elif reps and not weights:
        last_summary = f"{len(last_sets)}x{reps[0]}"
    else:
        parts = [f"{r or 0}@{_fmt_weight(w) if w is not None else 'bw'}" for w, r in last_sets]
        last_summary = ", ".join(parts)

    all_at_top = bool(reps) and all(r is not None and r >= rep_max for _w, r in last_sets)
    if all_at_top and top_weight is not None:
        return {"weight": top_weight + increment, "reps": rep_min, "sets": len(last_sets), "last_summary": last_summary}
    return {"weight": top_weight, "reps": min(min_reps + 1, rep_max), "sets": len(last_sets), "last_summary": last_summary}


async def compute_entry_target(
    db: AsyncSession, user_id: int, exercise_id: int,
    rep_min: int = DEFAULT_REP_MIN, rep_max: int = DEFAULT_REP_MAX,
) -> dict | None:
    """Target for the next performance of an exercise, from its own history."""
    history = await exercise_set_history(db, user_id, exercise_id, limit_sessions=1)
    if not history:
        return None
    return next_target(history[0]["sets"], rep_min=rep_min, rep_max=rep_max)


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


async def pattern_trend(
    db: AsyncSession, user_id: int, pattern_id: int, weeks: int = 12
) -> list[dict]:
    """Normalized e1RM trend for a pattern across its active staples.

    Each staple's weekly best e1RM is divided by its own first observed
    e1RM (baseline), then staple indices are averaged per week.
    """
    result = await db.execute(
        select(StapleExercise.exercise_id).where(
            StapleExercise.user_id == user_id,
            StapleExercise.pattern_id == pattern_id,
            StapleExercise.is_active == True,  # noqa: E712
        )
    )
    staple_ids = [row[0] for row in result.all()]
    if not staple_ids:
        return []

    # weekly best e1RM per staple: {exercise_id: {week_start: best_e1rm}}
    weekly_best: dict[int, dict[date, float]] = defaultdict(dict)
    for exercise_id in staple_ids:
        history = await exercise_set_history(db, user_id, exercise_id, limit_sessions=weeks * 3)
        for perf in history:
            week = _week_start(perf["performed_at"].date())
            best = max(
                (estimate_1rm(w, r) for w, r in perf["sets"] if w is not None and r),
                default=None,
            )
            if best is None:
                continue
            if week not in weekly_best[exercise_id] or best > weekly_best[exercise_id][week]:
                weekly_best[exercise_id][week] = best

    # normalize each staple to its earliest week's value
    indices_by_week: dict[date, list[float]] = defaultdict(list)
    for exercise_id, series in weekly_best.items():
        if not series:
            continue
        baseline = series[min(series.keys())]
        for week, value in series.items():
            indices_by_week[week].append(value / baseline)

    cutoff = _week_start(date.today()) - timedelta(weeks=weeks)
    return [
        {"week_start": week, "index": sum(vals) / len(vals)}
        for week, vals in sorted(indices_by_week.items())
        if week >= cutoff
    ]

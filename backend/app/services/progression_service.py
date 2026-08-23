"""
Progression math: Epley e1RM, double progression targets, and
pattern-level normalized strength trends.
"""

from collections import defaultdict
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exercise import CONDITIONING_PROTOCOLS, Exercise, SetProtocol
from app.models.staple import StapleExercise
from app.services.bodyweight_service import (
    bodyweight_timeline,
    effective_load,
    resolve_bodyweight,
)
from app.services.exercise_helpers import bodyweight_equipment_id
from app.services.history_service import exercise_set_history

DEFAULT_REP_MIN = 8
DEFAULT_REP_MAX = 12
DEFAULT_INCREMENT = 5.0
DEFAULT_SETS = 3

# Generous safety bound on rows fetched per staple in pattern_trend. Actual
# windowing correctness comes from the `since=` date filter, not this cap -
# it only guards against pathological history sizes.
PATTERN_TREND_SAFETY_LIMIT_SESSIONS = 1000


def estimate_1rm(weight: float, reps: int) -> float:
    """Epley estimated one-rep max."""
    return weight * (1 + reps / 30)


def _fmt_weight(weight: float) -> str:
    return f"{weight:g}"


def _fmt_clock(seconds: int) -> str:
    """Seconds as m:ss, the way a pace is actually read.

    "1:47" is how a 500m row is spoken and written; "107s" is arithmetic. Below
    a minute there is nothing to convert, so it stays in seconds.
    """
    if seconds < 60:
        return f"{seconds}s"
    return f"{seconds // 60}:{seconds % 60:02d}"


def _fmt_distance(meters: float) -> str:
    """Metres below 1km, kilometres above it."""
    if meters < 1000:
        return f"{meters:g}m"
    return f"{meters / 1000:g}km"


def _normalise(
    last_sets: list[tuple],
) -> list[tuple[float | None, int | None, int | None, float | None]]:
    """Accept 2-, 3- or 4-tuples; always return (weight, reps, time, distance).

    Callers predating conditioning pass (weight, reps) or
    (weight, reps, time_seconds) and must keep working unchanged.
    """
    return [
        (
            s[0],
            s[1],
            s[2] if len(s) > 2 else None,
            s[3] if len(s) > 3 else None,
        )
        for s in last_sets
    ]


def _summarise(sets: list[tuple[float | None, int | None, int | None, float | None]]) -> str:
    """Human summary of a performance, honest about what was actually recorded.

    Time-only sets summarise by duration. A set with no reps must never be
    rendered as '0 reps', which reads as a data-loss bug rather than as work
    measured a different way.

    A performance is only "uniform weighted" or "uniform bodyweight" if EVERY
    set agrees - a partially-weighted session (e.g. one set logged without a
    weight) falls through to the per-set summary rather than being misread as
    clean via the pre-filtered `weights` list.
    """
    reps = [r for _w, r, _t, _d in sets if r is not None]
    times = [t for _w, _r, t, _d in sets if t is not None]
    weights = [w for w, _r, _t, _d in sets if w is not None]
    distances = [d for _w, _r, _t, d in sets if d is not None]

    # Distance work reads as a pace, so it is summarised before the time-only
    # branch: "500m in 1:47" is the whole point, and "1x107s" throws away the
    # number that makes the time mean anything.
    if not reps and distances:
        load = f" @ {_fmt_weight(weights[0])}" if len(weights) == len(sets) and len(set(weights)) == 1 else ""
        if len(set(distances)) == 1 and len(times) == len(sets) and len(set(times)) == 1:
            prefix = f"{len(sets)}x" if len(sets) > 1 else ""
            return f"{prefix}{_fmt_distance(distances[0])} in {_fmt_clock(times[0])}{load}"
        parts = []
        for _w, _r, t, d in sets:
            if d is not None and t is not None:
                parts.append(f"{_fmt_distance(d)} in {_fmt_clock(t)}")
            elif d is not None:
                parts.append(_fmt_distance(d))
            elif t is not None:
                parts.append(_fmt_clock(t))
        return ", ".join(parts) + load

    if not reps and times:
        if len(set(times)) == 1:
            return f"{len(sets)}x{times[0]}s"
        return ", ".join(f"{t}s" for t in times)

    all_weighted = len(weights) == len(sets)
    all_bodyweight = len(weights) == 0

    if reps and all_weighted and len(set(weights)) == 1 and len(set(reps)) == 1:
        return f"{len(sets)}x{reps[0]} @ {_fmt_weight(weights[0])}"
    if reps and all_bodyweight and len(set(reps)) == 1:
        return f"{len(sets)}x{reps[0]}"

    parts = []
    for w, r, t, _d in sets:
        if r is None and t is not None:
            parts.append(f"{t}s")
        else:
            parts.append(
                f"{r if r is not None else 0}@{_fmt_weight(w) if w is not None else 'bw'}"
            )
    return ", ".join(parts)


def next_target(
    last_sets: list[tuple],
    rep_min: int = DEFAULT_REP_MIN,
    rep_max: int = DEFAULT_REP_MAX,
    increment: float = DEFAULT_INCREMENT,
    protocol: SetProtocol = SetProtocol.REPS,
) -> dict:
    """The next performance to aim for, interpreted through the set protocol.

    last_sets is the most recent completed session's sets as
    (weight, reps, time_seconds, distance_meters); shorter tuples are accepted
    and padded with None, so callers predating conditioning need no change.

    REPS / EMOM: double progression - add a rep until every set is at rep_max,
    then add load and reset to rep_min. Bodyweight work has no load to add, so
    it keeps adding reps past rep_max rather than being clamped back down to
    it; clamping prescribed 12 reps to somebody who had just done 15.

    AMRAP: beat the best rep count at the same load. Rep ranges do not apply -
    an AMRAP always clears a 12-rep ceiling, so feeding it through double
    progression escalated load every single session without bound.

    TIME: no prescription at all. Duration progression needs intent this
    function does not have, and inventing a rep target from rep_min produced a
    rep goal for a rowing machine.

    DISTANCE: pace, when exactly one variable is free. Holding distance fixed
    makes time a single ordered number to beat, which is a real prescription -
    500m in 1:47 asks for 500m in less. Holding time fixed asks for more ground
    covered. With both moving there is nothing to compare, so it prescribes
    nothing rather than guessing which one was meant.
    """
    conditioning = protocol in CONDITIONING_PROTOCOLS
    if not last_sets:
        return {
            "weight": None,
            "reps": None if conditioning else rep_min,
            "sets": DEFAULT_SETS,
            "time_seconds": None,
            "distance_meters": None,
            "reps_goal": None if conditioning else "target",
            "pace_goal": None,
            "last_summary": None,
        }

    sets = _normalise(last_sets)
    last_summary = _summarise(sets)
    weights = [w for w, _r, _t, _d in sets if w is not None]
    reps = [r for _w, r, _t, _d in sets if r is not None]
    top_weight = max(weights) if weights else None

    if protocol is SetProtocol.TIME:
        return {
            # The load rides along without being progressed. A weighted plank or
            # a loaded march is held at a weight, and forgetting it would ask the
            # user to re-derive their own kettlebell every session. Remembering a
            # load is not prescribing one: no duration target is offered.
            "weight": top_weight,
            "reps": None,
            "sets": len(sets),
            "time_seconds": None,
            "distance_meters": None,
            "reps_goal": None,
            "pace_goal": None,
            "last_summary": last_summary,
        }

    if protocol is SetProtocol.DISTANCE:
        times = [t for _w, _r, t, _d in sets if t is not None]
        distances = [d for _w, _r, _t, d in sets if d is not None]
        # The weight rides along so a ruck is prescribed at the pack it was
        # actually carried with. Pace at a lighter load is not an improvement,
        # and dropping the weight from the target would invite exactly that.
        carried = top_weight

        # Both numbers are needed for a pace. A distance with no clock, or a
        # clock with no distance, is a single measurement with nothing to
        # improve against.
        if distances and times and len(times) == len(sets) == len(distances):
            if len(set(distances)) == 1:
                return {
                    "weight": carried,
                    "reps": None,
                    "sets": len(sets),
                    "time_seconds": min(times),
                    "distance_meters": distances[0],
                    "reps_goal": None,
                    "pace_goal": "beat_time",
                    "last_summary": last_summary,
                }
            if len(set(times)) == 1:
                return {
                    "weight": carried,
                    "reps": None,
                    "sets": len(sets),
                    "time_seconds": times[0],
                    "distance_meters": max(distances),
                    "reps_goal": None,
                    "pace_goal": "beat_distance",
                    "last_summary": last_summary,
                }

        return {
            "weight": carried,
            "reps": None,
            "sets": len(sets),
            "time_seconds": None,
            "distance_meters": None,
            "reps_goal": None,
            "pace_goal": None,
            "last_summary": last_summary,
        }

    if protocol is SetProtocol.AMRAP:
        return {
            "weight": top_weight,
            "reps": max(reps) if reps else None,
            "sets": len(sets),
            "time_seconds": None,
            "distance_meters": None,
            "reps_goal": "beat" if reps else None,
            "pace_goal": None,
            "last_summary": last_summary,
        }

    # REPS / EMOM: double progression.
    min_reps = min(reps) if reps else rep_min
    all_at_top = bool(reps) and all(
        r is not None and r >= rep_max for _w, r, _t, _d in sets
    )

    if all_at_top and top_weight is not None:
        return {
            "weight": top_weight + increment,
            "reps": rep_min,
            "sets": len(sets),
            "time_seconds": None,
            "distance_meters": None,
            "reps_goal": "target",
            "pace_goal": None,
            "last_summary": last_summary,
        }

    # Bodyweight at or past the ceiling keeps climbing: there is no load to add,
    # so clamping to rep_max is the regression this guards against.
    next_reps = min_reps + 1 if top_weight is None else min(min_reps + 1, rep_max)
    return {
        "weight": top_weight,
        "reps": next_reps,
        "sets": len(sets),
        "time_seconds": None,
        "distance_meters": None,
        "reps_goal": "target",
        "pace_goal": None,
        "last_summary": last_summary,
    }


async def compute_entry_target(
    db: AsyncSession,
    user_id: int,
    exercise_id: int,
    rep_min: int = DEFAULT_REP_MIN,
    rep_max: int = DEFAULT_REP_MAX,
    *,
    protocol: SetProtocol,
) -> dict | None:
    """Target for the next performance of an exercise, from its own history.

    `protocol` is required and keyword-only. It used to default to REPS, which
    silently prescribed 9 reps on a rowing machine for any caller that forgot
    it - the exact failure the protocol branches exist to prevent. A missing
    argument is now a TypeError at the call site instead.

    Pass `RoundEntry.set_protocol` when logging against a round entry - it is
    denormalised per entry so reclassifying an exercise never rewrites what past
    sets meant - and `Exercise.set_protocol` when suggesting an exercise that
    has no entry yet.
    """
    history = await exercise_set_history(db, user_id, exercise_id, limit_sessions=1)
    if not history:
        return None
    return next_target(
        history[0]["sets"], rep_min=rep_min, rep_max=rep_max, protocol=protocol
    )


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


async def pattern_trend(
    db: AsyncSession, user_id: int, pattern_id: int, weeks: int = 12
) -> list[dict]:
    """Normalized e1RM trend for a pattern across its active staples.

    Each staple's weekly best e1RM is divided by its own first observed
    e1RM (baseline), then staple indices are averaged per week.

    Bodyweight staples contribute via leverage-scaled load, so a pattern
    trained mostly with push-ups still produces a trend. Without any bodyweight
    readings they are skipped rather than assigned a guessed bodyweight, which
    is the same as the old behaviour of ignoring every weightless set.
    """
    result = await db.execute(
        select(Exercise)
        .join(StapleExercise, StapleExercise.exercise_id == Exercise.id)
        .where(
            StapleExercise.user_id == user_id,
            StapleExercise.pattern_id == pattern_id,
            StapleExercise.is_active == True,  # noqa: E712
        )
    )
    staples = result.scalars().all()
    if not staples:
        return []

    # Fetched once, not per set: bodyweight resolution is a lookup, not a query.
    timeline = await bodyweight_timeline(db, user_id)
    bodyweight_id = await bodyweight_equipment_id(db)

    # Window correctness must come from a date filter, not a session-count
    # guess: a staple logged more often than ~weeks*3 times total (e.g. a
    # warm-up movement done nearly every session) would otherwise have its
    # true earliest in-window performance evicted by a count cap, silently
    # shifting the baseline the whole normalization depends on.
    cutoff_week = _week_start(date.today()) - timedelta(weeks=weeks)
    cutoff_dt = datetime.combine(cutoff_week, datetime.min.time())

    # weekly best e1RM per staple: {exercise_id: {week_start: best_e1rm}}
    weekly_best: dict[int, dict[date, float]] = defaultdict(dict)
    for exercise in staples:
        history = await exercise_set_history(
            db,
            user_id,
            exercise.id,
            limit_sessions=PATTERN_TREND_SAFETY_LIMIT_SESSIONS,
            since=cutoff_dt,
        )
        for perf in history:
            week = _week_start(perf["performed_at"].date())
            bodyweight = resolve_bodyweight(timeline, perf["performed_at"])
            estimates = []
            for w, r, _t, _d in perf["sets"]:
                if not r:
                    continue
                load = effective_load(exercise, w, bodyweight, bodyweight_id)
                if load is None:
                    continue
                estimates.append(estimate_1rm(load, r))
            best = max(estimates, default=None)
            if best is None:
                continue
            if (
                week not in weekly_best[exercise.id]
                or best > weekly_best[exercise.id][week]
            ):
                weekly_best[exercise.id][week] = best

    # normalize each staple to its earliest week's value
    indices_by_week: dict[date, list[float]] = defaultdict(list)
    for exercise_id, series in weekly_best.items():
        if not series:
            continue
        baseline = series[min(series.keys())]
        for week, value in series.items():
            indices_by_week[week].append(value / baseline)

    return [
        {"week_start": week, "index": sum(vals) / len(vals)}
        for week, vals in sorted(indices_by_week.items())
        if week >= cutoff_week
    ]

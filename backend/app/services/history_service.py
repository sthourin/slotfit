"""
Unified exercise performance history across legacy workout tables
(read-only) and new training session tables.
"""
from collections import defaultdict
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.models.workout import WorkoutSession, WorkoutExercise, WorkoutSet, WorkoutState
from app.models.training_session import (
    TrainingSession, SupersetRound, RoundEntry, EntrySet, SessionState,
)


def _legacy_base(user_id: int) -> Select:
    """Select (exercise_id, completed_at, session_id) rows from completed legacy workouts.

    One row per WorkoutExercise, so the same exercise performed twice in one
    session (two WorkoutExercise rows) yields two rows here by design -
    callers that need session-level counts must dedupe on session_id.
    """
    return (
        select(WorkoutExercise.exercise_id, WorkoutSession.completed_at, WorkoutSession.id)
        .join(WorkoutSession, WorkoutSession.id == WorkoutExercise.workout_session_id)
        .where(WorkoutSession.user_id == user_id, WorkoutSession.state == WorkoutState.COMPLETED)
    )


def _new_base(user_id: int) -> Select:
    """Select (exercise_id, completed_at, session_id) rows from completed training sessions.

    One row per RoundEntry, so the same exercise performed in two rounds of
    one session yields two rows here by design - callers that need
    session-level counts must dedupe on session_id.
    """
    return (
        select(RoundEntry.exercise_id, TrainingSession.completed_at, TrainingSession.id)
        .join(SupersetRound, SupersetRound.id == RoundEntry.round_id)
        .join(TrainingSession, TrainingSession.id == SupersetRound.session_id)
        .where(TrainingSession.user_id == user_id, TrainingSession.state == SessionState.COMPLETED)
    )


async def last_performed_map(
    db: AsyncSession, user_id: int, exercise_ids: list[int] | None = None
) -> dict[int, datetime]:
    """Most recent completed performance per exercise, across both histories."""
    result: dict[int, datetime] = {}
    for base in (_legacy_base(user_id), _new_base(user_id)):
        rows = (await db.execute(base)).all()
        for exercise_id, completed_at, _session_id in rows:
            if completed_at is None:
                continue
            if exercise_ids is not None and exercise_id not in exercise_ids:
                continue
            if exercise_id not in result or completed_at > result[exercise_id]:
                result[exercise_id] = completed_at
    return result


async def times_performed_map(db: AsyncSession, user_id: int) -> dict[int, int]:
    """Count of DISTINCT completed sessions in which each exercise appears, across both histories.

    The base queries return one row per WorkoutExercise / RoundEntry, so an
    exercise repeated across multiple rounds (or multiple WorkoutExercise
    entries) within a single session must be deduped down to that one
    session before counting. Legacy WorkoutSession.id and new
    TrainingSession.id are independent autoincrement sequences and can
    collide numerically, so session identity is tagged by generation.
    """
    sessions_by_exercise: dict[int, set[tuple[str, int]]] = defaultdict(set)
    for generation, base in (("legacy", _legacy_base(user_id)), ("new", _new_base(user_id))):
        rows = (await db.execute(base)).all()
        for exercise_id, completed_at, session_id in rows:
            if completed_at is None:
                continue
            sessions_by_exercise[exercise_id].add((generation, session_id))
    return {exercise_id: len(sessions) for exercise_id, sessions in sessions_by_exercise.items()}


async def exercise_set_history(
    db: AsyncSession, user_id: int, exercise_id: int, limit_sessions: int = 5,
    since: datetime | None = None,
) -> list[dict]:
    """Per-session set history for one exercise, newest first.

    since: when provided, only sessions completed on or after this datetime
    are considered - filtered at the query level so a caller windowing by
    date isn't at the mercy of limit_sessions truncating before reaching
    the window's true edge. When None (default), behavior is unchanged.

    Returns: [{"performed_at": datetime, "sets": [(weight, reps), ...]}]
    """
    legacy_query = (
        select(
            WorkoutSession.id, WorkoutSession.completed_at,
            WorkoutSet.weight, WorkoutSet.reps, WorkoutSet.set_number,
        )
        .join(WorkoutExercise, WorkoutExercise.workout_session_id == WorkoutSession.id)
        .join(WorkoutSet, WorkoutSet.workout_exercise_id == WorkoutExercise.id)
        .where(
            WorkoutSession.user_id == user_id,
            WorkoutSession.state == WorkoutState.COMPLETED,
            WorkoutExercise.exercise_id == exercise_id,
        )
    )
    if since is not None:
        legacy_query = legacy_query.where(WorkoutSession.completed_at >= since)
    legacy_rows = (await db.execute(legacy_query)).all()

    new_query = (
        select(
            TrainingSession.id, TrainingSession.completed_at,
            EntrySet.weight, EntrySet.reps, EntrySet.set_number,
        )
        .join(SupersetRound, SupersetRound.session_id == TrainingSession.id)
        .join(RoundEntry, RoundEntry.round_id == SupersetRound.id)
        .join(EntrySet, EntrySet.entry_id == RoundEntry.id)
        .where(
            TrainingSession.user_id == user_id,
            TrainingSession.state == SessionState.COMPLETED,
            RoundEntry.exercise_id == exercise_id,
            EntrySet.completed == True,  # noqa: E712
        )
    )
    if since is not None:
        new_query = new_query.where(TrainingSession.completed_at >= since)
    new_rows = (await db.execute(new_query)).all()

    # Keyed by (generation, session_id) - not by completed_at - so two
    # distinct sessions that happen to share an identical completed_at
    # timestamp are never merged into a single reported performance.
    sets_by_session: dict[tuple[str, int], list[tuple[int, float | None, int | None]]] = defaultdict(list)
    completed_at_by_session: dict[tuple[str, int], datetime] = {}

    for generation, rows in (("legacy", legacy_rows), ("new", new_rows)):
        for session_id, completed_at, weight, reps, set_number in rows:
            if completed_at is None:
                continue
            key = (generation, session_id)
            sets_by_session[key].append((set_number, weight, reps))
            completed_at_by_session[key] = completed_at

    ordered_keys = sorted(
        sets_by_session.keys(),
        key=lambda key: completed_at_by_session[key],
        reverse=True,
    )[:limit_sessions]

    performances: list[dict] = []
    for key in ordered_keys:
        ordered_sets = sorted(sets_by_session[key], key=lambda t: t[0])
        performances.append({
            "performed_at": completed_at_by_session[key],
            "sets": [(weight, reps) for _n, weight, reps in ordered_sets],
        })
    return performances

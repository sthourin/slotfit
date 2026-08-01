"""
Unified exercise performance history across legacy workout tables
(read-only) and new training session tables.
"""
from collections import defaultdict
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workout import WorkoutSession, WorkoutExercise, WorkoutSet, WorkoutState
from app.models.training_session import (
    TrainingSession, SupersetRound, RoundEntry, EntrySet, SessionState,
)


def _legacy_base(user_id: int):
    """Select (exercise_id, completed_at) pairs from completed legacy workouts."""
    return (
        select(WorkoutExercise.exercise_id, WorkoutSession.completed_at)
        .join(WorkoutSession, WorkoutSession.id == WorkoutExercise.workout_session_id)
        .where(WorkoutSession.user_id == user_id, WorkoutSession.state == WorkoutState.COMPLETED)
    )


def _new_base(user_id: int):
    """Select (exercise_id, completed_at) pairs from completed training sessions."""
    return (
        select(RoundEntry.exercise_id, TrainingSession.completed_at)
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
        for exercise_id, completed_at in rows:
            if completed_at is None:
                continue
            if exercise_ids is not None and exercise_id not in exercise_ids:
                continue
            if exercise_id not in result or completed_at > result[exercise_id]:
                result[exercise_id] = completed_at
    return result


async def times_performed_map(db: AsyncSession, user_id: int) -> dict[int, int]:
    """Count of completed sessions in which each exercise appears, across both histories."""
    counts: dict[int, int] = defaultdict(int)
    for base in (_legacy_base(user_id), _new_base(user_id)):
        rows = (await db.execute(base)).all()
        for exercise_id, _completed_at in rows:
            counts[exercise_id] += 1
    return dict(counts)


async def exercise_set_history(
    db: AsyncSession, user_id: int, exercise_id: int, limit_sessions: int = 5
) -> list[dict]:
    """Per-session set history for one exercise, newest first.

    Returns: [{"performed_at": datetime, "sets": [(weight, reps), ...]}]
    """
    performances: list[dict] = []

    legacy_rows = (
        await db.execute(
            select(WorkoutSession.completed_at, WorkoutSet.weight, WorkoutSet.reps, WorkoutSet.set_number)
            .join(WorkoutExercise, WorkoutExercise.workout_session_id == WorkoutSession.id)
            .join(WorkoutSet, WorkoutSet.workout_exercise_id == WorkoutExercise.id)
            .where(
                WorkoutSession.user_id == user_id,
                WorkoutSession.state == WorkoutState.COMPLETED,
                WorkoutExercise.exercise_id == exercise_id,
            )
        )
    ).all()
    new_rows = (
        await db.execute(
            select(TrainingSession.completed_at, EntrySet.weight, EntrySet.reps, EntrySet.set_number)
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
    ).all()

    by_session: dict[datetime, list[tuple]] = defaultdict(list)
    for completed_at, weight, reps, set_number in list(legacy_rows) + list(new_rows):
        if completed_at is None:
            continue
        by_session[completed_at].append((set_number, weight, reps))

    for completed_at in sorted(by_session.keys(), reverse=True)[:limit_sessions]:
        ordered = sorted(by_session[completed_at], key=lambda t: t[0])
        performances.append({
            "performed_at": completed_at,
            "sets": [(weight, reps) for _n, weight, reps in ordered],
        })
    return performances

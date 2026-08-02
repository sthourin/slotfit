"""
Derive initial staple pools from workout history.

Any exercise performed in 3+ completed sessions (legacy workouts or new
training sessions) becomes a staple in its mapped pattern.

Run from backend/: python -m scripts.backfill_staples
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models import User, StapleExercise, ExercisePatternMap
from app.services.history_service import times_performed_map

STAPLE_THRESHOLD = 3


async def backfill_user(db: AsyncSession, user: User) -> int:
    """Create staple rows for one user's frequently-performed exercises.

    Counts distinct completed sessions per exercise (legacy + new history,
    via times_performed_map), then for every exercise at or above
    STAPLE_THRESHOLD that is not already a staple for this user and has a
    row in ExercisePatternMap, inserts a new StapleExercise. Exercises
    already staple, or with no pattern mapping, are skipped without error.
    Additive only: never updates or deletes existing rows.

    Returns the number of new staples created for this user.
    """
    counts = await times_performed_map(db, user.id)
    candidates = [ex_id for ex_id, n in counts.items() if n >= STAPLE_THRESHOLD]
    if not candidates:
        return 0

    existing = {
        row[0]
        for row in (
            await db.execute(
                select(StapleExercise.exercise_id).where(
                    StapleExercise.user_id == user.id
                )
            )
        ).all()
    }
    mappings = {
        m.exercise_id: m.pattern_id
        for m in (
            await db.execute(
                select(ExercisePatternMap).where(
                    ExercisePatternMap.exercise_id.in_(candidates)
                )
            )
        )
        .scalars()
        .all()
    }

    created = 0
    for exercise_id in candidates:
        if exercise_id in existing or exercise_id not in mappings:
            continue
        db.add(
            StapleExercise(
                user_id=user.id,
                pattern_id=mappings[exercise_id],
                exercise_id=exercise_id,
            )
        )
        created += 1
    await db.commit()
    return created


async def main() -> None:
    """Backfill staples for every user in the database and print a per-user count.

    Idempotent: exercises already recorded as staples are skipped, so
    re-running this script after a successful run creates 0 new staples.
    """
    async with AsyncSessionLocal() as db:
        users = (await db.execute(select(User))).scalars().all()
        for user in users:
            created = await backfill_user(db, user)
            print(f"user {user.id} ({user.device_id}): {created} staples created")


if __name__ == "__main__":
    asyncio.run(main())

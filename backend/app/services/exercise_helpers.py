"""Shared exercise predicates.

Bodyweight identity lives here rather than being open-coded, because it is
load-bearing in two unrelated places (equipment filtering and progression) and
was wrong in both: the catalogue represents bodyweight as an equipment row
named "Bodyweight", not as a NULL primary_equipment_id, so a NULL check was
never true for any of the 209 bodyweight exercises.

The row's id is resolved by name at call time rather than hardcoded. Equipment
ids are assigned by whatever seeded the table, so a literal id is correct only
by accident - in the test fixtures, for instance, id 2 is "Dumbbell".
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.equipment import Equipment
from app.models.exercise import Exercise

BODYWEIGHT_EQUIPMENT_NAME = "Bodyweight"


async def bodyweight_equipment_id(db: AsyncSession) -> int | None:
    """Id of the "Bodyweight" equipment row, or None if the table has no such row.

    Callers resolve this once per request and pass it into `is_bodyweight`,
    which keeps that predicate pure and avoids a lazy relationship load on an
    async session.
    """
    return (
        await db.execute(
            select(Equipment.id).where(Equipment.name == BODYWEIGHT_EQUIPMENT_NAME)
        )
    ).scalar_one_or_none()


def is_bodyweight(exercise: Exercise, bodyweight_id: int | None = None) -> bool:
    """True when an exercise carries no external load by default.

    NULL equipment counts as bodyweight so a hand-created exercise that omits
    equipment is not silently treated as loaded. `bodyweight_id` should come
    from `bodyweight_equipment_id`; when it is None the predicate falls back to
    the NULL check alone, which is the correct answer for a database that has
    no Bodyweight row at all.
    """
    if exercise.primary_equipment_id is None:
        return True
    if bodyweight_id is None:
        return False
    return exercise.primary_equipment_id == bodyweight_id

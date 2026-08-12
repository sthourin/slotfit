"""Bodyweight resolution and effective load.

A bodyweight set's load is a function of when it happened, because bodyweight
is a time series. Callers scoring many sets should fetch the timeline once with
`bodyweight_timeline` and use `resolve_bodyweight`, rather than issuing a query
per set.
"""
from bisect import bisect_right
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bodyweight_reading import BodyweightReading
from app.models.exercise import Exercise
from app.services.exercise_helpers import is_bodyweight
from app.services.leverage import fraction_for


async def bodyweight_timeline(
    db: AsyncSession, user_id: int
) -> list[tuple[datetime, float]]:
    """All of a user's readings, oldest first."""
    rows = (
        await db.execute(
            select(BodyweightReading.recorded_at, BodyweightReading.weight)
            .where(BodyweightReading.user_id == user_id)
            .order_by(BodyweightReading.recorded_at)
        )
    ).all()
    return [(recorded_at, weight) for recorded_at, weight in rows]


def resolve_bodyweight(
    timeline: list[tuple[datetime, float]], when: datetime
) -> float | None:
    """The reading in effect at `when`.

    Falls back to the earliest reading for sets that predate the first weigh-in:
    those sets still happened at some bodyweight, and the nearest known value is
    a better estimate than discarding them.
    """
    if not timeline:
        return None
    index = bisect_right([recorded_at for recorded_at, _w in timeline], when)
    if index == 0:
        return timeline[0][1]
    return timeline[index - 1][1]


async def bodyweight_at(
    db: AsyncSession, user_id: int, when: datetime
) -> float | None:
    """Convenience single lookup. Prefer the timeline for bulk work."""
    return resolve_bodyweight(await bodyweight_timeline(db, user_id), when)


def effective_load(
    exercise: Exercise,
    logged_weight: float | None,
    bodyweight: float | None,
    bodyweight_id: int | None = None,
) -> float | None:
    """Total load moved by one set.

    Loaded exercises: the logged weight, unchanged. Bodyweight exercises: the
    leverage-scaled bodyweight plus any external load, because a weighted vest
    adds to what you already carry rather than replacing it.

    Returns None for bodyweight work with no reading to resolve against -
    scoring nothing is preferable to inventing a bodyweight. Loaded work needs
    no reading at all.
    """
    if not is_bodyweight(exercise, bodyweight_id):
        return logged_weight
    if bodyweight is None:
        return None
    fraction = fraction_for(exercise.name, exercise.bodyweight_fraction)
    return bodyweight * fraction + (logged_weight or 0.0)

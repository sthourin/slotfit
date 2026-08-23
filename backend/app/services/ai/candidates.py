"""The exercise set a recommendation may draw from, and enforcement of it.

An AI provider must be handed the catalogue it is allowed to pick from, and its
answer must be checked against that catalogue. Skipping either half produced
confident fabrication: asked for Chest with dumbbells available, the model
returned "Dumbbell Lateral Raise" at exercise_id 1101 - a real id belonging to
Bar Pull Up - along with two more inventions. Nothing in the response looked
wrong, and the UI would have shown one exercise and logged another.

The id is treated as the only thing the model chose. Names are read back from
the database, never from the response, so a mismatched pair cannot survive.
"""
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.exercise import Exercise, exercise_muscle_groups
from app.models.muscle_group import MuscleGroup
from app.services.ai.prompting import RecommendationPayload
from app.services.exercise_helpers import bodyweight_equipment_id, is_bodyweight

logger = get_logger(__name__)


async def fetch_candidates(
    db: AsyncSession,
    muscle_group_ids: List[int],
    available_equipment_ids: List[int],
) -> Tuple[List[Dict[str, Any]], Dict[int, Exercise]]:
    """Exercises targeting these muscle groups that the user can actually do.

    Returns (rows for the prompt, exercise-by-id for validation).

    Bodyweight movements are always included regardless of the equipment
    profile, per the catalogue-wide rule - they need no equipment, so filtering
    them out would hide the exercises that are always available.
    """
    query = select(Exercise).options(
        selectinload(Exercise.primary_equipment),
        selectinload(Exercise.muscle_groups),
    )
    if muscle_group_ids:
        query = (
            query.join(
                exercise_muscle_groups,
                Exercise.id == exercise_muscle_groups.c.exercise_id,
            )
            .where(exercise_muscle_groups.c.muscle_group_id.in_(muscle_group_ids))
            .distinct()
        )

    exercises = (await db.execute(query)).scalars().unique().all()
    bodyweight_id = await bodyweight_equipment_id(db)

    rows: List[Dict[str, Any]] = []
    by_id: Dict[int, Exercise] = {}
    for exercise in exercises:
        usable = (
            is_bodyweight(exercise, bodyweight_id)
            or not available_equipment_ids
            or exercise.primary_equipment_id in available_equipment_ids
        )
        if not usable:
            continue
        by_id[exercise.id] = exercise
        rows.append(
            {
                "id": exercise.id,
                "name": exercise.name,
                "equipment": (
                    exercise.primary_equipment.name
                    if exercise.primary_equipment
                    else None
                ),
                "mechanics": exercise.mechanics,
            }
        )

    rows.sort(key=lambda row: row["name"])
    return rows, by_id


async def muscle_group_names(
    db: AsyncSession, muscle_group_ids: List[int]
) -> Dict[int, str]:
    """id -> name, so the prompt can say "Chest" instead of "17"."""
    if not muscle_group_ids:
        return {}
    return dict(
        (
            await db.execute(
                select(MuscleGroup.id, MuscleGroup.name).where(
                    MuscleGroup.id.in_(muscle_group_ids)
                )
            )
        ).all()
    )


def ground_payload(
    payload: RecommendationPayload, by_id: Dict[int, Exercise], provider: str
) -> RecommendationPayload:
    """Drop entries that name an exercise outside the candidate set.

    Anything surviving has its name replaced with the database's, because the id
    is the choice and the name is only the model's label for it. A dropped entry
    is logged with its claimed name: silent filtering here would read as "the AI
    only returned two suggestions" with no way to find out why.
    """
    kept = []
    for item in payload.recommendations:
        exercise = by_id.get(item.exercise_id)
        if exercise is None:
            logger.warning(
                "%s recommended exercise_id=%s (%r), which is not a candidate - dropping",
                provider, item.exercise_id, item.exercise_name,
            )
            continue
        if exercise.name != item.exercise_name:
            logger.info(
                "%s labelled exercise_id=%s as %r; it is %r - using the database name",
                provider, item.exercise_id, item.exercise_name, exercise.name,
            )
        kept.append(item.model_copy(update={"exercise_name": exercise.name}))

    kept_not = []
    for item in payload.not_recommended:
        exercise = by_id.get(item.exercise_id)
        if exercise is None:
            # A "why not" entry for an exercise that was never a candidate
            # explains nothing - it was not on the table to begin with.
            continue
        kept_not.append(item.model_copy(update={"exercise_name": exercise.name}))

    return payload.model_copy(
        update={"recommendations": kept, "not_recommended": kept_not}
    )

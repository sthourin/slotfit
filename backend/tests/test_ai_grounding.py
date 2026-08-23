"""Recommendations must name exercises that exist and match their ids.

Before grounding, a request for Chest with dumbbells available came back with
"Dumbbell Lateral Raise" at exercise_id 1101 - a real id belonging to
Bar Pull Up - plus two more inventions. Nothing in the response looked wrong.
The UI would have displayed one exercise and logged another.
"""
import pytest

from app.models import Equipment, Exercise, MuscleGroup, User
from app.models.exercise import exercise_muscle_groups
from app.services.ai.candidates import (
    fetch_candidates,
    ground_payload,
    muscle_group_names,
)
from app.services.ai.prompting import (
    MAX_CANDIDATES,
    RecommendationPayload,
    build_context,
    create_prompt,
    format_candidates,
)

from sqlalchemy import insert


async def _catalogue(db):
    """Two chest exercises - one dumbbell, one bodyweight - and one back."""
    chest = MuscleGroup(name="Chest", level=1)
    back = MuscleGroup(name="Back", level=1)
    dumbbell = Equipment(name="Dumbbell")
    barbell = Equipment(name="Barbell")
    bodyweight = Equipment(name="Bodyweight")
    user = User(device_id="ai-ground-0001")
    db.add_all([chest, back, dumbbell, barbell, bodyweight, user])
    await db.flush()

    db_press = Exercise(
        name="Dumbbell Bench Press", mechanics="Compound",
        primary_equipment_id=dumbbell.id,
    )
    push_up = Exercise(
        name="Bodyweight Push Up", mechanics="Compound",
        primary_equipment_id=bodyweight.id,
    )
    bb_press = Exercise(
        name="Barbell Bench Press", mechanics="Compound",
        primary_equipment_id=barbell.id,
    )
    row = Exercise(
        name="Dumbbell Row", mechanics="Compound", primary_equipment_id=dumbbell.id
    )
    db.add_all([db_press, push_up, bb_press, row])
    await db.flush()
    for exercise, group in (
        (db_press, chest), (push_up, chest), (bb_press, chest), (row, back)
    ):
        await db.execute(
            insert(exercise_muscle_groups).values(
                exercise_id=exercise.id, muscle_group_id=group.id, role="target"
            )
        )
    await db.commit()
    return {
        "user": user, "chest": chest, "back": back, "dumbbell": dumbbell,
        "db_press": db_press, "push_up": push_up, "bb_press": bb_press, "row": row,
    }


@pytest.mark.asyncio
async def test_candidates_filter_by_muscle_group_and_equipment(test_db):
    c = await _catalogue(test_db)
    rows, by_id = await fetch_candidates(
        test_db, [c["chest"].id], [c["dumbbell"].id]
    )

    names = {row["name"] for row in rows}
    # Barbell bench is chest, but the barbell is not available.
    assert names == {"Dumbbell Bench Press", "Bodyweight Push Up"}
    # The back exercise never enters, whatever the equipment.
    assert "Dumbbell Row" not in names
    assert set(by_id) == {c["db_press"].id, c["push_up"].id}


@pytest.mark.asyncio
async def test_bodyweight_candidates_survive_an_empty_equipment_profile(test_db):
    """Bodyweight work needs no equipment, so it is always available."""
    c = await _catalogue(test_db)
    rows, _ = await fetch_candidates(test_db, [c["chest"].id], [999])
    assert {row["name"] for row in rows} == {"Bodyweight Push Up"}


@pytest.mark.asyncio
async def test_muscle_group_names_resolve(test_db):
    c = await _catalogue(test_db)
    assert await muscle_group_names(test_db, [c["chest"].id]) == {
        c["chest"].id: "Chest"
    }


@pytest.mark.asyncio
async def test_ground_payload_drops_exercises_outside_the_candidate_set(test_db):
    """The exact failure that motivated grounding."""
    c = await _catalogue(test_db)
    _rows, by_id = await fetch_candidates(test_db, [c["chest"].id], [c["dumbbell"].id])

    payload = RecommendationPayload.model_validate({
        "recommendations": [
            {"exercise_id": c["db_press"].id, "exercise_name": "Dumbbell Bench Press",
             "priority_score": 0.9, "reasoning": "real", "factors": {}},
            {"exercise_id": 999999, "exercise_name": "Dumbbell Lateral Raise",
             "priority_score": 0.8, "reasoning": "invented", "factors": {}},
        ],
        "not_recommended": [
            {"exercise_id": 999999, "exercise_name": "Invented", "reason": "nope"},
        ],
        "total_candidates": 2,
        "filtered_by_equipment": 0,
    })

    grounded = ground_payload(payload, by_id, "test")
    assert [r.exercise_id for r in grounded.recommendations] == [c["db_press"].id]
    # A "why not" for something that was never a candidate explains nothing.
    assert grounded.not_recommended == []


@pytest.mark.asyncio
async def test_ground_payload_overwrites_a_mislabelled_name(test_db):
    """The id is the choice; the name is only the model's label for it.

    This is the case that made the old output so hard to catch - a real id
    wearing another exercise's name.
    """
    c = await _catalogue(test_db)
    _rows, by_id = await fetch_candidates(test_db, [c["chest"].id], [c["dumbbell"].id])

    payload = RecommendationPayload.model_validate({
        "recommendations": [
            {"exercise_id": c["push_up"].id, "exercise_name": "Dumbbell Lateral Raise",
             "priority_score": 0.9, "reasoning": "mislabelled", "factors": {}},
        ],
        "total_candidates": 2,
        "filtered_by_equipment": 0,
    })

    grounded = ground_payload(payload, by_id, "test")
    assert grounded.recommendations[0].exercise_name == "Bodyweight Push Up"
    assert grounded.recommendations[0].exercise_id == c["push_up"].id


def test_prompt_names_muscle_groups_and_lists_candidates():
    """A prompt of bare ids is what let the model invent freely."""
    context = build_context(
        [17], [2], None, None, None, None,
        candidates=[{"id": 101, "name": "Dumbbell Bench Press",
                     "equipment": "Dumbbell", "mechanics": "Compound"}],
        muscle_group_names={17: "Chest"},
    )
    prompt = create_prompt(context, 3)
    assert "Chest (id 17)" in prompt
    assert "101 | Dumbbell Bench Press | Dumbbell | Compound" in prompt
    assert "MUST choose only from this list" in prompt


def test_candidate_truncation_is_announced_not_silent():
    """A silently clipped list reads as "the AI never suggests X"."""
    rows = [
        {"id": i, "name": f"Exercise {i}", "equipment": "Dumbbell",
         "mechanics": "Compound"}
        for i in range(MAX_CANDIDATES + 25)
    ]
    rendered = format_candidates(rows)
    assert "25 further candidates omitted" in rendered


def test_json_shape_is_only_spelled_out_when_asked_for():
    """Providers with a schema should not also get a prose description of it.

    Providers without one depend on it entirely, so it must still be available -
    removing it outright broke the Gemini path.
    """
    context = build_context([17], [2], None, None, None, None)
    assert "exact structure" not in create_prompt(context, 3)
    assert "exact structure" in create_prompt(context, 3, include_json_shape=True)

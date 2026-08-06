"""Tests for set protocols (AMRAP / EMOM) - app/models/exercise.py."""

import pytest

from app.models.exercise import SetProtocol, protocol_for_variant_type


def test_protocol_values_are_the_four_agreed_strings():
    assert {p.value for p in SetProtocol} == {"reps", "time", "amrap", "emom"}


@pytest.mark.parametrize(
    "variant_type,expected",
    [
        ("AMRAP", SetProtocol.AMRAP),
        ("EMOM", SetProtocol.EMOM),
        ("HIIT AMRAP", SetProtocol.AMRAP),
        ("HIIT EMOM", SetProtocol.EMOM),
    ],
)
def test_labels_infer_their_protocol(variant_type, expected):
    assert protocol_for_variant_type(variant_type) is expected


def test_inference_is_case_insensitive():
    # variant_type is free text; a lowercase label must not change behaviour.
    assert protocol_for_variant_type("hiit amrap") is SetProtocol.AMRAP
    assert protocol_for_variant_type("HiIt eMoM") is SetProtocol.EMOM


def test_inference_tolerates_extra_whitespace():
    assert protocol_for_variant_type("  HIIT   AMRAP  ") is SetProtocol.AMRAP


def test_bare_hiit_does_not_imply_amrap():
    """Intent without a stated protocol is not a protocol.

    An earlier draft mapped HIIT to AMRAP, which buried a guess about one
    person's training in the code. Compound labels make the guess unnecessary.
    """
    assert protocol_for_variant_type("HIIT") is SetProtocol.REPS


@pytest.mark.parametrize("variant_type", ["Strength", "Volume", "Endurance", "", None])
def test_non_protocol_variant_types_fall_back_to_reps(variant_type):
    assert protocol_for_variant_type(variant_type) is SetProtocol.REPS


from sqlalchemy import select

from app.models import (
    EntrySet,
    Exercise,
    RoundEntry,
    SupersetRound,
    TrainingSession,
    User,
)
from app.models.exercise import SetProtocol as SP
from app.services.pattern_taxonomy import (
    seed_movement_patterns,
    seed_exercise_pattern_map,
)


async def _session_with_exercise(test_db, protocol):
    """Seed one user, one exercise with the given protocol, and an open round."""
    await seed_movement_patterns(test_db)
    user = User(device_id="protocol-device-01")
    exercise = Exercise(
        name="Kettlebell Swing (HIIT AMRAP)",
        movement_pattern_1="Hip Hinge",
        mechanics="Compound",
        set_protocol=protocol,
    )
    test_db.add_all([user, exercise])
    await test_db.flush()
    await seed_exercise_pattern_map(test_db)
    session = TrainingSession(user_id=user.id)
    test_db.add(session)
    await test_db.flush()
    rnd = SupersetRound(session_id=session.id, order=1)
    test_db.add(rnd)
    await test_db.flush()
    return user, exercise, rnd


async def test_round_entry_defaults_to_reps(test_db):
    _user, exercise, rnd = await _session_with_exercise(test_db, SP.REPS)
    entry = RoundEntry(round_id=rnd.id, position=1, exercise_id=exercise.id, pattern_id=1)
    test_db.add(entry)
    await test_db.flush()
    assert entry.set_protocol == SP.REPS


async def test_round_entry_can_carry_a_protocol(test_db):
    _user, exercise, rnd = await _session_with_exercise(test_db, SP.AMRAP)
    entry = RoundEntry(
        round_id=rnd.id, position=1, exercise_id=exercise.id, pattern_id=1,
        set_protocol=exercise.set_protocol,
    )
    test_db.add(entry)
    await test_db.flush()
    assert entry.set_protocol == SP.AMRAP


async def test_reclassifying_the_exercise_does_not_rewrite_the_entry(test_db):
    """The denormalization guarantee, matching RoundEntry.pattern_id's contract."""
    _user, exercise, rnd = await _session_with_exercise(test_db, SP.AMRAP)
    entry = RoundEntry(
        round_id=rnd.id, position=1, exercise_id=exercise.id, pattern_id=1,
        set_protocol=exercise.set_protocol,
    )
    test_db.add(entry)
    await test_db.flush()

    exercise.set_protocol = SP.EMOM
    await test_db.flush()

    refreshed = (
        await test_db.execute(select(RoundEntry).where(RoundEntry.id == entry.id))
    ).scalar_one()
    assert refreshed.set_protocol == SP.AMRAP


async def test_a_set_outside_its_protocol_is_still_accepted(test_db):
    """Deliberate: mid-workout, a rejected set loses the rep entirely.

    An EMOM entry has no time field in the UI, but a time value arriving anyway
    must be stored rather than refused. Tighten only if loose proves wrong.
    """
    _user, exercise, rnd = await _session_with_exercise(test_db, SP.EMOM)
    entry = RoundEntry(
        round_id=rnd.id, position=1, exercise_id=exercise.id, pattern_id=1,
        set_protocol=exercise.set_protocol,
    )
    test_db.add(entry)
    await test_db.flush()

    test_db.add(EntrySet(entry_id=entry.id, set_number=1, weight=20, reps=8, time_seconds=60))
    await test_db.flush()

    stored = (
        await test_db.execute(select(EntrySet).where(EntrySet.entry_id == entry.id))
    ).scalar_one()
    assert stored.time_seconds == 60


from app.services.hevy_import import apply_map


async def _base_for_variant(test_db, device_id):
    await seed_movement_patterns(test_db)
    user = User(device_id=device_id)
    base = Exercise(
        name="Kettlebell Swing", movement_pattern_1="Hip Hinge", mechanics="Compound"
    )
    test_db.add_all([user, base])
    await test_db.flush()
    await seed_exercise_pattern_map(test_db)
    return user


async def test_hevy_variant_creation_infers_amrap_from_a_compound_label(test_db):
    user = await _base_for_variant(test_db, "protocol-device-02")
    doc = {"exercises": [{
        "hevy": "HIIT KB Swings", "slotfit": None, "candidates": [],
        "create": {"variant_of": "Kettlebell Swing", "variant_type": "HIIT AMRAP",
                   "default_time_seconds": 40},
    }]}
    await apply_map(test_db, doc, user)

    variant = (
        await test_db.execute(
            select(Exercise).where(Exercise.name == "Kettlebell Swing (HIIT AMRAP)")
        )
    ).scalar_one()
    assert variant.set_protocol == SP.AMRAP


async def test_hevy_variant_with_bare_hiit_stays_on_reps(test_db):
    """Guards the removed guess: intent alone must not pick a protocol."""
    user = await _base_for_variant(test_db, "protocol-device-05")
    doc = {"exercises": [{
        "hevy": "HIIT KB Swings", "slotfit": None, "candidates": [],
        "create": {"variant_of": "Kettlebell Swing", "variant_type": "HIIT"},
    }]}
    await apply_map(test_db, doc, user)

    variant = (
        await test_db.execute(
            select(Exercise).where(Exercise.name == "Kettlebell Swing (HIIT)")
        )
    ).scalar_one()
    assert variant.set_protocol == SP.REPS


async def test_hevy_variant_creation_infers_emom(test_db):
    user = await _base_for_variant(test_db, "protocol-device-03")
    doc = {"exercises": [{
        "hevy": "EMOM KB Swings", "slotfit": None, "candidates": [],
        "create": {"variant_of": "Kettlebell Swing", "variant_type": "HIIT EMOM"},
    }]}
    await apply_map(test_db, doc, user)

    variant = (
        await test_db.execute(
            select(Exercise).where(Exercise.name == "Kettlebell Swing (HIIT EMOM)")
        )
    ).scalar_one()
    assert variant.set_protocol == SP.EMOM


async def test_hevy_plain_create_stays_on_reps(test_db):
    await seed_movement_patterns(test_db)
    user = User(device_id="protocol-device-04")
    test_db.add(user)
    await test_db.flush()

    doc = {"exercises": [{
        "hevy": "Leg Press (Machine)", "slotfit": None, "candidates": [],
        "create": {"name": "Leg Press (Machine)", "pattern": "knee_dominant"},
    }]}
    await apply_map(test_db, doc, user)

    created = (
        await test_db.execute(
            select(Exercise).where(Exercise.name == "Leg Press (Machine)")
        )
    ).scalar_one()
    assert created.set_protocol == SP.REPS

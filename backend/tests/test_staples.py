"""Tests for staple exercises and exercise preferences"""
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import StapleExercise, ExercisePreference, MovementPattern, Exercise, User
from app.services.pattern_taxonomy import seed_movement_patterns


@pytest.mark.asyncio
async def test_staple_unique_per_user_exercise(test_db):
    await seed_movement_patterns(test_db)
    user = User(device_id="test-device-12345")
    ex = Exercise(name="Pull Up", movement_pattern_1="Vertical Pull", mechanics="Compound")
    test_db.add_all([user, ex])
    await test_db.flush()
    result = await test_db.execute(select(MovementPattern).where(MovementPattern.slug == "vertical_pull"))
    vp = result.scalar_one()

    test_db.add(StapleExercise(user_id=user.id, pattern_id=vp.id, exercise_id=ex.id))
    await test_db.commit()

    test_db.add(StapleExercise(user_id=user.id, pattern_id=vp.id, exercise_id=ex.id))
    with pytest.raises(IntegrityError):
        await test_db.commit()
    await test_db.rollback()


@pytest.mark.asyncio
async def test_preference_blacklist(test_db):
    user = User(device_id="test-device-12345")
    ex = Exercise(name="Barbell Bench Press", movement_pattern_1="Horizontal Push", mechanics="Compound")
    test_db.add_all([user, ex])
    await test_db.flush()

    test_db.add(ExercisePreference(user_id=user.id, exercise_id=ex.id, preference="never"))
    await test_db.commit()

    result = await test_db.execute(select(ExercisePreference).where(ExercisePreference.user_id == user.id))
    prefs = result.scalars().all()
    assert len(prefs) == 1
    assert prefs[0].preference == "never"

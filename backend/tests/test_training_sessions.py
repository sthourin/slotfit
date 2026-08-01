"""Tests for TrainingSession models and API"""
import pytest
from datetime import datetime
from sqlalchemy import select

from app.models import (
    TrainingSession, SupersetRound, RoundEntry, EntrySet,
    SessionState, MovementPattern, Exercise, User,
)
from app.services.pattern_taxonomy import seed_movement_patterns


@pytest.mark.asyncio
async def test_session_round_entry_set_hierarchy(test_db):
    await seed_movement_patterns(test_db)
    user = User(device_id="test-device-12345")
    ex = Exercise(name="Seated Cable Row", movement_pattern_1="Horizontal Pull", mechanics="Compound")
    test_db.add_all([user, ex])
    await test_db.flush()

    result = await test_db.execute(select(MovementPattern).where(MovementPattern.slug == "horizontal_pull"))
    hp = result.scalar_one()

    session = TrainingSession(user_id=user.id, state=SessionState.ACTIVE, started_at=datetime.utcnow())
    round1 = SupersetRound(order=1)
    entry = RoundEntry(position=1, exercise_id=ex.id, pattern_id=hp.id)
    entry.sets.append(EntrySet(set_number=1, weight=120.0, reps=10))
    round1.entries.append(entry)
    session.rounds.append(round1)
    test_db.add(session)
    await test_db.commit()

    result = await test_db.execute(select(TrainingSession).where(TrainingSession.user_id == user.id))
    loaded = result.scalar_one()
    assert loaded.state == SessionState.ACTIVE
    sets = (await test_db.execute(select(EntrySet))).scalars().all()
    assert len(sets) == 1
    assert sets[0].weight == 120.0
    assert sets[0].completed is True

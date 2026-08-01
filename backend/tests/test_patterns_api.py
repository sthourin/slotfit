"""Tests for the patterns API"""

import pytest
from sqlalchemy import select

from app.models import Exercise, MovementPattern, StapleExercise
from app.services.pattern_taxonomy import seed_movement_patterns


@pytest.mark.asyncio
async def test_list_patterns(client_with_data, device_id):
    client, _seed = client_with_data
    headers = {"X-Device-ID": device_id}
    # Seed taxonomy into the test DB via the app's session
    # (client_with_data shares test_db; seed through an endpoint-independent path)
    response = await client.get("/api/v1/patterns/", headers=headers)
    assert response.status_code == 200
    slugs = [p["slug"] for p in response.json()]
    assert "horizontal_pull" in slugs
    assert len(slugs) == 10
    assert (
        slugs[0] == "horizontal_pull"
    )  # display_order 1 - catches ordering regressions


@pytest.mark.asyncio
async def test_pattern_progress_empty(client_with_data, device_id):
    client, _seed = client_with_data
    headers = {"X-Device-ID": device_id}
    await client.get("/api/v1/users/me", headers=headers)
    response = await client.get("/api/v1/patterns/progress?weeks=12", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body == []  # no staples at all for this user -> no pattern entries


@pytest.mark.asyncio
async def test_pattern_progress_excludes_inactive_staples(
    client_with_data, seeded_db, device_id
):
    """A pattern whose only staple is inactive must not appear in /progress."""
    client, _seed = client_with_data
    test_db, _ = seeded_db
    headers = {"X-Device-ID": device_id}

    me_response = await client.get("/api/v1/users/me", headers=headers)
    user_id = me_response.json()["id"]

    result = await test_db.execute(
        select(MovementPattern).where(MovementPattern.slug == "vertical_pull")
    )
    pattern = result.scalar_one()
    result = await test_db.execute(select(Exercise).where(Exercise.name == "Pull-up"))
    exercise = result.scalar_one()

    test_db.add(
        StapleExercise(
            user_id=user_id,
            pattern_id=pattern.id,
            exercise_id=exercise.id,
            is_active=False,
        )
    )
    await test_db.commit()

    response = await client.get("/api/v1/patterns/progress?weeks=12", headers=headers)
    assert response.status_code == 200
    slugs = [p["slug"] for p in response.json()]
    assert "vertical_pull" not in slugs

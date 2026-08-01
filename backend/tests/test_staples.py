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


@pytest.mark.asyncio
async def test_staples_api_crud(client_with_data, device_id):
    """Test staples API CRUD operations"""
    client, seed = client_with_data
    headers = {"X-Device-ID": device_id}
    await client.get("/api/v1/users/me", headers=headers)

    exercises = (await client.get("/api/v1/exercises/?limit=1", headers=headers)).json()
    exercise = exercises["exercises"][0] if isinstance(exercises, dict) else exercises[0]

    created = await client.post("/api/v1/staples/", json={"exercise_id": exercise["id"]}, headers=headers)
    assert created.status_code == 201
    staple = created.json()
    assert staple["exercise_id"] == exercise["id"]
    assert staple["pattern_id"] > 0  # resolved server-side

    dup = await client.post("/api/v1/staples/", json={"exercise_id": exercise["id"]}, headers=headers)
    assert dup.status_code == 409

    listed = (await client.get("/api/v1/staples/", headers=headers)).json()
    assert any(s["id"] == staple["id"] for s in listed)

    toggled = await client.patch(f"/api/v1/staples/{staple['id']}", json={"is_active": False}, headers=headers)
    assert toggled.status_code == 200
    assert toggled.json()["is_active"] is False

    deleted = await client.delete(f"/api/v1/staples/{staple['id']}", headers=headers)
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_preferences_api(client_with_data, device_id):
    """Test exercise preferences API"""
    client, seed = client_with_data
    headers = {"X-Device-ID": device_id}
    await client.get("/api/v1/users/me", headers=headers)

    exercises = (await client.get("/api/v1/exercises/?limit=1", headers=headers)).json()
    exercise = exercises["exercises"][0] if isinstance(exercises, dict) else exercises[0]

    created = await client.post("/api/v1/staples/preferences",
                                json={"exercise_id": exercise["id"]}, headers=headers)
    assert created.status_code == 201
    pref = created.json()
    assert pref["preference"] == "never"

    listed = (await client.get("/api/v1/staples/preferences", headers=headers)).json()
    assert any(p["id"] == pref["id"] for p in listed)

    deleted = await client.delete(f"/api/v1/staples/preferences/{pref['id']}", headers=headers)
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_staples_preferences_route_ordering(client_with_data, device_id):
    """
    Regression test: /preferences must be declared before /{staple_id} routes.
    This test pins the route ordering — if /preferences matches /{staple_id} first,
    it will fail with 422 (invalid staple_id) instead of 200 with a list.
    """
    client, seed = client_with_data
    headers = {"X-Device-ID": device_id}
    await client.get("/api/v1/users/me", headers=headers)

    # GET /api/v1/staples/preferences must return 200, not 422
    response = await client.get("/api/v1/staples/preferences", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_staples_cross_user_isolation(client_with_data, device_id):
    """Test that a user cannot see or delete another user's staple"""
    client, seed = client_with_data
    headers_user1 = {"X-Device-ID": device_id}
    headers_user2 = {"X-Device-ID": "other-device-id"}

    # User 1 creates and authenticates
    await client.get("/api/v1/users/me", headers=headers_user1)

    exercises = (await client.get("/api/v1/exercises/?limit=1", headers=headers_user1)).json()
    exercise = exercises["exercises"][0] if isinstance(exercises, dict) else exercises[0]

    created = await client.post("/api/v1/staples/", json={"exercise_id": exercise["id"]}, headers=headers_user1)
    assert created.status_code == 201
    staple_id = created.json()["id"]

    # User 2 authenticates
    await client.get("/api/v1/users/me", headers=headers_user2)

    # User 2 attempts to patch user 1's staple
    patch_response = await client.patch(f"/api/v1/staples/{staple_id}", json={"is_active": False}, headers=headers_user2)
    assert patch_response.status_code == 404

    # User 2 attempts to delete user 1's staple
    delete_response = await client.delete(f"/api/v1/staples/{staple_id}", headers=headers_user2)
    assert delete_response.status_code == 404

    # User 1 can still see their own staple
    listed = (await client.get("/api/v1/staples/", headers=headers_user1)).json()
    assert any(s["id"] == staple_id for s in listed)

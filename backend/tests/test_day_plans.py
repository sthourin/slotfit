"""Tests for DayPlan models and API"""
import pytest
from sqlalchemy import select

from app.models import DayPlan, PatternGoal, MovementPattern, User
from app.services.pattern_taxonomy import seed_movement_patterns


@pytest.mark.asyncio
async def test_day_plan_with_goals(test_db):
    await seed_movement_patterns(test_db)
    user = User(device_id="test-device-12345")
    test_db.add(user)
    await test_db.flush()

    result = await test_db.execute(select(MovementPattern).where(MovementPattern.slug == "horizontal_pull"))
    hp = result.scalar_one()

    plan = DayPlan(
        user_id=user.id,
        name="Full Body A",
        warmup_preferences=[101, 102],
        rounds_target=3,
    )
    plan.goals.append(PatternGoal(pattern_id=hp.id, required=True, target_sets=6))
    test_db.add(plan)
    await test_db.commit()

    result = await test_db.execute(select(DayPlan).where(DayPlan.name == "Full Body A"))
    loaded = result.scalar_one()
    assert loaded.rounds_target == 3
    assert loaded.warmup_preferences == [101, 102]
    goals = (await test_db.execute(select(PatternGoal).where(PatternGoal.day_plan_id == loaded.id))).scalars().all()
    assert len(goals) == 1
    assert goals[0].required is True
    assert goals[0].rep_range_min is None  # defaults applied at service layer (8-12)


@pytest.mark.asyncio
async def test_day_plan_crud_api(client_with_data, device_id):
    client, _seed = client_with_data
    headers = {"X-Device-ID": device_id}
    await client.get("/api/v1/users/me", headers=headers)

    patterns = (await client.get("/api/v1/patterns/", headers=headers)).json()
    hp = next(p for p in patterns if p["slug"] == "horizontal_pull")

    create = await client.post("/api/v1/day-plans/", json={
        "name": "Full Body A",
        "warmup_preferences": [],
        "rounds_target": 3,
        "goals": [{"pattern_id": hp["id"], "required": True, "target_sets": 6}],
    }, headers=headers)
    assert create.status_code == 201
    plan = create.json()
    assert plan["goals"][0]["pattern_id"] == hp["id"]

    listed = (await client.get("/api/v1/day-plans/", headers=headers)).json()
    assert any(p["id"] == plan["id"] for p in listed)

    updated = await client.put(f"/api/v1/day-plans/{plan['id']}", json={
        "rounds_target": 4,
        "goals": [{"pattern_id": hp["id"], "required": False}],
    }, headers=headers)
    assert updated.status_code == 200
    assert updated.json()["rounds_target"] == 4
    assert updated.json()["goals"][0]["required"] is False

    deleted = await client.delete(f"/api/v1/day-plans/{plan['id']}", headers=headers)
    assert deleted.status_code == 204
    assert (await client.get(f"/api/v1/day-plans/{plan['id']}", headers=headers)).status_code == 404


@pytest.mark.asyncio
async def test_put_replaces_goals(client_with_data, device_id, test_db):
    """Test that PUT with goals list replaces all goals via delete-orphan cascade"""
    client, _seed = client_with_data
    headers = {"X-Device-ID": device_id}
    await client.get("/api/v1/users/me", headers=headers)

    patterns = (await client.get("/api/v1/patterns/", headers=headers)).json()
    hp = next(p for p in patterns if p["slug"] == "horizontal_pull")
    vp = next(p for p in patterns if p["slug"] == "vertical_pull")

    # Create a plan with 2 goals
    create = await client.post("/api/v1/day-plans/", json={
        "name": "Test Replacement",
        "warmup_preferences": [],
        "rounds_target": 3,
        "goals": [
            {"pattern_id": hp["id"], "required": True, "target_sets": 6},
            {"pattern_id": vp["id"], "required": True, "target_sets": 4},
        ],
    }, headers=headers)
    plan_id = create.json()["id"]
    assert len(create.json()["goals"]) == 2

    # Verify both goals exist in DB
    goals_before = (
        await test_db.execute(
            select(PatternGoal).where(PatternGoal.day_plan_id == plan_id)
        )
    ).scalars().all()
    assert len(goals_before) == 2

    # PUT with only 1 goal (should remove the old one)
    updated = await client.put(f"/api/v1/day-plans/{plan_id}", json={
        "goals": [{"pattern_id": hp["id"], "required": False}],
    }, headers=headers)
    assert updated.status_code == 200
    assert len(updated.json()["goals"]) == 1
    assert updated.json()["goals"][0]["pattern_id"] == hp["id"]

    # Verify only 1 goal remains in DB (cascade delete works)
    goals_after = (
        await test_db.execute(
            select(PatternGoal).where(PatternGoal.day_plan_id == plan_id)
        )
    ).scalars().all()
    assert len(goals_after) == 1


@pytest.mark.asyncio
async def test_user_scoping(client_with_data, device_id):
    """Test that a different user (X-Device-ID) cannot access another user's plan"""
    client, _seed = client_with_data
    headers1 = {"X-Device-ID": device_id}
    headers2 = {"X-Device-ID": "different-device-id"}

    # Ensure both users exist
    await client.get("/api/v1/users/me", headers=headers1)
    await client.get("/api/v1/users/me", headers=headers2)

    # User 1 creates a plan
    patterns = (await client.get("/api/v1/patterns/", headers=headers1)).json()
    hp = next(p for p in patterns if p["slug"] == "horizontal_pull")

    create = await client.post("/api/v1/day-plans/", json={
        "name": "User 1 Plan",
        "warmup_preferences": [],
        "rounds_target": 3,
        "goals": [{"pattern_id": hp["id"], "required": True, "target_sets": 6}],
    }, headers=headers1)
    plan_id = create.json()["id"]

    # User 1 can see the plan in GET
    get_resp = await client.get(f"/api/v1/day-plans/{plan_id}", headers=headers1)
    assert get_resp.status_code == 200

    # User 1 can see the plan in LIST
    list_resp = await client.get("/api/v1/day-plans/", headers=headers1)
    assert list_resp.status_code == 200
    assert any(p["id"] == plan_id for p in list_resp.json())

    # User 2 gets 404 on GET
    get_resp = await client.get(f"/api/v1/day-plans/{plan_id}", headers=headers2)
    assert get_resp.status_code == 404

    # User 2 cannot see user 1's plan in LIST (should be empty)
    list_resp = await client.get("/api/v1/day-plans/", headers=headers2)
    assert list_resp.status_code == 200
    assert not any(p["id"] == plan_id for p in list_resp.json())

    # User 2 gets 404 on PUT
    put_resp = await client.put(f"/api/v1/day-plans/{plan_id}", json={
        "rounds_target": 4,
    }, headers=headers2)
    assert put_resp.status_code == 404

    # User 2 cannot delete user 1's plan
    delete_resp = await client.delete(f"/api/v1/day-plans/{plan_id}", headers=headers2)
    assert delete_resp.status_code == 404

    # User 1 can still see the plan (verify it wasn't deleted)
    get_resp = await client.get(f"/api/v1/day-plans/{plan_id}", headers=headers1)
    assert get_resp.status_code == 200


@pytest.mark.asyncio
async def test_delete_conflicts_when_a_session_references_the_plan(
    client_with_data, device_id
):
    """A plan a session was started from cannot be deleted: 409, not a 500.

    `training_sessions.day_plan_id` has no ON DELETE rule, so without the
    reference check the delete raises ForeignKeyViolation. The unused plan in
    the same test proves the check is not simply rejecting every delete.
    """
    client, _seed = client_with_data
    headers = {"X-Device-ID": device_id}
    await client.get("/api/v1/users/me", headers=headers)

    patterns = (await client.get("/api/v1/patterns/", headers=headers)).json()
    hp = next(p for p in patterns if p["slug"] == "horizontal_pull")
    body = {
        "warmup_preferences": [],
        "rounds_target": 3,
        "goals": [{"pattern_id": hp["id"], "required": True, "target_sets": 3}],
    }

    used = (
        await client.post(
            "/api/v1/day-plans/", json={**body, "name": "Used Plan"}, headers=headers
        )
    ).json()
    unused = (
        await client.post(
            "/api/v1/day-plans/", json={**body, "name": "Unused Plan"}, headers=headers
        )
    ).json()

    started = await client.post(
        "/api/v1/sessions/", json={"day_plan_id": used["id"]}, headers=headers
    )
    assert started.status_code == 201

    conflict = await client.delete(f"/api/v1/day-plans/{used['id']}", headers=headers)
    assert conflict.status_code == 409
    assert "session" in conflict.json()["detail"].lower()
    # Still listed: a refused delete must not half-apply.
    assert (
        await client.get(f"/api/v1/day-plans/{used['id']}", headers=headers)
    ).status_code == 200

    # An unreferenced plan still deletes cleanly.
    ok = await client.delete(f"/api/v1/day-plans/{unused['id']}", headers=headers)
    assert ok.status_code == 204
    assert (
        await client.get(f"/api/v1/day-plans/{unused['id']}", headers=headers)
    ).status_code == 404


@pytest.mark.asyncio
async def test_put_without_goals_preserves_goals(client_with_data, device_id):
    """Test that PUT without goals key leaves existing goals untouched"""
    client, _seed = client_with_data
    headers = {"X-Device-ID": device_id}
    await client.get("/api/v1/users/me", headers=headers)

    patterns = (await client.get("/api/v1/patterns/", headers=headers)).json()
    hp = next(p for p in patterns if p["slug"] == "horizontal_pull")
    vp = next(p for p in patterns if p["slug"] == "vertical_pull")

    # Create a plan with 2 goals
    create = await client.post("/api/v1/day-plans/", json={
        "name": "Test Goals Preservation",
        "warmup_preferences": [],
        "rounds_target": 3,
        "goals": [
            {"pattern_id": hp["id"], "required": True, "target_sets": 6},
            {"pattern_id": vp["id"], "required": False, "target_sets": 4},
        ],
    }, headers=headers)
    plan_id = create.json()["id"]
    original_goals = create.json()["goals"]
    assert len(original_goals) == 2

    # PUT with only rounds_target (no goals key) should preserve goals
    updated = await client.put(f"/api/v1/day-plans/{plan_id}", json={
        "rounds_target": 5,
    }, headers=headers)
    assert updated.status_code == 200
    assert updated.json()["rounds_target"] == 5
    # Goals should be unchanged
    updated_goals = updated.json()["goals"]
    assert len(updated_goals) == 2
    assert updated_goals[0]["pattern_id"] == hp["id"]
    assert updated_goals[1]["pattern_id"] == vp["id"]
    assert updated_goals[0]["required"] is True
    assert updated_goals[1]["required"] is False

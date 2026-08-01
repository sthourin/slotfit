"""Tests for TrainingSession models and API"""

import pytest
from datetime import datetime
from sqlalchemy import select

from app.models import (
    TrainingSession,
    SupersetRound,
    RoundEntry,
    EntrySet,
    SessionState,
    MovementPattern,
    Exercise,
    User,
)
from app.services.pattern_taxonomy import seed_movement_patterns


@pytest.mark.asyncio
async def test_session_round_entry_set_hierarchy(test_db):
    await seed_movement_patterns(test_db)
    user = User(device_id="test-device-12345")
    ex = Exercise(
        name="Seated Cable Row",
        movement_pattern_1="Horizontal Pull",
        mechanics="Compound",
    )
    test_db.add_all([user, ex])
    await test_db.flush()

    result = await test_db.execute(
        select(MovementPattern).where(MovementPattern.slug == "horizontal_pull")
    )
    hp = result.scalar_one()

    session = TrainingSession(
        user_id=user.id, state=SessionState.ACTIVE, started_at=datetime.utcnow()
    )
    round1 = SupersetRound(order=1)
    entry = RoundEntry(position=1, exercise_id=ex.id, pattern_id=hp.id)
    entry.sets.append(EntrySet(set_number=1, weight=120.0, reps=10))
    round1.entries.append(entry)
    session.rounds.append(round1)
    test_db.add(session)
    await test_db.commit()

    result = await test_db.execute(
        select(TrainingSession).where(TrainingSession.user_id == user.id)
    )
    loaded = result.scalar_one()
    assert loaded.state == SessionState.ACTIVE
    sets = (await test_db.execute(select(EntrySet))).scalars().all()
    assert len(sets) == 1
    assert sets[0].weight == 120.0
    assert sets[0].completed is True


@pytest.mark.asyncio
async def test_session_lifecycle_api(client_with_data, device_id):
    client, _seed = client_with_data
    headers = {"X-Device-ID": device_id}
    await client.get("/api/v1/users/me", headers=headers)

    patterns = (await client.get("/api/v1/patterns/", headers=headers)).json()
    hp = next(p for p in patterns if p["slug"] == "horizontal_pull")
    hpush = next(p for p in patterns if p["slug"] == "horizontal_push")

    plan = (
        await client.post(
            "/api/v1/day-plans/",
            json={
                "name": "Full Body A",
                "warmup_preferences": [],
                "rounds_target": 2,
                "goals": [
                    {"pattern_id": hp["id"], "required": True, "target_sets": 1},
                    {"pattern_id": hpush["id"], "required": True, "target_sets": 3},
                ],
            },
            headers=headers,
        )
    ).json()

    # Start session
    created = await client.post(
        "/api/v1/sessions/", json={"day_plan_id": plan["id"]}, headers=headers
    )
    assert created.status_code == 201
    session = created.json()
    assert session["state"] == "active"

    # Second active session is rejected
    assert (
        await client.post("/api/v1/sessions/", json={}, headers=headers)
    ).status_code == 409

    # Resume endpoint finds it
    active = await client.get("/api/v1/sessions/active", headers=headers)
    assert active.status_code == 200
    assert active.json()["id"] == session["id"]

    # Round -> entry -> set
    rnd = (
        await client.post(f"/api/v1/sessions/{session['id']}/rounds", headers=headers)
    ).json()
    assert rnd["order"] == 1

    exercises = (await client.get("/api/v1/exercises/?limit=1", headers=headers)).json()
    exercise = (
        exercises["exercises"][0] if isinstance(exercises, dict) else exercises[0]
    )

    entry_resp = await client.post(
        f"/api/v1/sessions/rounds/{rnd['id']}/entries",
        json={"exercise_id": exercise["id"], "position": 1},
        headers=headers,
    )
    assert entry_resp.status_code == 201
    entry = entry_resp.json()
    assert entry["pattern_id"] > 0  # denormalized server-side

    dup = await client.post(
        f"/api/v1/sessions/rounds/{rnd['id']}/entries",
        json={"exercise_id": exercise["id"], "position": 1},
        headers=headers,
    )
    assert dup.status_code == 409  # position taken

    set_resp = await client.post(
        f"/api/v1/sessions/entries/{entry['id']}/sets",
        json={"set_number": 1, "weight": 100, "reps": 10},
        headers=headers,
    )
    assert set_resp.status_code == 201

    # Coverage reflects the completed set
    coverage = (
        await client.get(f"/api/v1/sessions/{session['id']}/coverage", headers=headers)
    ).json()
    assert len(coverage["goals"]) == 2
    covered_by_pattern = {g["pattern_id"]: g for g in coverage["goals"]}
    entry_pattern = entry["pattern_id"]
    if entry_pattern in covered_by_pattern:
        goal = covered_by_pattern[entry_pattern]
        assert goal["sets_done"] >= 1

    # Complete
    done = await client.post(
        f"/api/v1/sessions/{session['id']}/complete", headers=headers
    )
    assert done.status_code == 200
    assert done.json()["state"] == "completed"
    assert (
        await client.get("/api/v1/sessions/active", headers=headers)
    ).status_code == 404


@pytest.mark.asyncio
async def test_active_route_ordering_regression(client_with_data, device_id):
    """Pin GET /sessions/active ahead of GET /sessions/{session_id}.

    Both are GET, single-segment paths. If /{session_id} were declared first,
    "active" would bind to the int path param and FastAPI would return 422
    instead of resolving the dedicated /active route.
    """
    client, _seed = client_with_data
    headers = {"X-Device-ID": device_id}
    await client.get("/api/v1/users/me", headers=headers)

    # No active session yet -> 404, never 422
    resp = await client.get("/api/v1/sessions/active", headers=headers)
    assert resp.status_code == 404

    created = (await client.post("/api/v1/sessions/", json={}, headers=headers)).json()

    resp = await client.get("/api/v1/sessions/active", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


@pytest.mark.asyncio
async def test_cross_user_session_access_is_404(client_with_data, device_id):
    """A second user's device id must never see or mutate the first user's session."""
    client, _seed = client_with_data
    owner_headers = {"X-Device-ID": device_id}
    other_headers = {"X-Device-ID": "test-device-99999"}
    await client.get("/api/v1/users/me", headers=owner_headers)
    await client.get("/api/v1/users/me", headers=other_headers)

    session = (
        await client.post("/api/v1/sessions/", json={}, headers=owner_headers)
    ).json()
    rnd = (
        await client.post(
            f"/api/v1/sessions/{session['id']}/rounds", headers=owner_headers
        )
    ).json()

    exercises = (
        await client.get("/api/v1/exercises/?limit=1", headers=owner_headers)
    ).json()
    exercise = (
        exercises["exercises"][0] if isinstance(exercises, dict) else exercises[0]
    )
    entry = (
        await client.post(
            f"/api/v1/sessions/rounds/{rnd['id']}/entries",
            json={"exercise_id": exercise["id"], "position": 1},
            headers=owner_headers,
        )
    ).json()

    # Other user cannot read the session
    assert (
        await client.get(f"/api/v1/sessions/{session['id']}", headers=other_headers)
    ).status_code == 404
    # Other user's /active does not see the owner's session
    assert (
        await client.get("/api/v1/sessions/active", headers=other_headers)
    ).status_code == 404
    # Other user cannot add a round to the owner's session
    assert (
        await client.post(
            f"/api/v1/sessions/{session['id']}/rounds", headers=other_headers
        )
    ).status_code == 404
    # Other user cannot add an entry to the owner's round
    assert (
        await client.post(
            f"/api/v1/sessions/rounds/{rnd['id']}/entries",
            json={"exercise_id": exercise["id"], "position": 2},
            headers=other_headers,
        )
    ).status_code == 404
    # Other user cannot log a set on the owner's entry
    assert (
        await client.post(
            f"/api/v1/sessions/entries/{entry['id']}/sets",
            json={"set_number": 1, "weight": 50, "reps": 5},
            headers=other_headers,
        )
    ).status_code == 404
    # Other user cannot complete or discard the owner's session
    assert (
        await client.post(
            f"/api/v1/sessions/{session['id']}/complete", headers=other_headers
        )
    ).status_code == 404
    assert (
        await client.post(
            f"/api/v1/sessions/{session['id']}/discard", headers=other_headers
        )
    ).status_code == 404


@pytest.mark.asyncio
async def test_coverage_counts_only_completed_sets(client_with_data, device_id):
    """sets_done must count only completed=True sets, and covered flips true at the threshold."""
    client, _seed = client_with_data
    headers = {"X-Device-ID": device_id}
    await client.get("/api/v1/users/me", headers=headers)

    # None of the seed exercises set movement_pattern_1, so pattern_taxonomy's
    # classifier rolls every one of them up to the neutral "isolation" pattern.
    # Discover the exercise -> pattern mapping the server actually assigns
    # (rather than assuming a specific slug) by probing with a throwaway
    # session/round/entry, then build the day plan goal around that pattern.
    exercises = (
        await client.get("/api/v1/exercises/?search=Pull-up", headers=headers)
    ).json()
    exercise_list = exercises["exercises"] if isinstance(exercises, dict) else exercises
    exercise = exercise_list[0]

    probe_session = (
        await client.post("/api/v1/sessions/", json={}, headers=headers)
    ).json()
    probe_round = (
        await client.post(
            f"/api/v1/sessions/{probe_session['id']}/rounds", headers=headers
        )
    ).json()
    probe_entry = (
        await client.post(
            f"/api/v1/sessions/rounds/{probe_round['id']}/entries",
            json={"exercise_id": exercise["id"], "position": 1},
            headers=headers,
        )
    ).json()
    pattern_id = probe_entry["pattern_id"]
    await client.post(
        f"/api/v1/sessions/{probe_session['id']}/discard", headers=headers
    )

    plan = (
        await client.post(
            "/api/v1/day-plans/",
            json={
                "name": "Pull Day",
                "warmup_preferences": [],
                "rounds_target": 1,
                "goals": [
                    {"pattern_id": pattern_id, "required": True, "target_sets": 2}
                ],
            },
            headers=headers,
        )
    ).json()

    session = (
        await client.post(
            "/api/v1/sessions/", json={"day_plan_id": plan["id"]}, headers=headers
        )
    ).json()
    rnd = (
        await client.post(f"/api/v1/sessions/{session['id']}/rounds", headers=headers)
    ).json()

    entry = (
        await client.post(
            f"/api/v1/sessions/rounds/{rnd['id']}/entries",
            json={"exercise_id": exercise["id"], "position": 1},
            headers=headers,
        )
    ).json()
    assert entry["pattern_id"] == pattern_id

    # One completed set, one explicitly not-completed set: sets_done should be 1, not covered (target=2)
    await client.post(
        f"/api/v1/sessions/entries/{entry['id']}/sets",
        json={"set_number": 1, "weight": 100, "reps": 10, "completed": True},
        headers=headers,
    )
    await client.post(
        f"/api/v1/sessions/entries/{entry['id']}/sets",
        json={"set_number": 2, "weight": 100, "reps": 10, "completed": False},
        headers=headers,
    )

    coverage = (
        await client.get(f"/api/v1/sessions/{session['id']}/coverage", headers=headers)
    ).json()
    goal = next(g for g in coverage["goals"] if g["pattern_id"] == pattern_id)
    assert goal["sets_done"] == 1
    assert goal["covered"] is False

    # A second completed set brings sets_done to the target -> covered flips true
    await client.post(
        f"/api/v1/sessions/entries/{entry['id']}/sets",
        json={"set_number": 3, "weight": 100, "reps": 10, "completed": True},
        headers=headers,
    )
    coverage = (
        await client.get(f"/api/v1/sessions/{session['id']}/coverage", headers=headers)
    ).json()
    goal = next(g for g in coverage["goals"] if g["pattern_id"] == pattern_id)
    assert goal["sets_done"] == 2
    assert goal["covered"] is True

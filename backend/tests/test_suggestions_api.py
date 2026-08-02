"""Tests for the suggestions API (anchor and partner endpoints).

These exercise the thin HTTP wrappers around the suggestion engine built in
Task 8. Per the task brief, the shared `seed_data.py` exercises have no
`movement_pattern_1` and all roll up to the neutral `isolation` pattern (no
opposite), so any test asserting antagonist pairing builds its own
pattern-bearing exercises directly against the test database and re-runs
`seed_exercise_pattern_map` to classify them - mirroring the approach in
`tests/test_suggestion_service.py`.
"""

import pytest
from datetime import datetime

from sqlalchemy import select

from app.models import (
    Exercise,
    Equipment,
    StapleExercise,
    TrainingSession,
    SupersetRound,
    RoundEntry,
    EntrySet,
    SessionState,
)
from app.services.pattern_taxonomy import seed_exercise_pattern_map


async def _pattern_id(client, headers, slug):
    """Look up a movement pattern's id by slug via the patterns API."""
    patterns = (await client.get("/api/v1/patterns/", headers=headers)).json()
    return next(p["id"] for p in patterns if p["slug"] == slug)


async def _make_pull_push_pair(test_db):
    """Create a Horizontal Pull and a Horizontal Push compound exercise.

    Purpose-built (not from seed_data.py) so they classify into real,
    non-neutral, opposite-paired movement patterns once
    `seed_exercise_pattern_map` runs. Returns the (row, bench) Exercise rows.
    """
    cable = Equipment(name="Cable Machine - Suggestions Test")
    dumbbell = Equipment(name="Dumbbell - Suggestions Test")
    test_db.add_all([cable, dumbbell])
    await test_db.flush()

    row = Exercise(
        name="Seated Cable Row",
        movement_pattern_1="Horizontal Pull",
        mechanics="Compound",
        primary_equipment_id=cable.id,
    )
    bench = Exercise(
        name="Dumbbell Bench Press",
        movement_pattern_1="Horizontal Push",
        mechanics="Compound",
        primary_equipment_id=dumbbell.id,
    )
    test_db.add_all([row, bench])
    await test_db.flush()
    await seed_exercise_pattern_map(test_db)
    await test_db.commit()
    return row, bench


@pytest.mark.asyncio
async def test_anchor_and_partner_endpoints(client_with_data, device_id):
    """Both endpoints respond 200 with the documented top-level response shape."""
    client, _seed = client_with_data
    headers = {"X-Device-ID": device_id}
    await client.get("/api/v1/users/me", headers=headers)

    patterns = (await client.get("/api/v1/patterns/", headers=headers)).json()
    hp = next(p for p in patterns if p["slug"] == "horizontal_pull")

    plan = (
        await client.post(
            "/api/v1/day-plans/",
            json={
                "name": "Pull Day",
                "warmup_preferences": [],
                "rounds_target": 2,
                "goals": [{"pattern_id": hp["id"], "required": True, "target_sets": 3}],
            },
            headers=headers,
        )
    ).json()
    session = (
        await client.post(
            "/api/v1/sessions/", json={"day_plan_id": plan["id"]}, headers=headers
        )
    ).json()

    # Make one exercise a staple so anchors have content
    exercises = (await client.get("/api/v1/exercises/?limit=5", headers=headers)).json()
    items = exercises["exercises"] if isinstance(exercises, dict) else exercises
    await client.post(
        "/api/v1/staples/", json={"exercise_id": items[0]["id"]}, headers=headers
    )

    anchors = await client.get(
        f"/api/v1/suggestions/anchors?session_id={session['id']}", headers=headers
    )
    assert anchors.status_code == 200
    body = anchors.json()
    assert "groups" in body and "not_recommended" in body

    partners = await client.get(
        f"/api/v1/suggestions/partners?session_id={session['id']}"
        f"&anchor_exercise_id={items[0]['id']}&position=2",
        headers=headers,
    )
    assert partners.status_code == 200
    pbody = partners.json()
    assert "candidates" in pbody and "novelty" in pbody and "not_recommended" in pbody


@pytest.mark.asyncio
async def test_partner_position_validation(client_with_data, device_id):
    """FastAPI's Query(ge=2, le=3) constraint rejects position=5 with a 422."""
    client, _seed = client_with_data
    headers = {"X-Device-ID": device_id}
    await client.get("/api/v1/users/me", headers=headers)
    response = await client.get(
        "/api/v1/suggestions/partners?session_id=1&anchor_exercise_id=1&position=5",
        headers=headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_partner_suggestions_returns_antagonist_pattern_via_http(
    client_with_data, seeded_db, device_id
):
    """Anchoring on a Horizontal Pull staple returns the Horizontal Push staple.

    This is the assertion that proves antagonist pairing actually works
    through the HTTP layer, using purpose-built exercises rather than the
    neutral seed_data.py ones.
    """
    client, _seed = client_with_data
    test_db, _ = seeded_db
    headers = {"X-Device-ID": device_id}
    await client.get("/api/v1/users/me", headers=headers)

    row, bench = await _make_pull_push_pair(test_db)

    await client.post("/api/v1/staples/", json={"exercise_id": row.id}, headers=headers)
    await client.post(
        "/api/v1/staples/", json={"exercise_id": bench.id}, headers=headers
    )

    session = (await client.post("/api/v1/sessions/", json={}, headers=headers)).json()

    response = await client.get(
        f"/api/v1/suggestions/partners?session_id={session['id']}"
        f"&anchor_exercise_id={row.id}&position=2",
        headers=headers,
    )
    assert response.status_code == 200
    names = [c["exercise_name"] for c in response.json()["candidates"]]
    assert "Dumbbell Bench Press" in names
    assert "Seated Cable Row" not in names  # anchor is never its own partner


@pytest.mark.asyncio
async def test_partner_target_schema_round_trip_with_non_null_target(
    client_with_data, seeded_db, device_id
):
    """A candidate card with prior history serializes a non-null `target`.

    Task 8's review flagged that nothing had validated the engine's raw
    dicts against the response schemas - specifically whether the `target`
    field's shape matches what `compute_entry_target` returns. This asserts
    the round trip through the declared `response_model` succeeds and that
    the resulting `target` carries exactly the expected keys.
    """
    client, _seed = client_with_data
    test_db, _ = seeded_db
    headers = {"X-Device-ID": device_id}
    me = await client.get("/api/v1/users/me", headers=headers)
    user_id = me.json()["id"]

    row, bench = await _make_pull_push_pair(test_db)
    hpush_id = await _pattern_id(client, headers, "horizontal_push")

    await client.post("/api/v1/staples/", json={"exercise_id": row.id}, headers=headers)
    await client.post(
        "/api/v1/staples/", json={"exercise_id": bench.id}, headers=headers
    )

    # A prior COMPLETED session with logged sets on bench gives it history,
    # which is what makes compute_entry_target return a non-null target.
    done = TrainingSession(
        user_id=user_id,
        state=SessionState.COMPLETED,
        started_at=datetime(2026, 7, 27, 9),
        completed_at=datetime(2026, 7, 27, 10),
    )
    rnd = SupersetRound(order=1)
    entry = RoundEntry(position=1, exercise_id=bench.id, pattern_id=hpush_id)
    entry.sets.append(EntrySet(set_number=1, weight=60.0, reps=10))
    rnd.entries.append(entry)
    done.rounds.append(rnd)
    test_db.add(done)
    await test_db.commit()

    session = (await client.post("/api/v1/sessions/", json={}, headers=headers)).json()

    response = await client.get(
        f"/api/v1/suggestions/partners?session_id={session['id']}"
        f"&anchor_exercise_id={row.id}&position=2",
        headers=headers,
    )
    assert response.status_code == 200
    candidates = response.json()["candidates"]
    bench_card = next(
        c for c in candidates if c["exercise_name"] == "Dumbbell Bench Press"
    )
    assert bench_card["target"] is not None
    assert set(bench_card["target"].keys()) == {
        "weight",
        "reps",
        "sets",
        "last_summary",
    }
    assert bench_card["target"]["reps"] == 11  # double progression: 10 + 1


@pytest.mark.asyncio
async def test_cross_user_isolation_on_both_endpoints(client_with_data, device_id):
    """A second X-Device-ID gets 404 on the first user's session, on both endpoints.

    NoResultFound from `_session_context`'s `scalar_one()` - raised for a
    missing session OR one belonging to another user - is what the
    endpoints catch and map to 404. This is also what enforces cross-user
    isolation for these endpoints.
    """
    client, _seed = client_with_data
    owner_headers = {"X-Device-ID": device_id}
    await client.get("/api/v1/users/me", headers=owner_headers)

    session = (
        await client.post("/api/v1/sessions/", json={}, headers=owner_headers)
    ).json()

    other_headers = {"X-Device-ID": "other-device-99999"}
    await client.get("/api/v1/users/me", headers=other_headers)

    anchors = await client.get(
        f"/api/v1/suggestions/anchors?session_id={session['id']}",
        headers=other_headers,
    )
    assert anchors.status_code == 404

    partners = await client.get(
        f"/api/v1/suggestions/partners?session_id={session['id']}"
        f"&anchor_exercise_id=1&position=2",
        headers=other_headers,
    )
    assert partners.status_code == 404

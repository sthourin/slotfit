"""Tests for the bodyweight readings API"""
import pytest

HEADERS = {"X-Device-ID": "test-device-12345"}


@pytest.mark.asyncio
async def test_create_and_list_readings(client):
    created = await client.post(
        "/api/v1/bodyweight", json={"weight": 198.5}, headers=HEADERS
    )
    assert created.status_code == 201
    assert created.json()["weight"] == 198.5
    assert created.json()["source"] == "manual"

    listed = await client.get("/api/v1/bodyweight", headers=HEADERS)
    assert listed.status_code == 200
    assert len(listed.json()) == 1


@pytest.mark.asyncio
async def test_readings_are_listed_newest_first(client):
    await client.post(
        "/api/v1/bodyweight",
        json={"weight": 200.0, "recorded_at": "2026-01-01T09:00:00"},
        headers=HEADERS,
    )
    await client.post(
        "/api/v1/bodyweight",
        json={"weight": 190.0, "recorded_at": "2026-06-01T09:00:00"},
        headers=HEADERS,
    )

    body = (await client.get("/api/v1/bodyweight", headers=HEADERS)).json()
    assert [r["weight"] for r in body] == [190.0, 200.0]


@pytest.mark.asyncio
async def test_reposting_the_same_instant_and_source_updates_in_place(client):
    """A Health Connect resync must not duplicate rows."""
    first = await client.post(
        "/api/v1/bodyweight",
        json={
            "weight": 200.0,
            "recorded_at": "2026-01-01T09:00:00",
            "source": "health_connect",
        },
        headers=HEADERS,
    )
    second = await client.post(
        "/api/v1/bodyweight",
        json={
            "weight": 201.0,
            "recorded_at": "2026-01-01T09:00:00",
            "source": "health_connect",
        },
        headers=HEADERS,
    )
    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]

    body = (await client.get("/api/v1/bodyweight", headers=HEADERS)).json()
    assert len(body) == 1
    assert body[0]["weight"] == 201.0


@pytest.mark.asyncio
async def test_manual_and_synced_readings_at_the_same_instant_coexist(client):
    """Sources are independent: a sync must not clobber what the user typed."""
    await client.post(
        "/api/v1/bodyweight",
        json={
            "weight": 200.0,
            "recorded_at": "2026-01-01T09:00:00",
            "source": "manual",
        },
        headers=HEADERS,
    )
    await client.post(
        "/api/v1/bodyweight",
        json={
            "weight": 201.0,
            "recorded_at": "2026-01-01T09:00:00",
            "source": "health_connect",
        },
        headers=HEADERS,
    )
    assert len((await client.get("/api/v1/bodyweight", headers=HEADERS)).json()) == 2


@pytest.mark.asyncio
async def test_non_positive_weight_is_rejected(client):
    response = await client.post(
        "/api/v1/bodyweight", json={"weight": 0}, headers=HEADERS
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_delete_a_reading(client):
    created = await client.post(
        "/api/v1/bodyweight", json={"weight": 198.5}, headers=HEADERS
    )
    deleted = await client.delete(
        f"/api/v1/bodyweight/{created.json()['id']}", headers=HEADERS
    )
    assert deleted.status_code == 204
    assert (await client.get("/api/v1/bodyweight", headers=HEADERS)).json() == []


@pytest.mark.asyncio
async def test_readings_are_scoped_to_the_calling_device(client):
    """Bodyweight is about as personal as this app's data gets."""
    await client.post("/api/v1/bodyweight", json={"weight": 198.5}, headers=HEADERS)

    other = {"X-Device-ID": "other-device-99999"}
    assert (await client.get("/api/v1/bodyweight", headers=other)).json() == []


@pytest.mark.asyncio
async def test_cannot_delete_another_devices_reading(client):
    created = await client.post(
        "/api/v1/bodyweight", json={"weight": 198.5}, headers=HEADERS
    )
    other = {"X-Device-ID": "other-device-99999"}
    await client.delete(f"/api/v1/bodyweight/{created.json()['id']}", headers=other)

    # Still there for its owner.
    assert len((await client.get("/api/v1/bodyweight", headers=HEADERS)).json()) == 1

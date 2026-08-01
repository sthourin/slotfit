"""Tests for the patterns API"""
import pytest

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


@pytest.mark.asyncio
async def test_pattern_progress_empty(client_with_data, device_id):
    client, _seed = client_with_data
    headers = {"X-Device-ID": device_id}
    await client.get("/api/v1/users/me", headers=headers)
    response = await client.get("/api/v1/patterns/progress?weeks=12", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)  # one entry per pattern that has staples; empty user -> []

"""
Tests for Personal Records API endpoints
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_personal_record(client_with_data, device_id: str):
    """Test creating a personal record"""
    client, seed_data = client_with_data
    headers = {"X-Device-ID": device_id}
    
    # Get or create user
    await client.get("/api/v1/users/me", headers=headers)
    
    # Get an exercise from seed data
    exercises_response = await client.get("/api/v1/exercises/?limit=1")
    exercises = exercises_response.json()["exercises"]
    
    if not exercises:
        pytest.skip("No exercises available")
    
    exercise_id = exercises[0]["id"]
    
    record_data = {
        "exercise_id": exercise_id,
        "record_type": "weight",
        "value": 100.5,
        "context": {"notes": "Test PR", "unit": "kg"},
        "achieved_at": "2024-01-15T10:00:00Z"
    }
    
    response = await client.post(
        "/api/v1/personal-records/",
        json=record_data,
        headers=headers
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["exercise_id"] == exercise_id
    assert data["record_type"] == "weight"
    assert data["value"] == 100.5
    assert "id" in data


@pytest.mark.asyncio
async def test_list_personal_records(client_with_data, device_id: str):
    """Test listing personal records"""
    client, seed_data = client_with_data
    headers = {"X-Device-ID": device_id}
    
    await client.get("/api/v1/users/me", headers=headers)
    
    # Get an exercise from seed data
    exercises_response = await client.get("/api/v1/exercises/?limit=1")
    exercises = exercises_response.json()["exercises"]
    
    if not exercises:
        pytest.skip("No exercises available")
    
    exercise_id = exercises[0]["id"]
    
    # Create a record
    record_data = {
        "exercise_id": exercise_id,
        "record_type": "reps",
        "value": 20,
        "achieved_at": "2024-01-15T10:00:00Z"
    }
    await client.post(
        "/api/v1/personal-records/",
        json=record_data,
        headers=headers
    )
    
    # List records
    response = await client.get("/api/v1/personal-records/", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "records" in data
    assert "total" in data
    assert isinstance(data["records"], list)
    assert len(data["records"]) >= 1


@pytest.mark.asyncio
async def test_get_personal_record(client_with_data, device_id: str):
    """Test getting a single personal record"""
    client, seed_data = client_with_data
    headers = {"X-Device-ID": device_id}
    
    await client.get("/api/v1/users/me", headers=headers)
    
    # Get an exercise from seed data
    exercises_response = await client.get("/api/v1/exercises/?limit=1")
    exercises = exercises_response.json()["exercises"]
    
    if not exercises:
        pytest.skip("No exercises available")
    
    exercise_id = exercises[0]["id"]
    
    # Create record
    record_data = {
        "exercise_id": exercise_id,
        "record_type": "weight",
        "value": 150.0,
        "achieved_at": "2024-01-15T10:00:00Z"
    }
    create_response = await client.post(
        "/api/v1/personal-records/",
        json=record_data,
        headers=headers
    )
    record_id = create_response.json()["id"]
    
    # Get record
    response = await client.get(
        f"/api/v1/personal-records/{record_id}",
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == record_id
    assert data["value"] == 150.0


@pytest.mark.asyncio
async def test_update_personal_record(client_with_data, device_id: str):
    """Test updating a personal record"""
    client, seed_data = client_with_data
    headers = {"X-Device-ID": device_id}
    
    await client.get("/api/v1/users/me", headers=headers)
    
    # Get an exercise from seed data
    exercises_response = await client.get("/api/v1/exercises/?limit=1")
    exercises = exercises_response.json()["exercises"]
    
    if not exercises:
        pytest.skip("No exercises available")
    
    exercise_id = exercises[0]["id"]
    
    # Create record
    record_data = {
        "exercise_id": exercise_id,
        "record_type": "weight",
        "value": 100.0,
        "achieved_at": "2024-01-15T10:00:00Z"
    }
    create_response = await client.post(
        "/api/v1/personal-records/",
        json=record_data,
        headers=headers
    )
    record_id = create_response.json()["id"]
    
    # Update record
    update_data = {
        "value": 110.0,
        "context": {"notes": "Updated PR"}
    }
    
    response = await client.put(
        f"/api/v1/personal-records/{record_id}",
        json=update_data,
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["value"] == 110.0
    assert data["context"] is not None
    assert data["context"].get("notes") == "Updated PR"


@pytest.mark.asyncio
async def test_delete_personal_record(client_with_data, device_id: str):
    """Test deleting a personal record"""
    client, seed_data = client_with_data
    headers = {"X-Device-ID": device_id}
    
    await client.get("/api/v1/users/me", headers=headers)
    
    # Get an exercise from seed data
    exercises_response = await client.get("/api/v1/exercises/?limit=1")
    exercises = exercises_response.json()["exercises"]
    
    if not exercises:
        pytest.skip("No exercises available")
    
    exercise_id = exercises[0]["id"]
    
    # Create record
    record_data = {
        "exercise_id": exercise_id,
        "record_type": "weight",
        "value": 100.0,
        "achieved_at": "2024-01-15T10:00:00Z"
    }
    create_response = await client.post(
        "/api/v1/personal-records/",
        json=record_data,
        headers=headers
    )
    record_id = create_response.json()["id"]
    
    # Delete record
    response = await client.delete(
        f"/api/v1/personal-records/{record_id}",
        headers=headers
    )
    
    assert response.status_code == 204
    
    # Verify it's gone
    get_response = await client.get(
        f"/api/v1/personal-records/{record_id}",
        headers=headers
    )
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_list_records_by_exercise(client_with_data, device_id: str):
    """Test listing personal records filtered by exercise"""
    client, seed_data = client_with_data
    headers = {"X-Device-ID": device_id}
    
    await client.get("/api/v1/users/me", headers=headers)
    
    # Get an exercise from seed data
    exercises_response = await client.get("/api/v1/exercises/?limit=1")
    exercises = exercises_response.json()["exercises"]
    
    if not exercises:
        pytest.skip("No exercises available")
    
    exercise_id = exercises[0]["id"]
    
    # Create a record
    record_data = {
        "exercise_id": exercise_id,
        "record_type": "weight",
        "value": 100.0,
        "achieved_at": "2024-01-15T10:00:00Z"
    }
    await client.post(
        "/api/v1/personal-records/",
        json=record_data,
        headers=headers
    )
    
    # List records for this exercise
    response = await client.get(
        f"/api/v1/personal-records/?exercise_id={exercise_id}",
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "records" in data
    assert "total" in data
    # All records should be for this exercise
    for record in data["records"]:
        assert record["exercise_id"] == exercise_id

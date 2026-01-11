"""
Tests for Workout Session API endpoints
"""
import pytest
from httpx import AsyncClient
from datetime import datetime


@pytest.mark.asyncio
async def test_create_workout_session(client_with_data, device_id: str):
    client, seed_data = client_with_data
    """Test creating a workout session"""
    client, seed_data = client_with_data
    headers = {"X-Device-ID": device_id}
    
    # Get or create user
    await client.get("/api/v1/users/me", headers=headers)
    
    # Get muscle group and create routine first
    muscle_groups_response = await client.get("/api/v1/muscle-groups/")
    muscle_groups_data = muscle_groups_response.json()
    muscle_groups = muscle_groups_data.get("muscle_groups", [])
    assert len(muscle_groups) > 0
    
    muscle_group_id = muscle_groups[0]["id"]
    
    # Create routine
    routine_data = {
        "name": "Test Workout Routine",
        "slots": [
            {
                "name": "Test Slot",
                "muscle_group_ids": [muscle_group_id],
                "order": 1
            }
        ]
    }
    routine_response = await client.post(
        "/api/v1/routines/",
        json=routine_data,
        headers=headers
    )
    routine_id = routine_response.json()["id"]
    
    # Create workout
    workout_data = {
        "routine_template_id": routine_id,
        "notes": "Test workout"
    }
    
    response = await client.post(
        "/api/v1/workouts/",
        json=workout_data,
        headers=headers
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["routine_template_id"] == routine_id
    assert data["state"] == "draft"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_workout_sessions(client_with_data, device_id: str):
    client, seed_data = client_with_data
    """Test listing workout sessions"""
    client, seed_data = client_with_data
    headers = {"X-Device-ID": device_id}
    
    await client.get("/api/v1/users/me", headers=headers)
    
    # Get muscle group and create routine
    muscle_groups_response = await client.get("/api/v1/muscle-groups/")
    muscle_groups_data = muscle_groups_response.json()
    muscle_groups = muscle_groups_data.get("muscle_groups", [])
    assert len(muscle_groups) > 0
    
    muscle_group_id = muscle_groups[0]["id"]
    
    routine_data = {
        "name": "List Test Routine",
        "slots": [
            {
                "name": "Test Slot",
                "muscle_group_ids": [muscle_group_id],
                "order": 1
            }
        ]
    }
    routine_response = await client.post(
        "/api/v1/routines/",
        json=routine_data,
        headers=headers
    )
    routine_id = routine_response.json()["id"]
    
    # Create a workout
    workout_data = {"routine_template_id": routine_id}
    await client.post("/api/v1/workouts/", json=workout_data, headers=headers)
    
    # List workouts
    response = await client.get("/api/v1/workouts/", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "workouts" in data
    assert "total" in data
    assert len(data["workouts"]) >= 1


@pytest.mark.asyncio
async def test_get_workout_session(client_with_data, device_id: str):
    client, seed_data = client_with_data
    """Test getting a single workout session"""
    headers = {"X-Device-ID": device_id}
    
    await client.get("/api/v1/users/me", headers=headers)
    
    # Get muscle group and create routine
    muscle_groups_response = await client.get("/api/v1/muscle-groups/")
    muscle_groups_data = muscle_groups_response.json()
    muscle_groups = muscle_groups_data.get("muscle_groups", [])
    assert len(muscle_groups) > 0
    
    muscle_group_id = muscle_groups[0]["id"]
    
    routine_data = {
        "name": "Get Test Routine",
        "slots": [
            {
                "name": "Test Slot",
                "muscle_group_ids": [muscle_group_id],
                "order": 1
            }
        ]
    }
    routine_response = await client.post(
        "/api/v1/routines/",
        json=routine_data,
        headers=headers
    )
    routine_id = routine_response.json()["id"]
    
    # Create workout
    workout_data = {"routine_template_id": routine_id}
    create_response = await client.post(
        "/api/v1/workouts/",
        json=workout_data,
        headers=headers
    )
    workout_id = create_response.json()["id"]
    
    # Get workout
    response = await client.get(
        f"/api/v1/workouts/{workout_id}",
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == workout_id
    assert data["state"] == "draft"


@pytest.mark.asyncio
async def test_update_workout_session(client_with_data, device_id: str):
    client, seed_data = client_with_data
    """Test updating a workout session"""
    headers = {"X-Device-ID": device_id}
    
    await client.get("/api/v1/users/me", headers=headers)
    
    # Get muscle group and create routine
    muscle_groups_response = await client.get("/api/v1/muscle-groups/")
    muscle_groups_data = muscle_groups_response.json()
    muscle_groups = muscle_groups_data.get("muscle_groups", [])
    assert len(muscle_groups) > 0
    
    muscle_group_id = muscle_groups[0]["id"]
    
    routine_data = {
        "name": "Update Test Routine",
        "slots": [
            {
                "name": "Test Slot",
                "muscle_group_ids": [muscle_group_id],
                "order": 1
            }
        ]
    }
    routine_response = await client.post(
        "/api/v1/routines/",
        json=routine_data,
        headers=headers
    )
    routine_id = routine_response.json()["id"]
    
    # Create workout
    workout_data = {"routine_template_id": routine_id}
    create_response = await client.post(
        "/api/v1/workouts/",
        json=workout_data,
        headers=headers
    )
    workout_id = create_response.json()["id"]
    
    # Update workout
    update_data = {
        "state": "active"
    }
    
    response = await client.put(
        f"/api/v1/workouts/{workout_id}",
        json=update_data,
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["state"] == "active"


@pytest.mark.asyncio
async def test_complete_workout_session(client_with_data, device_id: str):
    client, seed_data = client_with_data
    """Test completing a workout session"""
    headers = {"X-Device-ID": device_id}
    
    await client.get("/api/v1/users/me", headers=headers)
    
    # Get muscle group and create routine
    muscle_groups_response = await client.get("/api/v1/muscle-groups/")
    muscle_groups_data = muscle_groups_response.json()
    muscle_groups = muscle_groups_data.get("muscle_groups", [])
    assert len(muscle_groups) > 0
    
    muscle_group_id = muscle_groups[0]["id"]
    
    routine_data = {
        "name": "Complete Test Routine",
        "slots": [
            {
                "name": "Test Slot",
                "muscle_group_ids": [muscle_group_id],
                "order": 1
            }
        ]
    }
    routine_response = await client.post(
        "/api/v1/routines/",
        json=routine_data,
        headers=headers
    )
    routine_id = routine_response.json()["id"]
    
    # Create workout
    workout_data = {"routine_template_id": routine_id}
    create_response = await client.post(
        "/api/v1/workouts/",
        json=workout_data,
        headers=headers
    )
    workout_id = create_response.json()["id"]
    
    # Set workout to active state first (required for completion)
    update_response = await client.put(
        f"/api/v1/workouts/{workout_id}",
        json={"state": "active"},
        headers=headers
    )
    assert update_response.status_code == 200
    
    # Complete workout
    response = await client.post(
        f"/api/v1/workouts/{workout_id}/complete",
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["state"] == "completed"
    assert data["completed_at"] is not None


@pytest.mark.asyncio
async def test_add_exercise_to_workout(client_with_data, device_id: str):
    client, seed_data = client_with_data
    """Test adding an exercise to a workout"""
    headers = {"X-Device-ID": device_id}
    
    await client.get("/api/v1/users/me", headers=headers)
    
    # Get muscle group and create routine
    muscle_groups_response = await client.get("/api/v1/muscle-groups/")
    muscle_groups_data = muscle_groups_response.json()
    muscle_groups = muscle_groups_data.get("muscle_groups", [])
    assert len(muscle_groups) > 0
    
    muscle_group_id = muscle_groups[0]["id"]
    
    routine_data = {
        "name": "Exercise Test Routine",
        "slots": [
            {
                "name": "Test Slot",
                "muscle_group_ids": [muscle_group_id],
                "order": 1
            }
        ]
    }
    routine_response = await client.post(
        "/api/v1/routines/",
        json=routine_data,
        headers=headers
    )
    routine_id = routine_response.json()["id"]
    
    # Get routine to find slot ID
    routine_get = await client.get(
        f"/api/v1/routines/{routine_id}",
        headers=headers
    )
    slots = routine_get.json().get("slots", [])
    assert len(slots) > 0
    slot_id = slots[0]["id"]
    
    # Create workout
    workout_data = {"routine_template_id": routine_id}
    create_response = await client.post(
        "/api/v1/workouts/",
        json=workout_data,
        headers=headers
    )
    workout_id = create_response.json()["id"]
    
    # Get an exercise
    exercises_response = await client.get("/api/v1/exercises/?limit=1")
    exercises = exercises_response.json()["exercises"]
    
    assert len(exercises) > 0
    
    exercise_id = exercises[0]["id"]
    
    # Add exercise to workout
    exercise_data = {
        "routine_slot_id": slot_id,
        "exercise_id": exercise_id
    }
    
    response = await client.post(
        f"/api/v1/workouts/{workout_id}/exercises",
        json=exercise_data,
        headers=headers
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["exercise_id"] == exercise_id
    assert data["routine_slot_id"] == slot_id

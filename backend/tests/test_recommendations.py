"""
Tests for AI Exercise Recommendation API endpoints
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_recommendations_basic(client_with_data, device_id: str):
    """Test getting exercise recommendations"""
    client, seed_data = client_with_data
    headers = {"X-Device-ID": device_id}
    
    # Get or create user
    await client.get("/api/v1/users/me", headers=headers)
    
    # Get muscle groups
    muscle_groups_response = await client.get("/api/v1/muscle-groups/")
    muscle_groups_data = muscle_groups_response.json()
    muscle_groups = muscle_groups_data.get("muscle_groups", [])
    assert len(muscle_groups) > 0
    
    muscle_group_id = muscle_groups[0]["id"]
    
    # Get recommendations (muscle_group_ids as list, available_equipment_ids optional - omit if empty)
    response = await client.get(
        f"/api/v1/recommendations/?muscle_group_ids={muscle_group_id}&limit=5",
        headers=headers
    )
    
    # Should return 200 even if AI service is not configured
    # (it will return empty recommendations)
    assert response.status_code == 200
    data = response.json()
    assert "recommendations" in data
    assert "not_recommended" in data
    assert isinstance(data["recommendations"], list)
    assert isinstance(data["not_recommended"], list)


@pytest.mark.asyncio
async def test_get_recommendations_with_equipment_profile(
    client_with_data, device_id: str
):
    """Test getting recommendations filtered by equipment profile"""
    client, seed_data = client_with_data
    headers = {"X-Device-ID": device_id}
    
    await client.get("/api/v1/users/me", headers=headers)
    
    # Create equipment profile
    profile_data = {
        "name": "Test Profile",
        "equipment_ids": [],
        "is_default": True
    }
    profile_response = await client.post(
        "/api/v1/equipment-profiles/",
        json=profile_data,
        headers=headers
    )
    profile_id = profile_response.json()["id"]
    
    # Get muscle groups
    muscle_groups_response = await client.get("/api/v1/muscle-groups/")
    muscle_groups_data = muscle_groups_response.json()
    muscle_groups = muscle_groups_data.get("muscle_groups", [])
    assert len(muscle_groups) > 0
    
    muscle_group_id = muscle_groups[0]["id"]
    
    # Get recommendations with equipment profile
    # Note: equipment_profile_id is not a parameter, we use available_equipment_ids
    # For now, just test without equipment filter (empty list is default)
    response = await client.get(
        f"/api/v1/recommendations/?muscle_group_ids={muscle_group_id}&limit=5",
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "recommendations" in data
    assert "not_recommended" in data


@pytest.mark.asyncio
async def test_get_recommendations_with_routine_slot(
    client_with_data, device_id: str
):
    """Test getting recommendations for a specific routine slot"""
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
        "name": "Recommendation Test Routine",
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
    
    # Get routine to find slot muscle groups
    routine_get = await client.get(
        f"/api/v1/routines/{routine_id}",
        headers=headers
    )
    slots = routine_get.json().get("slots", [])
    assert len(slots) > 0
    slot = slots[0]
    muscle_group_ids = slot.get("muscle_group_ids", [])
    assert len(muscle_group_ids) > 0
    
    # Get recommendations for slot (using muscle_group_ids from slot)
    response = await client.get(
        f"/api/v1/recommendations/?muscle_group_ids={muscle_group_ids[0]}&limit=5",
        headers=headers
    )

    assert response.status_code == 200
    data = response.json()
    assert "recommendations" in data
    assert "not_recommended" in data


@pytest.mark.asyncio
async def test_get_recommendations_with_completed_workout_history(
    client_with_data, device_id: str
):
    """Recommendations must succeed when the user has recent completed workouts.

    Regression test: get_user_workout_history refreshed a relationship named
    'workout_exercises', but the WorkoutSession model attribute is 'exercises',
    causing a KeyError (500) for any user with completed history in the last
    30 days.
    """
    client, seed_data = client_with_data
    headers = {"X-Device-ID": device_id}

    await client.get("/api/v1/users/me", headers=headers)

    # Get muscle group and create routine with one slot
    muscle_groups_response = await client.get("/api/v1/muscle-groups/")
    muscle_groups = muscle_groups_response.json().get("muscle_groups", [])
    assert len(muscle_groups) > 0
    muscle_group_id = muscle_groups[0]["id"]

    routine_data = {
        "name": "History Test Routine",
        "slots": [
            {
                "name": "Test Slot",
                "muscle_group_ids": [muscle_group_id],
                "order": 1
            }
        ]
    }
    routine_response = await client.post(
        "/api/v1/routines/", json=routine_data, headers=headers
    )
    routine_id = routine_response.json()["id"]

    routine_get = await client.get(f"/api/v1/routines/{routine_id}", headers=headers)
    slot_id = routine_get.json()["slots"][0]["id"]

    # Create a workout, add an exercise to it, and complete it
    create_response = await client.post(
        "/api/v1/workouts/", json={"routine_template_id": routine_id}, headers=headers
    )
    workout_id = create_response.json()["id"]

    exercises_response = await client.get("/api/v1/exercises/?limit=1")
    exercise_id = exercises_response.json()["exercises"][0]["id"]

    add_response = await client.post(
        f"/api/v1/workouts/{workout_id}/exercises",
        json={"routine_slot_id": slot_id, "exercise_id": exercise_id},
        headers=headers,
    )
    assert add_response.status_code == 201

    await client.put(
        f"/api/v1/workouts/{workout_id}", json={"state": "active"}, headers=headers
    )
    complete_response = await client.post(
        f"/api/v1/workouts/{workout_id}/complete", headers=headers
    )
    assert complete_response.status_code == 200

    # Recommendations must not 500 now that history exists
    response = await client.get(
        f"/api/v1/recommendations/?muscle_group_ids={muscle_group_id}&limit=5",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "recommendations" in data
    assert "not_recommended" in data

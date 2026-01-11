"""
Tests for Exercise API endpoints
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Exercise, MuscleGroup, Equipment


@pytest.mark.asyncio
async def test_list_exercises(client: AsyncClient, test_db: AsyncSession):
    """Test listing exercises"""
    response = await client.get("/api/v1/exercises/")
    
    assert response.status_code == 200
    data = response.json()
    assert "exercises" in data
    assert "total" in data
    assert isinstance(data["exercises"], list)


@pytest.mark.asyncio
async def test_list_exercises_with_pagination(client: AsyncClient):
    """Test exercise pagination"""
    response = await client.get("/api/v1/exercises/?skip=0&limit=10")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["exercises"]) <= 10


@pytest.mark.asyncio
async def test_search_exercises(client: AsyncClient):
    """Test searching exercises by name"""
    response = await client.get("/api/v1/exercises/?search=push")
    
    assert response.status_code == 200
    data = response.json()
    # All results should contain "push" in name (case-insensitive)
    for exercise in data["exercises"]:
        assert "push" in exercise["name"].lower()


@pytest.mark.asyncio
async def test_filter_exercises_by_muscle_group(client_with_data):
    """Test filtering exercises by muscle group"""
    client, seed_data = client_with_data
    
    # Get a muscle group ID from seeded data that has exercises
    # Based on seed data: Chest (id=1) has Push-up, Back (id=2) has Pull-up, etc.
    muscle_groups_response = await client.get("/api/v1/muscle-groups/")
    assert muscle_groups_response.status_code == 200
    muscle_groups_data = muscle_groups_response.json()
    muscle_groups = muscle_groups_data.get("muscle_groups", [])
    assert len(muscle_groups) > 0
    
    # Find a muscle group that has exercises (Chest, Back, Shoulders, Biceps, Quadriceps, or Core)
    # These are the ones with exercises in seed data
    target_names = ["Chest", "Back", "Shoulders", "Biceps", "Quadriceps", "Core"]
    target_mg = next((mg for mg in muscle_groups if mg["name"] in target_names), None)
    assert target_mg is not None, f"Could not find a muscle group with exercises. Available: {[mg['name'] for mg in muscle_groups]}"
    muscle_group_id = target_mg["id"]
    
    response = await client.get(
        f"/api/v1/exercises/?muscle_group_id={muscle_group_id}"
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["exercises"]) > 0
    # Verify all exercises target this muscle group
    for exercise in data["exercises"]:
        muscle_group_ids = [
            mg["id"] for mg in exercise.get("muscle_groups", [])
        ]
        assert muscle_group_id in muscle_group_ids


@pytest.mark.asyncio
async def test_get_exercise_by_id(client_with_data):
    """Test getting a single exercise by ID"""
    client, seed_data = client_with_data
    
    # Get an exercise ID from the list
    list_response = await client.get("/api/v1/exercises/?limit=1")
    assert list_response.status_code == 200
    
    exercises = list_response.json()["exercises"]
    assert len(exercises) > 0
    
    exercise_id = exercises[0]["id"]
    
    response = await client.get(f"/api/v1/exercises/{exercise_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == exercise_id
    assert "name" in data
    assert "muscle_groups" in data  # API returns muscle_groups, not target_muscle_groups


@pytest.mark.asyncio
async def test_duplicate_exercise(client_with_data, device_id: str):
    """Test duplicating an exercise to create a variant"""
    client, seed_data = client_with_data
    headers = {"X-Device-ID": device_id}
    
    # Get or create user
    await client.get("/api/v1/users/me", headers=headers)
    
    # Get an exercise to duplicate
    list_response = await client.get("/api/v1/exercises/?limit=1")
    assert list_response.status_code == 200
    
    exercises = list_response.json()["exercises"]
    assert len(exercises) > 0
    
    exercise_id = exercises[0]["id"]
    
    duplicate_data = {
        "name": "Push-up (HIIT Variant)",
        "variant_type": "HIIT",
        "notes": "High intensity version"
    }
    
    response = await client.post(
        f"/api/v1/exercises/{exercise_id}/duplicate",
        json=duplicate_data,
        headers=headers
    )
    
    # Duplicate endpoint may return 200 or 201
    assert response.status_code in [200, 201]
    data = response.json()
    assert data["name"] == "Push-up (HIIT Variant)"
    assert data["variant_type"] == "HIIT"
    assert data["base_exercise_id"] == exercise_id


@pytest.mark.asyncio
async def test_filter_exercises_by_equipment(client_with_data):
    """Test filtering exercises by equipment"""
    client, seed_data = client_with_data
    
    # Get equipment list
    equipment_response = await client.get("/api/v1/equipment/")
    assert equipment_response.status_code == 200
    equipment_list = equipment_response.json()
    assert len(equipment_list) > 0
    
    equipment_id = equipment_list[0]["id"]
    
    response = await client.get(
        f"/api/v1/exercises/?equipment_id={equipment_id}"
    )
    
    assert response.status_code == 200
    data = response.json()
    # May have exercises or may be empty depending on filter
    if len(data["exercises"]) > 0:
        # Verify all exercises use this equipment
        for exercise in data["exercises"]:
            assert exercise.get("primary_equipment", {}).get("id") == equipment_id


@pytest.mark.asyncio
async def test_filter_bodyweight_exercises(client_with_data):
    """Test filtering for bodyweight exercises (no equipment)"""
    client, seed_data = client_with_data
    
    # Get bodyweight equipment ID
    equipment_response = await client.get("/api/v1/equipment/")
    equipment_list = equipment_response.json()
    bodyweight_eq = next(eq for eq in equipment_list if eq["name"] == "Bodyweight")
    
    # Filter by bodyweight equipment (exercises with bodyweight as primary)
    response = await client.get(f"/api/v1/exercises/?equipment_id={bodyweight_eq['id']}")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["exercises"]) > 0
    # All exercises should have bodyweight as primary equipment
    for exercise in data["exercises"]:
        assert exercise.get("primary_equipment", {}).get("id") == bodyweight_eq["id"]

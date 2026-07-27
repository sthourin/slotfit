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


# ---- CRUD Tests ----


@pytest.mark.asyncio
async def test_create_exercise(client_with_data):
    """Test creating a new exercise"""
    client, seed_data = client_with_data

    # Get a muscle group ID for association
    mg_response = await client.get("/api/v1/muscle-groups/")
    muscle_groups = mg_response.json()["muscle_groups"]
    chest_mg = next(mg for mg in muscle_groups if mg["name"] == "Chest")

    create_data = {
        "name": "Test Custom Exercise",
        "description": "A test exercise",
        "difficulty": "Intermediate",
        "body_region": "Upper Body",
        "force_type": "Push",
        "mechanics": "Compound",
        "laterality": "Bilateral",
        "muscle_groups": [
            {"muscle_group_id": chest_mg["id"], "role": "target"},
        ],
    }

    response = await client.post("/api/v1/exercises/", json=create_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Custom Exercise"
    assert data["difficulty"] == "Intermediate"
    assert data["body_region"] == "Upper Body"
    assert data["is_custom"] is True
    assert len(data["muscle_groups"]) >= 1


@pytest.mark.asyncio
async def test_create_exercise_duplicate_name(client_with_data):
    """Test creating exercise with duplicate name fails"""
    client, seed_data = client_with_data

    # Get an existing exercise name
    list_response = await client.get("/api/v1/exercises/?limit=1")
    existing_name = list_response.json()["exercises"][0]["name"]

    create_data = {
        "name": existing_name,
    }

    response = await client.post("/api/v1/exercises/", json=create_data)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_update_exercise(client_with_data):
    """Test updating an exercise"""
    client, seed_data = client_with_data

    # Create an exercise first
    create_response = await client.post(
        "/api/v1/exercises/",
        json={"name": "Exercise To Update", "difficulty": "Easy"},
    )
    assert create_response.status_code == 201
    exercise_id = create_response.json()["id"]

    # Update it
    update_data = {
        "name": "Updated Exercise Name",
        "difficulty": "Advanced",
        "body_region": "Core",
    }
    response = await client.put(f"/api/v1/exercises/{exercise_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Exercise Name"
    assert data["difficulty"] == "Advanced"
    assert data["body_region"] == "Core"


@pytest.mark.asyncio
async def test_update_exercise_muscle_groups(client_with_data):
    """Test updating exercise muscle group associations"""
    client, seed_data = client_with_data

    # Get muscle groups
    mg_response = await client.get("/api/v1/muscle-groups/")
    muscle_groups = mg_response.json()["muscle_groups"]
    chest_mg = next(mg for mg in muscle_groups if mg["name"] == "Chest")
    back_mg = next(mg for mg in muscle_groups if mg["name"] == "Back")

    # Create exercise with Chest
    create_response = await client.post(
        "/api/v1/exercises/",
        json={
            "name": "MG Update Test",
            "muscle_groups": [{"muscle_group_id": chest_mg["id"], "role": "target"}],
        },
    )
    assert create_response.status_code == 201
    exercise_id = create_response.json()["id"]

    # Update to Back
    response = await client.put(
        f"/api/v1/exercises/{exercise_id}",
        json={
            "muscle_groups": [{"muscle_group_id": back_mg["id"], "role": "target"}],
        },
    )
    assert response.status_code == 200
    mg_names = [mg["name"] for mg in response.json()["muscle_groups"]]
    assert "Back" in mg_names


@pytest.mark.asyncio
async def test_delete_exercise(client_with_data):
    """Test deleting an exercise"""
    client, seed_data = client_with_data

    # Create an exercise to delete
    create_response = await client.post(
        "/api/v1/exercises/",
        json={"name": "Exercise To Delete"},
    )
    assert create_response.status_code == 201
    exercise_id = create_response.json()["id"]

    # Delete it
    response = await client.delete(f"/api/v1/exercises/{exercise_id}")
    assert response.status_code == 204

    # Verify it's gone
    get_response = await client.get(f"/api/v1/exercises/{exercise_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_exercise_with_variants(client_with_data, device_id: str):
    """Test that deleting a base exercise with variants is blocked"""
    client, seed_data = client_with_data
    headers = {"X-Device-ID": device_id}
    await client.get("/api/v1/users/me", headers=headers)

    # Create a base exercise
    base_response = await client.post(
        "/api/v1/exercises/",
        json={"name": "Base For Variant Test"},
    )
    assert base_response.status_code == 201
    base_id = base_response.json()["id"]

    # Create a variant
    variant_response = await client.post(
        f"/api/v1/exercises/{base_id}/duplicate",
        json={"variant_type": "HIIT"},
        headers=headers,
    )
    assert variant_response.status_code == 201

    # Try to delete the base — should be blocked
    response = await client.delete(f"/api/v1/exercises/{base_id}")
    assert response.status_code == 400
    assert "variant" in response.json()["detail"].lower()

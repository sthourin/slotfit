"""
Tests for Routine Template API endpoints
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_create_routine_template(client_with_data, device_id: str):
    """Test creating a routine template"""
    client, seed_data = client_with_data
    headers = {"X-Device-ID": device_id}
    
    # Get or create user
    await client.get("/api/v1/users/me", headers=headers)
    
    # Get a muscle group for the slot
    muscle_groups_response = await client.get("/api/v1/muscle-groups/")
    assert muscle_groups_response.status_code == 200
    muscle_groups_data = muscle_groups_response.json()
    muscle_groups = muscle_groups_data.get("muscle_groups", [])
    assert len(muscle_groups) > 0
    
    muscle_group_id = muscle_groups[0]["id"]
    
    routine_data = {
        "name": "Test Push Day",
        "description": "A test push workout",
        "slots": [
            {
                "name": "Chest Slot",
                "muscle_group_ids": [muscle_group_id],
                "slot_type": "standard",
                "order": 1
            }
        ]
    }
    
    response = await client.post(
        "/api/v1/routines/",
        json=routine_data,
        headers=headers
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Push Day"
    assert "slots" in data
    assert len(data["slots"]) == 1
    assert data["slots"][0]["name"] == "Chest Slot"


@pytest.mark.asyncio
async def test_list_routine_templates(client_with_data, device_id: str):
    """Test listing routine templates"""
    client, seed_data = client_with_data
    headers = {"X-Device-ID": device_id}
    
    await client.get("/api/v1/users/me", headers=headers)
    
    # Get muscle group
    muscle_groups_response = await client.get("/api/v1/muscle-groups/")
    muscle_groups_data = muscle_groups_response.json()
    muscle_groups = muscle_groups_data.get("muscle_groups", [])
    assert len(muscle_groups) > 0
    
    muscle_group_id = muscle_groups[0]["id"]
    
    # Create a routine
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
    await client.post("/api/v1/routines/", json=routine_data, headers=headers)
    
    # List routines
    response = await client.get("/api/v1/routines/", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "routines" in data
    assert "total" in data
    assert len(data["routines"]) >= 1


@pytest.mark.asyncio
async def test_get_routine_template(client_with_data, device_id: str):
    """Test getting a single routine template"""
    client, seed_data = client_with_data
    headers = {"X-Device-ID": device_id}
    
    await client.get("/api/v1/users/me", headers=headers)
    
    # Get muscle group
    muscle_groups_response = await client.get("/api/v1/muscle-groups/")
    muscle_groups_data = muscle_groups_response.json()
    muscle_groups = muscle_groups_data.get("muscle_groups", [])
    assert len(muscle_groups) > 0
    
    muscle_group_id = muscle_groups[0]["id"]
    
    # Create routine
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
    create_response = await client.post(
        "/api/v1/routines/",
        json=routine_data,
        headers=headers
    )
    routine_id = create_response.json()["id"]
    
    # Get routine
    response = await client.get(
        f"/api/v1/routines/{routine_id}",
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == routine_id
    assert data["name"] == "Get Test Routine"
    assert len(data["slots"]) == 1


@pytest.mark.asyncio
async def test_update_routine_template(client_with_data, device_id: str):
    """Test updating a routine template"""
    client, seed_data = client_with_data
    headers = {"X-Device-ID": device_id}
    
    await client.get("/api/v1/users/me", headers=headers)
    
    # Get muscle group
    muscle_groups_response = await client.get("/api/v1/muscle-groups/")
    muscle_groups_data = muscle_groups_response.json()
    muscle_groups = muscle_groups_data.get("muscle_groups", [])
    assert len(muscle_groups) > 0
    
    muscle_group_id = muscle_groups[0]["id"]
    
    # Create routine
    routine_data = {
        "name": "Original Name",
        "slots": [
            {
                "name": "Slot 1",
                "muscle_group_ids": [muscle_group_id],
                "order": 1
            }
        ]
    }
    create_response = await client.post(
        "/api/v1/routines/",
        json=routine_data,
        headers=headers
    )
    routine_id = create_response.json()["id"]
    
    # Update routine
    update_data = {
        "name": "Updated Name",
        "description": "Updated description"
    }
    
    response = await client.put(
        f"/api/v1/routines/{routine_id}",
        json=update_data,
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["description"] == "Updated description"


@pytest.mark.asyncio
async def test_delete_routine_template(client_with_data, device_id: str):
    """Test deleting a routine template"""
    client, seed_data = client_with_data
    headers = {"X-Device-ID": device_id}
    
    await client.get("/api/v1/users/me", headers=headers)
    
    # Get muscle group
    muscle_groups_response = await client.get("/api/v1/muscle-groups/")
    muscle_groups_data = muscle_groups_response.json()
    muscle_groups = muscle_groups_data.get("muscle_groups", [])
    assert len(muscle_groups) > 0
    
    muscle_group_id = muscle_groups[0]["id"]
    
    # Create routine
    routine_data = {
        "name": "To Delete",
        "slots": [
            {
                "name": "Test Slot",
                "muscle_group_ids": [muscle_group_id],
                "order": 1
            }
        ]
    }
    create_response = await client.post(
        "/api/v1/routines/",
        json=routine_data,
        headers=headers
    )
    routine_id = create_response.json()["id"]
    
    # Delete routine
    response = await client.delete(
        f"/api/v1/routines/{routine_id}",
        headers=headers
    )
    
    assert response.status_code == 204
    
    # Verify it's gone
    get_response = await client.get(
        f"/api/v1/routines/{routine_id}",
        headers=headers
    )
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_add_slot_to_routine(client_with_data, device_id: str):
    """Test adding a slot to an existing routine"""
    client, seed_data = client_with_data
    headers = {"X-Device-ID": device_id}
    
    await client.get("/api/v1/users/me", headers=headers)
    
    # Get muscle group
    muscle_groups_response = await client.get("/api/v1/muscle-groups/")
    muscle_groups_data = muscle_groups_response.json()
    muscle_groups = muscle_groups_data.get("muscle_groups", [])
    assert len(muscle_groups) > 0
    
    muscle_group_id = muscle_groups[0]["id"]
    
    # Create routine with one slot
    routine_data = {
        "name": "Multi-Slot Routine",
        "slots": [
            {
                "name": "Slot 1",
                "muscle_group_ids": [muscle_group_id],
                "order": 1
            }
        ]
    }
    create_response = await client.post(
        "/api/v1/routines/",
        json=routine_data,
        headers=headers
    )
    routine_id = create_response.json()["id"]
    
    # Add another slot
    slot_data = {
        "name": "Slot 2",
        "muscle_group_ids": [muscle_group_id],
        "order": 2
    }
    
    response = await client.post(
        f"/api/v1/routines/{routine_id}/slots",
        json=slot_data,
        headers=headers
    )
    
    assert response.status_code == 201
    data = response.json()
    # Response is the routine, not the slot
    assert data["name"] == "Multi-Slot Routine"
    assert len(data["slots"]) == 2
    # Verify the new slot is in the list
    slot_names = [slot["name"] for slot in data["slots"]]
    assert "Slot 2" in slot_names

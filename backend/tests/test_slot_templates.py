"""
Tests for Slot Template API endpoints
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_slot_template(client_with_data, device_id: str):
    client, seed_data = client_with_data
    """Test creating a slot template"""
    headers = {"X-Device-ID": device_id}
    
    # Get or create user
    await client.get("/api/v1/users/me", headers=headers)
    
    # Get muscle groups
    muscle_groups_response = await client.get("/api/v1/muscle-groups/")
    muscle_groups_data = muscle_groups_response.json()
    muscle_groups = muscle_groups_data.get("muscle_groups", [])
    assert len(muscle_groups) > 0
    
    muscle_group_id = muscle_groups[0]["id"]
    
    template_data = {
        "name": "Chest Focus Slot",
        "description": "A slot targeting chest muscles",
        "muscle_group_ids": [muscle_group_id],
        "slot_type": "standard",
        "sets": 3,
        "reps": "8-12"
    }
    
    response = await client.post(
        "/api/v1/slot-templates/",
        json=template_data,
        headers=headers
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Chest Focus Slot"
    assert data["slot_type"] == "standard"
    assert len(data["muscle_group_ids"]) == 1
    assert "id" in data


@pytest.mark.asyncio
async def test_list_slot_templates(client_with_data, device_id: str):
    client, seed_data = client_with_data
    """Test listing slot templates"""
    headers = {"X-Device-ID": device_id}
    
    await client.get("/api/v1/users/me", headers=headers)
    
    # Get muscle groups
    muscle_groups_response = await client.get("/api/v1/muscle-groups/")
    muscle_groups_data = muscle_groups_response.json()
    muscle_groups = muscle_groups_data.get("muscle_groups", [])
    assert len(muscle_groups) > 0
    
    muscle_group_id = muscle_groups[0]["id"]
    
    # Create a template
    template_data = {
        "name": "List Test Template",
        "muscle_group_ids": [muscle_group_id],
        "slot_type": "standard"
    }
    await client.post(
        "/api/v1/slot-templates/",
        json=template_data,
        headers=headers
    )
    
    # List templates
    response = await client.get("/api/v1/slot-templates/", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_get_slot_template(client_with_data, device_id: str):
    client, seed_data = client_with_data
    """Test getting a single slot template"""
    headers = {"X-Device-ID": device_id}
    
    await client.get("/api/v1/users/me", headers=headers)
    
    # Get muscle groups
    muscle_groups_response = await client.get("/api/v1/muscle-groups/")
    muscle_groups_data = muscle_groups_response.json()
    muscle_groups = muscle_groups_data.get("muscle_groups", [])
    assert len(muscle_groups) > 0
    
    muscle_group_id = muscle_groups[0]["id"]
    
    # Create template
    template_data = {
        "name": "Get Test Template",
        "muscle_group_ids": [muscle_group_id],
        "slot_type": "standard"
    }
    create_response = await client.post(
        "/api/v1/slot-templates/",
        json=template_data,
        headers=headers
    )
    template_id = create_response.json()["id"]
    
    # Get template
    response = await client.get(
        f"/api/v1/slot-templates/{template_id}",
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == template_id
    assert data["name"] == "Get Test Template"


@pytest.mark.asyncio
async def test_update_slot_template(client_with_data, device_id: str):
    client, seed_data = client_with_data
    """Test updating a slot template"""
    headers = {"X-Device-ID": device_id}
    
    await client.get("/api/v1/users/me", headers=headers)
    
    # Get muscle groups
    muscle_groups_response = await client.get("/api/v1/muscle-groups/")
    muscle_groups_data = muscle_groups_response.json()
    muscle_groups = muscle_groups_data.get("muscle_groups", [])
    assert len(muscle_groups) > 0
    
    muscle_group_id = muscle_groups[0]["id"]
    
    # Create template
    template_data = {
        "name": "Original Name",
        "muscle_group_ids": [muscle_group_id],
        "slot_type": "standard"
    }
    create_response = await client.post(
        "/api/v1/slot-templates/",
        json=template_data,
        headers=headers
    )
    template_id = create_response.json()["id"]
    
    # Update template
    update_data = {
        "name": "Updated Name",
        "notes": "Updated description"
    }
    
    response = await client.put(
        f"/api/v1/slot-templates/{template_id}",
        json=update_data,
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["notes"] == "Updated description"


@pytest.mark.asyncio
async def test_delete_slot_template(client_with_data, device_id: str):
    client, seed_data = client_with_data
    """Test deleting a slot template"""
    headers = {"X-Device-ID": device_id}
    
    await client.get("/api/v1/users/me", headers=headers)
    
    # Get muscle groups
    muscle_groups_response = await client.get("/api/v1/muscle-groups/")
    muscle_groups_data = muscle_groups_response.json()
    muscle_groups = muscle_groups_data.get("muscle_groups", [])
    assert len(muscle_groups) > 0
    
    muscle_group_id = muscle_groups[0]["id"]
    
    # Create template
    template_data = {
        "name": "To Delete",
        "muscle_group_ids": [muscle_group_id],
        "slot_type": "standard"
    }
    create_response = await client.post(
        "/api/v1/slot-templates/",
        json=template_data,
        headers=headers
    )
    template_id = create_response.json()["id"]
    
    # Delete template
    response = await client.delete(
        f"/api/v1/slot-templates/{template_id}",
        headers=headers
    )
    
    assert response.status_code == 204
    
    # Verify it's gone
    get_response = await client.get(
        f"/api/v1/slot-templates/{template_id}",
        headers=headers
    )
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_slot_template_validation(client_with_data, device_id: str):
    client, seed_data = client_with_data
    """Test that slot template validates slot_type"""
    headers = {"X-Device-ID": device_id}
    
    await client.get("/api/v1/users/me", headers=headers)
    
    # Get muscle groups
    muscle_groups_response = await client.get("/api/v1/muscle-groups/")
    muscle_groups_data = muscle_groups_response.json()
    muscle_groups = muscle_groups_data.get("muscle_groups", [])
    assert len(muscle_groups) > 0
    
    muscle_group_id = muscle_groups[0]["id"]
    
    # Try to create with invalid slot_type
    template_data = {
        "name": "Invalid Template",
        "muscle_group_ids": [muscle_group_id],
        "slot_type": "invalid_type"
    }
    
    response = await client.post(
        "/api/v1/slot-templates/",
        json=template_data,
        headers=headers
    )
    
    # Should fail validation
    assert response.status_code == 422

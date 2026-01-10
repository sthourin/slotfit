"""
Tests for Equipment Profile API endpoints
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import EquipmentProfile, Equipment


@pytest.mark.asyncio
async def test_create_equipment_profile(client: AsyncClient, device_id: str):
    """Test creating an equipment profile"""
    headers = {"X-Device-ID": device_id}
    
    # First, get or create user
    await client.get("/api/v1/users/me", headers=headers)
    
    # Create equipment profile
    profile_data = {
        "name": "Home Gym",
        "description": "My home gym equipment",
        "equipment_ids": [],
        "is_default": True
    }
    
    response = await client.post(
        "/api/v1/equipment-profiles/",
        json=profile_data,
        headers=headers
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Home Gym"
    assert data["is_default"] is True
    assert "id" in data


@pytest.mark.asyncio
async def test_list_equipment_profiles(client: AsyncClient, device_id: str):
    """Test listing equipment profiles"""
    headers = {"X-Device-ID": device_id}
    
    # Create user
    await client.get("/api/v1/users/me", headers=headers)
    
    # Create multiple profiles
    profile1 = {
        "name": "Home Gym",
        "equipment_ids": [],
        "is_default": True
    }
    profile2 = {
        "name": "Work Gym",
        "equipment_ids": [],
        "is_default": False
    }
    
    await client.post("/api/v1/equipment-profiles/", json=profile1, headers=headers)
    await client.post("/api/v1/equipment-profiles/", json=profile2, headers=headers)
    
    # List profiles
    response = await client.get("/api/v1/equipment-profiles/", headers=headers)
    
    assert response.status_code == 200
    profiles = response.json()
    assert len(profiles) == 2
    # Default should be first
    assert profiles[0]["is_default"] is True


@pytest.mark.asyncio
async def test_get_equipment_profile(client: AsyncClient, device_id: str):
    """Test getting a single equipment profile"""
    headers = {"X-Device-ID": device_id}
    
    await client.get("/api/v1/users/me", headers=headers)
    
    # Create profile
    create_response = await client.post(
        "/api/v1/equipment-profiles/",
        json={"name": "Test Gym", "equipment_ids": []},
        headers=headers
    )
    profile_id = create_response.json()["id"]
    
    # Get profile
    response = await client.get(
        f"/api/v1/equipment-profiles/{profile_id}",
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == profile_id
    assert data["name"] == "Test Gym"


@pytest.mark.asyncio
async def test_update_equipment_profile(client: AsyncClient, device_id: str):
    """Test updating an equipment profile"""
    headers = {"X-Device-ID": device_id}
    
    await client.get("/api/v1/users/me", headers=headers)
    
    # Create profile
    create_response = await client.post(
        "/api/v1/equipment-profiles/",
        json={"name": "Original Name", "equipment_ids": []},
        headers=headers
    )
    profile_id = create_response.json()["id"]
    
    # Update profile
    update_data = {
        "name": "Updated Name",
        "description": "Updated description"
    }
    
    response = await client.put(
        f"/api/v1/equipment-profiles/{profile_id}",
        json=update_data,
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    # Description is optional and may not be in response schema


@pytest.mark.asyncio
async def test_set_default_equipment_profile(client: AsyncClient, device_id: str):
    """Test setting a profile as default (should clear other defaults)"""
    headers = {"X-Device-ID": device_id}
    
    await client.get("/api/v1/users/me", headers=headers)
    
    # Create two profiles
    profile1 = await client.post(
        "/api/v1/equipment-profiles/",
        json={"name": "Profile 1", "equipment_ids": [], "is_default": True},
        headers=headers
    )
    profile1_id = profile1.json()["id"]
    
    profile2 = await client.post(
        "/api/v1/equipment-profiles/",
        json={"name": "Profile 2", "equipment_ids": [], "is_default": False},
        headers=headers
    )
    profile2_id = profile2.json()["id"]
    
    # Set profile2 as default
    response = await client.post(
        f"/api/v1/equipment-profiles/{profile2_id}/set-default",
        headers=headers
    )
    
    assert response.status_code == 200
    
    # Verify profile1 is no longer default
    profile1_response = await client.get(
        f"/api/v1/equipment-profiles/{profile1_id}",
        headers=headers
    )
    assert profile1_response.json()["is_default"] is False
    
    # Verify profile2 is now default
    profile2_response = await client.get(
        f"/api/v1/equipment-profiles/{profile2_id}",
        headers=headers
    )
    assert profile2_response.json()["is_default"] is True


@pytest.mark.asyncio
async def test_delete_equipment_profile(client: AsyncClient, device_id: str):
    """Test deleting an equipment profile"""
    headers = {"X-Device-ID": device_id}
    
    await client.get("/api/v1/users/me", headers=headers)
    
    # Create profile
    create_response = await client.post(
        "/api/v1/equipment-profiles/",
        json={"name": "To Delete", "equipment_ids": []},
        headers=headers
    )
    profile_id = create_response.json()["id"]
    
    # Delete profile
    response = await client.delete(
        f"/api/v1/equipment-profiles/{profile_id}",
        headers=headers
    )
    
    assert response.status_code == 204
    
    # Verify it's gone
    get_response = await client.get(
        f"/api/v1/equipment-profiles/{profile_id}",
        headers=headers
    )
    assert get_response.status_code == 404

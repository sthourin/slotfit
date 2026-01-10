"""
Tests for Injury API endpoints
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_injury_types(client_with_data):
    """Test listing predefined injury types"""
    client, seed_data = client_with_data
    response = await client.get("/api/v1/injury-types")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    # Should have some predefined injuries
    injury = data[0]
    assert "id" in injury
    assert "name" in injury
    assert "body_area" in injury


@pytest.mark.asyncio
async def test_get_injury_type(client_with_data):
    """Test getting a single injury type with restrictions"""
    client, seed_data = client_with_data
    # First, get an injury type ID
    list_response = await client.get("/api/v1/injury-types")
    assert list_response.status_code == 200
    
    injury_types = list_response.json()
    assert len(injury_types) > 0
    
    injury_type_id = injury_types[0]["id"]
    
    response = await client.get(
        f"/api/v1/injury-types/{injury_type_id}"
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == injury_type_id
    assert "name" in data
    assert "restrictions" in data


@pytest.mark.asyncio
async def test_create_user_injury(client_with_data, device_id: str):
    """Test creating a user injury"""
    client, seed_data = client_with_data
    headers = {"X-Device-ID": device_id}
    
    # Get or create user
    await client.get("/api/v1/users/me", headers=headers)
    
    # Get an injury type
    injury_types_response = await client.get("/api/v1/injury-types")
    injury_types = injury_types_response.json()
    assert len(injury_types) > 0
    
    injury_type_id = injury_types[0]["id"]
    
    injury_data = {
        "injury_type_id": injury_type_id,
        "severity": "moderate",
        "notes": "Test injury"
    }
    
    response = await client.post(
        "/api/v1/user-injuries",
        json=injury_data,
        headers=headers
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["injury_type_id"] == injury_type_id
    assert data["severity"] == "moderate"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_user_injuries(client_with_data, device_id: str):
    """Test listing user injuries"""
    client, seed_data = client_with_data
    headers = {"X-Device-ID": device_id}
    
    await client.get("/api/v1/users/me", headers=headers)
    
    # Get an injury type
    injury_types_response = await client.get("/api/v1/injury-types")
    injury_types = injury_types_response.json()
    assert len(injury_types) > 0
    
    injury_type_id = injury_types[0]["id"]
    
    # Create an injury
    injury_data = {
        "injury_type_id": injury_type_id,
        "severity": "mild"
    }
    await client.post(
        "/api/v1/injuries/user-injuries",
        json=injury_data,
        headers=headers
    )
    
    # List injuries
    response = await client.get(
        "/api/v1/user-injuries",
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_update_user_injury(client_with_data, device_id: str):
    """Test updating a user injury"""
    client, seed_data = client_with_data
    headers = {"X-Device-ID": device_id}
    
    await client.get("/api/v1/users/me", headers=headers)
    
    # Get an injury type
    injury_types_response = await client.get("/api/v1/injury-types")
    injury_types = injury_types_response.json()
    assert len(injury_types) > 0
    
    injury_type_id = injury_types[0]["id"]
    
    # Create injury
    injury_data = {
        "injury_type_id": injury_type_id,
        "severity": "mild"
    }
    create_response = await client.post(
        "/api/v1/user-injuries",
        json=injury_data,
        headers=headers
    )
    injury_id = create_response.json()["id"]
    
    # Update injury
    update_data = {
        "severity": "moderate",
        "notes": "Updated notes"
    }
    
    response = await client.put(
        f"/api/v1/user-injuries/{injury_id}",
        json=update_data,
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["severity"] == "moderate"
    assert data["notes"] == "Updated notes"


@pytest.mark.asyncio
async def test_delete_user_injury(client_with_data, device_id: str):
    """Test deleting a user injury"""
    client, seed_data = client_with_data
    headers = {"X-Device-ID": device_id}
    
    await client.get("/api/v1/users/me", headers=headers)
    
    # Get an injury type
    injury_types_response = await client.get("/api/v1/injury-types")
    injury_types = injury_types_response.json()
    assert len(injury_types) > 0
    
    injury_type_id = injury_types[0]["id"]
    
    # Create injury
    injury_data = {
        "injury_type_id": injury_type_id,
        "severity": "mild"
    }
    create_response = await client.post(
        "/api/v1/user-injuries",
        json=injury_data,
        headers=headers
    )
    injury_id = create_response.json()["id"]
    
    # Delete injury
    response = await client.delete(
        f"/api/v1/user-injuries/{injury_id}",
        headers=headers
    )
    
    assert response.status_code == 204
    
    # Verify it's gone by trying to list injuries (should not include deleted one)
    list_response = await client.get(
        "/api/v1/user-injuries",
        headers=headers
    )
    assert list_response.status_code == 200
    injuries = list_response.json()
    injury_ids = [inj["id"] for inj in injuries]
    assert injury_id not in injury_ids

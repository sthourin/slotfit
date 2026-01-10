"""
Basic API endpoint tests
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """Test root endpoint"""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "SlotFit API"
    assert data["status"] == "running"


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """Test health check endpoint"""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_users_me_requires_device_id(client: AsyncClient):
    """Test that /users/me requires X-Device-ID header"""
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 400
    assert "X-Device-ID" in response.json()["detail"]


@pytest.mark.asyncio
async def test_users_me_with_device_id(client: AsyncClient, device_id: str):
    """Test that /users/me creates user with device ID"""
    response = await client.get(
        "/api/v1/users/me",
        headers={"X-Device-ID": device_id}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["device_id"] == device_id
    assert "id" in data
    assert "display_name" in data

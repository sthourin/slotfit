"""
Test script for Equipment Profile API endpoints
Run this after starting the server: uvicorn app.main:app --reload
"""
import asyncio
import httpx

BASE_URL = "http://localhost:8000/api/v1/equipment-profiles"


async def test_equipment_profiles_api():
    """Test all Equipment Profile API endpoints"""
    async with httpx.AsyncClient() as client:
        print("=" * 60)
        print("Testing Equipment Profile API")
        print("=" * 60)
        
        # Test 1: List profiles (should be empty initially)
        print("\n1. GET /equipment-profiles/ - List all profiles")
        response = await client.get(f"{BASE_URL}/")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        
        # Test 2: Create a profile
        print("\n2. POST /equipment-profiles/ - Create profile")
        create_data = {
            "name": "Home Gym",
            "equipment_ids": [1, 2, 3, 5],
            "is_default": True
        }
        response = await client.post(f"{BASE_URL}/", json=create_data)
        print(f"   Status: {response.status_code}")
        profile1 = response.json()
        print(f"   Created: {profile1}")
        profile1_id = profile1["id"]
        
        # Test 3: Create another profile (non-default)
        print("\n3. POST /equipment-profiles/ - Create second profile")
        create_data2 = {
            "name": "Commercial Gym",
            "equipment_ids": [1, 2, 3, 4, 5, 6, 7, 8],
            "is_default": False
        }
        response = await client.post(f"{BASE_URL}/", json=create_data2)
        print(f"   Status: {response.status_code}")
        profile2 = response.json()
        print(f"   Created: {profile2}")
        profile2_id = profile2["id"]
        
        # Test 4: Get single profile
        print(f"\n4. GET /equipment-profiles/{profile1_id} - Get single profile")
        response = await client.get(f"{BASE_URL}/{profile1_id}")
        print(f"   Status: {response.status_code}")
        print(f"   Profile: {response.json()}")
        
        # Test 5: Update profile
        print(f"\n5. PUT /equipment-profiles/{profile2_id} - Update profile")
        update_data = {
            "name": "Commercial Gym (Updated)",
            "equipment_ids": [1, 2, 3, 4, 5, 6, 7, 8, 9]
        }
        response = await client.put(f"{BASE_URL}/{profile2_id}", json=update_data)
        print(f"   Status: {response.status_code}")
        print(f"   Updated: {response.json()}")
        
        # Test 6: List all profiles (should show 2)
        print("\n6. GET /equipment-profiles/ - List all profiles again")
        response = await client.get(f"{BASE_URL}/")
        print(f"   Status: {response.status_code}")
        profiles = response.json()
        print(f"   Found {len(profiles)} profiles:")
        for p in profiles:
            print(f"     - {p['name']} (ID: {p['id']}, Default: {p['is_default']})")
        
        # Test 7: Set default
        print(f"\n7. POST /equipment-profiles/{profile2_id}/set-default - Set as default")
        response = await client.post(f"{BASE_URL}/{profile2_id}/set-default")
        print(f"   Status: {response.status_code}")
        updated_profile = response.json()
        print(f"   Updated: {updated_profile}")
        
        # Verify default was cleared on profile1
        print(f"\n8. Verify default was cleared on profile1")
        response = await client.get(f"{BASE_URL}/{profile1_id}")
        profile1_updated = response.json()
        print(f"   Profile1 is_default: {profile1_updated['is_default']}")
        print(f"   Profile2 is_default: {updated_profile['is_default']}")
        
        # Test 9: Delete profile
        print(f"\n9. DELETE /equipment-profiles/{profile1_id} - Delete profile")
        response = await client.delete(f"{BASE_URL}/{profile1_id}")
        print(f"   Status: {response.status_code}")
        
        # Verify deletion
        print(f"\n10. Verify deletion - GET /equipment-profiles/{profile1_id}")
        response = await client.get(f"{BASE_URL}/{profile1_id}")
        print(f"   Status: {response.status_code} (should be 404)")
        
        # Final list
        print("\n11. Final list of profiles")
        response = await client.get(f"{BASE_URL}/")
        profiles = response.json()
        print(f"   Remaining profiles: {len(profiles)}")
        for p in profiles:
            print(f"     - {p['name']} (ID: {p['id']})")
        
        print("\n" + "=" * 60)
        print("All tests completed!")
        print("=" * 60)


if __name__ == "__main__":
    print("\nMake sure the server is running:")
    print("  cd backend")
    print("  uvicorn app.main:app --reload\n")
    print("Starting tests in 2 seconds...\n")
    import time
    time.sleep(2)
    asyncio.run(test_equipment_profiles_api())

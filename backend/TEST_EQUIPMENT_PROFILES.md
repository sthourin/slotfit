# Testing Equipment Profile API

## Quick Start

### 1. Start the Server
```bash
cd backend
uvicorn app.main:app --reload
```

### 2. Open Swagger UI
Navigate to: http://localhost:8000/docs

Find the **equipment-profiles** section and test endpoints interactively.

---

## Test Examples

### Using Swagger UI (Recommended)

1. **Create a Profile**
   - Endpoint: `POST /api/v1/equipment-profiles/`
   - Body:
   ```json
   {
     "name": "Home Gym",
     "equipment_ids": [1, 2, 3, 5],
     "is_default": true
   }
   ```

2. **List Profiles**
   - Endpoint: `GET /api/v1/equipment-profiles/`

3. **Get Single Profile**
   - Endpoint: `GET /api/v1/equipment-profiles/{profile_id}`
   - Replace `{profile_id}` with actual ID from step 1

4. **Update Profile**
   - Endpoint: `PUT /api/v1/equipment-profiles/{profile_id}`
   - Body:
   ```json
   {
     "name": "Home Gym (Updated)",
     "equipment_ids": [1, 2, 3, 5, 7]
   }
   ```

5. **Set Default**
   - Endpoint: `POST /api/v1/equipment-profiles/{profile_id}/set-default`
   - This will clear `is_default` on all other profiles

6. **Delete Profile**
   - Endpoint: `DELETE /api/v1/equipment-profiles/{profile_id}`

---

### Using curl (Command Line)

```bash
# List all profiles
curl http://localhost:8000/api/v1/equipment-profiles/

# Create a profile
curl -X POST http://localhost:8000/api/v1/equipment-profiles/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Home Gym", "equipment_ids": [1, 2, 3], "is_default": true}'

# Get single profile (replace 1 with actual ID)
curl http://localhost:8000/api/v1/equipment-profiles/1

# Update profile
curl -X PUT http://localhost:8000/api/v1/equipment-profiles/1 \
  -H "Content-Type: application/json" \
  -d '{"name": "Updated Name", "equipment_ids": [1, 2, 3, 4]}'

# Set as default
curl -X POST http://localhost:8000/api/v1/equipment-profiles/1/set-default

# Delete profile
curl -X DELETE http://localhost:8000/api/v1/equipment-profiles/1
```

---

### Using Python Script

Run the automated test script:

```bash
cd backend
python test_equipment_profiles_api.py
```

This will test all endpoints automatically.

---

### Using Python Requests

```python
import requests

BASE_URL = "http://localhost:8000/api/v1/equipment-profiles"

# Create profile
response = requests.post(f"{BASE_URL}/", json={
    "name": "Home Gym",
    "equipment_ids": [1, 2, 3],
    "is_default": True
})
profile = response.json()
print(f"Created: {profile}")

# List profiles
response = requests.get(f"{BASE_URL}/")
profiles = response.json()
print(f"All profiles: {profiles}")

# Get single profile
profile_id = profile["id"]
response = requests.get(f"{BASE_URL}/{profile_id}")
print(f"Single profile: {response.json()}")

# Update profile
response = requests.put(f"{BASE_URL}/{profile_id}", json={
    "name": "Updated Name"
})
print(f"Updated: {response.json()}")

# Set default
response = requests.post(f"{BASE_URL}/{profile_id}/set-default")
print(f"Set default: {response.json()}")

# Delete profile
response = requests.delete(f"{BASE_URL}/{profile_id}")
print(f"Deleted: {response.status_code}")
```

---

## Expected Behavior

### Default Profile Logic

- When creating a profile with `is_default: true`, all other profiles' `is_default` is automatically set to `false`
- When updating a profile to `is_default: true`, all other profiles' `is_default` is automatically set to `false`
- The `/set-default` endpoint explicitly sets one profile as default and clears others
- Only one profile should have `is_default: true` at any time

### List Ordering

- Default profiles appear first (`is_default: true`)
- Then sorted alphabetically by name

### Error Handling

- 404 when profile ID doesn't exist
- 422 for invalid request data
- Proper validation of `equipment_ids` (must be array of integers)

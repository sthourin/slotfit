# SlotFit Backend Tests

This directory contains comprehensive tests for the SlotFit backend API.

## Running Tests

### Run All Tests
```bash
cd backend
pytest
```

### Run Specific Test File
```bash
pytest tests/test_exercises.py
```

### Run Specific Test
```bash
pytest tests/test_exercises.py::test_list_exercises
```

### Run with Coverage
```bash
pytest --cov=app --cov-report=html --cov-report=term-missing
```

### Run with Verbose Output
```bash
pytest -v
```

## Test Files

- **test_api_basic.py** - Basic API health checks and user endpoints
- **test_equipment_profiles.py** - Equipment profile CRUD operations
- **test_exercises.py** - Exercise listing, filtering, and duplication
- **test_routines.py** - Routine template CRUD and slot management
- **test_workouts.py** - Workout session lifecycle (create, update, complete)
- **test_injuries.py** - Injury types and user injury management
- **test_recommendations.py** - AI exercise recommendation endpoints
- **test_personal_records.py** - Personal record tracking
- **test_slot_templates.py** - Reusable slot template management

## Test Database

Tests use an in-memory SQLite database (configured in `conftest.py`). Each test gets a fresh database instance, so tests are isolated and can run in parallel.

## Test Fixtures

- **test_db** - Provides a fresh AsyncSession for each test
- **client** - Provides an AsyncClient for making HTTP requests
- **device_id** - Provides a test device ID for user authentication

## Writing New Tests

1. Follow the existing patterns in the test files
2. Use the `client` fixture for API calls
3. Use the `device_id` fixture for authenticated endpoints
4. Use `pytest.skip()` if prerequisites aren't met (e.g., no exercises in database)
5. Test both success and error cases

## Common Test Patterns

### Testing CRUD Operations
```python
@pytest.mark.asyncio
async def test_create_resource(client: AsyncClient, device_id: str):
    headers = {"X-Device-ID": device_id}
    await client.get("/api/v1/users/me", headers=headers)
    
    response = await client.post("/api/v1/resource/", json={...}, headers=headers)
    assert response.status_code == 201
```

### Testing with Prerequisites
```python
@pytest.mark.asyncio
async def test_requires_data(client: AsyncClient):
    response = await client.get("/api/v1/some-endpoint/")
    data = response.json()
    
    if not data:
        pytest.skip("No data available")
    
    # Continue with test...
```

## Notes

- Tests require the database to be initialized with seed data (exercises, muscle groups, equipment)
- Some tests may skip if required data isn't available
- The AI recommendation tests will work even if the AI service isn't configured (returns empty recommendations)

# SlotFit Backend Test Suite

This document provides an overview of all available tests and how to run them.

## Quick Start

### Run All Tests
```bash
cd backend
pytest
```

### Run with Coverage Report
```bash
pytest --cov=app --cov-report=html --cov-report=term-missing
```

### Run Specific Test Suite
```bash
# Equipment Profiles
pytest tests/test_equipment_profiles.py -v

# Exercises
pytest tests/test_exercises.py -v

# Routines
pytest tests/test_routines.py -v

# Workouts
pytest tests/test_workouts.py -v

# Injuries
pytest tests/test_injuries.py -v

# Recommendations
pytest tests/test_recommendations.py -v

# Personal Records
pytest tests/test_personal_records.py -v

# Slot Templates
pytest tests/test_slot_templates.py -v
```

## Test Coverage

### 1. Basic API Tests (`test_api_basic.py`)
- ✅ Root endpoint
- ✅ Health check endpoint
- ✅ User creation with device ID
- ✅ Device ID validation

### 2. Equipment Profiles (`test_equipment_profiles.py`)
- ✅ Create equipment profile
- ✅ List equipment profiles (with default ordering)
- ✅ Get single equipment profile
- ✅ Update equipment profile
- ✅ Set default profile (clears other defaults)
- ✅ Delete equipment profile

### 3. Exercises (`test_exercises.py`)
- ✅ List exercises with pagination
- ✅ Search exercises by name
- ✅ Filter by muscle group
- ✅ Filter by equipment
- ✅ Filter bodyweight exercises
- ✅ Get exercise by ID
- ✅ Duplicate exercise (create variant)

### 4. Routines (`test_routines.py`)
- ✅ Create routine template with slots
- ✅ List routine templates
- ✅ Get single routine template
- ✅ Update routine template
- ✅ Delete routine template
- ✅ Add slot to existing routine

### 5. Workouts (`test_workouts.py`)
- ✅ Create workout session from routine
- ✅ List workout sessions
- ✅ Get single workout session
- ✅ Update workout session (state, notes)
- ✅ Complete workout session
- ✅ Add exercise to workout

### 6. Injuries (`test_injuries.py`)
- ✅ List predefined injury types
- ✅ Get injury type with restrictions
- ✅ Create user injury
- ✅ List user injuries
- ✅ Update user injury
- ✅ Delete user injury

### 7. Recommendations (`test_recommendations.py`)
- ✅ Get basic recommendations by muscle group
- ✅ Get recommendations with equipment profile filter
- ✅ Get recommendations for specific routine slot

### 8. Personal Records (`test_personal_records.py`)
- ✅ Create personal record
- ✅ List personal records
- ✅ Get single personal record
- ✅ Update personal record
- ✅ Delete personal record
- ✅ Filter records by exercise

### 9. Slot Templates (`test_slot_templates.py`)
- ✅ Create slot template
- ✅ List slot templates
- ✅ Get single slot template
- ✅ Update slot template
- ✅ Delete slot template
- ✅ Validate slot_type enum

## Test Statistics

- **Total Test Files**: 9
- **Total Test Cases**: ~50+
- **Coverage**: All major API endpoints

## Prerequisites

Before running tests, ensure:

1. **Database is initialized** with seed data:
   - Exercises (imported from CSV)
   - Muscle groups
   - Equipment
   - Injury types (if testing injuries)

2. **Dependencies installed**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Test database**: Tests use in-memory SQLite (no setup needed)

## Test Isolation

- Each test gets a fresh in-memory database
- Tests are independent and can run in any order
- No cleanup needed between tests

## Common Issues

### Tests Skip Due to Missing Data
Some tests require seed data (exercises, muscle groups, etc.). If tests skip, ensure:
- Exercise database has been imported
- Muscle groups exist
- Equipment exists

### AI Recommendation Tests
These tests will pass even if the AI service isn't configured. They verify the endpoint structure, not the AI logic.

### Authentication Tests
All user-scoped endpoints require a `X-Device-ID` header. The test fixtures handle this automatically.

## Running Specific Test Scenarios

### Test Only CRUD Operations
```bash
pytest -k "test_create or test_list or test_get or test_update or test_delete" -v
```

### Test Only User-Scoped Endpoints
```bash
pytest -k "device_id" -v
```

### Test Only Public Endpoints
```bash
pytest tests/test_exercises.py tests/test_api_basic.py -v
```

## Continuous Integration

These tests are designed to run in CI/CD pipelines:
- No external dependencies (in-memory database)
- Fast execution
- Deterministic results
- Parallel execution supported

## Next Steps

To add more tests:
1. Follow patterns in existing test files
2. Use fixtures from `conftest.py`
3. Add to appropriate test file or create new one
4. Update this document

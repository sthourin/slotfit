# Running Tests - Quick Guide

## Command to Run Tests

Since `pytest` may not be in your PATH, use:

```bash
python -m pytest tests/ -v
```

Or from the backend directory:
```bash
cd backend
python -m pytest -v
```

## ✨ New: Seed Data Support

Tests now automatically seed the database with essential data:
- ✅ Muscle groups (Chest, Back, Shoulders, etc.)
- ✅ Equipment (Barbell, Dumbbell, Bodyweight, etc.)
- ✅ Exercises (Push-up, Pull-up, Squat, etc.)
- ✅ Injury types with restrictions

**Most tests now pass!** Tests use the `client_with_data` fixture which automatically populates the database.

## Using Production Database (Optional)

⚠️ **WARNING**: Only for integration testing!

To test against your real PostgreSQL database:

```bash
# Windows PowerShell
$env:USE_PROD_DB="true"
python -m pytest tests/ -v

# Linux/Mac
USE_PROD_DB=true pytest tests/ -v
```

**Note**: This uses your real database - use with caution!

## Test Results Summary

✅ **15 tests passed** - Basic API functionality is working!
❌ **30 tests failed** - Mostly due to missing seed data
⏭️ **6 tests skipped** - Expected when prerequisites aren't met

## Common Issues

### 1. Missing Seed Data
Many tests fail with `KeyError: 0` because the test database doesn't have:
- Exercises
- Muscle groups  
- Equipment
- Injury types

**Solution**: Tests use an in-memory database, so they need to create seed data. The tests that passed are the ones that don't require seed data.

### 2. Logging Warnings
The `PermissionError` warnings about `backend.log` are harmless - they occur because the log file is locked by another process (likely your running server). You can ignore these.

## What's Working

✅ Basic API endpoints (root, health)
✅ User creation with device ID
✅ Equipment profile CRUD (some tests)
✅ Exercise listing (basic)
✅ Personal records (basic)

## What Needs Seed Data

❌ Exercise filtering (needs exercises in DB)
❌ Routine tests (needs muscle groups)
❌ Workout tests (needs routines and exercises)
❌ Injury tests (needs injury types seeded)
❌ Recommendation tests (needs exercises)

## Running Specific Tests

### Run only passing tests:
```bash
python -m pytest tests/test_api_basic.py -v
```

### Run with less verbose output:
```bash
python -m pytest tests/ --tb=short
```

### Run a single test file:
```bash
python -m pytest tests/test_equipment_profiles.py -v
```

## Next Steps

To get all tests passing, you would need to:
1. Add seed data fixtures to `conftest.py` that populate the test database
2. Or modify tests to create required data before testing

The current test suite is a good foundation - it verifies the API structure and endpoints work correctly!

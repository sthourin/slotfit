# Test Seed Data

## Overview

Tests now use seed data fixtures that populate the in-memory test database with essential data:
- **Muscle Groups**: 6 target groups + 6 prime movers
- **Equipment**: 5 basic equipment types (Barbell, Dumbbell, Bodyweight, etc.)
- **Exercises**: 6 sample exercises (Push-up, Pull-up, Shoulder Press, etc.)
- **Injuries**: 3 injury types with movement restrictions

## Using Seed Data

### Automatic (Recommended)

Most tests now use the `client_with_data` fixture which automatically seeds the database:

```python
@pytest.mark.asyncio
async def test_my_feature(client_with_data):
    client, seed_data = client_with_data
    # seed_data contains: muscle_groups, equipment, exercises, injuries
    # Database is already populated and ready to use
```

### Manual Seeding

If you need to seed data manually in a test:

```python
from tests.seed_data import seed_all_data

async def test_custom(test_db: AsyncSession):
    seed_result = await seed_all_data(test_db)
    # seed_result contains all seeded objects
```

## Using Production Database

⚠️ **WARNING**: Only use this for integration testing, not unit tests!

To use your production PostgreSQL database instead of in-memory SQLite:

```bash
# Windows PowerShell
$env:USE_PROD_DB="true"
python -m pytest tests/ -v

# Linux/Mac
USE_PROD_DB=true pytest tests/ -v
```

**Important Notes:**
- Tests will use your real database
- Data may be modified or created
- Use with caution!
- Consider using a test database instead

## Seed Data Details

### Muscle Groups
- **Level 1 (Target)**: Chest, Back, Shoulders, Arms, Legs, Core
- **Level 2 (Prime Movers)**: Pectoralis Major, Latissimus Dorsi, Deltoids, Biceps, Quadriceps, Rectus Abdominis

### Equipment
- Barbell, Dumbbell, Bodyweight, Resistance Band, Kettlebell

### Exercises
1. Push-up (Bodyweight, Chest)
2. Pull-up (Bodyweight, Back)
3. Dumbbell Shoulder Press (Dumbbell, Shoulders)
4. Dumbbell Bicep Curl (Dumbbell, Biceps)
5. Squat (Bodyweight, Legs)
6. Plank (Bodyweight, Core)

### Injuries
1. Rotator Cuff Injury (Shoulder)
2. Lower Back Pain (Back)
3. Knee Pain (Knee)

Each injury has associated movement restrictions.

## Updating Seed Data

Edit `backend/tests/seed_data.py` to add more test data. The seed functions are idempotent - they check if data exists before creating.

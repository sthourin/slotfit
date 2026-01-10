# Testing Injury-Aware Recommendations

This guide shows how to test the injury-aware recommendations feature.

## Prerequisites

1. Backend server running: `uvicorn app.main:app --reload --port 8000`
2. Database migrations applied: `alembic upgrade head`
3. Injury seed data loaded: `python -m app.data.seed_injuries`

## Step 1: Verify Injury Types Are Seeded

Open Swagger UI: http://localhost:8000/docs

**Test:** `GET /api/v1/injury-types`
- Should return a list of 12 injury types
- Try filtering by body area: `GET /api/v1/injury-types?body_area=Shoulder`

**Test:** `GET /api/v1/injury-types/{id}`
- Get details for a specific injury (e.g., ID 1 for "Rotator Cuff Injury")
- Should include `restrictions` array with movement restrictions

## Step 2: Add an Injury to User Profile

**Test:** `POST /api/v1/user-injuries`
```json
{
  "injury_type_id": 1,
  "severity": "moderate",
  "notes": "Recovering from physical therapy"
}
```

This adds "Rotator Cuff Injury" with moderate severity.

**Verify:** `GET /api/v1/user-injuries`
- Should return your active injury
- Should include injury type details

## Step 3: Test Recommendations with Injury Filtering

**Test:** `POST /api/v1/recommendations`
```json
{
  "muscle_group_ids": [1, 2],
  "available_equipment_ids": [1, 2, 3],
  "limit": 5
}
```

**Expected Results:**
1. `recommendations` array should NOT include exercises that match injury restrictions
2. `not_recommended` array should include exercises filtered by injury with reason like:
   - `"May aggravate Rotator Cuff Injury"`
3. Exercises with movement patterns like "Overhead Press", "Lateral Raise", "Upright Row" should appear in `not_recommended` (for Rotator Cuff Injury)

## Step 4: Test Severity-Based Filtering

**Update injury severity:**
```json
PUT /api/v1/user-injuries/{injury_id}
{
  "severity": "severe"
}
```

**Test recommendations again:**
- For Rotator Cuff Injury with "severe" severity, ALL "Push" exercises should be filtered out (since there's a force_type restriction with severity_threshold="severe")

**Change back to "mild":**
```json
PUT /api/v1/user-injuries/{injury_id}
{
  "severity": "mild"
}
```

- Only specific movement patterns should be restricted, not entire force types

## Step 5: Test Multiple Injuries

**Add another injury:**
```json
POST /api/v1/user-injuries
{
  "injury_type_id": 6,
  "severity": "moderate",
  "notes": "Lower back pain"
}
```

This adds "Lower Back Pain / Herniated Disc".

**Test recommendations:**
- Should filter exercises matching BOTH injuries
- `not_recommended` should show reasons for both injuries

## Step 6: Test Marking Injury as Healed

**Mark injury as inactive:**
```json
PUT /api/v1/user-injuries/{injury_id}
{
  "is_active": false
}
```

**Test recommendations:**
- Previously filtered exercises should now be recommended again
- `not_recommended` should no longer include that injury's reasons

## Step 7: Test with Different Providers

The injury filtering works with all AI providers:

1. **Claude Provider** (if ANTHROPIC_API_KEY is set)
   - Check prompt includes injury restrictions
   - Verify `not_recommended` includes injury reasons

2. **Gemini Provider** (if GEMINI_API_KEY is set)
   - Same as Claude

3. **Fallback Provider** (always available)
   - Rule-based filtering should exclude injury-matching exercises
   - `not_recommended` should have injury reasons

## Example Test Scenario

### Setup:
1. Add "Rotator Cuff Injury" (ID: 1) with severity "moderate"
2. Request recommendations for shoulder exercises (muscle_group_ids: [1, 2])

### Expected Behavior:
- **Should NOT recommend:**
  - Overhead Press (movement_pattern restriction)
  - Lateral Raise (movement_pattern restriction)
  - Upright Row (movement_pattern restriction)
  - Any Push exercises if severity is "severe"

- **Should recommend:**
  - Pull exercises
  - Isolation exercises
  - Exercises that don't match restrictions

- **not_recommended should include:**
  ```json
  {
    "exercise_id": 123,
    "exercise_name": "Overhead Press",
    "reason": "May aggravate Rotator Cuff Injury"
  }
  ```

## Testing via Python Script

You can also test programmatically:

```python
import asyncio
from app.core.database import AsyncSessionLocal
from app.services.ai.service import AIRecommendationService

async def test_injury_filtering():
    async with AsyncSessionLocal() as db:
        service = AIRecommendationService(db)
        
        # Get recommendations for shoulder exercises
        response = await service.get_recommendations(
            muscle_group_ids=[1, 2],  # Shoulder muscle groups
            available_equipment_ids=[1, 2, 3],
            limit=10
        )
        
        print(f"Total recommendations: {len(response.recommendations)}")
        print(f"Not recommended: {len(response.not_recommended)}")
        
        # Check for injury-related not_recommended entries
        injury_filtered = [
            entry for entry in response.not_recommended
            if "aggravate" in entry.reason.lower()
        ]
        print(f"Injury-filtered exercises: {len(injury_filtered)}")
        
        for entry in injury_filtered:
            print(f"  - {entry.exercise_name}: {entry.reason}")

if __name__ == "__main__":
    asyncio.run(test_injury_filtering())
```

## Verification Checklist

- [ ] Injury types are seeded (12 types)
- [ ] Can add injury to user profile
- [ ] Can list user injuries
- [ ] Recommendations exclude injury-matching exercises
- [ ] `not_recommended` includes injury reasons
- [ ] Severity-based filtering works (mild/moderate/severe)
- [ ] Multiple injuries are handled correctly
- [ ] Marking injury as inactive removes filtering
- [ ] All AI providers respect injury restrictions
- [ ] Bodyweight exercises still follow injury restrictions (no special treatment)

## Troubleshooting

**No injury types in database:**
```bash
cd backend
python -m app.data.seed_injuries
```

**Recommendations not filtering:**
- Verify user injury is `is_active: true`
- Check injury severity matches restriction threshold
- Verify exercise movement patterns match restrictions

**API errors:**
- Check database connection
- Verify migrations are applied: `alembic upgrade head`
- Check server logs for errors

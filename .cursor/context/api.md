# API Endpoints Quick Reference

Base URL: `http://localhost:8000/api/v1`

## Existing Endpoints

### Exercises
```
GET    /exercises              List exercises (with filters)
POST   /exercises              Create exercise
GET    /exercises/{id}         Get single exercise
PUT    /exercises/{id}         Update exercise
DELETE /exercises/{id}         Delete exercise
POST   /exercises/{id}/duplicate   Create variant
```

### Muscle Groups
```
GET    /muscle-groups          List all muscle groups
GET    /muscle-groups/{id}     Get single muscle group
```

### Equipment
```
GET    /equipment              List all equipment
GET    /equipment/{id}         Get single equipment
```

### Routines
```
GET    /routines               List routine templates
POST   /routines               Create routine template
GET    /routines/{id}          Get single routine
PUT    /routines/{id}          Update routine
DELETE /routines/{id}          Delete routine
GET    /routines/{id}/slots    Get slots for routine
POST   /routines/{id}/slots    Add slot to routine
```

### Workouts
```
GET    /workouts               List workout sessions
POST   /workouts               Create workout session
GET    /workouts/{id}          Get single workout
PUT    /workouts/{id}          Update workout
DELETE /workouts/{id}          Delete workout
POST   /workouts/{id}/start    Start workout
POST   /workouts/{id}/pause    Pause workout
POST   /workouts/{id}/complete Complete workout
POST   /workouts/{id}/abandon  Abandon workout
```

### Recommendations
```
POST   /recommendations        Get AI exercise recommendations
```

---

## NEW ENDPOINTS TO CREATE

### Equipment Profiles
```
GET    /equipment-profiles              List all profiles
POST   /equipment-profiles              Create profile
GET    /equipment-profiles/{id}         Get single profile
PUT    /equipment-profiles/{id}         Update profile
DELETE /equipment-profiles/{id}         Delete profile
POST   /equipment-profiles/{id}/set-default   Set as default profile
```

**Create/Update Schema:**
```json
{
  "name": "Home Gym",
  "equipment_ids": [1, 2, 5, 8],
  "is_default": false
}
```

### Slot Templates
```
GET    /slot-templates                  List templates (filter by slot_type)
POST   /slot-templates                  Create template
GET    /slot-templates/{id}             Get single template
PUT    /slot-templates/{id}             Update template
DELETE /slot-templates/{id}             Delete template
```

**Create/Update Schema:**
```json
{
  "name": "My Back Slot",
  "slot_type": "standard",
  "muscle_group_ids": [3, 4],
  "time_limit_seconds": null,
  "default_exercise_id": null,
  "target_sets": 3,
  "target_reps_min": 8,
  "target_reps_max": 12,
  "target_weight": null,
  "target_rest_seconds": 90,
  "notes": "Focus on lat engagement"
}
```

### Personal Records
```
GET    /personal-records                     List all PRs
GET    /personal-records/exercise/{id}       Get PRs for exercise
```

**Response Schema:**
```json
{
  "id": 1,
  "exercise_id": 42,
  "exercise_name": "Bench Press",
  "record_type": "weight",
  "value": 225.0,
  "context": {"reps": 5},
  "achieved_at": "2025-01-04T10:30:00Z",
  "workout_session_id": 15
}
```

### Analytics
```
GET    /analytics/weekly-volume?week_start=2025-01-01
GET    /analytics/slot-performance?routine_id=5
GET    /analytics/exercise-progression/{exercise_id}
GET    /analytics/movement-balance?workout_id=10
```

**Weekly Volume Response:**
```json
{
  "week_start": "2025-01-01",
  "muscle_groups": [
    {"muscle_group_id": 1, "name": "Chest", "total_sets": 12, "total_reps": 96, "total_volume": 15200},
    {"muscle_group_id": 2, "name": "Back", "total_sets": 15, "total_reps": 120, "total_volume": 18000}
  ]
}
```

### Enhanced Recommendations
```
POST   /recommendations/slot              Get recommendations for a slot
POST   /recommendations/quick-fill        Auto-fill all slots in workout
POST   /recommendations/generate-routine  Generate routine from constraints
```

**Quick-Fill Request:**
```json
{
  "workout_id": 5,
  "equipment_profile_id": 2
}
```

**Enhanced Recommendation Response:**
```json
{
  "recommendations": [
    {
      "exercise_id": 42,
      "exercise_name": "Barbell Bench Press",
      "priority_score": 0.92,
      "reasoning": "Not performed in 5 days, good for strength progression",
      "factors": {
        "frequency": "low",
        "last_performed": "2024-12-30",
        "progression_opportunity": true,
        "variety_boost": false,
        "movement_balance": "push needed",
        "weekly_volume_status": "chest at 60% weekly target"
      }
    }
  ],
  "not_recommended": [
    {
      "exercise_id": 43,
      "exercise_name": "Incline Dumbbell Press",
      "reason": "Performed yesterday - insufficient recovery"
    },
    {
      "exercise_id": 44,
      "exercise_name": "Cable Fly",
      "reason": "Cable machine not in selected equipment"
    }
  ],
  "total_candidates": 25,
  "filtered_by_equipment": 12
}
```

### Workout Enhancements
```
POST   /workouts/{id}/quick-fill         Auto-fill all slots
POST   /workouts/{id}/copy-last          Copy exercises from last workout with same routine
```

# SlotFit Implementation Tasks

> **For Cursor IDE**: Use `@` to reference files. Key references:
> - @.cursor/plans/slotfit_plan.md - Full project plan
> - @.cursor/context/schema.md - Database schema reference
> - @.cursor/context/api.md - API endpoints reference
> - @backend/app/models/ - Existing model patterns
> - @web/src/ - Web app source

---

## Phase 1: Backend Model Enhancements

### Task 1.1: Equipment Profile Model
**Status**: [x] Complete

Create the equipment profile model for location-based equipment presets.

**Reference**: @.cursor/context/schema.md (equipment_profiles table)

**Files to create:**
- `backend/app/models/equipment_profile.py`
- `backend/app/schemas/equipment_profile.py`

**Pattern to follow**: @backend/app/models/equipment.py

**Steps:**
1. Create model with fields from schema reference
2. Add to `backend/app/models/__init__.py`
3. Create Pydantic schemas (Create, Update, Response)
4. Run: `alembic revision --autogenerate -m "add equipment_profiles"`
5. Run: `alembic upgrade head`

**Test:** Can create profile via Python shell or API docs

---

### Task 1.2: Equipment Profile API
**Status**: [x] Complete

CRUD endpoints for equipment profiles.

**Reference**: @.cursor/context/api.md (Equipment Profiles section)

**Files to create:**
- `backend/app/api/v1/endpoints/equipment_profiles.py`

**Files to modify:**
- `backend/app/api/v1/api.py` (register router)

**Pattern to follow**: @backend/app/api/v1/endpoints/exercises.py

**Endpoints to implement:**
- GET /equipment-profiles
- POST /equipment-profiles
- GET /equipment-profiles/{id}
- PUT /equipment-profiles/{id}
- DELETE /equipment-profiles/{id}
- POST /equipment-profiles/{id}/set-default

**Special logic:** `set-default` should clear `is_default` on all other profiles first.

**Test:** All endpoints visible at http://localhost:8000/docs

---

### Task 1.3: Slot Template Model
**Status**: [x] Complete

Create reusable slot template model.

**Reference**: @.cursor/context/schema.md (slot_templates table)

**Files to create:**
- `backend/app/models/slot_template.py`
- `backend/app/schemas/slot_template.py`

**Validation needed:**
- `slot_type` must be one of: standard, warmup, finisher, active_recovery, wildcard

**Steps:**
1. Create model
2. Add SlotType enum or validator
3. Create Pydantic schemas
4. Run migration

---

### Task 1.4: Enhance RoutineSlot Model
**Status**: [x] Complete

Add new fields to existing RoutineSlot model.

**Reference**: @.cursor/context/schema.md (routine_slots NEW FIELDS section)

**File to modify:** @backend/app/models/routine.py

**New fields to add:**
```python
slot_type = Column(String, default='standard')
slot_template_id = Column(Integer, ForeignKey('slot_templates.id'), nullable=True)
time_limit_seconds = Column(Integer, nullable=True)
required_equipment_ids = Column(JSONB, nullable=True)
target_reps_min = Column(Integer, nullable=True)
target_reps_max = Column(Integer, nullable=True)
progression_rule = Column(JSONB, nullable=True)
```

**Steps:**
1. Add columns to model
2. Update relationship if needed
3. Create migration
4. Update Pydantic schemas in @backend/app/schemas/routine.py

---

### Task 1.5: Personal Records Model
**Status**: [x] Complete

Track PRs per exercise variant.

**Reference**: @.cursor/context/schema.md (personal_records table)

**Files to create:**
- `backend/app/models/personal_record.py`
- `backend/app/schemas/personal_record.py`

**RecordType enum values:** weight, reps, volume, time

---

### Task 1.6: Weekly Volume Model
**Status**: [x] Complete

Track weekly training volume per muscle group.

**Reference**: @.cursor/context/schema.md (weekly_volume table)

**Files to create:**
- `backend/app/models/weekly_volume.py`
- `backend/app/schemas/weekly_volume.py`

**Important:** Add unique constraint on (muscle_group_id, week_start, user_id)

---

### Task 1.7: Slot Template API
**Status**: [x] Complete

**Reference**: @.cursor/context/api.md (Slot Templates section)

**Files to create:**
- `backend/app/api/v1/endpoints/slot_templates.py`

**Endpoints:** Standard CRUD + filter by slot_type query param

---

### Task 1.8: Personal Records API
**Status**: [x] Complete

**Reference**: @.cursor/context/api.md (Personal Records section)

**Files to create:**
- `backend/app/api/v1/endpoints/personal_records.py`

**Endpoints:**
- GET /personal-records (list all, optional exercise_id filter)
- GET /personal-records/exercise/{exercise_id}

---

### Task 1.9: Analytics API
**Status**: [x] Complete

**Reference**: @.cursor/context/api.md (Analytics section)

**Files to create:**
- `backend/app/api/v1/endpoints/analytics.py`
- `backend/app/services/analytics_service.py`

**Endpoints:**
- GET /analytics/weekly-volume
- GET /analytics/slot-performance
- GET /analytics/exercise-progression/{exercise_id}

---

## Phase 2: AI Service Enhancements

### Task 2.1: Google Gemini API Integration
**Status**: [x] Complete

Add Google Gemini API as an alternative AI provider for exercise recommendations.

**Files created/modified:**
- `backend/app/services/ai/gemini_provider.py` - Gemini API provider implementation
- `backend/app/services/ai/service.py` - Updated to include Gemini in provider fallback chain
- `backend/app/core/config.py` - Added GEMINI_API_KEY configuration
- `backend/requirements.txt` - Added `google-genai>=0.2.0` dependency
- `backend/SETUP.md` - Added Gemini API key setup instructions

**Implementation details:**
- Uses new `google.genai` package (not deprecated `google-generativeai`)
- Model priority: `gemini-2.5-flash` → `gemini-2.0-flash` → `gemini-2.0-flash-001`
- Falls back gracefully if API key not configured or quota exceeded
- Provider priority: Claude → Gemini → Rule-based fallback
- Supports all enhanced features: weekly volume awareness, movement pattern balance

**Configuration:**
- Add `GEMINI_API_KEY=your_key_here` to `.env`
- Get API key from [Google AI Studio](https://makersuite.google.com/app/apikey)

**Test:** Verify Gemini provider works when GEMINI_API_KEY is set and Claude is unavailable

---

### Task 2.2: Enhanced Recommendation Response
**Status**: [x] Complete

Add "not_recommended" array to AI response to enable the "Why Not" section in the Exercise Selection Modal.

**Reference**: @.cursor/context/api.md (Enhanced Recommendation Response)

**Context files:**
- @backend/app/services/ai/service.py - Main recommendation service
- @backend/app/services/ai/base.py - Base schemas and interfaces
- @backend/app/services/ai/fallback_provider.py - Rule-based provider (pattern to follow)
- @backend/app/services/ai/claude_provider.py - Claude AI provider
- @backend/app/services/ai/gemini_provider.py - Gemini AI provider

---

#### Step 1: Update Base Schema
**File:** `backend/app/services/ai/base.py`

Add new dataclass for not-recommended exercises:
```python
@dataclass
class NotRecommendedExercise:
    exercise_id: int
    exercise_name: str
    reason: str  # Human-readable explanation
```

Update `RecommendationResponse` to include:
```python
not_recommended: List[NotRecommendedExercise] = field(default_factory=list)
```

---

#### Step 2: Update Pydantic Schemas
**File:** `backend/app/schemas/recommendation.py`

Add corresponding Pydantic models for API serialization:
- `NotRecommendedExerciseResponse` schema with fields: exercise_id, exercise_name, reason
- Update `RecommendationResponseSchema` to include `not_recommended: List[NotRecommendedExerciseResponse]`

---

#### Step 3: Update FallbackProvider (Most Important)
**File:** `backend/app/services/ai/fallback_provider.py`

Generate `not_recommended` entries for exercises that were filtered out.

**Reason categories to implement:**
1. `"Equipment not available: {equipment_name}"` - Exercise requires equipment not in `available_equipment_ids`
2. `"Weekly volume exceeded for {muscle_group} ({X} sets)"` - Muscle group has >20 sets this week
3. `"Performed {X} days ago - insufficient recovery"` - Exercise done in last 48 hours (if workout history available)
4. `"Does not target selected muscle groups"` - Exercise doesn't match slot's muscle group scope

**CRITICAL - Bodyweight Exercise Rule:**
Exercises with `primary_equipment_id IS NULL` (bodyweight exercises) should ALWAYS be included regardless of equipment filter. They must NEVER appear in `not_recommended` for equipment reasons.

**Implementation approach:**
```python
# 1. Query broader set of exercises (before equipment filter)
# 2. Apply muscle group filter first
# 3. Track which exercises get filtered by equipment and why
# 4. Track which exercises are deprioritized by weekly volume
# 5. Build not_recommended list with reasons
# 6. Limit not_recommended to top 10 entries
# 7. Prioritize showing diverse reason types (not all "equipment not available")
```

**Updated equipment filter logic:**
```python
# Include bodyweight exercises (primary_equipment_id IS NULL) always
if available_equipment_ids:
    query = query.where(
        or_(
            Exercise.primary_equipment_id.in_(available_equipment_ids),
            Exercise.secondary_equipment_id.in_(available_equipment_ids),
            Exercise.primary_equipment_id.is_(None),  # Bodyweight always included
        )
    )
```

---

#### Step 4: Update Claude Provider
**File:** `backend/app/services/ai/claude_provider.py`

Update the prompt to request `not_recommended` array in the JSON response.

Add to the expected response format in the prompt:
```
"not_recommended": [
  {"exercise_id": int, "exercise_name": "string", "reason": "string"}
]
```

Parse and include in response. If Claude doesn't return it, default to empty list.

---

#### Step 5: Update Gemini Provider
**File:** `backend/app/services/ai/gemini_provider.py`

Same changes as Claude provider - update prompt and parse response.

---

#### Step 6: Update API Endpoint
**File:** `backend/app/api/v1/endpoints/recommendations.py`

Ensure the endpoint returns the `not_recommended` field in the response using the updated schema.

---

#### Example Response Structure
```json
{
  "recommendations": [...],
  "not_recommended": [
    {
      "exercise_id": 43,
      "exercise_name": "Incline Dumbbell Press",
      "reason": "Performed 1 day ago - insufficient recovery"
    },
    {
      "exercise_id": 44,
      "exercise_name": "Cable Fly",
      "reason": "Equipment not available: Cable Machine"
    },
    {
      "exercise_id": 89,
      "exercise_name": "Chest Press Machine",
      "reason": "Weekly volume exceeded for Chest (22 sets)"
    }
  ],
  "total_candidates": 25,
  "filtered_by_equipment": 12,
  "provider": "fallback"
}
```

---

#### Testing
After implementation, test via Swagger UI at http://localhost:8000/docs:

1. POST /api/v1/recommendations with:
   - `muscle_group_ids`: [1, 2] (chest muscles)
   - `available_equipment_ids`: [1, 2] (limited equipment)
2. Verify `not_recommended` array contains entries with clear reasons
3. Verify bodyweight exercises are NOT in `not_recommended` for equipment reasons
4. Test with empty `available_equipment_ids` - should still work

---

#### Important Notes
- Keep `not_recommended` limited to ~10 entries to avoid response bloat
- Prioritize showing diverse reasons (don't show 10 "equipment not available")
- Bodyweight exercises (primary_equipment_id IS NULL) should NEVER be filtered for equipment reasons
- This feature is used by the "Why Not" expandable section in the Exercise Selection Modal (Task 4.4)

---

### Task 2.3: Periodization Awareness
**Status**: [x] Complete

Factor weekly volume into recommendations.

**Files to modify:**
- `backend/app/services/ai/service.py`
- `backend/app/services/ai/base.py`
- `backend/app/services/ai/claude_provider.py`
- `backend/app/services/ai/gemini_provider.py`
- `backend/app/services/ai/fallback_provider.py`

**Logic:**
1. Query WeeklyVolume for current week
2. Include in AI prompt context
3. Deprioritize muscle groups > 20 sets/week
4. Add weekly_volume_status to factors

---

### Task 2.4: Movement Pattern Balance
**Status**: [x] Complete

Balance push/pull, compound/isolation.

**Data source:** Exercise CSV has Movement Pattern columns

**Files modified:**
- `backend/app/services/ai/service.py` - Added `_get_workout_movement_patterns()` method and updated `get_recommendations()` to accept `workout_session_id`
- `backend/app/services/ai/base.py` - Updated interface to accept `movement_patterns` parameter
- `backend/app/services/ai/claude_provider.py` - Updated prompt to include movement pattern balance and boost underrepresented patterns
- `backend/app/services/ai/gemini_provider.py` - Updated prompt to include movement pattern balance and boost underrepresented patterns
- `backend/app/services/ai/fallback_provider.py` - Added logic to boost underrepresented movement patterns in rule-based recommendations
- `backend/app/api/v1/endpoints/recommendations.py` - Added optional `workout_session_id` query parameter

**Implementation:**
1. ✅ Calculate workout's current movement pattern counts (force_type, mechanics, movement_patterns)
2. ✅ Include in AI prompt with balance analysis
3. ✅ Boost underrepresented patterns (Push/Pull, Compound/Isolation)
4. ✅ Added `movement_balance` factor to recommendation response

---

### Task 2.5: Injury-Aware Recommendations
**Status**: [x] Complete

Add user injury profiles that filter exercises to prevent aggravating existing conditions. This is Phase 1 of injury support - using curated injury-to-movement-pattern mappings.

**IMPORTANT DISCLAIMER**: This feature helps users avoid potentially problematic exercises but is NOT medical advice. Users should consult healthcare professionals for injury management.

---

#### Step 1: Create Database Models

**File:** `backend/app/models/injury.py`

Create three models:

```python
from sqlalchemy import Column, String, Integer, ForeignKey, Text, Boolean, Table
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from app.models.base import Base

# Association table for injury -> restricted movement patterns
injury_movement_restrictions = Table(
    "injury_movement_restrictions",
    Base.metadata,
    Column("injury_type_id", Integer, ForeignKey("injury_types.id"), primary_key=True),
    Column("restriction_id", Integer, ForeignKey("movement_restrictions.id"), primary_key=True),
)


class InjuryType(Base):
    """Injury types with their movement restrictions - can be system-defined or user-created"""
    __tablename__ = "injury_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)  # e.g., "Rotator Cuff Injury"
    body_area = Column(String, nullable=False)  # e.g., "Shoulder", "Knee", "Lumbar Spine"
    description = Column(Text, nullable=True)  # Brief description
    severity_levels = Column(JSONB, default=["mild", "moderate", "severe"])
    is_system = Column(Boolean, default=False)  # True for seeded/predefined injuries, False for user-created
    user_id = Column(Integer, nullable=True)  # NULL for system injuries, set for user-created (when auth added)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    restrictions = relationship(
        "MovementRestriction",
        secondary=injury_movement_restrictions,
        back_populates="injuries"
    )
    user_injuries = relationship("UserInjury", back_populates="injury_type")


class MovementRestriction(Base):
    """Movement patterns or exercise attributes to avoid"""
    __tablename__ = "movement_restrictions"

    id = Column(Integer, primary_key=True, index=True)
    restriction_type = Column(String, nullable=False)  # "movement_pattern", "force_type", "plane_of_motion", "posture"
    restriction_value = Column(String, nullable=False)  # e.g., "Overhead Press", "Push", "Sagittal"
    severity_threshold = Column(String, default="mild")  # Applies at this severity and above
    
    # Relationships
    injuries = relationship(
        "InjuryType",
        secondary=injury_movement_restrictions,
        back_populates="restrictions"
    )


class UserInjury(Base):
    """User's active injuries"""
    __tablename__ = "user_injuries"

    id = Column(Integer, primary_key=True, index=True)
    injury_type_id = Column(Integer, ForeignKey("injury_types.id"), nullable=False)
    severity = Column(String, default="moderate")  # mild, moderate, severe
    notes = Column(Text, nullable=True)  # User's notes about their condition
    is_active = Column(Boolean, default=True)  # Can mark as healed without deleting
    user_id = Column(Integer, nullable=True)  # NULL for MVP (no auth)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    injury_type = relationship("InjuryType", back_populates="user_injuries")
```

**Don't forget:** Add to `backend/app/models/__init__.py`

---

#### Step 2: Create Pydantic Schemas

**File:** `backend/app/schemas/injury.py`

```python
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class MovementRestrictionResponse(BaseModel):
    id: int
    restriction_type: str
    restriction_value: str
    severity_threshold: str

    class Config:
        from_attributes = True


class InjuryTypeResponse(BaseModel):
    id: int
    name: str
    body_area: str
    description: Optional[str]
    severity_levels: List[str]
    restrictions: List[MovementRestrictionResponse] = []

    class Config:
        from_attributes = True


class InjuryTypeListResponse(BaseModel):
    """Simplified response for listing (without restrictions)"""
    id: int
    name: str
    body_area: str
    description: Optional[str]

    class Config:
        from_attributes = True


class UserInjuryCreate(BaseModel):
    injury_type_id: int
    severity: str = "moderate"  # mild, moderate, severe
    notes: Optional[str] = None


class UserInjuryUpdate(BaseModel):
    severity: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class UserInjuryResponse(BaseModel):
    id: int
    injury_type_id: int
    injury_type: InjuryTypeListResponse
    severity: str
    notes: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

---

#### Step 3: Create API Endpoints

**File:** `backend/app/api/v1/endpoints/injuries.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List

from app.core.database import get_db
from app.models.injury import InjuryType, UserInjury
from app.schemas.injury import (
    InjuryTypeResponse,
    InjuryTypeListResponse,
    UserInjuryCreate,
    UserInjuryUpdate,
    UserInjuryResponse,
)

router = APIRouter()


@router.get("/injury-types", response_model=List[InjuryTypeListResponse])
async def list_injury_types(
    body_area: str = None,
    db: AsyncSession = Depends(get_db)
):
    """List all predefined injury types, optionally filtered by body area"""
    query = select(InjuryType)
    if body_area:
        query = query.where(InjuryType.body_area == body_area)
    query = query.order_by(InjuryType.body_area, InjuryType.name)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/injury-types/{injury_type_id}", response_model=InjuryTypeResponse)
async def get_injury_type(
    injury_type_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get injury type with its movement restrictions"""
    query = select(InjuryType).where(
        InjuryType.id == injury_type_id
    ).options(selectinload(InjuryType.restrictions))
    result = await db.execute(query)
    injury_type = result.scalar_one_or_none()
    if not injury_type:
        raise HTTPException(status_code=404, detail="Injury type not found")
    return injury_type


@router.get("/user-injuries", response_model=List[UserInjuryResponse])
async def list_user_injuries(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """List user's injuries"""
    query = select(UserInjury).options(
        selectinload(UserInjury.injury_type)
    )
    if active_only:
        query = query.where(UserInjury.is_active == True)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/user-injuries", response_model=UserInjuryResponse)
async def add_user_injury(
    injury: UserInjuryCreate,
    db: AsyncSession = Depends(get_db)
):
    """Add an injury to user's profile"""
    # Verify injury type exists
    injury_type = await db.get(InjuryType, injury.injury_type_id)
    if not injury_type:
        raise HTTPException(status_code=404, detail="Injury type not found")
    
    # Check for duplicate active injury
    existing = await db.execute(
        select(UserInjury).where(
            UserInjury.injury_type_id == injury.injury_type_id,
            UserInjury.is_active == True
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="This injury is already in your profile")
    
    user_injury = UserInjury(**injury.model_dump())
    db.add(user_injury)
    await db.commit()
    await db.refresh(user_injury)
    
    # Load relationship for response
    await db.refresh(user_injury, ["injury_type"])
    return user_injury


@router.put("/user-injuries/{injury_id}", response_model=UserInjuryResponse)
async def update_user_injury(
    injury_id: int,
    updates: UserInjuryUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update user injury (severity, notes, or mark as healed)"""
    user_injury = await db.get(UserInjury, injury_id)
    if not user_injury:
        raise HTTPException(status_code=404, detail="User injury not found")
    
    for field, value in updates.model_dump(exclude_unset=True).items():
        setattr(user_injury, field, value)
    
    await db.commit()
    await db.refresh(user_injury, ["injury_type"])
    return user_injury


@router.delete("/user-injuries/{injury_id}")
async def delete_user_injury(
    injury_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Remove injury from user's profile"""
    user_injury = await db.get(UserInjury, injury_id)
    if not user_injury:
        raise HTTPException(status_code=404, detail="User injury not found")
    
    await db.delete(user_injury)
    await db.commit()
    return {"message": "Injury removed from profile"}
```

**Don't forget:** Register router in `backend/app/api/v1/api.py`

---

#### Step 4: Create Seed Data for Injury Types

**File:** `backend/app/data/seed_injuries.py`

Create seed data with common injuries and their movement restrictions:

```python
"""
Seed data for injury types and movement restrictions.
Run with: python -m app.data.seed_injuries
"""

INJURY_SEED_DATA = [
    {
        "name": "Rotator Cuff Injury",
        "body_area": "Shoulder",
        "description": "Injury to the muscles and tendons stabilizing the shoulder joint",
        "restrictions": [
            {"type": "movement_pattern", "value": "Overhead Press", "severity": "mild"},
            {"type": "movement_pattern", "value": "Lateral Raise", "severity": "mild"},
            {"type": "movement_pattern", "value": "Upright Row", "severity": "mild"},
            {"type": "force_type", "value": "Push", "severity": "severe"},  # Only severe
        ]
    },
    {
        "name": "AC Joint Separation",
        "body_area": "Shoulder",
        "description": "Injury to the acromioclavicular joint at top of shoulder",
        "restrictions": [
            {"type": "movement_pattern", "value": "Horizontal Press", "severity": "mild"},
            {"type": "movement_pattern", "value": "Dip", "severity": "mild"},
            {"type": "movement_pattern", "value": "Fly", "severity": "moderate"},
        ]
    },
    {
        "name": "Tennis Elbow (Lateral Epicondylitis)",
        "body_area": "Elbow",
        "description": "Pain on the outside of the elbow from overuse",
        "restrictions": [
            {"type": "movement_pattern", "value": "Wrist Extension", "severity": "mild"},
            {"type": "movement_pattern", "value": "Reverse Curl", "severity": "mild"},
            {"type": "movement_pattern", "value": "Pull", "severity": "severe"},
        ]
    },
    {
        "name": "Golfer's Elbow (Medial Epicondylitis)",
        "body_area": "Elbow",
        "description": "Pain on the inside of the elbow from overuse",
        "restrictions": [
            {"type": "movement_pattern", "value": "Wrist Flexion", "severity": "mild"},
            {"type": "movement_pattern", "value": "Curl", "severity": "moderate"},
        ]
    },
    {
        "name": "Lower Back Pain / Herniated Disc",
        "body_area": "Back",
        "description": "Pain in the lumbar region, possibly from disc issues",
        "restrictions": [
            {"type": "movement_pattern", "value": "Deadlift", "severity": "mild"},
            {"type": "movement_pattern", "value": "Good Morning", "severity": "mild"},
            {"type": "movement_pattern", "value": "Bent Over Row", "severity": "moderate"},
            {"type": "posture", "value": "Bent Over", "severity": "mild"},
            {"type": "plane_of_motion", "value": "Spinal Flexion", "severity": "mild"},
        ]
    },
    {
        "name": "Knee Pain (General)",
        "body_area": "Knee",
        "description": "General knee discomfort or mild injury",
        "restrictions": [
            {"type": "movement_pattern", "value": "Deep Squat", "severity": "mild"},
            {"type": "movement_pattern", "value": "Lunge", "severity": "moderate"},
            {"type": "movement_pattern", "value": "Leg Extension", "severity": "moderate"},
        ]
    },
    {
        "name": "ACL Injury / Recovery",
        "body_area": "Knee",
        "description": "Anterior cruciate ligament injury or post-surgery recovery",
        "restrictions": [
            {"type": "movement_pattern", "value": "Squat", "severity": "mild"},
            {"type": "movement_pattern", "value": "Lunge", "severity": "mild"},
            {"type": "movement_pattern", "value": "Jump", "severity": "mild"},
            {"type": "movement_pattern", "value": "Pivot", "severity": "mild"},
            {"type": "laterality", "value": "Unilateral", "severity": "moderate"},
        ]
    },
    {
        "name": "Patellar Tendinitis (Jumper's Knee)",
        "body_area": "Knee",
        "description": "Inflammation of the patellar tendon",
        "restrictions": [
            {"type": "movement_pattern", "value": "Jump", "severity": "mild"},
            {"type": "movement_pattern", "value": "Deep Squat", "severity": "mild"},
            {"type": "movement_pattern", "value": "Leg Extension", "severity": "mild"},
        ]
    },
    {
        "name": "Wrist Injury / Sprain",
        "body_area": "Wrist",
        "description": "Wrist pain or sprain affecting grip and wrist stability",
        "restrictions": [
            {"type": "movement_pattern", "value": "Wrist Curl", "severity": "mild"},
            {"type": "posture", "value": "Prone", "severity": "moderate"},  # Pushup position
            {"type": "movement_pattern", "value": "Push Up", "severity": "moderate"},
        ]
    },
    {
        "name": "Neck Pain / Strain",
        "body_area": "Neck",
        "description": "Cervical pain or muscle strain in the neck",
        "restrictions": [
            {"type": "movement_pattern", "value": "Shrug", "severity": "mild"},
            {"type": "movement_pattern", "value": "Overhead Press", "severity": "moderate"},
            {"type": "movement_pattern", "value": "Behind Neck", "severity": "mild"},
        ]
    },
    {
        "name": "Hip Impingement",
        "body_area": "Hip",
        "description": "Femoroacetabular impingement causing hip pain",
        "restrictions": [
            {"type": "movement_pattern", "value": "Deep Squat", "severity": "mild"},
            {"type": "movement_pattern", "value": "Hip Flexion", "severity": "moderate"},
            {"type": "movement_pattern", "value": "Lunge", "severity": "moderate"},
        ]
    },
    {
        "name": "Ankle Sprain",
        "body_area": "Ankle",
        "description": "Sprained ankle ligaments",
        "restrictions": [
            {"type": "movement_pattern", "value": "Calf Raise", "severity": "mild"},
            {"type": "movement_pattern", "value": "Jump", "severity": "mild"},
            {"type": "laterality", "value": "Unilateral", "severity": "moderate"},
        ]
    },
]

# Body areas for filtering
BODY_AREAS = ["Shoulder", "Elbow", "Back", "Knee", "Wrist", "Neck", "Hip", "Ankle"]
```

Create a migration script to seed this data, or add it to an Alembic migration.

---

#### Step 5: Integrate with Recommendation Service

**File:** `backend/app/services/ai/service.py`

Add method to fetch user injuries and their restrictions:

```python
async def _get_user_injury_restrictions(self) -> List[Dict[str, Any]]:
    """
    Get movement restrictions from user's active injuries.
    
    Returns list of restrictions with injury context:
    [
        {
            "injury_name": "Rotator Cuff Injury",
            "severity": "moderate",
            "restriction_type": "movement_pattern",
            "restriction_value": "Overhead Press"
        },
        ...
    ]
    """
    from app.models.injury import UserInjury, InjuryType, MovementRestriction
    
    query = select(UserInjury).where(
        UserInjury.is_active == True
    ).options(
        selectinload(UserInjury.injury_type).selectinload(InjuryType.restrictions)
    )
    result = await self.db.execute(query)
    user_injuries = result.scalars().all()
    
    restrictions = []
    severity_order = {"mild": 1, "moderate": 2, "severe": 3}
    
    for user_injury in user_injuries:
        user_severity = severity_order.get(user_injury.severity, 2)
        
        for restriction in user_injury.injury_type.restrictions:
            restriction_threshold = severity_order.get(restriction.severity_threshold, 1)
            
            # Only apply restriction if user's severity >= restriction threshold
            if user_severity >= restriction_threshold:
                restrictions.append({
                    "injury_name": user_injury.injury_type.name,
                    "severity": user_injury.severity,
                    "restriction_type": restriction.restriction_type,
                    "restriction_value": restriction.restriction_value,
                })
    
    return restrictions
```

Update `get_recommendations()` to pass injury restrictions to providers.

---

#### Step 6: Update FallbackProvider

**File:** `backend/app/services/ai/fallback_provider.py`

Add injury filtering to the recommendation logic:

```python
async def get_exercise_recommendations(
    self,
    muscle_group_ids: List[int],
    available_equipment_ids: List[int],
    user_workout_history: Optional[Dict[str, Any]] = None,
    weekly_volume: Optional[Dict[int, Dict[str, Any]]] = None,
    movement_patterns: Optional[Dict[str, Dict[str, int]]] = None,
    injury_restrictions: Optional[List[Dict[str, Any]]] = None,  # NEW PARAMETER
    limit: int = 5,
) -> RecommendationResponse:
```

Add filtering logic:

```python
def is_restricted_by_injury(exercise: Exercise, restrictions: List[Dict]) -> Optional[str]:
    """Check if exercise matches any injury restriction. Returns reason if restricted."""
    for r in restrictions:
        # Check movement pattern restrictions
        if r["restriction_type"] == "movement_pattern":
            patterns = [exercise.movement_pattern_1, exercise.movement_pattern_2, exercise.movement_pattern_3]
            if any(r["restriction_value"].lower() in (p or "").lower() for p in patterns):
                return f"May aggravate {r['injury_name']}"
        
        # Check force type restrictions
        elif r["restriction_type"] == "force_type":
            if exercise.force_type and r["restriction_value"].lower() in exercise.force_type.lower():
                return f"May aggravate {r['injury_name']}"
        
        # Check posture restrictions
        elif r["restriction_type"] == "posture":
            if exercise.posture and r["restriction_value"].lower() in exercise.posture.lower():
                return f"May aggravate {r['injury_name']}"
        
        # Check plane of motion restrictions
        elif r["restriction_type"] == "plane_of_motion":
            planes = [exercise.plane_of_motion_1, exercise.plane_of_motion_2, exercise.plane_of_motion_3]
            if any(r["restriction_value"].lower() in (p or "").lower() for p in planes):
                return f"May aggravate {r['injury_name']}"
        
        # Check laterality restrictions
        elif r["restriction_type"] == "laterality":
            if exercise.laterality and r["restriction_value"].lower() in exercise.laterality.lower():
                return f"May aggravate {r['injury_name']}"
    
    return None

# In the main method, filter exercises and track not_recommended:
for exercise in all_exercises:
    injury_reason = is_restricted_by_injury(exercise, injury_restrictions or [])
    if injury_reason:
        not_recommended.append(NotRecommendedExercise(
            exercise_id=exercise.id,
            exercise_name=exercise.name,
            reason=injury_reason
        ))
        continue  # Skip this exercise
    # ... rest of filtering logic
```

---

#### Step 7: Update AI Providers (Claude & Gemini)

Update prompts to include injury context:

```python
# Add to prompt context:
if injury_restrictions:
    prompt += f"""

User Injuries:
The user has the following active injuries. DO NOT recommend exercises that may aggravate these conditions:
{json.dumps(injury_restrictions, indent=2)}

For any exercise that could aggravate an injury, include it in the not_recommended array with reason "May aggravate [injury name]".
"""
```

---

#### Step 8: Run Migration

```bash
cd backend
alembic revision --autogenerate -m "add injury types and user injuries"
alembic upgrade head
```

Then seed the injury data.

---

#### Example API Usage

```bash
# List available injury types
GET /api/v1/injury-types

# Get injury details with restrictions
GET /api/v1/injury-types/1

# Add injury to profile
POST /api/v1/user-injuries
{
  "injury_type_id": 1,
  "severity": "moderate",
  "notes": "Recovering from physical therapy"
}

# Recommendations now include injury filtering
POST /api/v1/recommendations
{
  "muscle_group_ids": [1, 2],
  "available_equipment_ids": [1, 2, 3]
}
# Response includes:
# "not_recommended": [{"exercise_name": "Overhead Press", "reason": "May aggravate Rotator Cuff Injury"}]
```

---

#### Testing

1. Run migration and seed injury data
2. Add a test injury via API (e.g., Rotator Cuff, severity: moderate)
3. Request recommendations for shoulder exercises
4. Verify overhead pressing movements appear in `not_recommended` with injury reason
5. Mark injury as healed (`is_active: false`)
6. Verify those exercises are now recommended again

---

#### Important Notes

- **Disclaimer**: Add a disclaimer in the UI when users add injuries: "This feature helps avoid potentially problematic exercises but is not medical advice. Consult a healthcare professional for injury management."
- **Conservative approach**: When in doubt, exclude the exercise (better safe than sorry)
- **Severity matters**: Mild injuries may only restrict specific movements, while severe injuries may exclude entire force types
- **User override**: Future phase will allow users to override specific restrictions ("My PT cleared me for this")
- This is Phase 1 - future phases will add PubMed research integration and free-text injury input

---

## Phase 3: Web App Foundation

### Task 3.1: Tailwind CSS Setup
**Status**: [x] Complete

**Files to create/modify:**
- `web/tailwind.config.js`
- `web/postcss.config.js`
- `web/src/index.css`
- `web/package.json` (add dependencies)

**Commands:**
```bash
cd web
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

---

### Task 3.2: API Service Layer
**Status**: [x] Complete

TypeScript API client for backend.

**Files to create:**
- `web/src/services/api.ts` (base axios/fetch setup)
- `web/src/services/exercises.ts`
- `web/src/services/routines.ts`
- `web/src/services/workouts.ts`
- `web/src/services/equipmentProfiles.ts`
- `web/src/services/slotTemplates.ts`
- `web/src/services/recommendations.ts`
- `web/src/services/analytics.ts`

**Pattern:** Type-safe functions matching @.cursor/context/api.md

---

### Task 3.3: Zustand Stores
**Status**: [x] Complete

State management setup.

**Files to create:**
- `web/src/stores/workoutStore.ts` (active workout state)
- `web/src/stores/routineStore.ts` (routine editing state)
- `web/src/stores/equipmentStore.ts` (equipment profiles)
- `web/src/stores/uiStore.ts` (modals, toasts, theme)

**Features:**
- Persist workout state to localStorage
- Type-safe with TypeScript

---

### Task 3.4: Device-Based User System

**Status**: [x] Complete

Implement a user abstraction layer that works without authentication for MVP, but is architected to easily add real auth later. Uses device ID to identify users.

**Why this approach:**
- All code is written with proper user scoping from day one
- No refactoring needed when adding real authentication
- Each device gets its own data (injuries, equipment profiles, workout history)
- Industry standard pattern for MVP → Production evolution

---

#### Step 1: Create User Model

**File:** `backend/app/models/user.py`

```python
from sqlalchemy import Column, String, Integer, DateTime, Boolean
from sqlalchemy.sql import func
from app.models.base import Base


class User(Base):
    """User model - supports both device-based (MVP) and authenticated users (future)"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    
    # Device-based identification (MVP)
    device_id = Column(String, unique=True, index=True, nullable=True)
    
    # Future auth fields (nullable for now)
    email = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=True)
    
    # Profile info
    display_name = Column(String, default="Athlete")
    
    # Preferences (can expand later)
    preferred_units = Column(String, default="lbs")  # "lbs" or "kg"
    
    # Metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_seen_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<User(id={self.id}, device_id='{self.device_id}', display_name='{self.display_name}')>"
```

**Don't forget:** Add to `backend/app/models/__init__.py`

---

#### Step 2: Create User Schemas

**File:** `backend/app/schemas/user.py`

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class UserResponse(BaseModel):
    id: int
    device_id: Optional[str]
    display_name: str
    preferred_units: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    preferred_units: Optional[str] = None  # "lbs" or "kg"
```

---

#### Step 3: Create get_current_user Dependency

**File:** `backend/app/core/deps.py`

This is the **key abstraction** - all endpoints use this dependency to get the current user.

```python
from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.core.database import get_db
from app.core.config import settings
from app.models.user import User


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get the current user based on device ID header.
    
    For MVP: Uses X-Device-ID header to identify/create users
    For Future: Will validate JWT token and return authenticated user
    
    This abstraction allows swapping auth mechanisms without changing endpoint code.
    """
    
    # MVP Mode: Device-based identification
    device_id = request.headers.get("X-Device-ID")
    
    if not device_id:
        raise HTTPException(
            status_code=400,
            detail="X-Device-ID header is required. Generate a UUID on the client and send it with every request."
        )
    
    # Validate device_id format (should be UUID-like)
    if len(device_id) < 10 or len(device_id) > 50:
        raise HTTPException(
            status_code=400,
            detail="Invalid X-Device-ID format. Should be a UUID."
        )
    
    # Find existing user or create new one
    result = await db.execute(
        select(User).where(User.device_id == device_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        # Create new user for this device
        user = User(device_id=device_id)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        # Update last seen timestamp
        user.last_seen_at = datetime.utcnow()
        await db.commit()
    
    return user


# Optional: Dependency that doesn't require auth (for public endpoints)
async def get_optional_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> User | None:
    """
    Get current user if device ID provided, otherwise return None.
    Use for endpoints that work with or without user context.
    """
    device_id = request.headers.get("X-Device-ID")
    
    if not device_id:
        return None
    
    result = await db.execute(
        select(User).where(User.device_id == device_id)
    )
    return result.scalar_one_or_none()
```

---

#### Step 4: Create User API Endpoints

**File:** `backend/app/api/v1/endpoints/users.py`

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Get the current user's profile.
    Creates user automatically if device ID is new.
    """
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    updates: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update the current user's profile.
    """
    for field, value in updates.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    
    await db.commit()
    await db.refresh(current_user)
    return current_user
```

**Don't forget:** Register router in `backend/app/api/v1/api.py`:
```python
from app.api.v1.endpoints import users
api_router.include_router(users.router, prefix="/users", tags=["users"])
```

---

#### Step 5: Update Existing Endpoints to Use current_user

Update ALL user-scoped endpoints to use the `get_current_user` dependency and filter by `user_id`.

**Files to update:**
- `backend/app/api/v1/endpoints/equipment_profiles.py`
- `backend/app/api/v1/endpoints/injuries.py` 
- `backend/app/api/v1/endpoints/workouts.py`
- `backend/app/api/v1/endpoints/routines.py`
- `backend/app/api/v1/endpoints/personal_records.py`
- `backend/app/api/v1/endpoints/analytics.py`

**Pattern for each endpoint:**

```python
from app.core.deps import get_current_user
from app.models.user import User

@router.get("/equipment-profiles")
async def list_equipment_profiles(
    current_user: User = Depends(get_current_user),  # ADD THIS
    db: AsyncSession = Depends(get_db)
):
    # Filter by user_id
    query = select(EquipmentProfile).where(
        EquipmentProfile.user_id == current_user.id  # ADD THIS FILTER
    )
    # ...


@router.post("/equipment-profiles")
async def create_equipment_profile(
    profile: EquipmentProfileCreate,
    current_user: User = Depends(get_current_user),  # ADD THIS
    db: AsyncSession = Depends(get_db)
):
    # Set user_id when creating
    db_profile = EquipmentProfile(
        **profile.model_dump(),
        user_id=current_user.id  # ADD THIS
    )
    # ...
```

**Important:** The `exercises` and `muscle_groups` endpoints should NOT require user context - they are shared/global data.

---

#### Step 6: Update Models with Foreign Keys

Update models that have `user_id` to add proper foreign key relationship:

**Files to update:**
- `backend/app/models/equipment_profile.py`
- `backend/app/models/injury.py` (UserInjury)
- `backend/app/models/workout.py`
- `backend/app/models/routine.py`
- `backend/app/models/personal_record.py`
- `backend/app/models/weekly_volume.py`

**Pattern:**
```python
# Before:
user_id = Column(Integer, nullable=True)  # NULL for MVP

# After:
user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
user = relationship("User", backref="equipment_profiles")
```

**Note:** Run migration AFTER updating all models.

---

#### Step 7: Frontend - Device ID Generation and Storage

**File:** `web/src/services/api.ts`

Update the API client to generate and send device ID with every request:

```typescript
import { v4 as uuidv4 } from 'uuid';

const DEVICE_ID_KEY = 'slotfit_device_id';

/**
 * Get or create a persistent device ID for this browser.
 * This identifies the user for MVP (no auth required).
 */
function getDeviceId(): string {
  let deviceId = localStorage.getItem(DEVICE_ID_KEY);
  
  if (!deviceId) {
    deviceId = uuidv4();
    localStorage.setItem(DEVICE_ID_KEY, deviceId);
    console.log('Created new device ID:', deviceId);
  }
  
  return deviceId;
}

// Base API configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

/**
 * Fetch wrapper that automatically includes device ID header
 */
export async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const deviceId = getDeviceId();
  
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'X-Device-ID': deviceId,  // Always include device ID
      ...options.headers,
    },
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `API error: ${response.status}`);
  }
  
  return response.json();
}

// Export for use in stores if needed
export { getDeviceId };
```

**Install uuid package:**
```bash
cd web
npm install uuid
npm install -D @types/uuid
```

---

#### Step 8: Create User Store (Frontend)

**File:** `web/src/stores/userStore.ts`

```typescript
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { apiFetch } from '../services/api';

interface User {
  id: number;
  device_id: string | null;
  display_name: string;
  preferred_units: 'lbs' | 'kg';
  created_at: string;
}

interface UserStore {
  user: User | null;
  loading: boolean;
  error: string | null;
  
  // Actions
  fetchCurrentUser: () => Promise<void>;
  updateProfile: (updates: { display_name?: string; preferred_units?: string }) => Promise<void>;
  clearUser: () => void;
}

export const useUserStore = create<UserStore>()(
  persist(
    (set, get) => ({
      user: null,
      loading: false,
      error: null,

      fetchCurrentUser: async () => {
        set({ loading: true, error: null });
        try {
          const user = await apiFetch<User>('/users/me');
          set({ user, loading: false });
        } catch (error) {
          set({ error: (error as Error).message, loading: false });
        }
      },

      updateProfile: async (updates) => {
        set({ loading: true, error: null });
        try {
          const user = await apiFetch<User>('/users/me', {
            method: 'PUT',
            body: JSON.stringify(updates),
          });
          set({ user, loading: false });
        } catch (error) {
          set({ error: (error as Error).message, loading: false });
        }
      },

      clearUser: () => {
        set({ user: null, error: null });
      },
    }),
    {
      name: 'slotfit-user',
      partialize: (state) => ({ user: state.user }),
    }
  )
);
```

---

#### Step 9: Initialize User on App Load

**File:** `web/src/App.tsx`

Fetch user profile on app initialization:

```typescript
import { useEffect } from 'react';
import { useUserStore } from './stores/userStore';

function App() {
  const { fetchCurrentUser, user } = useUserStore();

  useEffect(() => {
    // Fetch/create user on app load
    fetchCurrentUser();
  }, [fetchCurrentUser]);

  // ... rest of app
}
```

---

#### Step 10: Run Migration

```bash
cd backend
alembic revision --autogenerate -m "add users table and update foreign keys"
alembic upgrade head
```

**Important Migration Note:** 
If you have existing data with `user_id = NULL`, you'll need to either:
1. Delete existing data (easiest for dev)
2. Create a default user and update existing records to reference it

---

#### Testing

1. **Backend:**
   - Start server: `uvicorn app.main:app --reload`
   - Test with curl (no device ID - should error):
     ```bash
     curl http://localhost:8000/api/v1/users/me
     # Expected: 400 error "X-Device-ID header is required"
     ```
   - Test with device ID (should create user):
     ```bash
     curl -H "X-Device-ID: test-device-123" http://localhost:8000/api/v1/users/me
     # Expected: User JSON with id, device_id, display_name
     ```
   - Test user-scoped endpoint:
     ```bash
     curl -H "X-Device-ID: test-device-123" http://localhost:8000/api/v1/equipment-profiles
     # Expected: Empty array (or user's profiles)
     ```

2. **Frontend:**
   - Open browser dev tools → Application → Local Storage
   - Verify `slotfit_device_id` is created
   - Check Network tab - all API requests should have `X-Device-ID` header
   - Open in incognito - should get a NEW device ID and separate data

---

#### Future Auth Upgrade Path

When ready to add real authentication:

1. Add auth provider (Clerk, Auth0, or custom JWT)
2. Update `get_current_user` dependency:
   ```python
   async def get_current_user(request: Request, db: AsyncSession) -> User:
       if settings.AUTH_ENABLED:
           # Validate JWT token, get user from token claims
           token = request.headers.get("Authorization")
           return await validate_token_and_get_user(token, db)
       else:
           # MVP: Device-based (existing code)
           device_id = request.headers.get("X-Device-ID")
           # ...
   ```
3. Add migration to link device-based users to authenticated accounts
4. **No other code changes needed** - all endpoints already use `current_user`

---

#### Important Notes

- **Device ID is sensitive**: Treat it like a session token. Don't log it or expose it.
- **Data isolation**: Each device ID gets completely separate data.
- **Lost device ID = lost data**: If user clears localStorage, they lose access to their data (acceptable for MVP).
- **Future linking**: Can add "link this device to account" feature when auth is added.
- This is the **industry standard pattern** for MVP → Production evolution.

---

### Task 3.5: User Profile & Settings Page

**Status**: [x] Complete

Create a settings page where users can manage their profile, equipment profiles, and injuries.

**Depends on:** Task 3.4 (User System)

**Files to create:**
- `web/src/pages/Settings.tsx`
- `web/src/components/settings/ProfileSection.tsx`
- `web/src/components/settings/EquipmentProfilesSection.tsx`
- `web/src/components/settings/InjuriesSection.tsx`
- `web/src/components/settings/EquipmentProfileModal.tsx`
- `web/src/components/settings/AddInjuryModal.tsx`

**Route:** `/settings`

---

#### Page Structure

```
Settings Page
├── Profile Section
│   ├── Display name (editable)
│   ├── Preferred units toggle (lbs/kg)
│   └── Device ID display (for debugging, collapsible)
│
├── Equipment Profiles Section
│   ├── List of profiles with equipment counts
│   ├── Default profile indicator (star icon)
│   ├── [+ Add Profile] button → Modal
│   ├── Edit/Delete actions per profile
│   └── "Set as Default" action
│
└── Injuries Section
    ├── Disclaimer banner: "Not medical advice..."
    ├── List of active injuries with severity badges
    ├── [+ Add Injury] button → Modal
    │   └── Select from predefined injury types
    │   └── Choose severity (mild/moderate/severe)
    │   └── Optional notes field
    ├── Edit severity / Mark as healed actions
    └── "Show healed injuries" toggle
```

---

#### Equipment Profile Modal

```
Create/Edit Equipment Profile Modal
├── Name input (e.g., "Home Gym", "Office Gym")
├── Equipment multi-select checklist
│   ├── Grouped by category (Free Weights, Machines, Cardio, etc.)
│   └── Search/filter equipment
├── "Set as default" checkbox
└── Save / Cancel buttons
```

---

#### Add Injury Modal

```
Add Injury Modal
├── Body area filter tabs (Shoulder, Knee, Back, etc.)
├── Injury type selection (cards or list)
│   └── Shows injury name + brief description
├── Severity selector (mild / moderate / severe)
│   └── With explanation of what each means
├── Notes textarea (optional)
├── Disclaimer checkbox: "I understand this is not medical advice"
└── Add / Cancel buttons
```

---

#### Implementation Notes

1. **Fetch data on mount:**
   - GET /users/me (profile)
   - GET /equipment-profiles (user's profiles)
   - GET /equipment (all available equipment for selection)
   - GET /user-injuries (user's injuries)
   - GET /injury-types (all available injury types)

2. **Equipment Profile CRUD:**
   - Use existing API endpoints from Task 1.2
   - After create/update, refresh the list
   - "Set as Default" calls POST /equipment-profiles/{id}/set-default

3. **Injury CRUD:**
   - Use existing API endpoints from Task 2.5
   - Group injury types by body_area in the modal
   - Show severity as colored badges (green/yellow/red)

4. **Styling:**
   - Use Tailwind CSS
   - Responsive layout (stack sections on mobile)
   - Toast notifications for success/error feedback

---

#### Testing

1. Create an equipment profile → verify it appears in list
2. Set profile as default → verify star indicator
3. Add an injury → verify it appears in active injuries
4. Mark injury as healed → verify it moves to healed section
5. Change display name → verify it persists
6. Open in incognito → verify completely separate data

---

## Phase 4: Web Workout Execution

### Task 4.1: Workout Start Flow
**Status**: [ ] Not Started

**Files to create:**
- `web/src/pages/WorkoutStart.tsx`
- `web/src/components/workout/RoutineSelector.tsx`
- `web/src/components/workout/EquipmentProfileSelector.tsx`
- `web/src/components/workout/QuickFillModal.tsx`
- `web/src/components/workout/LastWorkoutOption.tsx`

**Flow:**
1. Select routine from list
2. Select equipment profile (shows default)
3. Options: Quick-Fill or Copy Last Workout
4. Review slot exercises
5. Click "Start Workout"

---

### Task 4.2: Active Workout Interface
**Status**: [ ] Not Started

**Files to create:**
- `web/src/pages/Workout.tsx`
- `web/src/components/workout/SlotProgressBar.tsx`
- `web/src/components/workout/CurrentSlot.tsx`
- `web/src/components/workout/ExercisePanel.tsx`
- `web/src/components/workout/SetTracker.tsx`
- `web/src/components/workout/RestTimer.tsx`
- `web/src/components/workout/WorkoutControls.tsx`

**Features:**
- Slot progress bar (clickable)
- Current exercise with video link
- Set logging (reps, weight, rest)
- Rest timer with sound option
- Pause/Complete/Abandon buttons

---

### Task 4.3: Slot Navigation & Keyboard Shortcuts
**Status**: [ ] Not Started

**Files to create:**
- `web/src/hooks/useKeyboardShortcuts.ts`
- `web/src/hooks/useWorkoutNavigation.ts`

**Shortcuts:**
- `←` / `→` - Previous/Next slot
- `S` - Skip current slot
- `Enter` - Complete current set
- `Space` - Start/Stop rest timer
- `Escape` - Cancel action / Close modal

---

### Task 4.4: Exercise Selection Modal
**Status**: [ ] Not Started

**Files to create:**
- `web/src/components/workout/ExerciseSelector.tsx`
- `web/src/components/workout/RecommendationsPanel.tsx`
- `web/src/components/workout/WhyNotSection.tsx`
- `web/src/components/workout/ExerciseSearch.tsx`

**Features:**
- AI recommendations (top 5)
- "Why Not" expandable section
- Search/filter all exercises
- Equipment filter
- Video preview links

---

### Task 4.5: Workout Completion
**Status**: [ ] Not Started

**Files to create:**
- `web/src/components/workout/WorkoutSummary.tsx`
- `web/src/components/workout/PRNotification.tsx`
- `web/src/components/workout/VolumeBreakdown.tsx`

**Features:**
- Workout duration
- Volume per muscle group
- New PR highlights
- Save confirmation

---

## Phase 5: Analytics & History

### Task 5.1: Workout History Page
**Status**: [ ] Not Started

**Files to create:**
- `web/src/pages/WorkoutHistory.tsx`
- `web/src/components/history/WorkoutCard.tsx`
- `web/src/components/history/WorkoutDetail.tsx`

---

### Task 5.2: Analytics Dashboard
**Status**: [ ] Not Started

**Files to create:**
- `web/src/pages/Analytics.tsx`
- `web/src/components/analytics/VolumeChart.tsx`
- `web/src/components/analytics/ProgressionChart.tsx`
- `web/src/components/analytics/MovementBalance.tsx`
- `web/src/components/analytics/SlotPerformance.tsx`

**Charts:** Use recharts or chart.js

---

### Task 5.3: Personal Records Page
**Status**: [ ] Not Started

**Files to create:**
- `web/src/pages/PersonalRecords.tsx`
- `web/src/components/records/PRCard.tsx`
- `web/src/components/records/PRHistory.tsx`

---

## Verification Commands

After each task, verify with:

```bash
# Backend changes
cd backend
alembic upgrade head      # Apply migrations
pytest                    # Run tests
uvicorn app.main:app --reload  # Start server
# Check http://localhost:8000/docs

# Web changes
cd web
npm run dev              # Start dev server
npm run build            # Verify build works
# Check http://localhost:3000
```

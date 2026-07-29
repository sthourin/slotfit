# Pattern-Based Dynamic Sessions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace SlotFit's muscle-group-slot workout model with pattern-based dynamic sessions: day plans with pattern-coverage goals, live-built superset rounds (user anchors, app suggests antagonist partners from staple pools), and pattern-level progression.

**Architecture:** Clean-slate domain per the approved spec (`docs/superpowers/specs/2026-07-28-pattern-based-dynamic-sessions-design.md`). New SQLAlchemy models (`movement_patterns`, `exercise_pattern_map`, `day_plans`/`pattern_goals`, `training_sessions`→`superset_rounds`→`round_entries`→`entry_sets`, `staple_exercises`, `exercise_preferences`) sit alongside the old tables, which remain read-only history. Three new services (history, progression, suggestion) power a new API namespace, and the web app gets new pages (Day Plans, Session) that replace RoutineDesigner/WorkoutStart/Workout.

**Tech Stack:** FastAPI + SQLAlchemy async + Alembic + Pydantic v2 (backend); React 18 + TypeScript + Zustand + Tailwind + axios (web); pytest-asyncio (backend tests); Playwright (e2e).

## Global Constraints

- Python: type hints everywhere, Black-compatible formatting, docstrings on public functions.
- All new endpoints live under `/api/v1/` and resolve the user via `get_current_user` from `app/core/deps.py` (`X-Device-ID` header).
- Old tables (`routine_templates`, `routine_slots`, `workout_sessions`, `workout_exercises`, `workout_sets`) are NEVER written by new code — read-only history.
- Bodyweight exercises (`primary_equipment_id IS NULL`) are always equipment-available.
- Injury filtering is conservative: when a restriction matches, exclude.
- Backend tests use the existing fixtures in `backend/tests/conftest.py` (`client_with_data`, `device_id`) and pass `{"X-Device-ID": device_id}` headers.
- Migrations via `alembic revision --autogenerate -m "..."` then `alembic upgrade head`, run from `backend/`.
- Commit messages: prefix `[SH]`, e.g. `[SH] feat: add movement pattern taxonomy`.
- Frontend follows existing patterns: services wrap `apiClient` from `web/src/services/api.ts`; stores are Zustand; pages are Tailwind-styled function components.

## File Structure

Backend (create unless noted):

- `backend/app/models/movement_pattern.py` — MovementPattern, ExercisePatternMap
- `backend/app/models/day_plan.py` — DayPlan, PatternGoal
- `backend/app/models/training_session.py` — SessionState, TrainingSession, SupersetRound, RoundEntry, EntrySet
- `backend/app/models/staple.py` — StapleExercise, ExercisePreference
- `backend/app/models/__init__.py` — modify: register all new models
- `backend/app/services/pattern_taxonomy.py` — rollup rules + seed functions
- `backend/app/services/history_service.py` — unified legacy+new performance history
- `backend/app/services/progression_service.py` — e1RM, double progression, pattern trends
- `backend/app/services/suggestion_service.py` — anchor/partner suggestions + filters + why-not
- `backend/app/schemas/pattern.py`, `backend/app/schemas/day_plan.py`, `backend/app/schemas/training_session.py`, `backend/app/schemas/staple.py`, `backend/app/schemas/suggestion.py`
- `backend/app/api/v1/endpoints/patterns.py`, `day_plans.py`, `staples.py`, `training_sessions.py`, `suggestions.py`
- `backend/app/api/v1/api.py` — modify: register new routers
- `backend/scripts/seed_patterns.py` — seed taxonomy + exercise mapping
- `backend/scripts/backfill_staples.py` — derive staples from legacy history
- Tests: `backend/tests/test_pattern_taxonomy.py`, `test_history_service.py`, `test_progression_service.py`, `test_suggestion_service.py`, `test_day_plans.py`, `test_training_sessions.py`, `test_staples.py`, `test_suggestions_api.py`, `test_patterns_api.py`

Web (create unless noted):

- `web/src/services/patterns.ts`, `dayPlans.ts`, `staples.ts`, `sessions.ts`, `suggestions.ts`
- `web/src/stores/dayPlanStore.ts`, `web/src/stores/sessionStore.ts`
- `web/src/pages/DayPlans.tsx`, `web/src/pages/Session.tsx`
- `web/src/App.tsx` — modify: routes/nav cutover
- `web/e2e/dynamic-session.spec.ts` — new critical-path e2e

---

### Task 1: MovementPattern model + taxonomy seed

**Files:**
- Create: `backend/app/models/movement_pattern.py` (MovementPattern only in this task)
- Modify: `backend/app/models/__init__.py`
- Create: `backend/app/services/pattern_taxonomy.py` (PATTERNS + seed_movement_patterns)
- Test: `backend/tests/test_pattern_taxonomy.py`

**Interfaces:**
- Consumes: `app.models.base.Base`
- Produces: `MovementPattern` model (`id, slug, name, opposite_pattern_id, is_neutral, display_order`); `PATTERNS: list[dict]`; `async seed_movement_patterns(db: AsyncSession) -> None` (idempotent, resolves `opposite_pattern_id` by slug)

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_pattern_taxonomy.py
"""Tests for movement pattern taxonomy"""
import pytest
from sqlalchemy import select

from app.models import MovementPattern
from app.services.pattern_taxonomy import seed_movement_patterns


@pytest.mark.asyncio
async def test_seed_movement_patterns(test_db):
    await seed_movement_patterns(test_db)

    result = await test_db.execute(select(MovementPattern))
    patterns = {p.slug: p for p in result.scalars().all()}

    assert len(patterns) == 10
    assert patterns["horizontal_pull"].opposite_pattern_id == patterns["horizontal_push"].id
    assert patterns["horizontal_push"].opposite_pattern_id == patterns["horizontal_pull"].id
    assert patterns["vertical_pull"].opposite_pattern_id == patterns["vertical_push"].id
    assert patterns["knee_dominant"].opposite_pattern_id == patterns["hip_hinge"].id
    assert patterns["core"].is_neutral is True
    assert patterns["core"].opposite_pattern_id is None
    assert patterns["isolation"].is_neutral is True
    assert patterns["conditioning"].is_neutral is True
    assert patterns["carry"].is_neutral is True


@pytest.mark.asyncio
async def test_seed_is_idempotent(test_db):
    await seed_movement_patterns(test_db)
    await seed_movement_patterns(test_db)

    result = await test_db.execute(select(MovementPattern))
    assert len(result.scalars().all()) == 10
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_pattern_taxonomy.py -v`
Expected: FAIL with `ImportError: cannot import name 'MovementPattern'`

- [ ] **Step 3: Write the model**

```python
# backend/app/models/movement_pattern.py
"""
Movement pattern taxonomy models
"""
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import Base


class MovementPattern(Base):
    """Curated training pattern (~10 rows, seeded)."""
    __tablename__ = "movement_patterns"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    opposite_pattern_id = Column(Integer, ForeignKey("movement_patterns.id"), nullable=True)
    is_neutral = Column(Boolean, default=False, nullable=False)
    display_order = Column(Integer, nullable=False, default=0)

    opposite = relationship("MovementPattern", remote_side=[id], uselist=False)

    def __repr__(self):
        return f"<MovementPattern(id={self.id}, slug='{self.slug}')>"
```

Add to `backend/app/models/__init__.py`: import `MovementPattern` from `app.models.movement_pattern` and append `"MovementPattern"` to `__all__`.

- [ ] **Step 4: Write the seed function**

```python
# backend/app/services/pattern_taxonomy.py
"""
Movement pattern taxonomy: curated pattern list, seed helpers, and the
rollup that classifies raw exercise movement patterns into the curated ten.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.movement_pattern import MovementPattern

# Curated taxonomy. Opposites drive antagonist pairing; neutral patterns
# are valid as a superset's third entry with any pair.
PATTERNS: list[dict] = [
    {"slug": "horizontal_pull", "name": "Horizontal Pull", "opposite": "horizontal_push", "is_neutral": False, "display_order": 1},
    {"slug": "horizontal_push", "name": "Horizontal Push", "opposite": "horizontal_pull", "is_neutral": False, "display_order": 2},
    {"slug": "vertical_pull", "name": "Vertical Pull", "opposite": "vertical_push", "is_neutral": False, "display_order": 3},
    {"slug": "vertical_push", "name": "Vertical Push", "opposite": "vertical_pull", "is_neutral": False, "display_order": 4},
    {"slug": "knee_dominant", "name": "Knee Dominant", "opposite": "hip_hinge", "is_neutral": False, "display_order": 5},
    {"slug": "hip_hinge", "name": "Hip Hinge", "opposite": "knee_dominant", "is_neutral": False, "display_order": 6},
    {"slug": "core", "name": "Core", "opposite": None, "is_neutral": True, "display_order": 7},
    {"slug": "carry", "name": "Carry / Locomotion", "opposite": None, "is_neutral": True, "display_order": 8},
    {"slug": "isolation", "name": "Isolation", "opposite": None, "is_neutral": True, "display_order": 9},
    {"slug": "conditioning", "name": "Conditioning", "opposite": None, "is_neutral": True, "display_order": 10},
]


async def seed_movement_patterns(db: AsyncSession) -> None:
    """Idempotently seed the curated movement patterns and wire opposites."""
    result = await db.execute(select(MovementPattern))
    existing = {p.slug: p for p in result.scalars().all()}

    # Pass 1: ensure rows exist
    for spec in PATTERNS:
        if spec["slug"] not in existing:
            row = MovementPattern(
                slug=spec["slug"],
                name=spec["name"],
                is_neutral=spec["is_neutral"],
                display_order=spec["display_order"],
            )
            db.add(row)
            existing[spec["slug"]] = row
    await db.flush()

    # Pass 2: wire opposite FKs by slug
    for spec in PATTERNS:
        opposite_slug = spec["opposite"]
        existing[spec["slug"]].opposite_pattern_id = (
            existing[opposite_slug].id if opposite_slug else None
        )
    await db.commit()
```

- [ ] **Step 5: Create migration and run tests**

Run: `cd backend && alembic revision --autogenerate -m "add movement_patterns" && alembic upgrade head`
Run: `cd backend && pytest tests/test_pattern_taxonomy.py -v`
Expected: PASS (both tests)

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/movement_pattern.py backend/app/models/__init__.py backend/app/services/pattern_taxonomy.py backend/tests/test_pattern_taxonomy.py backend/alembic/versions/
git commit -m "[SH] feat: add movement pattern taxonomy model and seed"
```

---

### Task 2: ExercisePatternMap + classification rollup + seed script

**Files:**
- Modify: `backend/app/models/movement_pattern.py` (add ExercisePatternMap)
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/services/pattern_taxonomy.py` (add classify_exercise, seed_exercise_pattern_map)
- Create: `backend/scripts/seed_patterns.py`
- Test: `backend/tests/test_pattern_taxonomy.py` (extend)

**Interfaces:**
- Consumes: `MovementPattern`, `Exercise` (fields `movement_pattern_1`, `mechanics`)
- Produces: `ExercisePatternMap` model (`exercise_id` unique, `pattern_id`, `is_override`); `classify_exercise(raw_pattern: str | None, mechanics: str | None) -> str` (returns a pattern slug); `async seed_exercise_pattern_map(db: AsyncSession) -> int` (rows written; skips `is_override=True` rows)

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_pattern_taxonomy.py`:

```python
from app.models import Exercise, ExercisePatternMap
from app.services.pattern_taxonomy import classify_exercise, seed_exercise_pattern_map


def test_classify_exercise_rollup():
    # Direct compound mappings
    assert classify_exercise("Horizontal Pull", "Compound") == "horizontal_pull"
    assert classify_exercise("Vertical Pull", "Compound") == "vertical_pull"
    assert classify_exercise("Horizontal Push", "Compound") == "horizontal_push"
    assert classify_exercise("Horizontal Adduction", "Compound") == "horizontal_push"
    assert classify_exercise("Vertical Push", "Compound") == "vertical_push"
    assert classify_exercise("Knee Dominant", "Compound") == "knee_dominant"
    assert classify_exercise("Hip Hinge", "Compound") == "hip_hinge"
    assert classify_exercise("Hip Extension", "Compound") == "hip_hinge"
    # Core wins even for compound mechanics
    assert classify_exercise("Anti-Extension", "Compound") == "core"
    assert classify_exercise("Rotational", "Compound") == "core"
    assert classify_exercise("Isometric Hold", "Compound") == "core"
    # Carry / conditioning
    assert classify_exercise("Loaded Carry", "Compound") == "carry"
    assert classify_exercise("Locomotion", "Compound") == "conditioning"
    # Isolation mechanics trumps direct map (leg extension is Knee Dominant + Isolation)
    assert classify_exercise("Knee Dominant", "Isolation") == "isolation"
    assert classify_exercise("Elbow Flexion", "Isolation") == "isolation"
    # Unknown / unsorted falls back to isolation
    assert classify_exercise("Unsorted*", "Compound") == "isolation"
    assert classify_exercise(None, None) == "isolation"


@pytest.mark.asyncio
async def test_seed_exercise_pattern_map(test_db):
    await seed_movement_patterns(test_db)
    test_db.add(Exercise(name="Cable Row", movement_pattern_1="Horizontal Pull", mechanics="Compound"))
    test_db.add(Exercise(name="Leg Extension", movement_pattern_1="Knee Dominant", mechanics="Isolation"))
    await test_db.commit()

    written = await seed_exercise_pattern_map(test_db)
    assert written == 2

    result = await test_db.execute(
        select(ExercisePatternMap, Exercise.name, MovementPattern.slug)
        .join(Exercise, Exercise.id == ExercisePatternMap.exercise_id)
        .join(MovementPattern, MovementPattern.id == ExercisePatternMap.pattern_id)
    )
    by_name = {name: slug for _, name, slug in result.all()}
    assert by_name["Cable Row"] == "horizontal_pull"
    assert by_name["Leg Extension"] == "isolation"


@pytest.mark.asyncio
async def test_seed_preserves_overrides(test_db):
    await seed_movement_patterns(test_db)
    ex = Exercise(name="Rowing Machine", movement_pattern_1="Horizontal Pull", mechanics="Compound")
    test_db.add(ex)
    await test_db.commit()
    await seed_exercise_pattern_map(test_db)

    # Manually override to conditioning
    result = await test_db.execute(select(MovementPattern).where(MovementPattern.slug == "conditioning"))
    conditioning = result.scalar_one()
    result = await test_db.execute(select(ExercisePatternMap).where(ExercisePatternMap.exercise_id == ex.id))
    row = result.scalar_one()
    row.pattern_id = conditioning.id
    row.is_override = True
    await test_db.commit()

    await seed_exercise_pattern_map(test_db)  # re-seed must not clobber
    await test_db.refresh(row)
    assert row.pattern_id == conditioning.id
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_pattern_taxonomy.py -v`
Expected: FAIL with `ImportError: cannot import name 'ExercisePatternMap'`

- [ ] **Step 3: Add the model**

Append to `backend/app/models/movement_pattern.py`:

```python
class ExercisePatternMap(Base):
    """Maps each exercise to exactly one curated pattern."""
    __tablename__ = "exercise_pattern_map"

    id = Column(Integer, primary_key=True, index=True)
    exercise_id = Column(Integer, ForeignKey("exercises.id"), unique=True, nullable=False, index=True)
    pattern_id = Column(Integer, ForeignKey("movement_patterns.id"), nullable=False, index=True)
    is_override = Column(Boolean, default=False, nullable=False)

    exercise = relationship("Exercise")
    pattern = relationship("MovementPattern")

    def __repr__(self):
        return f"<ExercisePatternMap(exercise_id={self.exercise_id}, pattern_id={self.pattern_id})>"
```

Register `ExercisePatternMap` in `backend/app/models/__init__.py`.

- [ ] **Step 4: Add rollup + map seeding**

Append to `backend/app/services/pattern_taxonomy.py`:

```python
from app.models.exercise import Exercise
from app.models.movement_pattern import ExercisePatternMap

# Raw movement_pattern_1 values that always classify as core, regardless of mechanics
CORE_RAW = {
    "Anti-Extension", "Anti-Rotational", "Anti-Lateral Flexion",
    "Spinal Flexion", "Spinal Extension", "Rotational", "Isometric Hold",
}

# Direct raw -> curated mapping for compound movements
DIRECT_MAP = {
    "Horizontal Pull": "horizontal_pull",
    "Vertical Pull": "vertical_pull",
    "Horizontal Push": "horizontal_push",
    "Horizontal Adduction": "horizontal_push",
    "Vertical Push": "vertical_push",
    "Knee Dominant": "knee_dominant",
    "Hip Hinge": "hip_hinge",
    "Hip Extension": "hip_hinge",
}


def classify_exercise(raw_pattern: str | None, mechanics: str | None) -> str:
    """Roll up a raw movement pattern + mechanics into a curated pattern slug.

    Rule order matters: core > carry/conditioning > isolation mechanics > direct map > isolation fallback.
    """
    raw = (raw_pattern or "").strip()
    if raw in CORE_RAW:
        return "core"
    if raw == "Loaded Carry":
        return "carry"
    if raw == "Locomotion":
        return "conditioning"
    if (mechanics or "").strip() == "Isolation":
        return "isolation"
    return DIRECT_MAP.get(raw, "isolation")


async def seed_exercise_pattern_map(db: AsyncSession) -> int:
    """Classify every exercise into the map. Preserves is_override rows. Returns rows written."""
    result = await db.execute(select(MovementPattern))
    pattern_by_slug = {p.slug: p for p in result.scalars().all()}

    result = await db.execute(select(ExercisePatternMap))
    existing = {m.exercise_id: m for m in result.scalars().all()}

    result = await db.execute(select(Exercise))
    written = 0
    for exercise in result.scalars().all():
        slug = classify_exercise(exercise.movement_pattern_1, exercise.mechanics)
        pattern_id = pattern_by_slug[slug].id
        row = existing.get(exercise.id)
        if row is None:
            db.add(ExercisePatternMap(exercise_id=exercise.id, pattern_id=pattern_id))
            written += 1
        elif not row.is_override and row.pattern_id != pattern_id:
            row.pattern_id = pattern_id
            written += 1
    await db.commit()
    return written
```

- [ ] **Step 5: Write the seed script**

```python
# backend/scripts/seed_patterns.py
"""
Seed the movement pattern taxonomy and exercise->pattern map.
Run from backend/: python -m scripts.seed_patterns
"""
import asyncio

from app.core.database import AsyncSessionLocal
from app.services.pattern_taxonomy import seed_movement_patterns, seed_exercise_pattern_map


async def main() -> None:
    async with AsyncSessionLocal() as db:
        await seed_movement_patterns(db)
        written = await seed_exercise_pattern_map(db)
        print(f"Patterns seeded; exercise map rows written/updated: {written}")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 6: Create migration, run tests, run script**

Run: `cd backend && alembic revision --autogenerate -m "add exercise_pattern_map" && alembic upgrade head`
Run: `cd backend && pytest tests/test_pattern_taxonomy.py -v`
Expected: PASS (all tests)
Run: `cd backend && python -m scripts.seed_patterns`
Expected: prints a written count > 3000 (one row per exercise)

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/movement_pattern.py backend/app/models/__init__.py backend/app/services/pattern_taxonomy.py backend/scripts/seed_patterns.py backend/tests/test_pattern_taxonomy.py backend/alembic/versions/
git commit -m "[SH] feat: add exercise pattern map with rollup classification"
```

---

### Task 3: DayPlan + PatternGoal models and schemas

**Files:**
- Create: `backend/app/models/day_plan.py`
- Create: `backend/app/schemas/day_plan.py`
- Modify: `backend/app/models/__init__.py`
- Test: `backend/tests/test_day_plans.py` (model-level tests only in this task)

**Interfaces:**
- Consumes: `MovementPattern`, `User`
- Produces: `DayPlan` (`id, user_id, name, description, warmup_preferences: JSONB list[int] of exercise ids, rounds_target: int`, rel `goals`); `PatternGoal` (`id, day_plan_id, pattern_id, required: bool, target_sets: int | None, rep_range_min: int | None, rep_range_max: int | None`); Pydantic `DayPlanCreate/DayPlanUpdate/DayPlanResponse/PatternGoalCreate/PatternGoalResponse`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_day_plans.py
"""Tests for DayPlan models and API"""
import pytest
from sqlalchemy import select

from app.models import DayPlan, PatternGoal, MovementPattern, User
from app.services.pattern_taxonomy import seed_movement_patterns


@pytest.mark.asyncio
async def test_day_plan_with_goals(test_db):
    await seed_movement_patterns(test_db)
    user = User(device_id="test-device-12345")
    test_db.add(user)
    await test_db.flush()

    result = await test_db.execute(select(MovementPattern).where(MovementPattern.slug == "horizontal_pull"))
    hp = result.scalar_one()

    plan = DayPlan(
        user_id=user.id,
        name="Full Body A",
        warmup_preferences=[101, 102],
        rounds_target=3,
    )
    plan.goals.append(PatternGoal(pattern_id=hp.id, required=True, target_sets=6))
    test_db.add(plan)
    await test_db.commit()

    result = await test_db.execute(select(DayPlan).where(DayPlan.name == "Full Body A"))
    loaded = result.scalar_one()
    assert loaded.rounds_target == 3
    assert loaded.warmup_preferences == [101, 102]
    goals = (await test_db.execute(select(PatternGoal).where(PatternGoal.day_plan_id == loaded.id))).scalars().all()
    assert len(goals) == 1
    assert goals[0].required is True
    assert goals[0].rep_range_min is None  # defaults applied at service layer (8-12)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_day_plans.py -v`
Expected: FAIL with `ImportError: cannot import name 'DayPlan'`

- [ ] **Step 3: Write the models**

```python
# backend/app/models/day_plan.py
"""
Day Plan models - pattern-coverage goals replacing routine templates
"""
from sqlalchemy import Column, String, Integer, Text, Boolean, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class DayPlan(Base):
    __tablename__ = "day_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    warmup_preferences = Column(JSONB, nullable=False, default=list)  # ordered exercise ids, most preferred first
    rounds_target = Column(Integer, nullable=False, default=3)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", backref="day_plans")
    goals = relationship(
        "PatternGoal",
        back_populates="day_plan",
        cascade="all, delete-orphan",
        order_by="PatternGoal.id",
    )

    def __repr__(self):
        return f"<DayPlan(id={self.id}, name='{self.name}')>"


class PatternGoal(Base):
    __tablename__ = "pattern_goals"

    id = Column(Integer, primary_key=True, index=True)
    day_plan_id = Column(Integer, ForeignKey("day_plans.id"), nullable=False, index=True)
    pattern_id = Column(Integer, ForeignKey("movement_patterns.id"), nullable=False)
    required = Column(Boolean, default=True, nullable=False)
    target_sets = Column(Integer, nullable=True)
    rep_range_min = Column(Integer, nullable=True)  # service default 8 when unset
    rep_range_max = Column(Integer, nullable=True)  # service default 12 when unset

    day_plan = relationship("DayPlan", back_populates="goals")
    pattern = relationship("MovementPattern")

    def __repr__(self):
        return f"<PatternGoal(id={self.id}, day_plan_id={self.day_plan_id}, pattern_id={self.pattern_id})>"
```

Register `DayPlan`, `PatternGoal` in `backend/app/models/__init__.py`.

- [ ] **Step 4: Write the schemas**

```python
# backend/app/schemas/day_plan.py
"""Pydantic schemas for Day Plans"""
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class PatternGoalCreate(BaseModel):
    pattern_id: int
    required: bool = True
    target_sets: Optional[int] = Field(None, ge=1, le=30)
    rep_range_min: Optional[int] = Field(None, ge=1, le=50)
    rep_range_max: Optional[int] = Field(None, ge=1, le=50)


class PatternGoalResponse(PatternGoalCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    day_plan_id: int


class DayPlanCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    warmup_preferences: List[int] = []
    rounds_target: int = Field(3, ge=1, le=10)
    goals: List[PatternGoalCreate] = []


class DayPlanUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    warmup_preferences: Optional[List[int]] = None
    rounds_target: Optional[int] = Field(None, ge=1, le=10)
    goals: Optional[List[PatternGoalCreate]] = None  # full replacement when provided


class DayPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: Optional[str]
    warmup_preferences: List[int]
    rounds_target: int
    goals: List[PatternGoalResponse]
```

- [ ] **Step 5: Create migration and run tests**

Run: `cd backend && alembic revision --autogenerate -m "add day_plans and pattern_goals" && alembic upgrade head`
Run: `cd backend && pytest tests/test_day_plans.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/day_plan.py backend/app/schemas/day_plan.py backend/app/models/__init__.py backend/tests/test_day_plans.py backend/alembic/versions/
git commit -m "[SH] feat: add DayPlan and PatternGoal models"
```

---

### Task 4: TrainingSession / SupersetRound / RoundEntry / EntrySet models and schemas

**Files:**
- Create: `backend/app/models/training_session.py`
- Create: `backend/app/schemas/training_session.py`
- Modify: `backend/app/models/__init__.py`
- Test: `backend/tests/test_training_sessions.py` (model-level tests only in this task)

**Interfaces:**
- Consumes: `DayPlan`, `MovementPattern`, `Exercise`, `User`
- Produces: `SessionState` enum (`draft/active/completed/discarded`); `TrainingSession` (`id, user_id, day_plan_id, state, started_at, completed_at, notes`, rel `rounds`); `SupersetRound` (`id, session_id, order`, rel `entries`); `RoundEntry` (`id, round_id, position, exercise_id, pattern_id`, rel `sets`); `EntrySet` (`id, entry_id, set_number, weight, reps, time_seconds, completed`)

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_training_sessions.py
"""Tests for TrainingSession models and API"""
import pytest
from datetime import datetime
from sqlalchemy import select

from app.models import (
    TrainingSession, SupersetRound, RoundEntry, EntrySet,
    SessionState, MovementPattern, Exercise, User,
)
from app.services.pattern_taxonomy import seed_movement_patterns


@pytest.mark.asyncio
async def test_session_round_entry_set_hierarchy(test_db):
    await seed_movement_patterns(test_db)
    user = User(device_id="test-device-12345")
    ex = Exercise(name="Seated Cable Row", movement_pattern_1="Horizontal Pull", mechanics="Compound")
    test_db.add_all([user, ex])
    await test_db.flush()

    result = await test_db.execute(select(MovementPattern).where(MovementPattern.slug == "horizontal_pull"))
    hp = result.scalar_one()

    session = TrainingSession(user_id=user.id, state=SessionState.ACTIVE, started_at=datetime.utcnow())
    round1 = SupersetRound(order=1)
    entry = RoundEntry(position=1, exercise_id=ex.id, pattern_id=hp.id)
    entry.sets.append(EntrySet(set_number=1, weight=120.0, reps=10))
    round1.entries.append(entry)
    session.rounds.append(round1)
    test_db.add(session)
    await test_db.commit()

    result = await test_db.execute(select(TrainingSession).where(TrainingSession.user_id == user.id))
    loaded = result.scalar_one()
    assert loaded.state == SessionState.ACTIVE
    sets = (await test_db.execute(select(EntrySet))).scalars().all()
    assert len(sets) == 1
    assert sets[0].weight == 120.0
    assert sets[0].completed is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_training_sessions.py -v`
Expected: FAIL with `ImportError: cannot import name 'TrainingSession'`

- [ ] **Step 3: Write the models**

```python
# backend/app/models/training_session.py
"""
Training session models - live-built superset rounds
"""
import enum

from sqlalchemy import Column, String, Integer, Float, Boolean, Text, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.models.base import Base


class SessionState(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    DISCARDED = "discarded"


class TrainingSession(Base):
    __tablename__ = "training_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    day_plan_id = Column(Integer, ForeignKey("day_plans.id"), nullable=True)
    state = Column(
        SQLEnum(SessionState, values_callable=lambda x: [e.value for e in x]),
        default=SessionState.DRAFT, nullable=False,
    )
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    user = relationship("User", backref="training_sessions")
    day_plan = relationship("DayPlan")
    rounds = relationship(
        "SupersetRound", back_populates="session",
        order_by="SupersetRound.order", cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<TrainingSession(id={self.id}, state='{self.state.value}')>"


class SupersetRound(Base):
    __tablename__ = "superset_rounds"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("training_sessions.id"), nullable=False, index=True)
    order = Column(Integer, nullable=False)

    session = relationship("TrainingSession", back_populates="rounds")
    entries = relationship(
        "RoundEntry", back_populates="round",
        order_by="RoundEntry.position", cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<SupersetRound(id={self.id}, order={self.order})>"


class RoundEntry(Base):
    __tablename__ = "round_entries"

    id = Column(Integer, primary_key=True, index=True)
    round_id = Column(Integer, ForeignKey("superset_rounds.id"), nullable=False, index=True)
    position = Column(Integer, nullable=False)  # 1-3
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=False, index=True)
    # Denormalized at logging time so later mapping edits don't rewrite history
    pattern_id = Column(Integer, ForeignKey("movement_patterns.id"), nullable=False, index=True)

    round = relationship("SupersetRound", back_populates="entries")
    exercise = relationship("Exercise")
    pattern = relationship("MovementPattern")
    sets = relationship(
        "EntrySet", back_populates="entry",
        order_by="EntrySet.set_number", cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<RoundEntry(id={self.id}, position={self.position}, exercise_id={self.exercise_id})>"


class EntrySet(Base):
    __tablename__ = "entry_sets"

    id = Column(Integer, primary_key=True, index=True)
    entry_id = Column(Integer, ForeignKey("round_entries.id"), nullable=False, index=True)
    set_number = Column(Integer, nullable=False)
    weight = Column(Float, nullable=True)
    reps = Column(Integer, nullable=True)
    time_seconds = Column(Integer, nullable=True)
    completed = Column(Boolean, default=True, nullable=False)

    entry = relationship("RoundEntry", back_populates="sets")
```

Register `TrainingSession`, `SupersetRound`, `RoundEntry`, `EntrySet`, `SessionState` in `backend/app/models/__init__.py`.

- [ ] **Step 4: Write the schemas**

```python
# backend/app/schemas/training_session.py
"""Pydantic schemas for training sessions"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class EntrySetCreate(BaseModel):
    set_number: int = Field(..., ge=1, le=50)
    weight: Optional[float] = Field(None, ge=0)
    reps: Optional[int] = Field(None, ge=0, le=500)
    time_seconds: Optional[int] = Field(None, ge=0)
    completed: bool = True


class EntrySetResponse(EntrySetCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    entry_id: int


class RoundEntryCreate(BaseModel):
    exercise_id: int
    position: int = Field(..., ge=1, le=3)


class TargetResponse(BaseModel):
    weight: Optional[float]
    reps: int
    sets: int
    last_summary: Optional[str]  # e.g. "3x10 @ 120"


class RoundEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    round_id: int
    position: int
    exercise_id: int
    exercise_name: str
    pattern_id: int
    pattern_slug: str
    sets: List[EntrySetResponse] = []
    target: Optional[TargetResponse] = None


class SupersetRoundResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    session_id: int
    order: int
    entries: List[RoundEntryResponse] = []


class TrainingSessionCreate(BaseModel):
    day_plan_id: Optional[int] = None


class TrainingSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    day_plan_id: Optional[int]
    state: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    notes: Optional[str]
    rounds: List[SupersetRoundResponse] = []


class CoverageGoal(BaseModel):
    pattern_id: int
    slug: str
    name: str
    required: bool
    target_sets: int
    sets_done: int
    covered: bool


class CoverageResponse(BaseModel):
    goals: List[CoverageGoal]
```

- [ ] **Step 5: Create migration and run tests**

Run: `cd backend && alembic revision --autogenerate -m "add training sessions, rounds, entries, sets" && alembic upgrade head`
Run: `cd backend && pytest tests/test_training_sessions.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/training_session.py backend/app/schemas/training_session.py backend/app/models/__init__.py backend/tests/test_training_sessions.py backend/alembic/versions/
git commit -m "[SH] feat: add TrainingSession round/entry/set models"
```

---

### Task 5: StapleExercise + ExercisePreference models and schemas

**Files:**
- Create: `backend/app/models/staple.py`
- Create: `backend/app/schemas/staple.py`
- Modify: `backend/app/models/__init__.py`
- Test: `backend/tests/test_staples.py` (model-level tests only in this task)

**Interfaces:**
- Consumes: `MovementPattern`, `Exercise`, `User`
- Produces: `StapleExercise` (`id, user_id, pattern_id, exercise_id, is_active, added_at`; unique `(user_id, exercise_id)`); `ExercisePreference` (`id, user_id, exercise_id, preference` — value `"never"`; unique `(user_id, exercise_id)`); schemas `StapleCreate/StapleResponse/PreferenceCreate/PreferenceResponse`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_staples.py
"""Tests for staple exercises and exercise preferences"""
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import StapleExercise, ExercisePreference, MovementPattern, Exercise, User
from app.services.pattern_taxonomy import seed_movement_patterns


@pytest.mark.asyncio
async def test_staple_unique_per_user_exercise(test_db):
    await seed_movement_patterns(test_db)
    user = User(device_id="test-device-12345")
    ex = Exercise(name="Pull Up", movement_pattern_1="Vertical Pull", mechanics="Compound")
    test_db.add_all([user, ex])
    await test_db.flush()
    result = await test_db.execute(select(MovementPattern).where(MovementPattern.slug == "vertical_pull"))
    vp = result.scalar_one()

    test_db.add(StapleExercise(user_id=user.id, pattern_id=vp.id, exercise_id=ex.id))
    await test_db.commit()

    test_db.add(StapleExercise(user_id=user.id, pattern_id=vp.id, exercise_id=ex.id))
    with pytest.raises(IntegrityError):
        await test_db.commit()
    await test_db.rollback()


@pytest.mark.asyncio
async def test_preference_blacklist(test_db):
    user = User(device_id="test-device-12345")
    ex = Exercise(name="Barbell Bench Press", movement_pattern_1="Horizontal Push", mechanics="Compound")
    test_db.add_all([user, ex])
    await test_db.flush()

    test_db.add(ExercisePreference(user_id=user.id, exercise_id=ex.id, preference="never"))
    await test_db.commit()

    result = await test_db.execute(select(ExercisePreference).where(ExercisePreference.user_id == user.id))
    prefs = result.scalars().all()
    assert len(prefs) == 1
    assert prefs[0].preference == "never"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_staples.py -v`
Expected: FAIL with `ImportError: cannot import name 'StapleExercise'`

- [ ] **Step 3: Write the models**

```python
# backend/app/models/staple.py
"""
Staple exercises (per-pattern proven pool) and exercise preferences (blacklist)
"""
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class StapleExercise(Base):
    __tablename__ = "staple_exercises"
    __table_args__ = (UniqueConstraint("user_id", "exercise_id", name="uq_staple_user_exercise"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    pattern_id = Column(Integer, ForeignKey("movement_patterns.id"), nullable=False, index=True)
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    added_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    pattern = relationship("MovementPattern")
    exercise = relationship("Exercise")

    def __repr__(self):
        return f"<StapleExercise(user_id={self.user_id}, exercise_id={self.exercise_id})>"


class ExercisePreference(Base):
    __tablename__ = "exercise_preferences"
    __table_args__ = (UniqueConstraint("user_id", "exercise_id", name="uq_pref_user_exercise"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=False)
    preference = Column(String, nullable=False, default="never")  # only "never" for now

    exercise = relationship("Exercise")

    def __repr__(self):
        return f"<ExercisePreference(user_id={self.user_id}, exercise_id={self.exercise_id}, preference='{self.preference}')>"
```

Register `StapleExercise`, `ExercisePreference` in `backend/app/models/__init__.py`.

- [ ] **Step 4: Write the schemas**

```python
# backend/app/schemas/staple.py
"""Pydantic schemas for staples and exercise preferences"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class StapleCreate(BaseModel):
    exercise_id: int
    # pattern_id is resolved server-side from ExercisePatternMap


class StapleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    pattern_id: int
    exercise_id: int
    exercise_name: str
    is_active: bool
    added_at: datetime
    last_performed: Optional[datetime] = None  # derived, filled by endpoint


class PreferenceCreate(BaseModel):
    exercise_id: int
    preference: str = "never"


class PreferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    exercise_id: int
    exercise_name: str
    preference: str
```

- [ ] **Step 5: Create migration and run tests**

Run: `cd backend && alembic revision --autogenerate -m "add staple_exercises and exercise_preferences" && alembic upgrade head`
Run: `cd backend && pytest tests/test_staples.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/staple.py backend/app/schemas/staple.py backend/app/models/__init__.py backend/tests/test_staples.py backend/alembic/versions/
git commit -m "[SH] feat: add staple exercises and exercise preference blacklist"
```

---

### Task 6: History service (unified legacy + new performance history)

**Files:**
- Create: `backend/app/services/history_service.py`
- Test: `backend/tests/test_history_service.py`

**Interfaces:**
- Consumes: legacy `WorkoutSession/WorkoutExercise/WorkoutSet` (+`WorkoutState`), new `TrainingSession/SupersetRound/RoundEntry/EntrySet` (+`SessionState`)
- Produces:
  - `async last_performed_map(db, user_id: int, exercise_ids: list[int] | None = None) -> dict[int, datetime]` — most recent completed performance per exercise across BOTH histories (missing key = never performed)
  - `async times_performed_map(db, user_id: int) -> dict[int, int]` — completed-session performance counts per exercise across both histories
  - `async exercise_set_history(db, user_id: int, exercise_id: int, limit_sessions: int = 5) -> list[dict]` — newest-first `[{"performed_at": datetime, "sets": [(weight: float | None, reps: int | None), ...]}]`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_history_service.py
"""Tests for the unified history service (legacy + new tables)"""
import pytest
from datetime import datetime

from app.models import (
    User, Exercise, MovementPattern,
    WorkoutSession, WorkoutExercise, WorkoutSet,
    TrainingSession, SupersetRound, RoundEntry, EntrySet, SessionState,
)
from app.models.workout import WorkoutState
from app.services.pattern_taxonomy import seed_movement_patterns
from app.services.history_service import (
    last_performed_map, times_performed_map, exercise_set_history,
)
from sqlalchemy import select


async def _setup(test_db):
    await seed_movement_patterns(test_db)
    user = User(device_id="test-device-12345")
    ex = Exercise(name="Seated Cable Row", movement_pattern_1="Horizontal Pull", mechanics="Compound")
    test_db.add_all([user, ex])
    await test_db.flush()
    result = await test_db.execute(select(MovementPattern).where(MovementPattern.slug == "horizontal_pull"))
    return user, ex, result.scalar_one()


@pytest.mark.asyncio
async def test_history_spans_legacy_and_new(test_db):
    user, ex, hp = await _setup(test_db)

    # Legacy completed workout on Jan 5
    legacy = WorkoutSession(user_id=user.id, state=WorkoutState.COMPLETED,
                            started_at=datetime(2026, 1, 5, 9), completed_at=datetime(2026, 1, 5, 10))
    we = WorkoutExercise(exercise_id=ex.id)
    we.sets.append(WorkoutSet(set_number=1, weight=100.0, reps=10))
    we.sets.append(WorkoutSet(set_number=2, weight=100.0, reps=9))
    legacy.exercises.append(we)
    test_db.add(legacy)

    # New completed session on Feb 1
    new = TrainingSession(user_id=user.id, state=SessionState.COMPLETED,
                          started_at=datetime(2026, 2, 1, 9), completed_at=datetime(2026, 2, 1, 10))
    rnd = SupersetRound(order=1)
    entry = RoundEntry(position=1, exercise_id=ex.id, pattern_id=hp.id)
    entry.sets.append(EntrySet(set_number=1, weight=110.0, reps=10))
    rnd.entries.append(entry)
    new.rounds.append(rnd)
    test_db.add(new)
    await test_db.commit()

    last = await last_performed_map(test_db, user.id, [ex.id])
    assert last[ex.id] == datetime(2026, 2, 1, 10)  # newer of the two

    counts = await times_performed_map(test_db, user.id)
    assert counts[ex.id] == 2

    history = await exercise_set_history(test_db, user.id, ex.id)
    assert len(history) == 2
    assert history[0]["performed_at"] == datetime(2026, 2, 1, 10)  # newest first
    assert history[0]["sets"] == [(110.0, 10)]
    assert history[1]["sets"] == [(100.0, 10), (100.0, 9)]


@pytest.mark.asyncio
async def test_incomplete_sessions_are_ignored(test_db):
    user, ex, hp = await _setup(test_db)
    active = TrainingSession(user_id=user.id, state=SessionState.ACTIVE, started_at=datetime(2026, 3, 1, 9))
    rnd = SupersetRound(order=1)
    entry = RoundEntry(position=1, exercise_id=ex.id, pattern_id=hp.id)
    entry.sets.append(EntrySet(set_number=1, weight=110.0, reps=10))
    rnd.entries.append(entry)
    active.rounds.append(rnd)
    test_db.add(active)
    await test_db.commit()

    assert await last_performed_map(test_db, user.id, [ex.id]) == {}
    assert (await times_performed_map(test_db, user.id)).get(ex.id) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_history_service.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.history_service'`

- [ ] **Step 3: Write the service**

```python
# backend/app/services/history_service.py
"""
Unified exercise performance history across legacy workout tables
(read-only) and new training session tables.
"""
from collections import defaultdict
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workout import WorkoutSession, WorkoutExercise, WorkoutSet, WorkoutState
from app.models.training_session import (
    TrainingSession, SupersetRound, RoundEntry, EntrySet, SessionState,
)


def _legacy_base(user_id: int):
    """Select (exercise_id, completed_at) pairs from completed legacy workouts."""
    return (
        select(WorkoutExercise.exercise_id, WorkoutSession.completed_at)
        .join(WorkoutSession, WorkoutSession.id == WorkoutExercise.workout_session_id)
        .where(WorkoutSession.user_id == user_id, WorkoutSession.state == WorkoutState.COMPLETED)
    )


def _new_base(user_id: int):
    """Select (exercise_id, completed_at) pairs from completed training sessions."""
    return (
        select(RoundEntry.exercise_id, TrainingSession.completed_at)
        .join(SupersetRound, SupersetRound.id == RoundEntry.round_id)
        .join(TrainingSession, TrainingSession.id == SupersetRound.session_id)
        .where(TrainingSession.user_id == user_id, TrainingSession.state == SessionState.COMPLETED)
    )


async def last_performed_map(
    db: AsyncSession, user_id: int, exercise_ids: list[int] | None = None
) -> dict[int, datetime]:
    """Most recent completed performance per exercise, across both histories."""
    result: dict[int, datetime] = {}
    for base in (_legacy_base(user_id), _new_base(user_id)):
        rows = (await db.execute(base)).all()
        for exercise_id, completed_at in rows:
            if completed_at is None:
                continue
            if exercise_ids is not None and exercise_id not in exercise_ids:
                continue
            if exercise_id not in result or completed_at > result[exercise_id]:
                result[exercise_id] = completed_at
    return result


async def times_performed_map(db: AsyncSession, user_id: int) -> dict[int, int]:
    """Count of completed sessions in which each exercise appears, across both histories."""
    counts: dict[int, int] = defaultdict(int)
    for base in (_legacy_base(user_id), _new_base(user_id)):
        rows = (await db.execute(base)).all()
        for exercise_id, _completed_at in rows:
            counts[exercise_id] += 1
    return dict(counts)


async def exercise_set_history(
    db: AsyncSession, user_id: int, exercise_id: int, limit_sessions: int = 5
) -> list[dict]:
    """Per-session set history for one exercise, newest first.

    Returns: [{"performed_at": datetime, "sets": [(weight, reps), ...]}]
    """
    performances: list[dict] = []

    legacy_rows = (
        await db.execute(
            select(WorkoutSession.completed_at, WorkoutSet.weight, WorkoutSet.reps, WorkoutSet.set_number)
            .join(WorkoutExercise, WorkoutExercise.workout_session_id == WorkoutSession.id)
            .join(WorkoutSet, WorkoutSet.workout_exercise_id == WorkoutExercise.id)
            .where(
                WorkoutSession.user_id == user_id,
                WorkoutSession.state == WorkoutState.COMPLETED,
                WorkoutExercise.exercise_id == exercise_id,
            )
        )
    ).all()
    new_rows = (
        await db.execute(
            select(TrainingSession.completed_at, EntrySet.weight, EntrySet.reps, EntrySet.set_number)
            .join(SupersetRound, SupersetRound.session_id == TrainingSession.id)
            .join(RoundEntry, RoundEntry.round_id == SupersetRound.id)
            .join(EntrySet, EntrySet.entry_id == RoundEntry.id)
            .where(
                TrainingSession.user_id == user_id,
                TrainingSession.state == SessionState.COMPLETED,
                RoundEntry.exercise_id == exercise_id,
                EntrySet.completed == True,  # noqa: E712
            )
        )
    ).all()

    by_session: dict[datetime, list[tuple]] = defaultdict(list)
    for completed_at, weight, reps, set_number in list(legacy_rows) + list(new_rows):
        if completed_at is None:
            continue
        by_session[completed_at].append((set_number, weight, reps))

    for completed_at in sorted(by_session.keys(), reverse=True)[:limit_sessions]:
        ordered = sorted(by_session[completed_at], key=lambda t: t[0])
        performances.append({
            "performed_at": completed_at,
            "sets": [(weight, reps) for _n, weight, reps in ordered],
        })
    return performances
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_history_service.py -v`
Expected: PASS (both tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/history_service.py backend/tests/test_history_service.py
git commit -m "[SH] feat: add unified history service across legacy and new tables"
```

---

### Task 7: Progression service (e1RM, double progression, pattern trends)

**Files:**
- Create: `backend/app/services/progression_service.py`
- Test: `backend/tests/test_progression_service.py`

**Interfaces:**
- Consumes: `history_service.exercise_set_history`, `StapleExercise`
- Produces:
  - `estimate_1rm(weight: float, reps: int) -> float` — Epley: `weight * (1 + reps / 30)`
  - `next_target(last_sets: list[tuple[float | None, int | None]], rep_min: int = 8, rep_max: int = 12, increment: float = 5.0) -> dict` — `{"weight", "reps", "sets", "last_summary"}`; `None` input list → `{"weight": None, "reps": rep_min, "sets": 3, "last_summary": None}`
  - `async compute_entry_target(db, user_id, exercise_id, rep_min=8, rep_max=12) -> dict | None` — wraps history + next_target; None when no history
  - `async pattern_trend(db, user_id: int, pattern_id: int, weeks: int = 12) -> list[dict]` — `[{"week_start": date, "index": float}]`, each staple's weekly best e1RM normalized to its own first observed value (index 1.0 = baseline), averaged across staples

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_progression_service.py
"""Tests for progression math"""
import pytest
from datetime import datetime

from sqlalchemy import select

from app.models import (
    User, Exercise, MovementPattern, StapleExercise,
    TrainingSession, SupersetRound, RoundEntry, EntrySet, SessionState,
)
from app.services.pattern_taxonomy import seed_movement_patterns
from app.services.progression_service import estimate_1rm, next_target, pattern_trend


def test_estimate_1rm_epley():
    assert estimate_1rm(100.0, 10) == pytest.approx(133.33, abs=0.01)
    assert estimate_1rm(100.0, 1) == pytest.approx(103.33, abs=0.01)


def test_next_target_adds_rep_below_range_top():
    # Last: 3x10 @ 120, range 8-12 -> same weight, 11 reps
    target = next_target([(120.0, 10), (120.0, 10), (120.0, 10)])
    assert target == {"weight": 120.0, "reps": 11, "sets": 3, "last_summary": "3x10 @ 120"}


def test_next_target_bumps_weight_at_range_top():
    # All sets at rep_max -> +increment, back to rep_min
    target = next_target([(120.0, 12), (120.0, 12), (120.0, 12)], increment=5.0)
    assert target == {"weight": 125.0, "reps": 8, "sets": 3, "last_summary": "3x12 @ 120"}


def test_next_target_no_history():
    target = next_target([])
    assert target == {"weight": None, "reps": 8, "sets": 3, "last_summary": None}


def test_next_target_bodyweight_sets():
    # Weight None (bodyweight): progress reps only
    target = next_target([(None, 10), (None, 10)])
    assert target["weight"] is None
    assert target["reps"] == 11
    assert target["sets"] == 2


async def _completed_session(test_db, user, ex, pattern, when, weight, reps):
    s = TrainingSession(user_id=user.id, state=SessionState.COMPLETED, started_at=when, completed_at=when)
    r = SupersetRound(order=1)
    e = RoundEntry(position=1, exercise_id=ex.id, pattern_id=pattern.id)
    e.sets.append(EntrySet(set_number=1, weight=weight, reps=reps))
    r.entries.append(e)
    s.rounds.append(r)
    test_db.add(s)
    await test_db.commit()


@pytest.mark.asyncio
async def test_pattern_trend_normalizes_across_staples(test_db):
    await seed_movement_patterns(test_db)
    user = User(device_id="test-device-12345")
    row = Exercise(name="Cable Row", movement_pattern_1="Horizontal Pull", mechanics="Compound")
    test_db.add_all([user, row])
    await test_db.flush()
    result = await test_db.execute(select(MovementPattern).where(MovementPattern.slug == "horizontal_pull"))
    hp = result.scalar_one()
    test_db.add(StapleExercise(user_id=user.id, pattern_id=hp.id, exercise_id=row.id))
    await test_db.commit()

    # Week 1: 100x10 (e1RM 133.3, baseline -> index 1.0); Week 3: 110x10 (index 1.1)
    await _completed_session(test_db, user, row, hp, datetime(2026, 1, 5, 9), 100.0, 10)
    await _completed_session(test_db, user, row, hp, datetime(2026, 1, 19, 9), 110.0, 10)

    trend = await pattern_trend(test_db, user.id, hp.id, weeks=52)
    assert len(trend) == 2
    assert trend[0]["index"] == pytest.approx(1.0)
    assert trend[1]["index"] == pytest.approx(1.1, abs=0.001)
    assert trend[0]["week_start"] < trend[1]["week_start"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_progression_service.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.progression_service'`

- [ ] **Step 3: Write the service**

```python
# backend/app/services/progression_service.py
"""
Progression math: Epley e1RM, double progression targets, and
pattern-level normalized strength trends.
"""
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.staple import StapleExercise
from app.models.training_session import (
    TrainingSession, SupersetRound, RoundEntry, EntrySet, SessionState,
)
from app.services.history_service import exercise_set_history

DEFAULT_REP_MIN = 8
DEFAULT_REP_MAX = 12
DEFAULT_INCREMENT = 5.0
DEFAULT_SETS = 3


def estimate_1rm(weight: float, reps: int) -> float:
    """Epley estimated one-rep max."""
    return weight * (1 + reps / 30)


def _fmt_weight(weight: float) -> str:
    return f"{weight:g}"


def next_target(
    last_sets: list[tuple[float | None, int | None]],
    rep_min: int = DEFAULT_REP_MIN,
    rep_max: int = DEFAULT_REP_MAX,
    increment: float = DEFAULT_INCREMENT,
) -> dict:
    """Double progression: add a rep until every set hits rep_max, then add load.

    last_sets is the most recent completed session's sets as (weight, reps).
    """
    if not last_sets:
        return {"weight": None, "reps": rep_min, "sets": DEFAULT_SETS, "last_summary": None}

    weights = [w for w, _r in last_sets if w is not None]
    reps = [r for _w, r in last_sets if r is not None]
    top_weight = max(weights) if weights else None
    min_reps = min(reps) if reps else rep_min

    if reps and weights and len(set(weights)) == 1 and len(set(reps)) == 1:
        last_summary = f"{len(last_sets)}x{reps[0]} @ {_fmt_weight(weights[0])}"
    elif reps and not weights:
        last_summary = f"{len(last_sets)}x{reps[0]}"
    else:
        parts = [f"{r or 0}@{_fmt_weight(w) if w is not None else 'bw'}" for w, r in last_sets]
        last_summary = ", ".join(parts)

    all_at_top = bool(reps) and all(r is not None and r >= rep_max for _w, r in last_sets)
    if all_at_top and top_weight is not None:
        return {"weight": top_weight + increment, "reps": rep_min, "sets": len(last_sets), "last_summary": last_summary}
    return {"weight": top_weight, "reps": min(min_reps + 1, rep_max), "sets": len(last_sets), "last_summary": last_summary}


async def compute_entry_target(
    db: AsyncSession, user_id: int, exercise_id: int,
    rep_min: int = DEFAULT_REP_MIN, rep_max: int = DEFAULT_REP_MAX,
) -> dict | None:
    """Target for the next performance of an exercise, from its own history."""
    history = await exercise_set_history(db, user_id, exercise_id, limit_sessions=1)
    if not history:
        return None
    return next_target(history[0]["sets"], rep_min=rep_min, rep_max=rep_max)


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


async def pattern_trend(
    db: AsyncSession, user_id: int, pattern_id: int, weeks: int = 12
) -> list[dict]:
    """Normalized e1RM trend for a pattern across its active staples.

    Each staple's weekly best e1RM is divided by its own first observed
    e1RM (baseline), then staple indices are averaged per week.
    """
    result = await db.execute(
        select(StapleExercise.exercise_id).where(
            StapleExercise.user_id == user_id,
            StapleExercise.pattern_id == pattern_id,
            StapleExercise.is_active == True,  # noqa: E712
        )
    )
    staple_ids = [row[0] for row in result.all()]
    if not staple_ids:
        return []

    # weekly best e1RM per staple: {exercise_id: {week_start: best_e1rm}}
    weekly_best: dict[int, dict[date, float]] = defaultdict(dict)
    for exercise_id in staple_ids:
        history = await exercise_set_history(db, user_id, exercise_id, limit_sessions=weeks * 3)
        for perf in history:
            week = _week_start(perf["performed_at"].date())
            best = max(
                (estimate_1rm(w, r) for w, r in perf["sets"] if w is not None and r),
                default=None,
            )
            if best is None:
                continue
            if week not in weekly_best[exercise_id] or best > weekly_best[exercise_id][week]:
                weekly_best[exercise_id][week] = best

    # normalize each staple to its earliest week's value
    indices_by_week: dict[date, list[float]] = defaultdict(list)
    for exercise_id, series in weekly_best.items():
        if not series:
            continue
        baseline = series[min(series.keys())]
        for week, value in series.items():
            indices_by_week[week].append(value / baseline)

    cutoff = _week_start(date.today()) - timedelta(weeks=weeks)
    return [
        {"week_start": week, "index": sum(vals) / len(vals)}
        for week, vals in sorted(indices_by_week.items())
        if week >= cutoff
    ]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_progression_service.py -v`
Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/progression_service.py backend/tests/test_progression_service.py
git commit -m "[SH] feat: add progression service with e1RM and pattern trends"
```

---

### Task 8: Suggestion service (anchors, partners, filters, why-not)

**Files:**
- Create: `backend/app/services/suggestion_service.py`
- Create: `backend/app/schemas/suggestion.py`
- Test: `backend/tests/test_suggestion_service.py`

**Interfaces:**
- Consumes: `MovementPattern`, `ExercisePatternMap`, `StapleExercise`, `ExercisePreference`, `TrainingSession` hierarchy, `EquipmentProfile`, injury models, `history_service.last_performed_map`, `progression_service.compute_entry_target`
- Produces:
  - `async anchor_suggestions(db, user_id: int, session_id: int) -> dict` — `{"groups": [{"pattern": PatternInfo, "covered": bool, "staples": [SuggestionCard]}], "not_recommended": [...]}` — uncovered required goals first, then uncovered optional, then covered
  - `async partner_suggestions(db, user_id: int, session_id: int, anchor_exercise_id: int, position: int) -> dict` — `{"candidates": [SuggestionCard], "novelty": SuggestionCard | None, "not_recommended": [...]}`
  - `SuggestionCard` fields: `exercise_id, exercise_name, pattern_id, pattern_slug, equipment_name, is_bodyweight, last_performed, is_staple, target`
  - Not-recommended entries: `{"exercise_name": str, "reason": str}`, max 10, diverse reasons

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_suggestion_service.py
"""Tests for the suggestion engine"""
import pytest
from datetime import datetime

from sqlalchemy import select

from app.models import (
    User, Exercise, Equipment, MovementPattern, ExercisePatternMap,
    StapleExercise, ExercisePreference, DayPlan, PatternGoal,
    TrainingSession, SupersetRound, RoundEntry, EntrySet, SessionState,
)
from app.services.pattern_taxonomy import seed_movement_patterns, seed_exercise_pattern_map
from app.services.suggestion_service import anchor_suggestions, partner_suggestions


async def _pattern(db, slug):
    result = await db.execute(select(MovementPattern).where(MovementPattern.slug == slug))
    return result.scalar_one()


async def _setup(test_db):
    """User with a day plan (pull+push goals), staples on both patterns, one active session."""
    await seed_movement_patterns(test_db)
    user = User(device_id="test-device-12345")
    cable = Equipment(name="Cable Machine")
    db_bell = Equipment(name="Dumbbell")
    test_db.add_all([user, cable, db_bell])
    await test_db.flush()

    row = Exercise(name="Seated Cable Row", movement_pattern_1="Horizontal Pull",
                   mechanics="Compound", primary_equipment_id=cable.id)
    bench = Exercise(name="Dumbbell Bench Press", movement_pattern_1="Horizontal Push",
                     mechanics="Compound", primary_equipment_id=db_bell.id)
    pushup = Exercise(name="Push Up", movement_pattern_1="Horizontal Push",
                      mechanics="Compound", primary_equipment_id=None)  # bodyweight
    bb_bench = Exercise(name="Barbell Bench Press", movement_pattern_1="Horizontal Push",
                        mechanics="Compound", primary_equipment_id=cable.id)
    test_db.add_all([row, bench, pushup, bb_bench])
    await test_db.flush()
    await seed_exercise_pattern_map(test_db)

    hp = await _pattern(test_db, "horizontal_pull")
    hpush = await _pattern(test_db, "horizontal_push")

    test_db.add_all([
        StapleExercise(user_id=user.id, pattern_id=hp.id, exercise_id=row.id),
        StapleExercise(user_id=user.id, pattern_id=hpush.id, exercise_id=bench.id),
        StapleExercise(user_id=user.id, pattern_id=hpush.id, exercise_id=pushup.id),
    ])
    # Blacklist barbell bench
    test_db.add(ExercisePreference(user_id=user.id, exercise_id=bb_bench.id, preference="never"))

    plan = DayPlan(user_id=user.id, name="Full Body A", warmup_preferences=[], rounds_target=3)
    plan.goals.append(PatternGoal(pattern_id=hp.id, required=True, target_sets=3))
    plan.goals.append(PatternGoal(pattern_id=hpush.id, required=True, target_sets=3))
    test_db.add(plan)
    await test_db.flush()

    session = TrainingSession(user_id=user.id, day_plan_id=plan.id,
                              state=SessionState.ACTIVE, started_at=datetime(2026, 7, 29, 9))
    test_db.add(session)
    await test_db.commit()
    return user, session, {"row": row, "bench": bench, "pushup": pushup, "bb_bench": bb_bench,
                           "hp": hp, "hpush": hpush}


@pytest.mark.asyncio
async def test_anchor_groups_uncovered_goals_first(test_db):
    user, session, d = await _setup(test_db)
    result = await anchor_suggestions(test_db, user.id, session.id)

    slugs = [g["pattern"]["slug"] for g in result["groups"]]
    assert "horizontal_pull" in slugs and "horizontal_push" in slugs
    for group in result["groups"]:
        assert group["covered"] is False
        names = [c["exercise_name"] for c in group["staples"]]
        assert "Barbell Bench Press" not in names  # blacklisted


@pytest.mark.asyncio
async def test_partner_suggests_opposite_pattern(test_db):
    user, session, d = await _setup(test_db)
    # Anchor = cable row (horizontal_pull) -> partners must be horizontal_push staples
    result = await partner_suggestions(test_db, user.id, session.id,
                                       anchor_exercise_id=d["row"].id, position=2)
    names = [c["exercise_name"] for c in result["candidates"]]
    assert "Dumbbell Bench Press" in names
    assert "Push Up" in names
    assert "Barbell Bench Press" not in names  # blacklisted
    reasons = [n["reason"] for n in result["not_recommended"]]
    assert any("never" in r.lower() or "blacklist" in r.lower() for r in reasons)


@pytest.mark.asyncio
async def test_partner_ranked_least_recent_first(test_db):
    user, session, d = await _setup(test_db)
    # Bench performed recently; push up never -> push up ranks first
    done = TrainingSession(user_id=user.id, state=SessionState.COMPLETED,
                           started_at=datetime(2026, 7, 27, 9), completed_at=datetime(2026, 7, 27, 10))
    rnd = SupersetRound(order=1)
    entry = RoundEntry(position=1, exercise_id=d["bench"].id, pattern_id=d["hpush"].id)
    entry.sets.append(EntrySet(set_number=1, weight=60.0, reps=10))
    rnd.entries.append(entry)
    done.rounds.append(rnd)
    test_db.add(done)
    await test_db.commit()

    result = await partner_suggestions(test_db, user.id, session.id,
                                       anchor_exercise_id=d["row"].id, position=2)
    names = [c["exercise_name"] for c in result["candidates"]]
    assert names.index("Push Up") < names.index("Dumbbell Bench Press")
    # Bench card carries a progression target from history
    bench_card = next(c for c in result["candidates"] if c["exercise_name"] == "Dumbbell Bench Press")
    assert bench_card["target"]["reps"] == 11


@pytest.mark.asyncio
async def test_position_three_offers_neutral_patterns(test_db):
    user, session, d = await _setup(test_db)
    plank = Exercise(name="Plank", movement_pattern_1="Isometric Hold",
                     mechanics="Compound", primary_equipment_id=None)
    test_db.add(plank)
    await test_db.flush()
    await seed_exercise_pattern_map(test_db)
    core = await _pattern(test_db, "core")
    test_db.add(StapleExercise(user_id=user.id, pattern_id=core.id, exercise_id=plank.id))
    await test_db.commit()

    result = await partner_suggestions(test_db, user.id, session.id,
                                       anchor_exercise_id=d["row"].id, position=3)
    names = [c["exercise_name"] for c in result["candidates"]]
    assert "Plank" in names
    # The antagonist pair is NOT re-offered at position 3
    assert "Dumbbell Bench Press" not in names or "Plank" in names


@pytest.mark.asyncio
async def test_novelty_candidate_is_non_staple_compound(test_db):
    user, session, d = await _setup(test_db)
    incline = Exercise(name="Incline Dumbbell Bench Press", movement_pattern_1="Horizontal Push",
                       mechanics="Compound", primary_equipment_id=None)
    test_db.add(incline)
    await test_db.flush()
    await seed_exercise_pattern_map(test_db)
    await test_db.commit()

    result = await partner_suggestions(test_db, user.id, session.id,
                                       anchor_exercise_id=d["row"].id, position=2)
    assert result["novelty"] is not None
    assert result["novelty"]["exercise_name"] == "Incline Dumbbell Bench Press"
    assert result["novelty"]["is_staple"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_suggestion_service.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.suggestion_service'`

- [ ] **Step 3: Write the suggestion schemas**

```python
# backend/app/schemas/suggestion.py
"""Pydantic schemas for anchor/partner suggestions"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

from app.schemas.training_session import TargetResponse


class PatternInfo(BaseModel):
    id: int
    slug: str
    name: str


class SuggestionCard(BaseModel):
    exercise_id: int
    exercise_name: str
    pattern_id: int
    pattern_slug: str
    equipment_name: Optional[str]
    is_bodyweight: bool
    last_performed: Optional[datetime]
    is_staple: bool
    target: Optional[TargetResponse]


class NotRecommendedEntry(BaseModel):
    exercise_name: str
    reason: str


class AnchorGroup(BaseModel):
    pattern: PatternInfo
    covered: bool
    staples: List[SuggestionCard]


class AnchorSuggestionsResponse(BaseModel):
    groups: List[AnchorGroup]
    not_recommended: List[NotRecommendedEntry]


class PartnerSuggestionsResponse(BaseModel):
    candidates: List[SuggestionCard]
    novelty: Optional[SuggestionCard]
    not_recommended: List[NotRecommendedEntry]
```

- [ ] **Step 4: Write the service**

```python
# backend/app/services/suggestion_service.py
"""
Anchor and partner suggestion engine.

Anchors: the user's staples grouped by the session's uncovered pattern goals.
Partners: opposite-pattern staples for position 2, neutral/uncovered patterns
for position 3, ranked least-recently-performed first. All lists pass through
blacklist, injury, equipment, and weekly-volume filters, and rejected
exercises are reported in a "why not" list.
"""
from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exercise import Exercise
from app.models.equipment_profile import EquipmentProfile
from app.models.movement_pattern import MovementPattern, ExercisePatternMap
from app.models.staple import StapleExercise, ExercisePreference
from app.models.day_plan import DayPlan, PatternGoal
from app.models.training_session import TrainingSession, SupersetRound, RoundEntry, EntrySet
from app.models.injury import UserInjury, InjuryType, MovementRestriction, injury_movement_restrictions
from app.services.history_service import last_performed_map
from app.services.progression_service import compute_entry_target

WEEKLY_SET_LIMIT = 20
NOVELTY_STALENESS_DAYS = 90
SEVERITY_ORDER = {"mild": 0, "moderate": 1, "severe": 2}


async def _blacklisted_ids(db: AsyncSession, user_id: int) -> set[int]:
    result = await db.execute(
        select(ExercisePreference.exercise_id).where(
            ExercisePreference.user_id == user_id,
            ExercisePreference.preference == "never",
        )
    )
    return {row[0] for row in result.all()}


async def _injury_restrictions(db: AsyncSession, user_id: int) -> list[dict]:
    """Active restrictions as [{"type", "value", "injury_name"}], severity-gated."""
    result = await db.execute(
        select(MovementRestriction, UserInjury.severity, InjuryType.name)
        .join(injury_movement_restrictions,
              injury_movement_restrictions.c.restriction_id == MovementRestriction.id)
        .join(InjuryType, InjuryType.id == injury_movement_restrictions.c.injury_type_id)
        .join(UserInjury, UserInjury.injury_type_id == InjuryType.id)
        .where(UserInjury.user_id == user_id, UserInjury.is_active == True)  # noqa: E712
    )
    restrictions = []
    for restriction, severity, injury_name in result.all():
        if SEVERITY_ORDER.get(severity, 1) >= SEVERITY_ORDER.get(restriction.severity_threshold, 0):
            restrictions.append({
                "type": restriction.restriction_type,
                "value": restriction.restriction_value,
                "injury_name": injury_name,
            })
    return restrictions


def _injury_reason(exercise: Exercise, restrictions: list[dict]) -> str | None:
    """Conservative match: any restriction hit excludes the exercise."""
    fields = {
        "movement_pattern": [exercise.movement_pattern_1, exercise.movement_pattern_2, exercise.movement_pattern_3],
        "force_type": [exercise.force_type],
        "plane_of_motion": [exercise.plane_of_motion_1, exercise.plane_of_motion_2, exercise.plane_of_motion_3],
        "posture": [exercise.posture],
    }
    for r in restrictions:
        values = [v.lower() for v in fields.get(r["type"], []) if v]
        if r["value"].lower() in values:
            return f"May aggravate {r['injury_name']} (not medical advice - consult a healthcare professional)"
    return None


async def _available_equipment_ids(db: AsyncSession, user_id: int) -> set[int] | None:
    """Equipment ids from the user's default profile; None = no profile (allow all)."""
    result = await db.execute(
        select(EquipmentProfile).where(
            EquipmentProfile.user_id == user_id,
            EquipmentProfile.is_default == True,  # noqa: E712
        )
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        return None
    return set(profile.equipment_ids or [])


async def _weekly_sets_by_muscle_group(db: AsyncSession, user_id: int) -> dict[int, int]:
    """Completed sets this ISO week per muscle group id, from new tables."""
    week_start = datetime.utcnow() - timedelta(days=datetime.utcnow().weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(RoundEntry.exercise_id, EntrySet.id)
        .join(SupersetRound, SupersetRound.id == RoundEntry.round_id)
        .join(TrainingSession, TrainingSession.id == SupersetRound.session_id)
        .join(EntrySet, EntrySet.entry_id == RoundEntry.id)
        .where(
            TrainingSession.user_id == user_id,
            TrainingSession.started_at >= week_start,
            EntrySet.completed == True,  # noqa: E712
        )
    )
    sets_per_exercise: dict[int, int] = defaultdict(int)
    for exercise_id, _set_id in result.all():
        sets_per_exercise[exercise_id] += 1
    if not sets_per_exercise:
        return {}

    counts: dict[int, int] = defaultdict(int)
    exercises = (await db.execute(
        select(Exercise).where(Exercise.id.in_(sets_per_exercise.keys()))
    )).scalars().all()
    for exercise in exercises:
        for mg in exercise.muscle_groups:
            counts[mg.id] += sets_per_exercise[exercise.id]
    return dict(counts)


async def _filter_cards(
    db: AsyncSession, user_id: int, exercises: list[Exercise],
    pattern_by_exercise: dict[int, MovementPattern],
    staple_ids: set[int],
    rep_ranges: dict[int, tuple[int, int]],
) -> tuple[list[dict], list[dict]]:
    """Apply blacklist -> injury -> equipment -> weekly volume. Returns (cards, not_recommended)."""
    blacklist = await _blacklisted_ids(db, user_id)
    restrictions = await _injury_restrictions(db, user_id)
    available = await _available_equipment_ids(db, user_id)
    weekly = await _weekly_sets_by_muscle_group(db, user_id)
    last_map = await last_performed_map(db, user_id, [e.id for e in exercises])

    cards: list[dict] = []
    rejected: list[dict] = []
    for exercise in exercises:
        if exercise.id in blacklist:
            rejected.append({"exercise_name": exercise.name, "reason": "Marked never (blacklisted in your preferences)"})
            continue
        reason = _injury_reason(exercise, restrictions)
        if reason:
            rejected.append({"exercise_name": exercise.name, "reason": reason})
            continue
        is_bodyweight = exercise.primary_equipment_id is None
        if not is_bodyweight and available is not None and exercise.primary_equipment_id not in available:
            rejected.append({"exercise_name": exercise.name, "reason": "Equipment not in your current profile"})
            continue
        over = [mg for mg in exercise.muscle_groups if weekly.get(mg.id, 0) > WEEKLY_SET_LIMIT]
        if over:
            rejected.append({"exercise_name": exercise.name,
                             "reason": f"Weekly volume exceeded for {over[0].name} (>{WEEKLY_SET_LIMIT} sets)"})
            continue

        pattern = pattern_by_exercise[exercise.id]
        rep_min, rep_max = rep_ranges.get(pattern.id, (8, 12))
        cards.append({
            "exercise_id": exercise.id,
            "exercise_name": exercise.name,
            "pattern_id": pattern.id,
            "pattern_slug": pattern.slug,
            "equipment_name": exercise.primary_equipment.name if exercise.primary_equipment else None,
            "is_bodyweight": is_bodyweight,
            "last_performed": last_map.get(exercise.id),
            "is_staple": exercise.id in staple_ids,
            "target": await compute_entry_target(db, user_id, exercise.id, rep_min, rep_max),
        })

    # Least-recently-performed first; never-performed (None) sorts first
    cards.sort(key=lambda c: (c["last_performed"] is not None, c["last_performed"] or datetime.min))
    return cards, _diverse_limit(rejected)


def _diverse_limit(rejected: list[dict], limit: int = 10) -> list[dict]:
    """Cap why-not entries at `limit` with diverse reason types."""
    by_reason: dict[str, list[dict]] = defaultdict(list)
    for entry in rejected:
        by_reason[entry["reason"].split("(")[0]].append(entry)
    diverse: list[dict] = []
    per_type = max(1, limit // max(1, len(by_reason)))
    for entries in by_reason.values():
        diverse.extend(entries[:per_type])
    return diverse[:limit]


async def _session_context(db: AsyncSession, user_id: int, session_id: int):
    """Load session, its goals (with rep ranges), and per-pattern completed set counts."""
    session = (await db.execute(
        select(TrainingSession).where(
            TrainingSession.id == session_id, TrainingSession.user_id == user_id,
        )
    )).scalar_one()

    goals: list[PatternGoal] = []
    if session.day_plan_id:
        goals = (await db.execute(
            select(PatternGoal).where(PatternGoal.day_plan_id == session.day_plan_id)
        )).scalars().all()

    sets_by_pattern: dict[int, int] = defaultdict(int)
    rows = (await db.execute(
        select(RoundEntry.pattern_id, EntrySet.id)
        .join(SupersetRound, SupersetRound.id == RoundEntry.round_id)
        .join(EntrySet, EntrySet.entry_id == RoundEntry.id)
        .where(SupersetRound.session_id == session_id, EntrySet.completed == True)  # noqa: E712
    )).all()
    for pattern_id, _sid in rows:
        sets_by_pattern[pattern_id] += 1

    rep_ranges = {
        g.pattern_id: (g.rep_range_min or 8, g.rep_range_max or 12) for g in goals
    }
    return session, goals, dict(sets_by_pattern), rep_ranges


def _goal_covered(goal: PatternGoal, sets_by_pattern: dict[int, int]) -> bool:
    target = goal.target_sets or 3
    return sets_by_pattern.get(goal.pattern_id, 0) >= target


async def _staples_with_exercises(db: AsyncSession, user_id: int, pattern_ids: list[int]):
    """Active staples for the given patterns, with Exercise rows loaded."""
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(StapleExercise)
        .where(
            StapleExercise.user_id == user_id,
            StapleExercise.is_active == True,  # noqa: E712
            StapleExercise.pattern_id.in_(pattern_ids),
        )
        .options(
            selectinload(StapleExercise.exercise).selectinload(Exercise.muscle_groups),
            selectinload(StapleExercise.exercise).selectinload(Exercise.primary_equipment),
            selectinload(StapleExercise.pattern),
        )
    )
    return result.scalars().all()


async def anchor_suggestions(db: AsyncSession, user_id: int, session_id: int) -> dict:
    """Staples grouped by the session's pattern goals, uncovered required goals first."""
    session, goals, sets_by_pattern, rep_ranges = await _session_context(db, user_id, session_id)

    ordered_goals = sorted(
        goals,
        key=lambda g: (_goal_covered(g, sets_by_pattern), not g.required),
    )
    staples = await _staples_with_exercises(db, user_id, [g.pattern_id for g in ordered_goals])
    staples_by_pattern: dict[int, list] = defaultdict(list)
    for staple in staples:
        staples_by_pattern[staple.pattern_id].append(staple)

    groups = []
    all_rejected: list[dict] = []
    for goal in ordered_goals:
        pattern_staples = staples_by_pattern.get(goal.pattern_id, [])
        if not pattern_staples:
            continue
        pattern = pattern_staples[0].pattern
        exercises = [s.exercise for s in pattern_staples]
        pattern_by_exercise = {s.exercise_id: s.pattern for s in pattern_staples}
        staple_ids = {s.exercise_id for s in pattern_staples}
        cards, rejected = await _filter_cards(db, user_id, exercises, pattern_by_exercise, staple_ids, rep_ranges)
        all_rejected.extend(rejected)
        groups.append({
            "pattern": {"id": pattern.id, "slug": pattern.slug, "name": pattern.name},
            "covered": _goal_covered(goal, sets_by_pattern),
            "staples": cards,
        })
    return {"groups": groups, "not_recommended": _diverse_limit(all_rejected)}


async def partner_suggestions(
    db: AsyncSession, user_id: int, session_id: int,
    anchor_exercise_id: int, position: int,
) -> dict:
    """Partner candidates for a superset entry.

    position 2: opposite pattern of the anchor's pattern.
    position 3: neutral patterns plus any uncovered goals (never the anchor's pair).
    """
    session, goals, sets_by_pattern, rep_ranges = await _session_context(db, user_id, session_id)

    anchor_map = (await db.execute(
        select(ExercisePatternMap).where(ExercisePatternMap.exercise_id == anchor_exercise_id)
    )).scalar_one()
    anchor_pattern = (await db.execute(
        select(MovementPattern).where(MovementPattern.id == anchor_map.pattern_id)
    )).scalar_one()

    if position == 2:
        if anchor_pattern.opposite_pattern_id is None:
            # Neutral anchor: fall back to uncovered goals
            target_pattern_ids = [g.pattern_id for g in goals if not _goal_covered(g, sets_by_pattern)]
        else:
            target_pattern_ids = [anchor_pattern.opposite_pattern_id]
    else:  # position == 3
        neutral_ids = [p.id for p in (await db.execute(
            select(MovementPattern).where(MovementPattern.is_neutral == True)  # noqa: E712
        )).scalars().all()]
        pair_ids = {anchor_pattern.id, anchor_pattern.opposite_pattern_id}
        uncovered = [g.pattern_id for g in goals
                     if not _goal_covered(g, sets_by_pattern) and g.pattern_id not in pair_ids]
        target_pattern_ids = list(dict.fromkeys(neutral_ids + uncovered))

    staples = await _staples_with_exercises(db, user_id, target_pattern_ids)
    exercises = [s.exercise for s in staples]
    pattern_by_exercise = {s.exercise_id: s.pattern for s in staples}
    staple_ids = {s.exercise_id for s in staples}
    cards, rejected = await _filter_cards(db, user_id, exercises, pattern_by_exercise, staple_ids, rep_ranges)

    novelty = await _novelty_candidate(db, user_id, target_pattern_ids, staple_ids, rep_ranges)
    return {"candidates": cards, "novelty": novelty, "not_recommended": rejected}


async def _novelty_candidate(
    db: AsyncSession, user_id: int, pattern_ids: list[int],
    staple_ids: set[int], rep_ranges: dict[int, tuple[int, int]],
) -> dict | None:
    """One 'try something new' compound: matches pattern + equipment, not a staple,
    not blacklisted, not performed in the last NOVELTY_STALENESS_DAYS."""
    from sqlalchemy.orm import selectinload
    blacklist = await _blacklisted_ids(db, user_id)
    available = await _available_equipment_ids(db, user_id)
    restrictions = await _injury_restrictions(db, user_id)

    result = await db.execute(
        select(Exercise, ExercisePatternMap.pattern_id)
        .join(ExercisePatternMap, ExercisePatternMap.exercise_id == Exercise.id)
        .where(
            ExercisePatternMap.pattern_id.in_(pattern_ids),
            Exercise.mechanics == "Compound",
        )
        .options(selectinload(Exercise.primary_equipment), selectinload(Exercise.muscle_groups))
        .limit(200)
    )
    rows = result.all()
    if not rows:
        return None
    last_map = await last_performed_map(db, user_id, [e.id for e, _p in rows])
    cutoff = datetime.utcnow() - timedelta(days=NOVELTY_STALENESS_DAYS)
    patterns = {p.id: p for p in (await db.execute(
        select(MovementPattern).where(MovementPattern.id.in_(pattern_ids))
    )).scalars().all()}

    for exercise, pattern_id in rows:
        if exercise.id in staple_ids or exercise.id in blacklist:
            continue
        if _injury_reason(exercise, restrictions):
            continue
        is_bodyweight = exercise.primary_equipment_id is None
        if not is_bodyweight and available is not None and exercise.primary_equipment_id not in available:
            continue
        last = last_map.get(exercise.id)
        if last is not None and last > cutoff:
            continue
        pattern = patterns[pattern_id]
        rep_min, rep_max = rep_ranges.get(pattern_id, (8, 12))
        return {
            "exercise_id": exercise.id,
            "exercise_name": exercise.name,
            "pattern_id": pattern_id,
            "pattern_slug": pattern.slug,
            "equipment_name": exercise.primary_equipment.name if exercise.primary_equipment else None,
            "is_bodyweight": is_bodyweight,
            "last_performed": last,
            "is_staple": False,
            "target": await compute_entry_target(db, user_id, exercise.id, rep_min, rep_max),
        }
    return None
```

(`EquipmentProfile.equipment_ids` is a JSONB array and `is_default` a Boolean — verified against `backend/app/models/equipment_profile.py`.)

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_suggestion_service.py -v`
Expected: PASS (all tests)

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/suggestion_service.py backend/app/schemas/suggestion.py backend/tests/test_suggestion_service.py
git commit -m "[SH] feat: add anchor/partner suggestion engine with filters and why-not"
```

---

### Task 9: Patterns API (list + progress)

**Files:**
- Create: `backend/app/schemas/pattern.py`
- Create: `backend/app/api/v1/endpoints/patterns.py`
- Modify: `backend/app/api/v1/api.py`
- Modify: `backend/tests/seed_data.py` (add taxonomy seeding to `seed_all_data`)
- Test: `backend/tests/test_patterns_api.py`

(Seeding at app startup is intentionally NOT done — `scripts/seed_patterns.py` owns production seeding; tests seed via `seed_all_data`.)

**Interfaces:**
- Consumes: `MovementPattern`, `progression_service.pattern_trend`, `get_current_user`
- Produces: `GET /api/v1/patterns/` → `List[PatternResponse]`; `GET /api/v1/patterns/progress?weeks=12` → `List[PatternProgressResponse]`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_patterns_api.py
"""Tests for the patterns API"""
import pytest

from app.services.pattern_taxonomy import seed_movement_patterns


@pytest.mark.asyncio
async def test_list_patterns(client_with_data, device_id):
    client, _seed = client_with_data
    headers = {"X-Device-ID": device_id}
    # Seed taxonomy into the test DB via the app's session
    # (client_with_data shares test_db; seed through an endpoint-independent path)
    response = await client.get("/api/v1/patterns/", headers=headers)
    assert response.status_code == 200
    slugs = [p["slug"] for p in response.json()]
    assert "horizontal_pull" in slugs
    assert len(slugs) == 10


@pytest.mark.asyncio
async def test_pattern_progress_empty(client_with_data, device_id):
    client, _seed = client_with_data
    headers = {"X-Device-ID": device_id}
    await client.get("/api/v1/users/me", headers=headers)
    response = await client.get("/api/v1/patterns/progress?weeks=12", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)  # one entry per pattern that has staples; empty user -> []
```

Add taxonomy seeding to `tests/seed_data.py`'s `seed_all_data` so `client_with_data` includes the 10 patterns: inside `seed_all_data`, call `await seed_movement_patterns(db)` and `await seed_exercise_pattern_map(db)` after exercises are seeded.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_patterns_api.py -v`
Expected: FAIL with 404 (router not registered)

- [ ] **Step 3: Write schemas and endpoints**

```python
# backend/app/schemas/pattern.py
"""Pydantic schemas for movement patterns"""
from datetime import date
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class PatternResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    slug: str
    name: str
    opposite_pattern_id: Optional[int]
    is_neutral: bool
    display_order: int


class TrendPoint(BaseModel):
    week_start: date
    index: float


class PatternProgressResponse(BaseModel):
    pattern_id: int
    slug: str
    name: str
    trend: List[TrendPoint]
```

```python
# backend/app/api/v1/endpoints/patterns.py
"""Movement pattern endpoints"""
from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import MovementPattern, StapleExercise, User
from app.schemas.pattern import PatternResponse, PatternProgressResponse, TrendPoint
from app.services.progression_service import pattern_trend

router = APIRouter()


@router.get("/", response_model=List[PatternResponse])
async def list_patterns(db: AsyncSession = Depends(get_db)):
    """List the curated movement patterns."""
    result = await db.execute(select(MovementPattern).order_by(MovementPattern.display_order))
    return [PatternResponse.model_validate(p) for p in result.scalars().all()]


@router.get("/progress", response_model=List[PatternProgressResponse])
async def get_pattern_progress(
    weeks: int = Query(12, ge=1, le=52),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Normalized e1RM trend per pattern (only patterns where the user has staples)."""
    result = await db.execute(
        select(MovementPattern)
        .join(StapleExercise, StapleExercise.pattern_id == MovementPattern.id)
        .where(StapleExercise.user_id == user.id)
        .distinct()
        .order_by(MovementPattern.display_order)
    )
    responses = []
    for pattern in result.scalars().all():
        trend = await pattern_trend(db, user.id, pattern.id, weeks=weeks)
        responses.append(PatternProgressResponse(
            pattern_id=pattern.id, slug=pattern.slug, name=pattern.name,
            trend=[TrendPoint(**point) for point in trend],
        ))
    return responses
```

Register in `backend/app/api/v1/api.py`:

```python
from app.api.v1.endpoints import patterns
api_router.include_router(patterns.router, prefix="/patterns", tags=["patterns"])
```

- [ ] **Step 4: Run tests, then commit**

Run: `cd backend && pytest tests/test_patterns_api.py -v`
Expected: PASS

```bash
git add backend/app/schemas/pattern.py backend/app/api/v1/endpoints/patterns.py backend/app/api/v1/api.py backend/tests/test_patterns_api.py backend/tests/seed_data.py
git commit -m "[SH] feat: add patterns API with progress trends"
```

---

### Task 10: Day Plans API (CRUD)

**Files:**
- Create: `backend/app/api/v1/endpoints/day_plans.py`
- Modify: `backend/app/api/v1/api.py`
- Test: `backend/tests/test_day_plans.py` (extend with API tests)

**Interfaces:**
- Consumes: `DayPlan`, `PatternGoal`, day_plan schemas, `get_current_user`
- Produces: `GET /api/v1/day-plans/`, `POST /api/v1/day-plans/` (201), `GET /api/v1/day-plans/{id}`, `PUT /api/v1/day-plans/{id}` (goals list replaces all when provided), `DELETE /api/v1/day-plans/{id}` (204)

- [ ] **Step 1: Write the failing API tests**

Append to `backend/tests/test_day_plans.py`:

```python
@pytest.mark.asyncio
async def test_day_plan_crud_api(client_with_data, device_id):
    client, _seed = client_with_data
    headers = {"X-Device-ID": device_id}
    await client.get("/api/v1/users/me", headers=headers)

    patterns = (await client.get("/api/v1/patterns/", headers=headers)).json()
    hp = next(p for p in patterns if p["slug"] == "horizontal_pull")

    create = await client.post("/api/v1/day-plans/", json={
        "name": "Full Body A",
        "warmup_preferences": [],
        "rounds_target": 3,
        "goals": [{"pattern_id": hp["id"], "required": True, "target_sets": 6}],
    }, headers=headers)
    assert create.status_code == 201
    plan = create.json()
    assert plan["goals"][0]["pattern_id"] == hp["id"]

    listed = (await client.get("/api/v1/day-plans/", headers=headers)).json()
    assert any(p["id"] == plan["id"] for p in listed)

    updated = await client.put(f"/api/v1/day-plans/{plan['id']}", json={
        "rounds_target": 4,
        "goals": [{"pattern_id": hp["id"], "required": False}],
    }, headers=headers)
    assert updated.status_code == 200
    assert updated.json()["rounds_target"] == 4
    assert updated.json()["goals"][0]["required"] is False

    deleted = await client.delete(f"/api/v1/day-plans/{plan['id']}", headers=headers)
    assert deleted.status_code == 204
    assert (await client.get(f"/api/v1/day-plans/{plan['id']}", headers=headers)).status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_day_plans.py -v`
Expected: new test FAILS with 404 (router not registered)

- [ ] **Step 3: Write the endpoints**

```python
# backend/app/api/v1/endpoints/day_plans.py
"""Day plan endpoints"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import DayPlan, PatternGoal, User
from app.schemas.day_plan import DayPlanCreate, DayPlanUpdate, DayPlanResponse

router = APIRouter()


async def _get_owned_plan(db: AsyncSession, user: User, plan_id: int) -> DayPlan:
    result = await db.execute(
        select(DayPlan)
        .where(DayPlan.id == plan_id, DayPlan.user_id == user.id)
        .options(selectinload(DayPlan.goals))
    )
    plan = result.scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=404, detail="Day plan not found")
    return plan


@router.get("/", response_model=List[DayPlanResponse])
async def list_day_plans(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(
        select(DayPlan).where(DayPlan.user_id == user.id)
        .options(selectinload(DayPlan.goals)).order_by(DayPlan.name)
    )
    return [DayPlanResponse.model_validate(p) for p in result.scalars().all()]


@router.post("/", response_model=DayPlanResponse, status_code=201)
async def create_day_plan(
    data: DayPlanCreate,
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    plan = DayPlan(
        user_id=user.id, name=data.name, description=data.description,
        warmup_preferences=data.warmup_preferences, rounds_target=data.rounds_target,
    )
    for goal in data.goals:
        plan.goals.append(PatternGoal(**goal.model_dump()))
    db.add(plan)
    await db.commit()
    return DayPlanResponse.model_validate(await _get_owned_plan(db, user, plan.id))


@router.get("/{plan_id}", response_model=DayPlanResponse)
async def get_day_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    return DayPlanResponse.model_validate(await _get_owned_plan(db, user, plan_id))


@router.put("/{plan_id}", response_model=DayPlanResponse)
async def update_day_plan(
    plan_id: int, data: DayPlanUpdate,
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    plan = await _get_owned_plan(db, user, plan_id)
    for field in ("name", "description", "warmup_preferences", "rounds_target"):
        value = getattr(data, field)
        if value is not None:
            setattr(plan, field, value)
    if data.goals is not None:
        plan.goals.clear()
        for goal in data.goals:
            plan.goals.append(PatternGoal(**goal.model_dump()))
    await db.commit()
    return DayPlanResponse.model_validate(await _get_owned_plan(db, user, plan_id))


@router.delete("/{plan_id}", status_code=204)
async def delete_day_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    plan = await _get_owned_plan(db, user, plan_id)
    await db.delete(plan)
    await db.commit()
```

Register in `backend/app/api/v1/api.py`:

```python
from app.api.v1.endpoints import day_plans
api_router.include_router(day_plans.router, prefix="/day-plans", tags=["day-plans"])
```

- [ ] **Step 4: Run tests, then commit**

Run: `cd backend && pytest tests/test_day_plans.py -v`
Expected: PASS

```bash
git add backend/app/api/v1/endpoints/day_plans.py backend/app/api/v1/api.py backend/tests/test_day_plans.py
git commit -m "[SH] feat: add day plans CRUD API"
```

---

### Task 11: Staples & preferences API

**Files:**
- Create: `backend/app/api/v1/endpoints/staples.py`
- Modify: `backend/app/api/v1/api.py`
- Test: `backend/tests/test_staples.py` (extend with API tests)

**Interfaces:**
- Consumes: `StapleExercise`, `ExercisePreference`, `ExercisePatternMap`, staple schemas, `history_service.last_performed_map`
- Produces: `GET /api/v1/staples/` (grouped-friendly flat list with `last_performed`), `POST /api/v1/staples/` (201; resolves `pattern_id` from the exercise's pattern map; 409 on duplicate), `DELETE /api/v1/staples/{id}` (204, hard delete), `PATCH /api/v1/staples/{id}` body `{"is_active": bool}`; `GET /api/v1/staples/preferences`, `POST /api/v1/staples/preferences` (201), `DELETE /api/v1/staples/preferences/{id}` (204)

- [ ] **Step 1: Write the failing API tests**

Append to `backend/tests/test_staples.py`:

```python
@pytest.mark.asyncio
async def test_staples_api_crud(client_with_data, device_id):
    client, seed = client_with_data
    headers = {"X-Device-ID": device_id}
    await client.get("/api/v1/users/me", headers=headers)

    exercises = (await client.get("/api/v1/exercises/?limit=1", headers=headers)).json()
    exercise = exercises["exercises"][0] if isinstance(exercises, dict) else exercises[0]

    created = await client.post("/api/v1/staples/", json={"exercise_id": exercise["id"]}, headers=headers)
    assert created.status_code == 201
    staple = created.json()
    assert staple["exercise_id"] == exercise["id"]
    assert staple["pattern_id"] > 0  # resolved server-side

    dup = await client.post("/api/v1/staples/", json={"exercise_id": exercise["id"]}, headers=headers)
    assert dup.status_code == 409

    listed = (await client.get("/api/v1/staples/", headers=headers)).json()
    assert any(s["id"] == staple["id"] for s in listed)

    toggled = await client.patch(f"/api/v1/staples/{staple['id']}", json={"is_active": False}, headers=headers)
    assert toggled.status_code == 200
    assert toggled.json()["is_active"] is False

    deleted = await client.delete(f"/api/v1/staples/{staple['id']}", headers=headers)
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_preferences_api(client_with_data, device_id):
    client, seed = client_with_data
    headers = {"X-Device-ID": device_id}
    await client.get("/api/v1/users/me", headers=headers)

    exercises = (await client.get("/api/v1/exercises/?limit=1", headers=headers)).json()
    exercise = exercises["exercises"][0] if isinstance(exercises, dict) else exercises[0]

    created = await client.post("/api/v1/staples/preferences",
                                json={"exercise_id": exercise["id"]}, headers=headers)
    assert created.status_code == 201
    pref = created.json()
    assert pref["preference"] == "never"

    listed = (await client.get("/api/v1/staples/preferences", headers=headers)).json()
    assert any(p["id"] == pref["id"] for p in listed)

    deleted = await client.delete(f"/api/v1/staples/preferences/{pref['id']}", headers=headers)
    assert deleted.status_code == 204
```

Note: check the shape returned by `GET /api/v1/exercises/` in `backend/app/api/v1/endpoints/exercises.py` when writing this test and use the actual key (the dict/list fallback above covers both shapes).

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_staples.py -v`
Expected: new tests FAIL with 404

- [ ] **Step 3: Write the endpoints**

```python
# backend/app/api/v1/endpoints/staples.py
"""Staple pool and exercise preference (blacklist) endpoints"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import StapleExercise, ExercisePreference, ExercisePatternMap, User
from app.schemas.staple import StapleCreate, StapleResponse, PreferenceCreate, PreferenceResponse
from app.services.history_service import last_performed_map

router = APIRouter()


class StaplePatch(BaseModel):
    is_active: bool


def _staple_response(staple: StapleExercise, last_performed=None) -> StapleResponse:
    return StapleResponse(
        id=staple.id, pattern_id=staple.pattern_id, exercise_id=staple.exercise_id,
        exercise_name=staple.exercise.name, is_active=staple.is_active,
        added_at=staple.added_at, last_performed=last_performed,
    )


@router.get("/", response_model=List[StapleResponse])
async def list_staples(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(
        select(StapleExercise).where(StapleExercise.user_id == user.id)
        .options(selectinload(StapleExercise.exercise))
        .order_by(StapleExercise.pattern_id, StapleExercise.added_at)
    )
    staples = result.scalars().all()
    last_map = await last_performed_map(db, user.id, [s.exercise_id for s in staples])
    return [_staple_response(s, last_map.get(s.exercise_id)) for s in staples]


@router.post("/", response_model=StapleResponse, status_code=201)
async def create_staple(
    data: StapleCreate,
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    existing = (await db.execute(
        select(StapleExercise).where(
            StapleExercise.user_id == user.id, StapleExercise.exercise_id == data.exercise_id,
        )
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Exercise is already a staple")

    mapping = (await db.execute(
        select(ExercisePatternMap).where(ExercisePatternMap.exercise_id == data.exercise_id)
    )).scalar_one_or_none()
    if mapping is None:
        raise HTTPException(status_code=404, detail="Exercise has no pattern mapping")

    staple = StapleExercise(user_id=user.id, pattern_id=mapping.pattern_id, exercise_id=data.exercise_id)
    db.add(staple)
    await db.commit()
    staple = (await db.execute(
        select(StapleExercise).where(StapleExercise.id == staple.id)
        .options(selectinload(StapleExercise.exercise))
    )).scalar_one()
    return _staple_response(staple)


@router.patch("/{staple_id}", response_model=StapleResponse)
async def patch_staple(
    staple_id: int, data: StaplePatch,
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    staple = (await db.execute(
        select(StapleExercise).where(StapleExercise.id == staple_id, StapleExercise.user_id == user.id)
        .options(selectinload(StapleExercise.exercise))
    )).scalar_one_or_none()
    if staple is None:
        raise HTTPException(status_code=404, detail="Staple not found")
    staple.is_active = data.is_active
    await db.commit()
    return _staple_response(staple)


@router.delete("/{staple_id}", status_code=204)
async def delete_staple(
    staple_id: int,
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    staple = (await db.execute(
        select(StapleExercise).where(StapleExercise.id == staple_id, StapleExercise.user_id == user.id)
    )).scalar_one_or_none()
    if staple is None:
        raise HTTPException(status_code=404, detail="Staple not found")
    await db.delete(staple)
    await db.commit()


@router.get("/preferences", response_model=List[PreferenceResponse])
async def list_preferences(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(
        select(ExercisePreference).where(ExercisePreference.user_id == user.id)
        .options(selectinload(ExercisePreference.exercise))
    )
    return [
        PreferenceResponse(id=p.id, exercise_id=p.exercise_id,
                           exercise_name=p.exercise.name, preference=p.preference)
        for p in result.scalars().all()
    ]


@router.post("/preferences", response_model=PreferenceResponse, status_code=201)
async def create_preference(
    data: PreferenceCreate,
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    existing = (await db.execute(
        select(ExercisePreference).where(
            ExercisePreference.user_id == user.id, ExercisePreference.exercise_id == data.exercise_id,
        )
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Preference already exists")
    pref = ExercisePreference(user_id=user.id, exercise_id=data.exercise_id, preference=data.preference)
    db.add(pref)
    await db.commit()
    pref = (await db.execute(
        select(ExercisePreference).where(ExercisePreference.id == pref.id)
        .options(selectinload(ExercisePreference.exercise))
    )).scalar_one()
    return PreferenceResponse(id=pref.id, exercise_id=pref.exercise_id,
                              exercise_name=pref.exercise.name, preference=pref.preference)


@router.delete("/preferences/{pref_id}", status_code=204)
async def delete_preference(
    pref_id: int,
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    pref = (await db.execute(
        select(ExercisePreference).where(
            ExercisePreference.id == pref_id, ExercisePreference.user_id == user.id,
        )
    )).scalar_one_or_none()
    if pref is None:
        raise HTTPException(status_code=404, detail="Preference not found")
    await db.delete(pref)
    await db.commit()
```

IMPORTANT: register the `/preferences` routes BEFORE the `/{staple_id}` routes in the file (as shown via path specificity: FastAPI matches `/preferences` before `/{staple_id}` only when declared first — in the file above, move the three preference handlers ABOVE `patch_staple`/`delete_staple`).

Register in `backend/app/api/v1/api.py`:

```python
from app.api.v1.endpoints import staples
api_router.include_router(staples.router, prefix="/staples", tags=["staples"])
```

- [ ] **Step 4: Run tests, then commit**

Run: `cd backend && pytest tests/test_staples.py -v`
Expected: PASS

```bash
git add backend/app/api/v1/endpoints/staples.py backend/app/api/v1/api.py backend/tests/test_staples.py
git commit -m "[SH] feat: add staples and exercise preferences API"
```

---

### Task 12: Training sessions API (lifecycle, rounds, entries, sets, coverage)

**Files:**
- Create: `backend/app/api/v1/endpoints/training_sessions.py`
- Modify: `backend/app/api/v1/api.py`
- Test: `backend/tests/test_training_sessions.py` (extend with API tests)

**Interfaces:**
- Consumes: session models + schemas, `ExercisePatternMap`, `PatternGoal`, `progression_service.compute_entry_target`, `get_current_user`
- Produces:
  - `POST /api/v1/sessions/` body `{day_plan_id?}` → 201 `TrainingSessionResponse` (state `active`, `started_at` now); 409 if an active/draft session already exists
  - `GET /api/v1/sessions/active` → 200 full nested session or 404
  - `GET /api/v1/sessions/` query `state?` → list (history)
  - `GET /api/v1/sessions/{id}` → full nested with per-entry `target`
  - `POST /api/v1/sessions/{id}/rounds` → 201 `SupersetRoundResponse` (order auto-incremented)
  - `POST /api/v1/sessions/rounds/{round_id}/entries` body `RoundEntryCreate` → 201 `RoundEntryResponse` with `target` (pattern_id denormalized server-side from ExercisePatternMap; 409 if position taken)
  - `POST /api/v1/sessions/entries/{entry_id}/sets` body `EntrySetCreate` → 201 `EntrySetResponse`
  - `POST /api/v1/sessions/{id}/complete` → 200 (state completed, `completed_at` now)
  - `POST /api/v1/sessions/{id}/discard` → 200 (state discarded)
  - `GET /api/v1/sessions/{id}/coverage` → `CoverageResponse`

- [ ] **Step 1: Write the failing API test**

Append to `backend/tests/test_training_sessions.py`:

```python
@pytest.mark.asyncio
async def test_session_lifecycle_api(client_with_data, device_id):
    client, _seed = client_with_data
    headers = {"X-Device-ID": device_id}
    await client.get("/api/v1/users/me", headers=headers)

    patterns = (await client.get("/api/v1/patterns/", headers=headers)).json()
    hp = next(p for p in patterns if p["slug"] == "horizontal_pull")
    hpush = next(p for p in patterns if p["slug"] == "horizontal_push")

    plan = (await client.post("/api/v1/day-plans/", json={
        "name": "Full Body A", "warmup_preferences": [], "rounds_target": 2,
        "goals": [
            {"pattern_id": hp["id"], "required": True, "target_sets": 1},
            {"pattern_id": hpush["id"], "required": True, "target_sets": 3},
        ],
    }, headers=headers)).json()

    # Start session
    created = await client.post("/api/v1/sessions/", json={"day_plan_id": plan["id"]}, headers=headers)
    assert created.status_code == 201
    session = created.json()
    assert session["state"] == "active"

    # Second active session is rejected
    assert (await client.post("/api/v1/sessions/", json={}, headers=headers)).status_code == 409

    # Resume endpoint finds it
    active = await client.get("/api/v1/sessions/active", headers=headers)
    assert active.status_code == 200
    assert active.json()["id"] == session["id"]

    # Round -> entry -> set
    rnd = (await client.post(f"/api/v1/sessions/{session['id']}/rounds", headers=headers)).json()
    assert rnd["order"] == 1

    exercises = (await client.get("/api/v1/exercises/?limit=1", headers=headers)).json()
    exercise = exercises["exercises"][0] if isinstance(exercises, dict) else exercises[0]

    entry_resp = await client.post(f"/api/v1/sessions/rounds/{rnd['id']}/entries",
                                   json={"exercise_id": exercise["id"], "position": 1}, headers=headers)
    assert entry_resp.status_code == 201
    entry = entry_resp.json()
    assert entry["pattern_id"] > 0  # denormalized server-side

    dup = await client.post(f"/api/v1/sessions/rounds/{rnd['id']}/entries",
                            json={"exercise_id": exercise["id"], "position": 1}, headers=headers)
    assert dup.status_code == 409  # position taken

    set_resp = await client.post(f"/api/v1/sessions/entries/{entry['id']}/sets",
                                 json={"set_number": 1, "weight": 100, "reps": 10}, headers=headers)
    assert set_resp.status_code == 201

    # Coverage reflects the completed set
    coverage = (await client.get(f"/api/v1/sessions/{session['id']}/coverage", headers=headers)).json()
    assert len(coverage["goals"]) == 2
    covered_by_pattern = {g["pattern_id"]: g for g in coverage["goals"]}
    entry_pattern = entry["pattern_id"]
    if entry_pattern in covered_by_pattern:
        goal = covered_by_pattern[entry_pattern]
        assert goal["sets_done"] >= 1

    # Complete
    done = await client.post(f"/api/v1/sessions/{session['id']}/complete", headers=headers)
    assert done.status_code == 200
    assert done.json()["state"] == "completed"
    assert (await client.get("/api/v1/sessions/active", headers=headers)).status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_training_sessions.py -v`
Expected: new test FAILS with 404

- [ ] **Step 3: Write the endpoints**

```python
# backend/app/api/v1/endpoints/training_sessions.py
"""Training session lifecycle endpoints"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import (
    TrainingSession, SupersetRound, RoundEntry, EntrySet, SessionState,
    ExercisePatternMap, MovementPattern, PatternGoal, User,
)
from app.schemas.training_session import (
    TrainingSessionCreate, TrainingSessionResponse, SupersetRoundResponse,
    RoundEntryCreate, RoundEntryResponse, EntrySetCreate, EntrySetResponse,
    TargetResponse, CoverageResponse, CoverageGoal,
)
from app.services.progression_service import compute_entry_target

router = APIRouter()

_SESSION_LOAD = (
    selectinload(TrainingSession.rounds)
    .selectinload(SupersetRound.entries)
    .selectinload(RoundEntry.sets),
    selectinload(TrainingSession.rounds)
    .selectinload(SupersetRound.entries)
    .selectinload(RoundEntry.exercise),
    selectinload(TrainingSession.rounds)
    .selectinload(SupersetRound.entries)
    .selectinload(RoundEntry.pattern),
)


async def _load_session(db: AsyncSession, user: User, session_id: int) -> TrainingSession:
    result = await db.execute(
        select(TrainingSession)
        .where(TrainingSession.id == session_id, TrainingSession.user_id == user.id)
        .options(*_SESSION_LOAD)
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


async def _rep_range_for(db: AsyncSession, session: TrainingSession, pattern_id: int) -> tuple[int, int]:
    if session.day_plan_id:
        goal = (await db.execute(
            select(PatternGoal).where(
                PatternGoal.day_plan_id == session.day_plan_id,
                PatternGoal.pattern_id == pattern_id,
            )
        )).scalar_one_or_none()
        if goal:
            return (goal.rep_range_min or 8, goal.rep_range_max or 12)
    return (8, 12)


async def _entry_response(db: AsyncSession, user: User, session: TrainingSession, entry: RoundEntry) -> RoundEntryResponse:
    rep_min, rep_max = await _rep_range_for(db, session, entry.pattern_id)
    target = await compute_entry_target(db, user.id, entry.exercise_id, rep_min, rep_max)
    return RoundEntryResponse(
        id=entry.id, round_id=entry.round_id, position=entry.position,
        exercise_id=entry.exercise_id, exercise_name=entry.exercise.name,
        pattern_id=entry.pattern_id, pattern_slug=entry.pattern.slug,
        sets=[EntrySetResponse.model_validate(s) for s in entry.sets],
        target=TargetResponse(**target) if target else None,
    )


async def _session_response(db: AsyncSession, user: User, session: TrainingSession) -> TrainingSessionResponse:
    rounds = []
    for rnd in session.rounds:
        entries = [await _entry_response(db, user, session, e) for e in rnd.entries]
        rounds.append(SupersetRoundResponse(
            id=rnd.id, session_id=rnd.session_id, order=rnd.order, entries=entries,
        ))
    return TrainingSessionResponse(
        id=session.id, day_plan_id=session.day_plan_id, state=session.state.value,
        started_at=session.started_at, completed_at=session.completed_at,
        notes=session.notes, rounds=rounds,
    )


@router.post("/", response_model=TrainingSessionResponse, status_code=201)
async def create_session(
    data: TrainingSessionCreate,
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    existing = (await db.execute(
        select(TrainingSession).where(
            TrainingSession.user_id == user.id,
            TrainingSession.state.in_([SessionState.DRAFT, SessionState.ACTIVE]),
        )
    )).scalars().first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Session {existing.id} is already in progress")

    session = TrainingSession(
        user_id=user.id, day_plan_id=data.day_plan_id,
        state=SessionState.ACTIVE, started_at=datetime.utcnow(),
    )
    db.add(session)
    await db.commit()
    return await _session_response(db, user, await _load_session(db, user, session.id))


@router.get("/active", response_model=TrainingSessionResponse)
async def get_active_session(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(TrainingSession)
        .where(
            TrainingSession.user_id == user.id,
            TrainingSession.state.in_([SessionState.DRAFT, SessionState.ACTIVE]),
        )
        .options(*_SESSION_LOAD)
    )
    session = result.scalars().first()
    if session is None:
        raise HTTPException(status_code=404, detail="No active session")
    return await _session_response(db, user, session)


@router.get("/", response_model=List[TrainingSessionResponse])
async def list_sessions(
    state: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    query = (
        select(TrainingSession)
        .where(TrainingSession.user_id == user.id)
        .options(*_SESSION_LOAD)
        .order_by(TrainingSession.started_at.desc())
        .limit(limit)
    )
    if state:
        query = query.where(TrainingSession.state == SessionState(state))
    result = await db.execute(query)
    return [await _session_response(db, user, s) for s in result.scalars().all()]


@router.get("/{session_id}", response_model=TrainingSessionResponse)
async def get_session(
    session_id: int,
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    return await _session_response(db, user, await _load_session(db, user, session_id))


@router.post("/{session_id}/rounds", response_model=SupersetRoundResponse, status_code=201)
async def create_round(
    session_id: int,
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    session = await _load_session(db, user, session_id)
    next_order = max((r.order for r in session.rounds), default=0) + 1
    rnd = SupersetRound(session_id=session.id, order=next_order)
    db.add(rnd)
    await db.commit()
    return SupersetRoundResponse(id=rnd.id, session_id=rnd.session_id, order=rnd.order, entries=[])


@router.post("/rounds/{round_id}/entries", response_model=RoundEntryResponse, status_code=201)
async def create_entry(
    round_id: int, data: RoundEntryCreate,
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    rnd = (await db.execute(
        select(SupersetRound)
        .join(TrainingSession, TrainingSession.id == SupersetRound.session_id)
        .where(SupersetRound.id == round_id, TrainingSession.user_id == user.id)
        .options(selectinload(SupersetRound.entries))
    )).scalar_one_or_none()
    if rnd is None:
        raise HTTPException(status_code=404, detail="Round not found")
    if any(e.position == data.position for e in rnd.entries):
        raise HTTPException(status_code=409, detail=f"Position {data.position} already filled")

    mapping = (await db.execute(
        select(ExercisePatternMap).where(ExercisePatternMap.exercise_id == data.exercise_id)
    )).scalar_one_or_none()
    if mapping is None:
        raise HTTPException(status_code=404, detail="Exercise has no pattern mapping")

    entry = RoundEntry(
        round_id=rnd.id, position=data.position,
        exercise_id=data.exercise_id, pattern_id=mapping.pattern_id,
    )
    db.add(entry)
    await db.commit()

    entry = (await db.execute(
        select(RoundEntry).where(RoundEntry.id == entry.id)
        .options(selectinload(RoundEntry.exercise), selectinload(RoundEntry.pattern),
                 selectinload(RoundEntry.sets))
    )).scalar_one()
    session = await _load_session(db, user, rnd.session_id)
    return await _entry_response(db, user, session, entry)


@router.post("/entries/{entry_id}/sets", response_model=EntrySetResponse, status_code=201)
async def create_set(
    entry_id: int, data: EntrySetCreate,
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    entry = (await db.execute(
        select(RoundEntry)
        .join(SupersetRound, SupersetRound.id == RoundEntry.round_id)
        .join(TrainingSession, TrainingSession.id == SupersetRound.session_id)
        .where(RoundEntry.id == entry_id, TrainingSession.user_id == user.id)
    )).scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    entry_set = EntrySet(entry_id=entry.id, **data.model_dump())
    db.add(entry_set)
    await db.commit()
    return EntrySetResponse.model_validate(entry_set)


@router.post("/{session_id}/complete", response_model=TrainingSessionResponse)
async def complete_session(
    session_id: int,
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    session = await _load_session(db, user, session_id)
    session.state = SessionState.COMPLETED
    session.completed_at = datetime.utcnow()
    await db.commit()
    return await _session_response(db, user, await _load_session(db, user, session_id))


@router.post("/{session_id}/discard", response_model=TrainingSessionResponse)
async def discard_session(
    session_id: int,
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    session = await _load_session(db, user, session_id)
    session.state = SessionState.DISCARDED
    await db.commit()
    return await _session_response(db, user, await _load_session(db, user, session_id))


@router.get("/{session_id}/coverage", response_model=CoverageResponse)
async def get_coverage(
    session_id: int,
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    session = await _load_session(db, user, session_id)
    goals: list[PatternGoal] = []
    if session.day_plan_id:
        goals = (await db.execute(
            select(PatternGoal).where(PatternGoal.day_plan_id == session.day_plan_id)
            .options(selectinload(PatternGoal.pattern))
        )).scalars().all()

    sets_by_pattern: dict[int, int] = {}
    for rnd in session.rounds:
        for entry in rnd.entries:
            done = sum(1 for s in entry.sets if s.completed)
            sets_by_pattern[entry.pattern_id] = sets_by_pattern.get(entry.pattern_id, 0) + done

    coverage_goals = []
    for goal in goals:
        target = goal.target_sets or 3
        done = sets_by_pattern.get(goal.pattern_id, 0)
        coverage_goals.append(CoverageGoal(
            pattern_id=goal.pattern_id, slug=goal.pattern.slug, name=goal.pattern.name,
            required=goal.required, target_sets=target, sets_done=done, covered=done >= target,
        ))
    return CoverageResponse(goals=coverage_goals)
```

Route-ordering note: declare `/active` BEFORE `/{session_id}` (as in the file above) so `GET /sessions/active` doesn't match the int path.

Register in `backend/app/api/v1/api.py`:

```python
from app.api.v1.endpoints import training_sessions
api_router.include_router(training_sessions.router, prefix="/sessions", tags=["sessions"])
```

- [ ] **Step 4: Run tests, then commit**

Run: `cd backend && pytest tests/test_training_sessions.py -v`
Expected: PASS

```bash
git add backend/app/api/v1/endpoints/training_sessions.py backend/app/api/v1/api.py backend/tests/test_training_sessions.py
git commit -m "[SH] feat: add training session lifecycle API"
```

---

### Task 13: Suggestions API

**Files:**
- Create: `backend/app/api/v1/endpoints/suggestions.py`
- Modify: `backend/app/api/v1/api.py`
- Test: `backend/tests/test_suggestions_api.py`

**Interfaces:**
- Consumes: `suggestion_service.anchor_suggestions`, `suggestion_service.partner_suggestions`, suggestion schemas
- Produces: `GET /api/v1/suggestions/anchors?session_id=N` → `AnchorSuggestionsResponse`; `GET /api/v1/suggestions/partners?session_id=N&anchor_exercise_id=M&position=2|3` → `PartnerSuggestionsResponse`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_suggestions_api.py
"""Tests for the suggestions API"""
import pytest


@pytest.mark.asyncio
async def test_anchor_and_partner_endpoints(client_with_data, device_id):
    client, _seed = client_with_data
    headers = {"X-Device-ID": device_id}
    await client.get("/api/v1/users/me", headers=headers)

    patterns = (await client.get("/api/v1/patterns/", headers=headers)).json()
    hp = next(p for p in patterns if p["slug"] == "horizontal_pull")

    plan = (await client.post("/api/v1/day-plans/", json={
        "name": "Pull Day", "warmup_preferences": [], "rounds_target": 2,
        "goals": [{"pattern_id": hp["id"], "required": True, "target_sets": 3}],
    }, headers=headers)).json()
    session = (await client.post("/api/v1/sessions/", json={"day_plan_id": plan["id"]},
                                 headers=headers)).json()

    # Make one exercise a staple so anchors have content
    exercises = (await client.get("/api/v1/exercises/?limit=5", headers=headers)).json()
    items = exercises["exercises"] if isinstance(exercises, dict) else exercises
    await client.post("/api/v1/staples/", json={"exercise_id": items[0]["id"]}, headers=headers)

    anchors = await client.get(f"/api/v1/suggestions/anchors?session_id={session['id']}", headers=headers)
    assert anchors.status_code == 200
    body = anchors.json()
    assert "groups" in body and "not_recommended" in body

    partners = await client.get(
        f"/api/v1/suggestions/partners?session_id={session['id']}"
        f"&anchor_exercise_id={items[0]['id']}&position=2",
        headers=headers,
    )
    assert partners.status_code == 200
    pbody = partners.json()
    assert "candidates" in pbody and "novelty" in pbody and "not_recommended" in pbody


@pytest.mark.asyncio
async def test_partner_position_validation(client_with_data, device_id):
    client, _seed = client_with_data
    headers = {"X-Device-ID": device_id}
    await client.get("/api/v1/users/me", headers=headers)
    response = await client.get(
        "/api/v1/suggestions/partners?session_id=1&anchor_exercise_id=1&position=5",
        headers=headers,
    )
    assert response.status_code == 422
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_suggestions_api.py -v`
Expected: FAIL with 404

- [ ] **Step 3: Write the endpoints**

```python
# backend/app/api/v1/endpoints/suggestions.py
"""Anchor and partner suggestion endpoints"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import User
from app.schemas.suggestion import AnchorSuggestionsResponse, PartnerSuggestionsResponse
from app.services.suggestion_service import anchor_suggestions, partner_suggestions

router = APIRouter()


@router.get("/anchors", response_model=AnchorSuggestionsResponse)
async def get_anchor_suggestions(
    session_id: int = Query(...),
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    """Staples grouped by the session's uncovered pattern goals."""
    try:
        return await anchor_suggestions(db, user.id, session_id)
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Session not found")


@router.get("/partners", response_model=PartnerSuggestionsResponse)
async def get_partner_suggestions(
    session_id: int = Query(...),
    anchor_exercise_id: int = Query(...),
    position: int = Query(..., ge=2, le=3),
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    """Antagonist partners (position 2) or neutral/uncovered third entries (position 3)."""
    try:
        return await partner_suggestions(db, user.id, session_id, anchor_exercise_id, position)
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Session or exercise mapping not found")
```

Register in `backend/app/api/v1/api.py`:

```python
from app.api.v1.endpoints import suggestions
api_router.include_router(suggestions.router, prefix="/suggestions", tags=["suggestions"])
```

- [ ] **Step 4: Run tests, then commit**

Run: `cd backend && pytest tests/test_suggestions_api.py -v`
Expected: PASS

```bash
git add backend/app/api/v1/endpoints/suggestions.py backend/app/api/v1/api.py backend/tests/test_suggestions_api.py
git commit -m "[SH] feat: add suggestions API"
```

---

### Task 14: Backfill script (staples from legacy history)

**Files:**
- Create: `backend/scripts/backfill_staples.py`
- Test: manual verification via script output (script operates on the real DB; core logic reuses tested services)

**Interfaces:**
- Consumes: `history_service.times_performed_map`, `ExercisePatternMap`, `StapleExercise`
- Produces: staple rows for every exercise the user has logged 3+ times in completed workouts (legacy + new), skipping existing staples

- [ ] **Step 1: Write the script**

```python
# backend/scripts/backfill_staples.py
"""
Derive initial staple pools from workout history.

Any exercise performed in 3+ completed sessions (legacy workouts or new
training sessions) becomes a staple in its mapped pattern.

Run from backend/: python -m scripts.backfill_staples
"""
import asyncio

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models import User, StapleExercise, ExercisePatternMap
from app.services.history_service import times_performed_map

STAPLE_THRESHOLD = 3


async def backfill_user(db, user: User) -> int:
    counts = await times_performed_map(db, user.id)
    candidates = [ex_id for ex_id, n in counts.items() if n >= STAPLE_THRESHOLD]
    if not candidates:
        return 0

    existing = {
        row[0] for row in (await db.execute(
            select(StapleExercise.exercise_id).where(StapleExercise.user_id == user.id)
        )).all()
    }
    mappings = {
        m.exercise_id: m.pattern_id for m in (await db.execute(
            select(ExercisePatternMap).where(ExercisePatternMap.exercise_id.in_(candidates))
        )).scalars().all()
    }

    created = 0
    for exercise_id in candidates:
        if exercise_id in existing or exercise_id not in mappings:
            continue
        db.add(StapleExercise(
            user_id=user.id, pattern_id=mappings[exercise_id], exercise_id=exercise_id,
        ))
        created += 1
    await db.commit()
    return created


async def main() -> None:
    async with AsyncSessionLocal() as db:
        users = (await db.execute(select(User))).scalars().all()
        for user in users:
            created = await backfill_user(db, user)
            print(f"user {user.id} ({user.device_id}): {created} staples created")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Run the script and verify**

Run: `cd backend && python -m scripts.seed_patterns && python -m scripts.backfill_staples`
Expected: per-user staple counts printed; re-running prints `0 staples created` (idempotent).
Verify: `GET http://localhost:8000/api/v1/staples/` (with your device header via the web app or docs UI) shows your frequently-logged exercises.

- [ ] **Step 3: Commit**

```bash
git add backend/scripts/backfill_staples.py
git commit -m "[SH] feat: add staple backfill script from workout history"
```

---

### Task 15: Web API services and types

**Files:**
- Create: `web/src/services/patterns.ts`, `web/src/services/dayPlans.ts`, `web/src/services/staples.ts`, `web/src/services/sessions.ts`, `web/src/services/suggestions.ts`
- Modify: `web/src/services/index.ts` (re-export new services)

**Interfaces:**
- Consumes: `apiClient` from `web/src/services/api.ts`
- Produces: typed functions — `listPatterns()`, `getPatternProgress(weeks)`, `listDayPlans()/createDayPlan()/updateDayPlan()/deleteDayPlan()`, `listStaples()/createStaple()/patchStaple()/deleteStaple()/listPreferences()/createPreference()/deletePreference()`, `createSession()/getActiveSession()/getSession()/listSessions()/createRound()/createEntry()/createSet()/completeSession()/discardSession()/getCoverage()`, `getAnchorSuggestions()/getPartnerSuggestions()` — with exported TS interfaces mirroring the backend response schemas

- [ ] **Step 1: Write the services (no unit test infra in web; verification is `npm run build`)**

```typescript
// web/src/services/patterns.ts
import { apiClient } from './api'

export interface MovementPattern {
  id: number
  slug: string
  name: string
  opposite_pattern_id: number | null
  is_neutral: boolean
  display_order: number
}

export interface TrendPoint {
  week_start: string
  index: number
}

export interface PatternProgress {
  pattern_id: number
  slug: string
  name: string
  trend: TrendPoint[]
}

export async function listPatterns(): Promise<MovementPattern[]> {
  const { data } = await apiClient.get('/patterns/')
  return data
}

export async function getPatternProgress(weeks = 12): Promise<PatternProgress[]> {
  const { data } = await apiClient.get('/patterns/progress', { params: { weeks } })
  return data
}
```

```typescript
// web/src/services/dayPlans.ts
import { apiClient } from './api'

export interface PatternGoal {
  id?: number
  pattern_id: number
  required: boolean
  target_sets: number | null
  rep_range_min: number | null
  rep_range_max: number | null
}

export interface DayPlan {
  id: number
  name: string
  description: string | null
  warmup_preferences: number[]
  rounds_target: number
  goals: PatternGoal[]
}

export type DayPlanInput = Omit<DayPlan, 'id'>

export async function listDayPlans(): Promise<DayPlan[]> {
  const { data } = await apiClient.get('/day-plans/')
  return data
}

export async function createDayPlan(input: DayPlanInput): Promise<DayPlan> {
  const { data } = await apiClient.post('/day-plans/', input)
  return data
}

export async function updateDayPlan(id: number, input: Partial<DayPlanInput>): Promise<DayPlan> {
  const { data } = await apiClient.put(`/day-plans/${id}`, input)
  return data
}

export async function deleteDayPlan(id: number): Promise<void> {
  await apiClient.delete(`/day-plans/${id}`)
}
```

```typescript
// web/src/services/staples.ts
import { apiClient } from './api'

export interface Staple {
  id: number
  pattern_id: number
  exercise_id: number
  exercise_name: string
  is_active: boolean
  added_at: string
  last_performed: string | null
}

export interface ExercisePreference {
  id: number
  exercise_id: number
  exercise_name: string
  preference: string
}

export async function listStaples(): Promise<Staple[]> {
  const { data } = await apiClient.get('/staples/')
  return data
}

export async function createStaple(exerciseId: number): Promise<Staple> {
  const { data } = await apiClient.post('/staples/', { exercise_id: exerciseId })
  return data
}

export async function patchStaple(id: number, isActive: boolean): Promise<Staple> {
  const { data } = await apiClient.patch(`/staples/${id}`, { is_active: isActive })
  return data
}

export async function deleteStaple(id: number): Promise<void> {
  await apiClient.delete(`/staples/${id}`)
}

export async function listPreferences(): Promise<ExercisePreference[]> {
  const { data } = await apiClient.get('/staples/preferences')
  return data
}

export async function createPreference(exerciseId: number): Promise<ExercisePreference> {
  const { data } = await apiClient.post('/staples/preferences', { exercise_id: exerciseId })
  return data
}

export async function deletePreference(id: number): Promise<void> {
  await apiClient.delete(`/staples/preferences/${id}`)
}
```

```typescript
// web/src/services/sessions.ts
import { apiClient } from './api'

export interface Target {
  weight: number | null
  reps: number
  sets: number
  last_summary: string | null
}

export interface EntrySet {
  id: number
  entry_id: number
  set_number: number
  weight: number | null
  reps: number | null
  time_seconds: number | null
  completed: boolean
}

export interface RoundEntry {
  id: number
  round_id: number
  position: number
  exercise_id: number
  exercise_name: string
  pattern_id: number
  pattern_slug: string
  sets: EntrySet[]
  target: Target | null
}

export interface SupersetRound {
  id: number
  session_id: number
  order: number
  entries: RoundEntry[]
}

export interface TrainingSession {
  id: number
  day_plan_id: number | null
  state: 'draft' | 'active' | 'completed' | 'discarded'
  started_at: string | null
  completed_at: string | null
  notes: string | null
  rounds: SupersetRound[]
}

export interface CoverageGoal {
  pattern_id: number
  slug: string
  name: string
  required: boolean
  target_sets: number
  sets_done: number
  covered: boolean
}

export interface Coverage {
  goals: CoverageGoal[]
}

export async function createSession(dayPlanId: number | null): Promise<TrainingSession> {
  const { data } = await apiClient.post('/sessions/', { day_plan_id: dayPlanId })
  return data
}

export async function getActiveSession(): Promise<TrainingSession | null> {
  try {
    const { data } = await apiClient.get('/sessions/active')
    return data
  } catch {
    return null
  }
}

export async function getSession(id: number): Promise<TrainingSession> {
  const { data } = await apiClient.get(`/sessions/${id}`)
  return data
}

export async function listSessions(state?: string, limit = 20): Promise<TrainingSession[]> {
  const { data } = await apiClient.get('/sessions/', { params: { state, limit } })
  return data
}

export async function createRound(sessionId: number): Promise<SupersetRound> {
  const { data } = await apiClient.post(`/sessions/${sessionId}/rounds`)
  return data
}

export async function createEntry(roundId: number, exerciseId: number, position: number): Promise<RoundEntry> {
  const { data } = await apiClient.post(`/sessions/rounds/${roundId}/entries`, {
    exercise_id: exerciseId,
    position,
  })
  return data
}

export async function createSet(
  entryId: number,
  set: { set_number: number; weight?: number | null; reps?: number | null; time_seconds?: number | null }
): Promise<EntrySet> {
  const { data } = await apiClient.post(`/sessions/entries/${entryId}/sets`, set)
  return data
}

export async function completeSession(id: number): Promise<TrainingSession> {
  const { data } = await apiClient.post(`/sessions/${id}/complete`)
  return data
}

export async function discardSession(id: number): Promise<TrainingSession> {
  const { data } = await apiClient.post(`/sessions/${id}/discard`)
  return data
}

export async function getCoverage(sessionId: number): Promise<Coverage> {
  const { data } = await apiClient.get(`/sessions/${sessionId}/coverage`)
  return data
}
```

```typescript
// web/src/services/suggestions.ts
import { apiClient } from './api'
import type { Target } from './sessions'

export interface SuggestionCard {
  exercise_id: number
  exercise_name: string
  pattern_id: number
  pattern_slug: string
  equipment_name: string | null
  is_bodyweight: boolean
  last_performed: string | null
  is_staple: boolean
  target: Target | null
}

export interface NotRecommendedEntry {
  exercise_name: string
  reason: string
}

export interface AnchorGroup {
  pattern: { id: number; slug: string; name: string }
  covered: boolean
  staples: SuggestionCard[]
}

export interface AnchorSuggestions {
  groups: AnchorGroup[]
  not_recommended: NotRecommendedEntry[]
}

export interface PartnerSuggestions {
  candidates: SuggestionCard[]
  novelty: SuggestionCard | null
  not_recommended: NotRecommendedEntry[]
}

export async function getAnchorSuggestions(sessionId: number): Promise<AnchorSuggestions> {
  const { data } = await apiClient.get('/suggestions/anchors', { params: { session_id: sessionId } })
  return data
}

export async function getPartnerSuggestions(
  sessionId: number,
  anchorExerciseId: number,
  position: 2 | 3
): Promise<PartnerSuggestions> {
  const { data } = await apiClient.get('/suggestions/partners', {
    params: { session_id: sessionId, anchor_exercise_id: anchorExerciseId, position },
  })
  return data
}
```

Re-export all five modules from `web/src/services/index.ts` following its existing export style.

- [ ] **Step 2: Verify build, then commit**

Run: `cd web && npm run build`
Expected: tsc passes with no errors

```bash
git add web/src/services/patterns.ts web/src/services/dayPlans.ts web/src/services/staples.ts web/src/services/sessions.ts web/src/services/suggestions.ts web/src/services/index.ts
git commit -m "[SH] feat: add web API services for patterns, day plans, staples, sessions"
```

---

### Task 16: Zustand stores (dayPlanStore, sessionStore)

**Files:**
- Create: `web/src/stores/dayPlanStore.ts`, `web/src/stores/sessionStore.ts`
- Modify: `web/src/stores/index.ts` (re-export)

**Interfaces:**
- Consumes: Task 15 services
- Produces:
  - `useDayPlanStore`: `{ plans, patterns, loading, error, fetchAll(), save(input, id?), remove(id) }`
  - `useSessionStore`: `{ session, coverage, loading, error, start(dayPlanId), resume(), refresh(), addRound(), addEntry(roundId, exerciseId, position), logSet(entryId, set), complete(), discard() }` — every mutation refreshes `session` and `coverage` from the server (server is the source of truth; no optimistic state)

- [ ] **Step 1: Write the stores**

```typescript
// web/src/stores/dayPlanStore.ts
import { create } from 'zustand'
import { listDayPlans, createDayPlan, updateDayPlan, deleteDayPlan } from '../services/dayPlans'
import type { DayPlan, DayPlanInput } from '../services/dayPlans'
import { listPatterns } from '../services/patterns'
import type { MovementPattern } from '../services/patterns'

interface DayPlanState {
  plans: DayPlan[]
  patterns: MovementPattern[]
  loading: boolean
  error: string | null
  fetchAll: () => Promise<void>
  save: (input: DayPlanInput, id?: number) => Promise<DayPlan>
  remove: (id: number) => Promise<void>
}

export const useDayPlanStore = create<DayPlanState>((set, get) => ({
  plans: [],
  patterns: [],
  loading: false,
  error: null,

  fetchAll: async () => {
    set({ loading: true, error: null })
    try {
      const [plans, patterns] = await Promise.all([listDayPlans(), listPatterns()])
      set({ plans, patterns, loading: false })
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to load day plans', loading: false })
    }
  },

  save: async (input, id) => {
    const saved = id ? await updateDayPlan(id, input) : await createDayPlan(input)
    await get().fetchAll()
    return saved
  },

  remove: async (id) => {
    await deleteDayPlan(id)
    set({ plans: get().plans.filter((p) => p.id !== id) })
  },
}))
```

```typescript
// web/src/stores/sessionStore.ts
import { create } from 'zustand'
import {
  createSession, getActiveSession, getSession, createRound, createEntry,
  createSet, completeSession, discardSession, getCoverage,
} from '../services/sessions'
import type { TrainingSession, Coverage, EntrySet } from '../services/sessions'

interface SessionState {
  session: TrainingSession | null
  coverage: Coverage | null
  loading: boolean
  error: string | null
  start: (dayPlanId: number | null) => Promise<TrainingSession>
  resume: () => Promise<TrainingSession | null>
  refresh: () => Promise<void>
  addRound: () => Promise<number>
  addEntry: (roundId: number, exerciseId: number, position: number) => Promise<void>
  logSet: (entryId: number, s: { set_number: number; weight?: number | null; reps?: number | null }) => Promise<EntrySet>
  complete: () => Promise<void>
  discard: () => Promise<void>
}

export const useSessionStore = create<SessionState>((set, get) => ({
  session: null,
  coverage: null,
  loading: false,
  error: null,

  start: async (dayPlanId) => {
    set({ loading: true, error: null })
    try {
      const session = await createSession(dayPlanId)
      set({ session, loading: false })
      await get().refresh()
      return session
    } catch (e) {
      set({ error: e instanceof Error ? e.message : 'Failed to start session', loading: false })
      throw e
    }
  },

  resume: async () => {
    const session = await getActiveSession()
    set({ session })
    if (session) await get().refresh()
    return session
  },

  refresh: async () => {
    const current = get().session
    if (!current) return
    const [session, coverage] = await Promise.all([
      getSession(current.id),
      getCoverage(current.id),
    ])
    set({ session, coverage })
  },

  addRound: async () => {
    const current = get().session
    if (!current) throw new Error('No active session')
    const round = await createRound(current.id)
    await get().refresh()
    return round.id
  },

  addEntry: async (roundId, exerciseId, position) => {
    await createEntry(roundId, exerciseId, position)
    await get().refresh()
  },

  logSet: async (entryId, s) => {
    const logged = await createSet(entryId, s)
    await get().refresh()
    return logged
  },

  complete: async () => {
    const current = get().session
    if (!current) return
    const session = await completeSession(current.id)
    set({ session })
  },

  discard: async () => {
    const current = get().session
    if (!current) return
    await discardSession(current.id)
    set({ session: null, coverage: null })
  },
}))
```

Match the store creation idiom used in `web/src/stores/routineStore.ts` (e.g. `create<T>()(...)` with middleware) if it differs from the plain `create<T>(...)` shown here.

- [ ] **Step 2: Verify build, then commit**

Run: `cd web && npm run build`
Expected: tsc passes

```bash
git add web/src/stores/dayPlanStore.ts web/src/stores/sessionStore.ts web/src/stores/index.ts
git commit -m "[SH] feat: add day plan and session Zustand stores"
```

---

### Task 17: Day Plans page (designer)

**Files:**
- Create: `web/src/pages/DayPlans.tsx`

**Interfaces:**
- Consumes: `useDayPlanStore`, `useSessionStore.start`, `react-router-dom` `useNavigate`
- Produces: route component for `/` — lists day plans, create/edit form (name, description, rounds target, warm-up preference note, pattern goal checklist with required toggle + target sets), Start Session button per plan

- [ ] **Step 1: Write the page**

```tsx
// web/src/pages/DayPlans.tsx
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDayPlanStore } from '../stores/dayPlanStore'
import { useSessionStore } from '../stores/sessionStore'
import type { DayPlan, DayPlanInput, PatternGoal } from '../services/dayPlans'

const EMPTY: DayPlanInput = {
  name: '',
  description: null,
  warmup_preferences: [],
  rounds_target: 3,
  goals: [],
}

export default function DayPlans() {
  const { plans, patterns, loading, error, fetchAll, save, remove } = useDayPlanStore()
  const startSession = useSessionStore((s) => s.start)
  const navigate = useNavigate()
  const [editing, setEditing] = useState<DayPlan | null>(null)
  const [draft, setDraft] = useState<DayPlanInput | null>(null)

  useEffect(() => {
    fetchAll()
  }, [fetchAll])

  const openEditor = (plan?: DayPlan) => {
    setEditing(plan ?? null)
    setDraft(plan ? { ...plan, goals: plan.goals.map((g) => ({ ...g })) } : { ...EMPTY, goals: [] })
  }

  const toggleGoal = (patternId: number) => {
    if (!draft) return
    const has = draft.goals.some((g) => g.pattern_id === patternId)
    const goals: PatternGoal[] = has
      ? draft.goals.filter((g) => g.pattern_id !== patternId)
      : [...draft.goals, { pattern_id: patternId, required: true, target_sets: 3, rep_range_min: null, rep_range_max: null }]
    setDraft({ ...draft, goals })
  }

  const submit = async () => {
    if (!draft || !draft.name.trim()) return
    await save(draft, editing?.id)
    setDraft(null)
    setEditing(null)
  }

  const handleStart = async (plan: DayPlan) => {
    await startSession(plan.id)
    navigate('/session')
  }

  if (loading) return <div className="container mx-auto p-6">Loading day plans...</div>

  return (
    <div className="container mx-auto p-6 max-w-3xl">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Day Plans</h1>
        <button onClick={() => openEditor()} className="bg-blue-600 text-white px-4 py-2 rounded-md">
          New Day Plan
        </button>
      </div>
      {error && <div className="text-red-600 mb-4">{error}</div>}

      {plans.map((plan) => (
        <div key={plan.id} className="bg-white rounded-lg shadow p-4 mb-3 flex justify-between items-center">
          <div>
            <div className="font-semibold">{plan.name}</div>
            <div className="text-sm text-gray-500">
              {plan.rounds_target} rounds ·{' '}
              {plan.goals
                .map((g) => patterns.find((p) => p.id === g.pattern_id)?.name ?? g.pattern_id)
                .join(', ')}
            </div>
          </div>
          <div className="space-x-2">
            <button onClick={() => handleStart(plan)} className="bg-green-600 text-white px-3 py-1.5 rounded-md">
              Start Session
            </button>
            <button onClick={() => openEditor(plan)} className="text-blue-600 px-2">Edit</button>
            <button onClick={() => remove(plan.id)} className="text-red-500 px-2">Delete</button>
          </div>
        </div>
      ))}
      {plans.length === 0 && <p className="text-gray-500">No day plans yet. Create one to get started.</p>}

      {draft && (
        <div className="bg-white rounded-lg shadow p-6 mt-6">
          <h2 className="text-lg font-semibold mb-4">{editing ? 'Edit Day Plan' : 'New Day Plan'}</h2>
          <label className="block mb-3">
            <span className="text-sm text-gray-600">Name</span>
            <input
              value={draft.name}
              onChange={(e) => setDraft({ ...draft, name: e.target.value })}
              className="mt-1 w-full border rounded-md px-3 py-2"
              placeholder="e.g. Full Body A"
            />
          </label>
          <label className="block mb-3">
            <span className="text-sm text-gray-600">Rounds target</span>
            <input
              type="number"
              min={1}
              max={10}
              value={draft.rounds_target}
              onChange={(e) => setDraft({ ...draft, rounds_target: Number(e.target.value) })}
              className="mt-1 w-24 border rounded-md px-3 py-2"
            />
          </label>
          <div className="mb-4">
            <span className="text-sm text-gray-600 block mb-2">Pattern goals</span>
            {patterns
              .filter((p) => p.slug !== 'conditioning')
              .map((p) => {
                const goal = draft.goals.find((g) => g.pattern_id === p.id)
                return (
                  <div key={p.id} className="flex items-center gap-3 py-1">
                    <label className="flex items-center gap-2 flex-1">
                      <input type="checkbox" checked={!!goal} onChange={() => toggleGoal(p.id)} />
                      {p.name}
                    </label>
                    {goal && (
                      <>
                        <label className="text-sm flex items-center gap-1">
                          <input
                            type="checkbox"
                            checked={goal.required}
                            onChange={(e) =>
                              setDraft({
                                ...draft,
                                goals: draft.goals.map((g) =>
                                  g.pattern_id === p.id ? { ...g, required: e.target.checked } : g
                                ),
                              })
                            }
                          />
                          required
                        </label>
                        <input
                          type="number"
                          min={1}
                          max={30}
                          value={goal.target_sets ?? 3}
                          onChange={(e) =>
                            setDraft({
                              ...draft,
                              goals: draft.goals.map((g) =>
                                g.pattern_id === p.id ? { ...g, target_sets: Number(e.target.value) } : g
                              ),
                            })
                          }
                          className="w-16 border rounded-md px-2 py-1 text-sm"
                          title="Target sets"
                        />
                      </>
                    )}
                  </div>
                )
              })}
          </div>
          <div className="space-x-2">
            <button onClick={submit} className="bg-blue-600 text-white px-4 py-2 rounded-md">
              {editing ? 'Save Changes' : 'Create Day Plan'}
            </button>
            <button onClick={() => { setDraft(null); setEditing(null) }} className="text-gray-600 px-3">
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
```

Warm-up preferences UI: for the MVP of this page, `warmup_preferences` passes through unchanged (default `[]`); the Session page falls back to "pick any conditioning exercise" when the list is empty. A preference picker (search + ordered list) can be added to this form later without schema changes.

- [ ] **Step 2: Verify build, then commit**

Run: `cd web && npm run build`
Expected: tsc passes

```bash
git add web/src/pages/DayPlans.tsx
git commit -m "[SH] feat: add Day Plans designer page"
```

---

### Task 18: Session page (warm-up, rounds loop, coverage, summary)

**Files:**
- Create: `web/src/components/session/CoverageChips.tsx`
- Create: `web/src/components/session/SuggestionList.tsx`
- Create: `web/src/components/session/EntryCard.tsx`
- Create: `web/src/pages/Session.tsx`

**Interfaces:**
- Consumes: `useSessionStore`, `getAnchorSuggestions`, `getPartnerSuggestions`, exercise search service (`web/src/services/exercises.ts` — reuse its existing search function for the fallback picker)
- Produces: route component for `/session` — warm-up card first, then rounds: anchor pick (grouped staples) → partner suggestions (position 2, optional 3) → per-entry set logging with target display → coverage chips → Finish with summary

- [ ] **Step 1: Write the shared components**

```tsx
// web/src/components/session/CoverageChips.tsx
import type { Coverage } from '../../services/sessions'

export default function CoverageChips({ coverage }: { coverage: Coverage | null }) {
  if (!coverage || coverage.goals.length === 0) return null
  return (
    <div className="flex flex-wrap gap-2 mb-4" data-testid="coverage-chips">
      {coverage.goals.map((g) => (
        <span
          key={g.pattern_id}
          className={`px-3 py-1 rounded-full text-sm ${
            g.covered
              ? 'bg-green-100 text-green-800'
              : g.required
                ? 'bg-yellow-100 text-yellow-800'
                : 'bg-gray-100 text-gray-600'
          }`}
        >
          {g.name} {g.sets_done}/{g.target_sets}
          {!g.required && ' (optional)'}
        </span>
      ))}
    </div>
  )
}
```

```tsx
// web/src/components/session/SuggestionList.tsx
import { useState } from 'react'
import type { SuggestionCard, NotRecommendedEntry } from '../../services/suggestions'

interface Props {
  cards: SuggestionCard[]
  novelty?: SuggestionCard | null
  notRecommended: NotRecommendedEntry[]
  onSelect: (card: SuggestionCard) => void
}

export default function SuggestionList({ cards, novelty, notRecommended, onSelect }: Props) {
  const [showWhyNot, setShowWhyNot] = useState(false)
  return (
    <div>
      {cards.map((card) => (
        <button
          key={card.exercise_id}
          onClick={() => onSelect(card)}
          className="w-full text-left bg-white border rounded-lg p-3 mb-2 hover:border-blue-400"
        >
          <div className="font-medium">{card.exercise_name}</div>
          <div className="text-sm text-gray-500">
            {card.is_bodyweight ? 'Bodyweight' : card.equipment_name}
            {card.target?.last_summary && ` · Last: ${card.target.last_summary}`}
            {card.target && ` · Target: ${card.target.sets}x${card.target.reps}${card.target.weight != null ? ` @ ${card.target.weight}` : ''}`}
          </div>
        </button>
      ))}
      {novelty && (
        <button
          onClick={() => onSelect(novelty)}
          className="w-full text-left border-2 border-dashed border-purple-300 rounded-lg p-3 mb-2 hover:border-purple-500"
        >
          <div className="text-sm text-purple-600 font-medium">Try something new</div>
          <div className="font-medium">{novelty.exercise_name}</div>
        </button>
      )}
      {notRecommended.length > 0 && (
        <div className="mt-2">
          <button onClick={() => setShowWhyNot(!showWhyNot)} className="text-sm text-gray-500 underline">
            Why not others? ({notRecommended.length})
          </button>
          {showWhyNot && (
            <ul className="text-sm text-gray-500 mt-1 list-disc pl-5">
              {notRecommended.map((n, i) => (
                <li key={i}>{n.exercise_name}: {n.reason}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
```

```tsx
// web/src/components/session/EntryCard.tsx
import { useState } from 'react'
import type { RoundEntry } from '../../services/sessions'

interface Props {
  entry: RoundEntry
  onLogSet: (entryId: number, set: { set_number: number; weight?: number | null; reps?: number | null }) => Promise<unknown>
}

export default function EntryCard({ entry, onLogSet }: Props) {
  const [weight, setWeight] = useState<string>(entry.target?.weight != null ? String(entry.target.weight) : '')
  const [reps, setReps] = useState<string>(entry.target ? String(entry.target.reps) : '')

  const logSet = async () => {
    await onLogSet(entry.id, {
      set_number: entry.sets.length + 1,
      weight: weight === '' ? null : Number(weight),
      reps: reps === '' ? null : Number(reps),
    })
  }

  return (
    <div className="bg-white rounded-lg border p-4 mb-2">
      <div className="flex justify-between">
        <div>
          <span className="text-xs text-gray-400 uppercase mr-2">#{entry.position}</span>
          <span className="font-semibold">{entry.exercise_name}</span>
          <span className="ml-2 text-xs text-gray-500">{entry.pattern_slug.replace('_', ' ')}</span>
        </div>
        <span className="text-sm text-gray-500">{entry.sets.length} sets</span>
      </div>
      {entry.target?.last_summary && (
        <div className="text-sm text-gray-500 mt-1">
          Last: {entry.target.last_summary} → Target: {entry.target.sets}x{entry.target.reps}
          {entry.target.weight != null && ` @ ${entry.target.weight}`}
        </div>
      )}
      <div className="flex gap-2 mt-3 items-center">
        <input
          value={weight}
          onChange={(e) => setWeight(e.target.value)}
          placeholder="weight"
          className="w-24 border rounded-md px-2 py-1"
          inputMode="decimal"
        />
        <input
          value={reps}
          onChange={(e) => setReps(e.target.value)}
          placeholder="reps"
          className="w-20 border rounded-md px-2 py-1"
          inputMode="numeric"
        />
        <button onClick={logSet} className="bg-blue-600 text-white px-3 py-1.5 rounded-md text-sm">
          Log Set
        </button>
      </div>
      {entry.sets.length > 0 && (
        <div className="text-sm text-gray-600 mt-2">
          {entry.sets.map((s) => `${s.reps ?? '-'}${s.weight != null ? `@${s.weight}` : ''}`).join(', ')}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Write the Session page**

```tsx
// web/src/pages/Session.tsx
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSessionStore } from '../stores/sessionStore'
import { getAnchorSuggestions, getPartnerSuggestions } from '../services/suggestions'
import type { AnchorSuggestions, PartnerSuggestions, SuggestionCard } from '../services/suggestions'
import CoverageChips from '../components/session/CoverageChips'
import SuggestionList from '../components/session/SuggestionList'
import EntryCard from '../components/session/EntryCard'

type Picker =
  | { kind: 'anchor'; roundId: number }
  | { kind: 'partner'; roundId: number; anchorExerciseId: number; position: 2 | 3 }
  | null

export default function Session() {
  const { session, coverage, resume, refresh, addRound, addEntry, logSet, complete, discard } = useSessionStore()
  const navigate = useNavigate()
  const [picker, setPicker] = useState<Picker>(null)
  const [anchorData, setAnchorData] = useState<AnchorSuggestions | null>(null)
  const [partnerData, setPartnerData] = useState<PartnerSuggestions | null>(null)
  const [finished, setFinished] = useState(false)

  useEffect(() => {
    if (!session) resume()
  }, [session, resume])

  useEffect(() => {
    if (!picker || !session) return
    if (picker.kind === 'anchor') {
      getAnchorSuggestions(session.id).then(setAnchorData)
    } else {
      getPartnerSuggestions(session.id, picker.anchorExerciseId, picker.position).then(setPartnerData)
    }
  }, [picker, session])

  if (!session) {
    return (
      <div className="container mx-auto p-6">
        <p className="text-gray-500">No active session.</p>
        <button onClick={() => navigate('/')} className="text-blue-600 underline mt-2">
          Pick a day plan to start
        </button>
      </div>
    )
  }

  const startRound = async () => {
    const roundId = await addRound()
    setPicker({ kind: 'anchor', roundId })
  }

  const selectExercise = async (card: SuggestionCard) => {
    if (!picker) return
    const position = picker.kind === 'anchor' ? 1 : picker.position
    await addEntry(picker.roundId, card.exercise_id, position)
    if (picker.kind === 'anchor') {
      setPicker({ kind: 'partner', roundId: picker.roundId, anchorExerciseId: card.exercise_id, position: 2 })
    } else if (picker.position === 2) {
      setPicker(null) // user can add a #3 explicitly from the round card
    } else {
      setPicker(null)
    }
    setAnchorData(null)
    setPartnerData(null)
  }

  const finish = async () => {
    await complete()
    setFinished(true)
  }

  if (finished) {
    return (
      <div className="container mx-auto p-6 max-w-2xl">
        <h1 className="text-2xl font-bold mb-4">Session Complete</h1>
        <CoverageChips coverage={coverage} />
        <div className="bg-white rounded-lg border p-4">
          {session.rounds.map((r) => (
            <div key={r.id} className="mb-2">
              <span className="text-sm text-gray-400 mr-2">Round {r.order}:</span>
              {r.entries.map((e) => `${e.exercise_name} (${e.sets.length} sets)`).join(' + ')}
            </div>
          ))}
        </div>
        <button onClick={() => navigate('/')} className="mt-4 bg-blue-600 text-white px-4 py-2 rounded-md">
          Back to Day Plans
        </button>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-6 max-w-2xl">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold">Active Session</h1>
        <div className="space-x-3">
          <button onClick={finish} className="bg-green-600 text-white px-4 py-2 rounded-md">
            Finish Session
          </button>
          <button
            onClick={async () => { if (confirm('Discard this session?')) { await discard(); navigate('/') } }}
            className="text-red-500"
          >
            Discard
          </button>
        </div>
      </div>

      <CoverageChips coverage={coverage} />

      {session.rounds.map((round) => (
        <div key={round.id} className="mb-6">
          <div className="flex justify-between items-center mb-2">
            <h2 className="font-semibold text-gray-700">Round {round.order}</h2>
            {round.entries.length > 0 && round.entries.length < 3 && (
              <button
                onClick={() =>
                  setPicker({
                    kind: 'partner',
                    roundId: round.id,
                    anchorExerciseId: round.entries[0].exercise_id,
                    position: (round.entries.length + 1) as 2 | 3,
                  })
                }
                className="text-sm text-blue-600"
              >
                + Add exercise #{round.entries.length + 1}
              </button>
            )}
          </div>
          {round.entries.map((entry) => (
            <EntryCard key={entry.id} entry={entry} onLogSet={logSet} />
          ))}
          {round.entries.length === 0 && <p className="text-sm text-gray-400">Pick an anchor below.</p>}
        </div>
      ))}

      {picker && (
        <div className="bg-gray-50 border rounded-lg p-4 mb-4">
          <h3 className="font-semibold mb-3">
            {picker.kind === 'anchor' ? "What's free? Pick your anchor" : `Partner suggestion (#${picker.position})`}
          </h3>
          {picker.kind === 'anchor' &&
            anchorData?.groups.map((group) => (
              <div key={group.pattern.id} className="mb-3">
                <div className="text-sm text-gray-500 mb-1">
                  {group.pattern.name} {group.covered && '(covered)'}
                </div>
                <SuggestionList
                  cards={group.staples}
                  notRecommended={[]}
                  onSelect={selectExercise}
                />
              </div>
            ))}
          {picker.kind === 'anchor' && anchorData && (
            <SuggestionList cards={[]} notRecommended={anchorData.not_recommended} onSelect={selectExercise} />
          )}
          {picker.kind === 'partner' && partnerData && (
            <SuggestionList
              cards={partnerData.candidates}
              novelty={partnerData.novelty}
              notRecommended={partnerData.not_recommended}
              onSelect={selectExercise}
            />
          )}
          <button onClick={() => setPicker(null)} className="text-sm text-gray-500 mt-2">
            Cancel
          </button>
        </div>
      )}

      {!picker && (
        <button onClick={startRound} className="w-full border-2 border-dashed rounded-lg py-3 text-gray-600 hover:border-blue-400">
          + Start Round {session.rounds.length + 1}
        </button>
      )}
    </div>
  )
}
```

Two required additions to the components above:

1. **Time input in EntryCard** (for warm-ups and timed work). Add alongside weight/reps:

```tsx
// EntryCard: add state and input next to weight/reps
const [timeSec, setTimeSec] = useState<string>('')
// in logSet payload: time_seconds: timeSec === '' ? null : Number(timeSec)
// in the input row:
<input
  value={timeSec}
  onChange={(e) => setTimeSec(e.target.value)}
  placeholder="time (sec)"
  className="w-24 border rounded-md px-2 py-1"
  inputMode="numeric"
/>
```

(Also widen the store/service `logSet` set parameter to include `time_seconds?: number | null` — the backend `EntrySetCreate` already accepts it.)

2. **Warm-up card** — shown when `session.rounds.length === 0` and the day plan has `warmup_preferences`. Add above the rounds list in `Session.tsx`:

```tsx
// Session.tsx: fetch warm-up preference exercises once
// (getExercise(id) from web/src/services/exercises.ts; plan comes from useDayPlanStore)
const dayPlan = useDayPlanStore((s) => s.plans.find((p) => p.id === session?.day_plan_id))
const [warmups, setWarmups] = useState<{ id: number; name: string }[]>([])
useEffect(() => {
  if (!dayPlan?.warmup_preferences?.length) return
  Promise.all(dayPlan.warmup_preferences.map((id) => getExercise(id))).then(setWarmups)
}, [dayPlan])

{session.rounds.length === 0 && warmups.length > 0 && (
  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4" data-testid="warmup-card">
    <h3 className="font-semibold mb-2">Warm-up — what's available?</h3>
    {warmups.map((w, i) => (
      <button
        key={w.id}
        onClick={async () => {
          const roundId = await addRound()
          await addEntry(roundId, w.id, 1)
        }}
        className={`block w-full text-left rounded-md px-3 py-2 mb-1 ${
          i === 0 ? 'bg-white border-2 border-blue-400 font-medium' : 'bg-white border'
        }`}
      >
        {w.name} {i === 0 && <span className="text-xs text-blue-600">(preferred)</span>}
      </button>
    ))}
  </div>
)}
```

The chosen warm-up becomes round 1 with a single entry; duration is logged via the new time input. If `warmup_preferences` is empty the card doesn't render and round 1 starts at the anchor picker as usual.

3. **"Add to staples?" prompts on the finish summary.** In the `finished` block, offer to staple any exercise used this session that isn't already a staple:

```tsx
// finished view: compute non-staple exercises used this session
const [staples, setStaples] = useState<Staple[]>([])
useEffect(() => { if (finished) listStaples().then(setStaples) }, [finished])
const stapleIds = new Set(staples.map((s) => s.exercise_id))
const newExercises = session.rounds
  .flatMap((r) => r.entries)
  .filter((e) => !stapleIds.has(e.exercise_id))

{newExercises.length > 0 && (
  <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 mt-4">
    <h3 className="font-semibold mb-2">New exercises this session</h3>
    {newExercises.map((e) => (
      <div key={e.id} className="flex justify-between items-center py-1">
        <span>{e.exercise_name}</span>
        <button
          onClick={async () => { await createStaple(e.exercise_id); setStaples(await listStaples()) }}
          className="text-sm bg-purple-600 text-white px-3 py-1 rounded-md"
        >
          Add to staples
        </button>
      </div>
    ))}
  </div>
)}
```

(`listStaples`/`createStaple` from `../services/staples`, `Staple` type from the same module; `getExercise` — use the existing single-exercise fetch in `web/src/services/exercises.ts`, adding it there if only a list fetch exists: `export async function getExercise(id: number) { const { data } = await apiClient.get(`/exercises/${id}`); return data }`.)

- [ ] **Step 3: Verify build, then commit**

Run: `cd web && npm run build`
Expected: tsc passes

```bash
git add web/src/components/session/ web/src/pages/Session.tsx
git commit -m "[SH] feat: add dynamic Session page with anchor/partner flow"
```

---

### Task 19: App cutover (routes, nav, resume banner, retire old flow)

**Files:**
- Modify: `web/src/App.tsx`
- Delete: `web/src/pages/RoutineDesigner.tsx`, `web/src/pages/WorkoutStart.tsx`, `web/src/pages/Workout.tsx` (and their now-unused components — check imports before deleting each)
- Delete: `web/e2e/routine-designer.spec.ts`, `web/e2e/workout-critical-path.spec.ts`
- Modify: `web/src/pages/WorkoutHistory.tsx` (add "Sessions" list from new API above the legacy list)

**Interfaces:**
- Consumes: `DayPlans`, `Session` pages, `getActiveSession`
- Produces: `/` → DayPlans, `/session` → Session; nav shows Day Plans / Session / Exercise Browser / History / Analytics / Records / Settings; a resume banner on all pages when an active session exists

- [ ] **Step 1: Update App.tsx**

Replace the RoutineDesigner/WorkoutStart/Workout imports and routes:

```tsx
// web/src/App.tsx — new imports (replacing RoutineDesigner, WorkoutStart, Workout)
import DayPlans from './pages/DayPlans'
import Session from './pages/Session'
import ResumeBanner from './components/session/ResumeBanner'
```

Routes block:

```tsx
<Routes>
  <Route path="/" element={<DayPlans />} />
  <Route path="/session" element={<Session />} />
  <Route path="/exercises" element={<ExerciseBrowser />} />
  <Route path="/history" element={<WorkoutHistory />} />
  <Route path="/analytics" element={<Analytics />} />
  <Route path="/records" element={<PersonalRecords />} />
  <Route path="/settings" element={<Settings />} />
</Routes>
```

Nav links: "Day Plans" → `/`, "Session" → `/session`, keep the rest. Render `<ResumeBanner />` directly under the `<nav>` element.

- [ ] **Step 2: Write the resume banner**

```tsx
// web/src/components/session/ResumeBanner.tsx
import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useSessionStore } from '../../stores/sessionStore'

export default function ResumeBanner() {
  const { session, resume, discard } = useSessionStore()
  const [checked, setChecked] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    if (!checked) {
      resume().finally(() => setChecked(true))
    }
  }, [checked, resume])

  if (!session || session.state === 'completed' || location.pathname === '/session') return null

  return (
    <div className="bg-yellow-50 border-b border-yellow-200 px-6 py-2 flex justify-between items-center" data-testid="resume-banner">
      <span className="text-sm text-yellow-800">You have an unfinished session.</span>
      <div className="space-x-3">
        <button onClick={() => navigate('/session')} className="text-sm font-medium text-blue-600">Resume</button>
        <button onClick={() => discard()} className="text-sm text-red-500">Discard</button>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Add sessions list to WorkoutHistory**

In `WorkoutHistory.tsx`, render a "Sessions" section above the existing legacy list (retitle the old section "Legacy Workouts"), using the page's existing card markup:

```tsx
// WorkoutHistory.tsx additions
import { listSessions } from '../services/sessions'
import type { TrainingSession } from '../services/sessions'

const [sessions, setSessions] = useState<TrainingSession[]>([])
useEffect(() => { listSessions('completed').then(setSessions) }, [])

// above the legacy list:
<h2 className="text-lg font-semibold mb-2">Sessions</h2>
{sessions.map((s) => (
  <div key={s.id} className="bg-white rounded-lg shadow p-4 mb-2">
    <div className="font-medium">{s.started_at ? new Date(s.started_at).toLocaleDateString() : '—'}</div>
    <div className="text-sm text-gray-500">
      {s.rounds.length} rounds ·{' '}
      {s.rounds.map((r) => r.entries.map((e) => e.exercise_name).join(' + ')).join(' | ')}
    </div>
  </div>
))}
{sessions.length === 0 && <p className="text-sm text-gray-400 mb-4">No sessions yet.</p>}
```

- [ ] **Step 3b: Surface pattern progress in Analytics**

Add a "Pattern Progress" section to `web/src/pages/Analytics.tsx` (above the existing content), fulfilling the spec's per-pattern trend + weekly coverage view:

```tsx
// Analytics.tsx additions
import { getPatternProgress } from '../services/patterns'
import type { PatternProgress } from '../services/patterns'

const [progress, setProgress] = useState<PatternProgress[]>([])
useEffect(() => { getPatternProgress(12).then(setProgress) }, [])

<section className="mb-8">
  <h2 className="text-lg font-semibold mb-3">Pattern Progress (12 weeks)</h2>
  {progress.map((p) => {
    const latest = p.trend[p.trend.length - 1]
    const delta = latest ? Math.round((latest.index - 1) * 100) : null
    return (
      <div key={p.pattern_id} className="bg-white rounded-lg shadow p-4 mb-2 flex justify-between items-center">
        <span className="font-medium">{p.name}</span>
        <span className="text-sm text-gray-500">{p.trend.length} weeks tracked</span>
        <span className={`font-semibold ${delta != null && delta >= 0 ? 'text-green-600' : 'text-red-500'}`}>
          {delta != null ? `${delta >= 0 ? '+' : ''}${delta}% vs baseline` : 'no data'}
        </span>
      </div>
    )
  })}
  {progress.length === 0 && <p className="text-sm text-gray-400">Complete some sessions to see pattern trends.</p>}
</section>
```

(A chart can replace the delta rows later; the list satisfies the trend + weekly view requirement with the data already flowing.)

- [ ] **Step 4: Delete retired pages and specs**

```bash
git rm web/src/pages/RoutineDesigner.tsx web/src/pages/WorkoutStart.tsx web/src/pages/Workout.tsx
git rm web/e2e/routine-designer.spec.ts web/e2e/workout-critical-path.spec.ts
```

Then run `cd web && npm run build` and delete any now-orphaned components/stores the compiler flags as unused imports (remove the imports; only delete a component file when nothing else imports it — check with grep first).

- [ ] **Step 5: Verify build and remaining e2e, then commit**

Run: `cd web && npm run build`
Expected: tsc passes
Run: `cd web && npx playwright test e2e/app-shell.spec.ts e2e/read-pages.spec.ts`
Expected: PASS after updating any nav-label assertions in those specs ("Routine Designer" → "Day Plans", "Start Workout" → "Session")

```bash
git add -A web/src web/e2e
git commit -m "[SH] feat: cut web app over to day plans and dynamic sessions"
```

---

### Task 20: E2E critical path (dynamic session)

**Files:**
- Create: `web/e2e/dynamic-session.spec.ts`

**Interfaces:**
- Consumes: running backend (seeded with patterns via `python -m scripts.seed_patterns`) + web dev server per `web/playwright.config.ts` (baseURL `http://localhost:3000`); `useDevice` helper
- Produces: one spec covering: create day plan → start session → anchor pick → partner pick → log sets → coverage updates → finish → summary

- [ ] **Step 1: Write the spec**

```typescript
// web/e2e/dynamic-session.spec.ts
import { test, expect } from '@playwright/test'
import { useDevice } from './helpers/device'

test.beforeEach(async ({ page }) => {
  await useDevice(page)
})

test('create day plan, run a dynamic session with a superset round, finish', async ({ page }) => {
  page.on('dialog', (dialog) => dialog.accept())

  // Create a day plan with pull + push goals
  await page.goto('/')
  await page.getByRole('button', { name: 'New Day Plan' }).click()
  await page.getByPlaceholder('e.g. Full Body A').fill('E2E Dynamic Day')
  await page.getByLabel('Horizontal Pull').check()
  await page.getByLabel('Horizontal Push').check()
  await page.getByRole('button', { name: 'Create Day Plan' }).click()
  await expect(page.getByText('E2E Dynamic Day')).toBeVisible()

  // A staple is needed for anchor suggestions: add one via the Exercise Browser
  // (the browser page gets an "Add to Staples" action in this task if not present:
  // a button per exercise row calling createStaple(exercise.id))
  await page.goto('/exercises')
  await page.getByPlaceholder(/search/i).first().fill('cable row')
  await page.getByRole('button', { name: 'Add to Staples' }).first().click()
  await page.getByPlaceholder(/search/i).first().fill('push up')
  await page.getByRole('button', { name: 'Add to Staples' }).first().click()

  // Start the session
  await page.goto('/')
  await page.getByRole('button', { name: 'Start Session' }).first().click()
  await expect(page.getByRole('heading', { name: 'Active Session' })).toBeVisible({ timeout: 10_000 })

  // Round 1: anchor
  await page.getByRole('button', { name: /Start Round 1/ }).click()
  await expect(page.getByText(/Pick your anchor/)).toBeVisible()
  await page.getByRole('button', { name: /Cable Row/i }).first().click()

  // Partner suggestions appear (opposite pattern)
  await expect(page.getByText(/Partner suggestion/)).toBeVisible()
  await page.getByRole('button', { name: /Push Up/i }).first().click()

  // Log a set on each entry
  const entryCards = page.locator('div.bg-white.rounded-lg.border')
  await entryCards.first().getByPlaceholder('weight').fill('100')
  await entryCards.first().getByPlaceholder('reps').fill('10')
  await entryCards.first().getByRole('button', { name: 'Log Set' }).click()
  await expect(page.getByText('1 sets').first()).toBeVisible()

  // Coverage chips reflect progress
  await expect(page.getByTestId('coverage-chips')).toBeVisible()

  // Finish
  await page.getByRole('button', { name: 'Finish Session' }).click()
  await expect(page.getByRole('heading', { name: 'Session Complete' })).toBeVisible()
  await expect(page.getByText(/Round 1:/)).toBeVisible()
})
```

Supporting change: add an "Add to Staples" button to each exercise row/card in `web/src/pages/ExerciseBrowser.tsx` that calls `createStaple(exercise.id)` (from Task 15's `staples.ts`) and shows a brief confirmation; ignore 409 (already a staple).

- [ ] **Step 2: Run the e2e suite**

Run: `cd web && npx playwright test e2e/dynamic-session.spec.ts`
Expected: PASS (backend must be running with patterns seeded: `cd backend && python -m scripts.seed_patterns && uvicorn app.main:app --port 8000`; the Playwright `webServer` config starts the web app)

- [ ] **Step 3: Commit**

```bash
git add web/e2e/dynamic-session.spec.ts web/src/pages/ExerciseBrowser.tsx
git commit -m "[SH] test: add dynamic session e2e critical path"
```

---

## Final Verification

- [ ] `cd backend && pytest` — full backend suite green
- [ ] `cd web && npm run build && npx playwright test` — build + all e2e green
- [ ] Manual smoke: seed scripts run against the dev DB (`python -m scripts.seed_patterns`, `python -m scripts.backfill_staples`), then walk the vignette: open app → Day Plans → start session → warm-up/anchor → partner suggestion shows opposite pattern → log sets → coverage chips update → finish → summary

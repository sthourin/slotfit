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
**Status**: [ ] Not Started  [ ] In Progress  [ ] Complete

Add "not_recommended" array to AI response.

**Reference**: @.cursor/context/api.md (Enhanced Recommendation Response)

**Files to modify:**
- `backend/app/schemas/recommendation.py`
- `backend/app/services/ai/recommendation_service.py`

**Add to response:**
- `not_recommended` array with exercise_id, exercise_name, reason
- New factors: movement_balance, weekly_volume_status

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

## Phase 4: Web Workout Execution

### Task 4.1: Workout Start Flow
**Status**: [ ] Not Started  [ ] In Progress  [ ] Complete

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
**Status**: [ ] Not Started  [ ] In Progress  [ ] Complete

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
**Status**: [ ] Not Started  [ ] In Progress  [ ] Complete

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
**Status**: [ ] Not Started  [ ] In Progress  [ ] Complete

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
**Status**: [ ] Not Started  [ ] In Progress  [ ] Complete

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
**Status**: [ ] Not Started  [ ] In Progress  [ ] Complete

**Files to create:**
- `web/src/pages/WorkoutHistory.tsx`
- `web/src/components/history/WorkoutCard.tsx`
- `web/src/components/history/WorkoutDetail.tsx`

---

### Task 5.2: Analytics Dashboard
**Status**: [ ] Not Started  [ ] In Progress  [ ] Complete

**Files to create:**
- `web/src/pages/Analytics.tsx`
- `web/src/components/analytics/VolumeChart.tsx`
- `web/src/components/analytics/ProgressionChart.tsx`
- `web/src/components/analytics/MovementBalance.tsx`
- `web/src/components/analytics/SlotPerformance.tsx`

**Charts:** Use recharts or chart.js

---

### Task 5.3: Personal Records Page
**Status**: [ ] Not Started  [ ] In Progress  [ ] Complete

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

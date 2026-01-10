# SlotFit - Claude Code Project Guide

## Project Overview

SlotFit is a workout planning app with a novel "slot-based" approach. Users create routine templates with flexible slots targeting muscle groups, then select exercises on-the-fly during workouts based on available equipment.

**Development Strategy**: Web-first - build a fully-featured web app before Android native development.

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, PostgreSQL, SQLAlchemy, Alembic
- **Web**: React 18, TypeScript, Vite, Zustand, Tailwind CSS
- **AI**: Anthropic Claude API

## Project Structure

```
slotfit/
├── backend/           # FastAPI backend
│   ├── app/
│   │   ├── api/v1/    # API routes
│   │   ├── models/    # SQLAlchemy models
│   │   ├── schemas/   # Pydantic schemas
│   │   ├── services/  # Business logic
│   │   └── core/      # Config
│   ├── alembic/       # Database migrations
│   └── tests/
├── web/               # React frontend
│   └── src/
├── android/           # Future - Native Android
└── assets/            # Exercise database CSV
```

## Quick Commands

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Database
```bash
cd backend
alembic upgrade head          # Run migrations
alembic revision --autogenerate -m "description"  # Create migration
```

### Web
```bash
cd web
npm install
npm run dev
```

### Tests
```bash
cd backend
pytest
```

## Current State

### Completed
- ✅ Backend project structure
- ✅ Core models: Exercise, MuscleGroup, Equipment, RoutineTemplate, RoutineSlot, WorkoutSession, WorkoutExercise, WorkoutSet
- ✅ Exercise database CSV (3,244 exercises)
- ✅ Basic API endpoints

### In Progress
- 🔄 AI recommendation service
- 🔄 Web interface foundation

### Not Started (Priority Order)
1. Equipment Profiles (location-based equipment presets)
2. Enhanced Slot Types (warmup, finisher, active_recovery, wildcard)
3. Slot Templates (reusable configurations)
4. Personal Records tracking
5. Weekly Volume tracking (periodization)
6. Web workout execution interface

## Key Documentation

- **Main Plan**: `.cursor/plans/slotfit_plan.md`
- **Analysis**: `.cursor/plans/slotfit_plan_analysis.md`
- **Exercise CSV**: `assets/slotfit_exercise_database_with_urls.csv`

## Database Connection

Default PostgreSQL connection (check `backend/.env`):
```
DATABASE_URL=postgresql://user:password@localhost:5432/slotfit
```

## API Conventions

- All endpoints under `/api/v1/`
- Pydantic schemas for request/response validation
- SQLAlchemy async sessions
- Standard CRUD patterns

## Code Style

- Python: Black formatter, isort for imports
- TypeScript: ESLint + Prettier
- Use type hints everywhere
- Docstrings for public functions

## Important Notes

1. **Exercise Database**: CSV in `assets/` - don't modify, import via scripts
2. **Muscle Group Hierarchy**: 4 levels (Target → Prime Mover → Secondary → Tertiary)
3. **Slot-to-Exercise**: 1:1 relationship (one exercise per slot)
4. **Web-First**: Build all features for web before Android
5. **No Auth Yet**: MVP uses browser local storage, auth deferred

## Design Decisions

These decisions have been made during development and should be followed consistently.

### Bodyweight Exercises
Exercises with `primary_equipment_id = NULL` (bodyweight exercises) are **ALWAYS** available regardless of equipment profile selection. They should never be filtered out for equipment reasons in recommendations or exercise selection.

### Workout Slot Pre-Population
When starting a workout from a routine:
1. Query the most recent **COMPLETED** workout using that routine
2. Pre-fill slots with the exercises from that workout
3. If no previous completed workout exists, slots start empty (user selects exercises)

This provides continuity for users who repeat the same routine regularly.

### Save As New Routine
If the user modifies exercises during a workout (different from the pre-filled selections):
- At workout completion, prompt: "You made changes to this routine. Save as new routine?"
- Options: "Save as New", "Update Original", "Don't Save Changes"
- This allows maintaining alternate versions (e.g., "Push Day - Home" vs "Push Day - Gym")

### Workout Resume (Simple Implementation)
On app load, check localStorage for active workout state:
- If found and `workout.state` is `'draft'` or `'active'`:
  - Show a **banner** at top of screen: "You have an unfinished workout. [Resume] [Discard]"
- No modal interruption - just a persistent banner until user takes action
- This is the simplest implementation; can be enhanced later if needed

### AI Recommendation "Why Not" Feature
The recommendation response includes a `not_recommended` array explaining why exercises were filtered:
- Equipment not available
- Weekly volume exceeded for muscle group (>20 sets)
- Performed recently (within 48 hours)
- Does not target selected muscle groups
- May aggravate user's injury (see below)

Limit to ~10 entries with diverse reason types. This powers the "Why Not" expandable section in the Exercise Selection Modal.

### Injury-Aware Recommendations
Users can add injuries to their profile, which filters exercise recommendations:

**Architecture (Phase 1 - Curated Mappings):**
- Predefined injury types (e.g., "Rotator Cuff Injury", "Lower Back Pain")
- Each injury has movement restrictions (patterns, force types, postures to avoid)
- Severity levels (mild/moderate/severe) determine which restrictions apply
- Exercises matching restrictions appear in `not_recommended` with reason "May aggravate {injury}"

**Key Design Decisions:**
- **Conservative approach**: When uncertain, exclude the exercise (safety first)
- **Severity-based filtering**: Mild injuries restrict specific movements; severe injuries may exclude entire force types
- **Always include disclaimer**: "Not medical advice - consult a healthcare professional"
- **Bodyweight exercises**: Still follow injury restrictions (no special treatment)

**Future Phases:**
- Phase 2: PubMed research integration to expand injury mappings
- Phase 3: Free-text injury input with AI interpretation
- Phase 3: User overrides ("My PT cleared me for this exercise")

## Common Tasks

### Adding a New Model
1. Create model in `backend/app/models/`
2. Add to `backend/app/models/__init__.py`
3. Create Pydantic schemas in `backend/app/schemas/`
4. Create Alembic migration
5. Add API endpoints in `backend/app/api/v1/endpoints/`

### Adding a New API Endpoint
1. Create endpoint file in `backend/app/api/v1/endpoints/`
2. Register router in `backend/app/api/v1/api.py`
3. Add Pydantic schemas for request/response
4. Write tests in `backend/tests/`

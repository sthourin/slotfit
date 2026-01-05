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

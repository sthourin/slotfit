# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SlotFit is a workout planning app with a "slot-based" approach. Users create routine templates with flexible slots targeting muscle groups, then select exercises on-the-fly during workouts based on available equipment.

**Development Strategy**: Web-first - build fully-featured web app before Android native development.

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, PostgreSQL, SQLAlchemy (async), Alembic
- **Web**: React 18, TypeScript, Vite, Zustand, Tailwind CSS
- **AI**: Anthropic Claude API (with Gemini fallback)

## Quick Commands

### Backend
```bash
# PREFERRED: Use restart script to avoid stale server issues
.\restart-server.bat

# Or manually:
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Database
```bash
cd backend
alembic upgrade head                           # Run migrations
alembic revision --autogenerate -m "description"  # Create migration
```

### Web
```bash
cd web
npm install
npm run dev      # Dev server at http://localhost:3000
npm run build    # Production build
npm run lint     # ESLint
```

### Tests
```bash
cd backend
pytest                              # Run all tests
pytest tests/test_exercises.py      # Single test file
pytest -k "test_create"             # Tests matching pattern
pytest --cov=app --cov-report=html  # With coverage report
```

## Critical: FastAPI Server Management

**Stale server processes cause new endpoints to not appear in OpenAPI/Swagger.**

### Symptoms of Stale Server
- New endpoints missing from http://localhost:8000/docs
- API returns 404 for newly added endpoints
- Changes to Pydantic schemas not reflected

### Solution
Always kill Python processes before restarting:
```bash
# Windows (preferred)
.\restart-server.bat

# Or manually:
taskkill /F /IM python.exe
cd backend && uvicorn app.main:app --reload --port 8000
```

## Architecture

### Backend Structure
```
backend/
├── app/
│   ├── api/v1/endpoints/   # Route handlers (one file per resource)
│   ├── models/             # SQLAlchemy models
│   ├── schemas/            # Pydantic request/response schemas
│   ├── services/           # Business logic
│   │   └── ai/             # AI recommendation providers
│   └── core/               # Config, database, dependencies
├── alembic/                # Database migrations
└── tests/                  # pytest tests with seed data fixtures
```

### Web Structure
```
web/src/
├── pages/           # Route components
├── components/      # Reusable UI components
├── services/        # API client functions
├── stores/          # Zustand state stores
└── hooks/           # Custom React hooks
```

### Key Architectural Patterns

**User Identification (MVP)**: Device-based using `X-Device-ID` header. All user-scoped endpoints use `get_current_user` dependency from `backend/app/core/deps.py`.

**AI Recommendations**: Three-provider fallback chain (Claude → Gemini → Rule-based) in `backend/app/services/ai/`. All providers implement `AIProvider` interface from `base.py`.

**Workout State**: Persisted to localStorage via Zustand. Check for `'draft'` or `'active'` state on app load to support resume functionality.

## Domain Concepts

### Slot-Based System
- **RoutineTemplate**: Collection of slots defining workout structure
- **RoutineSlot**: Placeholder scoped to muscle groups, filled with exercise during workout
- **Slot Types**: standard, warmup, finisher, active_recovery, wildcard
- **1:1 Relationship**: One exercise per slot

### Key Business Rules
- **Bodyweight Exercises**: `primary_equipment_id = NULL` - ALWAYS available regardless of equipment profile
- **Workout Pre-Population**: Query most recent COMPLETED workout for that routine to pre-fill exercises
- **Weekly Volume**: Deprioritize muscle groups exceeding 20 sets/week in recommendations
- **Injury Filtering**: Conservative approach - exclude exercises when uncertain

## API Conventions

- All endpoints under `/api/v1/`
- User-scoped endpoints require `X-Device-ID` header
- Global data (exercises, muscle groups, equipment) doesn't require user context
- Pydantic schemas for all request/response validation

## Adding New Features

### New Backend Model
1. Create model in `backend/app/models/{feature}.py`
2. Add to `backend/app/models/__init__.py`
3. Create schemas in `backend/app/schemas/{feature}.py`
4. Create endpoint in `backend/app/api/v1/endpoints/{feature}.py`
5. Register router in `backend/app/api/v1/api.py`
6. Run: `alembic revision --autogenerate -m "add {feature}"`
7. Run: `alembic upgrade head`

### New Web Feature
1. Create page in `web/src/pages/{Feature}.tsx`
2. Create components in `web/src/components/{feature}/`
3. Create API service in `web/src/services/{feature}.ts`
4. Create store (if needed) in `web/src/stores/{feature}Store.ts`
5. Add route to `App.tsx`

## Code Style

### Python
- Type hints on all functions
- Async/await for database operations
- Black formatter, isort for imports

### TypeScript
- Strict TypeScript - no `any` types
- Functional components with hooks
- Tailwind CSS only (no CSS modules)

## Key Files Reference

- **Main Plan**: `.cursor/plans/slotfit_plan.md`
- **Task List**: `TASKS.md`
- **Exercise CSV**: `assets/slotfit_exercise_database_with_urls.csv` (don't modify directly)
- **API Router**: `backend/app/api/v1/api.py`
- **User Auth**: `backend/app/core/deps.py` (`get_current_user`)
- **AI Service**: `backend/app/services/ai/service.py`

## Test Infrastructure

Tests use in-memory SQLite with seed data fixtures:
- `conftest.py` - Shared fixtures (`client`, `seeded_db`, `client_with_data`)
- `seed_data.py` - Centralized seed data for muscle groups, equipment, exercises, injuries

Use `USE_PROD_DB=true` environment variable to test against production database.

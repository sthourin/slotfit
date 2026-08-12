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

# REQUIRED after migrations, on every database (dev, e2e, CI):
# seeds movement_patterns and the exercise -> pattern map.
./venv/Scripts/python.exe -m scripts.seed_patterns

# Seeds exercises.bodyweight_fraction for curated bodyweight movements.
# Without it every bodyweight exercise falls back to the default fraction,
# which is usable but undifferentiated.
./venv/Scripts/python.exe -m scripts.seed_leverage
```

The pattern seed is not run by app startup, Alembic, or CI. On a database where
it has not been run, `movement_patterns` is empty and the pattern-based session
feature is inert: entry creation and staple creation both 404.

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

## Configuration

`.env` at the repo root is the single canonical config file. The FastAPI app,
alembic, and everything under `backend/scripts` read it through
`app.core.config`, which resolves it by absolute path — so commands work from
any working directory. `hevy/pull_hevy.py` reads it directly.

Copy `.env.example` to `.env` and fill it in; that template documents every
variable and where to get each key.

Two files stay separate on purpose:
- `web/.env` — Vite only exposes `VITE_`-prefixed vars to the browser bundle,
  so client config is kept physically apart from server secrets.
- `.env.e2e` — the e2e overlay. Nothing auto-loads it; Playwright requires
  `E2E_DATABASE_URL` exported in the shell so a run cannot silently target the
  dev database.

Default PostgreSQL connection:
```
DATABASE_URL=postgresql+asyncpg://postgres:slotfit@localhost:5432/slotfit
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
3. **Movement Patterns**: Every exercise maps to one movement pattern; a session is built live from superset rounds, not from pre-planned slots
4. **Web-First**: Build all features for web before Android
5. **No Auth Yet**: MVP uses browser local storage, auth deferred

## Design Decisions

These decisions have been made during development and should be followed consistently.

### Bodyweight Exercises
Bodyweight exercises are identified by `is_bodyweight()` in
`app/services/exercise_helpers.py`. The catalogue represents bodyweight as an
equipment row named `Bodyweight`: all 209 bodyweight exercises point at it and
**none** use `NULL`. An earlier version of this note claimed
`primary_equipment_id = NULL` was the marker, and the code implemented exactly
that, so the rule below silently never applied to a single exercise.

Resolve the row's id with `bodyweight_equipment_id(db)` once per request and
pass it in. Do not hardcode the id — equipment ids come from whatever seeded the
table, and in the test fixtures id 2 is `Dumbbell`. `NULL` still counts as
bodyweight so a hand-created exercise without equipment is not treated as loaded.

These exercises are **ALWAYS** available regardless of equipment profile
selection. They should never be filtered out for equipment reasons in
recommendations or exercise selection. Use the predicate — do not open-code an
equipment comparison.

### Bodyweight Load and Leverage
Bodyweight exercises carry real load, and that load is scored rather than
ignored:

- Bodyweight is a **dated time series** (`bodyweight_readings`), not a profile
  field. Each set resolves against the reading in effect on the day it was
  performed, so a new weigh-in never retroactively rewrites past volume or
  e1RM. Readings carry a `source` (`manual`, `health_connect`) and upsert on
  (user, instant, source) so a sync is idempotent. Health Connect will
  eventually write here.
- A per-exercise `bodyweight_fraction` scales that reading to the load actually
  moved — a push-up is ~0.64 of bodyweight, a squat ~0.85, an arm circle ~0.05.
  Curated values live in `app/services/leverage.py` and are seeded by
  `scripts.seed_leverage`. Uncurated exercises fall back to
  `DEFAULT_BODYWEIGHT_FRACTION` (0.64), deliberately not 1.0.
- External load **adds** to the bodyweight component: a weighted vest is extra
  load on top of what you already carry.
- With no readings, bodyweight work is **excluded** from e1RM and volume rather
  than assigned a guessed bodyweight.
- `avg_weight` in analytics stays the **logged** weight. It is what the user
  typed, and reporting a leverage-derived number under that name would
  misrepresent their history back to them.
- Progression targets are unaffected. Bodyweight progression stays rep-based
  (last reps + 1, no ceiling); leverage changes how work is scored, not what is
  prescribed.

### Weekly Volume
Volume is computed live from logged sets by
`app/services/volume_service.py`, across both the legacy workout tables and the
training-session tables. It does **not** read the `weekly_volume` aggregate
table: nothing has ever written that table, so every figure the analytics page
and the AI recommendation prompt reported was zero regardless of training.

A set is credited to its **target** muscle group only. The four roles are
levels of a hierarchy over one movement, not a list of muscles worked — a bench
press has target "Chest" (level 1) and prime mover "Pectoralis Major" (level 2),
so counting both reports the same set twice, and adding secondary and tertiary
contributors inflates the chart into noise.

Tonnage uses effective load, so bodyweight work counts. A bodyweight set with
no weigh-in to price it still contributes its sets and reps — those are known —
and simply adds no tonnage.

### Set Protocols and Progression
`next_target` is protocol-aware, and each protocol means something different:

- **REPS / EMOM** — double progression: add a rep until every set is at
  `rep_max`, then add load and reset to `rep_min`.
- **Bodyweight** — no load to add, so reps keep climbing past `rep_max`.
  Clamping to the ceiling prescribed 12 reps to somebody who had just done 15.
- **AMRAP** — beat the best rep count at the same load. Rep ranges do not
  apply: an AMRAP always clears a 12-rep ceiling, so double progression
  escalated load every session without bound.
- **TIME** — no prescription at all. Inventing a rep target from `rep_min`
  produced a rep goal for a rowing machine.

Every logged set must record reps or a duration. Weight alone is not a result,
and a set with neither still credited pattern coverage.

### Pattern-Based Dynamic Sessions
Routine templates with pre-planned muscle-group slots are retired. A session is
built live in the gym instead:
1. A **Day Plan** carries pattern goals (target sets per movement pattern), not an exercise list
2. Starting a session **proposes a whole workout** - anchor, partner, and optional third per round - which the user adjusts by swapping any slot for whatever station is free
3. Each proposed **partner** works the OPPOSITE movement pattern, drawn from the user's staple pool
4. Sets are logged per round entry; pattern coverage updates against the day plan's goals
5. Unstarted rounds re-propose as the session progresses; slots the user chose explicitly are pinned and survive

**Informed by many workouts, a copy of none.** Proposals come from evidence
accumulated across history - which staples are least recently performed, which
patterns are under-covered, what progression the logged sets support. What is
ruled out is replaying the most recent session, which is how the retired routine
templates behaved. There is no "save as new routine" prompt, because there is no
template to diverge from.

An earlier version of this section said "nothing is pre-filled," which overshot
the intent and read as a prohibition on proposing anything at all. See
`docs/superpowers/specs/2026-08-02-proposed-sessions-design.md`.

### Staple Pool
Anchor and partner suggestions come exclusively from the user's **staples** -
exercises they have marked as ones they actually do. A user with an empty pool
gets no suggestions, so the anchor picker must always point them at
`/exercises` to add some rather than rendering an empty list.

### Session Resume (Simple Implementation)
On app load, call `GET /sessions/active` (the server is the source of truth):
- If it returns a session in state `'draft'` or `'active'`:
  - Show a **banner** at top of screen: "You have an unfinished session. [Resume] [Discard]"
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

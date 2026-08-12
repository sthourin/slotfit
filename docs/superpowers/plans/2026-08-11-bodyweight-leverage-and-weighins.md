# Bodyweight Leverage and Weigh-Ins Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make bodyweight work carry real load in the strength math, by recording dated bodyweight readings and multiplying them by a per-exercise leverage coefficient.

**Architecture:** Bodyweight is stored as a time series (`bodyweight_readings`), not a profile field, because a single number would silently rewrite the volume and e1RM of three years of past sets every time it changed — and because Health Connect will eventually feed readings in continuously. Each set resolves its load against the reading in effect on the day it was performed. A per-exercise `bodyweight_fraction` converts that reading into the load actually moved: a push-up is not a pull-up. Coefficients are curated in code and seeded into a column, mirroring the existing `pattern_taxonomy` + `seed_patterns` arrangement.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy async, Alembic, pytest; React 18, TypeScript, Vite, Zustand, Tailwind.

## Global Constraints

- Backend commands must use `backend/venv/Scripts/python.exe`.
- Run backend tests as `cd backend && ./venv/Scripts/python.exe -m pytest`.
- Commit subjects are prefixed `[SH]`.
- Bodyweight exercises are identified by `is_bodyweight()` from `app/services/exercise_helpers.py` (equipment id 2, or NULL). **This helper is created in Task 5 of `2026-08-11-session-flow-fixes.md` — that task is a hard prerequisite for this plan.**
- Weights are in the user's preferred units (`users.preferred_units`, default `"lbs"`). Readings are stored in the same units as logged sets; no unit conversion is introduced here.
- Do not modify `assets/slotfit_exercise_database_with_urls.csv`.
- Seed scripts are not run by app startup, Alembic, or CI. Any new seed must be documented in `CLAUDE.md` next to `scripts.seed_patterns`.

## Decisions This Plan Implements

From the 2026-08-11 standup:

- Bodyweight gets the **full treatment with leverage coefficients**, so e1RM works across push-ups, pull-ups and dips.
- Coefficients are **curated for the user's 15 bodyweight staples**, with a documented default for the remaining 194.
- Bodyweight is a **dated log**, not a static number — Health Connect will update it regularly.

## Scope Boundary

In scope: the readings table and API, the coefficient column and seed, an `effective_load` resolver, and wiring it into e1RM (`pattern_trend`) and volume (`analytics_service`).

Out of scope, deliberately:
- **Progression targets.** `next_target` stays rep-based for bodyweight (last reps + 1, no ceiling) as decided. Leverage does not change what the app prescribes, only how it scores what was done.
- **Personal records.** Records are user-entered rows (`personal_records`), not derived from e1RM, so they are unaffected.
- **Health Connect ingestion itself.** This plan only makes the schema ready for it: readings carry a `source` and are idempotent per source and instant.

## Curated Coefficients

The fraction of bodyweight moved by each of the user's 15 bodyweight staples. Values are conventional strength-training estimates, not measurements; the point is that they are differentiated and defensible, not exact.

| Exercise | Fraction | Reasoning |
|---|---|---|
| Bodyweight Push Up | 0.64 | Standard estimate for hands-and-feet support |
| Bodyweight Squat | 0.85 | Trunk and both legs above the knee joint |
| Bodyweight Walking Lunge | 0.85 | As squat, split stance |
| Bodyweight Squat Jump | 0.85 | Same mass; the jump adds velocity, not load |
| Jumping Lunge | 0.85 | As above, alternating |
| Bodyweight Glute Bridge | 0.55 | Hips and trunk only; shoulders and feet grounded |
| Bodyweight Crunch | 0.35 | Head, arms and upper trunk |
| Superman | 0.35 | Limbs and upper trunk, prone |
| Bodyweight Copenhagen Plank | 0.50 | Side-supported, adductor-loaded |
| Plank Jacks | 0.64 | Plank support, as push-up |
| Bodyweight Mountain Climber (HIIT AMRAP) | 0.64 | Plank support |
| Bodyweight HIIT Burpee | 0.70 | Composite: push-up plus squat-jump phases |
| Bodyweight Skater Jump (HIIT AMRAP) | 0.85 | Single-leg lateral, full lower body |
| High Knees | 0.30 | Running gait; one leg cycling at a time |
| Arm Circles | 0.05 | Arm mass only — near-zero load by design |

`DEFAULT_BODYWEIGHT_FRACTION = 0.64` for anything uncurated: the push-up value, the most common bodyweight movement shape in the catalogue. It is deliberately not 1.0 — assuming full bodyweight for 194 unreviewed exercises would inflate e1RM far more often than it would be right.

## File Structure

**Backend — create**
- `app/models/bodyweight_reading.py` — the `BodyweightReading` model.
- `app/schemas/bodyweight_reading.py` — request/response schemas.
- `app/api/v1/endpoints/bodyweight.py` — list/create/delete readings.
- `app/services/bodyweight_service.py` — reading lookup by date and the `effective_load` resolver.
- `app/services/leverage.py` — the curated table and the default.
- `scripts/seed_leverage.py` — writes the curated fractions into `exercises.bodyweight_fraction`.
- `alembic/versions/<rev>_add_bodyweight_readings_and_fraction.py`

**Backend — modify**
- `app/models/__init__.py` — export `BodyweightReading`.
- `app/models/exercise.py` — add `bodyweight_fraction`.
- `app/api/v1/api.py` — register the router.
- `app/services/progression_service.py` — bodyweight-aware e1RM in `pattern_trend`.
- `app/services/analytics_service.py` — bodyweight-aware volume.
- `CLAUDE.md` — document the new seed script and the design decision.

**Web — create**
- `src/services/bodyweight.ts`
- `src/components/settings/BodyweightLog.tsx`

**Web — modify**
- `src/pages/Settings.tsx` — mount the log.

**Tests — create**
- `backend/tests/test_bodyweight_service.py`
- `backend/tests/test_bodyweight_api.py`

**Tests — modify**
- `backend/tests/test_progression_service.py`

---

## Task 1: Model, migration and the coefficient column

**Files:**
- Create: `backend/app/models/bodyweight_reading.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/models/exercise.py`
- Create: `backend/alembic/versions/<rev>_add_bodyweight_readings_and_fraction.py` (generated)

**Interfaces:**
- Produces: `BodyweightReading` with `id`, `user_id`, `weight`, `recorded_at: DateTime`, `source: str`, `created_at`.
- Produces: `Exercise.bodyweight_fraction: float | None`.

- [ ] **Step 1: Write the model**

Create `backend/app/models/bodyweight_reading.py`:

```python
"""Bodyweight readings - a time series, not a profile field.

Bodyweight drifts. Storing one number and applying it to all history would
silently rewrite the volume and e1RM of every past set each time it changed, so
each reading is dated and sets resolve against the reading in effect on the day
they were performed.

`source` exists because Health Connect will eventually write here alongside
manual entry, and a sync must be able to be idempotent.
"""
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class BodyweightReading(Base):
    __tablename__ = "bodyweight_readings"
    __table_args__ = (
        # One reading per source per instant, so re-running a sync cannot
        # duplicate rows while manual entry stays independent of it.
        UniqueConstraint("user_id", "recorded_at", "source", name="uq_bodyweight_user_instant_source"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # In the user's preferred units (users.preferred_units), same as logged sets.
    weight = Column(Float, nullable=False)
    recorded_at = Column(DateTime, nullable=False, index=True)
    # "manual" today; "health_connect" once that sync exists.
    source = Column(String, nullable=False, default="manual", server_default="manual")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", backref="bodyweight_readings")

    def __repr__(self):
        return f"<BodyweightReading(id={self.id}, weight={self.weight}, recorded_at={self.recorded_at})>"
```

- [ ] **Step 2: Export it and add the exercise column**

In `backend/app/models/__init__.py`, add `BodyweightReading` to the imports and `__all__`, following the existing style.

In `backend/app/models/exercise.py`, add beside the other classification columns:

```python
    # Fraction of bodyweight this movement actually loads: a push-up is ~0.64,
    # a pull-up ~1.0. NULL means uncurated - readers apply
    # DEFAULT_BODYWEIGHT_FRACTION rather than assuming full bodyweight.
    bodyweight_fraction = Column(Float, nullable=True)
```

- [ ] **Step 3: Generate the migration**

```bash
cd backend && ./venv/Scripts/python.exe -m alembic revision --autogenerate -m "add bodyweight readings and fraction"
```

Read the generated file before running it. Confirm it creates `bodyweight_readings` with the unique constraint and adds `exercises.bodyweight_fraction` as nullable, and that it has **not** picked up unrelated drift. Delete any spurious operations.

- [ ] **Step 4: Apply it**

```bash
cd backend && ./venv/Scripts/python.exe -m alembic upgrade head
```

Verify:

```bash
docker exec slotfit-db psql -U postgres -d slotfit -c "\d bodyweight_readings"
docker exec slotfit-db psql -U postgres -d slotfit -c "SELECT count(*) FROM exercises WHERE bodyweight_fraction IS NOT NULL;"
```

Expected: the table exists; the count is 0 (nothing seeded yet).

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/ backend/alembic/versions/
git commit -m "[SH] feat: add bodyweight readings table and leverage fraction column"
```

---

## Task 2: Curated coefficients and the seed script

**Files:**
- Create: `backend/app/services/leverage.py`
- Create: `backend/scripts/seed_leverage.py`
- Modify: `CLAUDE.md`

**Interfaces:**
- Produces: `DEFAULT_BODYWEIGHT_FRACTION: float = 0.64` and `CURATED_FRACTIONS: dict[str, float]` keyed by exact exercise name.
- Produces: `python -m scripts.seed_leverage` writes `CURATED_FRACTIONS` into `exercises.bodyweight_fraction`.

- [ ] **Step 1: Write the curated table**

Create `backend/app/services/leverage.py`:

```python
"""How much of a person's bodyweight each movement actually loads.

Applying one number to everything would be worse than useless: a push-up moves
roughly two thirds of bodyweight, a pull-up all of it, an arm circle almost
none. e1RM computed without that distinction is not comparable across
exercises.

Only the movements the user actually trains are curated. Everything else gets
DEFAULT_BODYWEIGHT_FRACTION, which is the push-up value rather than 1.0 -
assuming full bodyweight for hundreds of unreviewed catalogue rows would
overstate load far more often than it would be correct.

Values are conventional strength-training estimates, not measurements.
"""

# Push-up. The most common bodyweight movement shape in the catalogue, and a
# deliberately conservative stand-in for anything uncurated.
DEFAULT_BODYWEIGHT_FRACTION = 0.64

CURATED_FRACTIONS: dict[str, float] = {
    # Plank-support upper body
    "Bodyweight Push Up": 0.64,
    "Plank Jacks": 0.64,
    "Bodyweight Mountain Climber (HIIT AMRAP)": 0.64,
    # Full lower body
    "Bodyweight Squat": 0.85,
    "Bodyweight Walking Lunge": 0.85,
    "Bodyweight Squat Jump": 0.85,
    "Jumping Lunge": 0.85,
    "Bodyweight Skater Jump (HIIT AMRAP)": 0.85,
    # Composite
    "Bodyweight HIIT Burpee": 0.70,
    # Partially supported
    "Bodyweight Glute Bridge": 0.55,
    "Bodyweight Copenhagen Plank": 0.50,
    # Trunk and limbs only
    "Bodyweight Crunch": 0.35,
    "Superman": 0.35,
    "High Knees": 0.30,
    "Arm Circles": 0.05,
}


def fraction_for(name: str, stored: float | None) -> float:
    """Resolve a movement's bodyweight fraction.

    `stored` is the seeded column value and wins when present, so a
    hand-adjusted row is not overridden by this table at read time.
    """
    if stored is not None:
        return stored
    return CURATED_FRACTIONS.get(name, DEFAULT_BODYWEIGHT_FRACTION)
```

- [ ] **Step 2: Write the seed script**

Create `backend/scripts/seed_leverage.py`, following the structure of `backend/scripts/seed_patterns.py` (read that file first and match its session/bootstrap idiom):

```python
"""Seed exercises.bodyweight_fraction from the curated table.

Idempotent: re-running overwrites the curated rows with the same values and
leaves everything else untouched. Like the pattern seed, this is NOT run by app
startup, Alembic, or CI - run it by hand on every database.
"""
import asyncio

from sqlalchemy import select

from app.core.database import async_session_maker
from app.models.exercise import Exercise
from app.services.leverage import CURATED_FRACTIONS


async def seed_leverage() -> int:
    updated = 0
    async with async_session_maker() as db:
        for name, fraction in CURATED_FRACTIONS.items():
            exercise = (
                await db.execute(select(Exercise).where(Exercise.name == name))
            ).scalar_one_or_none()
            if exercise is None:
                print(f"  skip (not found): {name}")
                continue
            exercise.bodyweight_fraction = fraction
            updated += 1
        await db.commit()
    print(f"Seeded {updated} bodyweight fractions.")
    return updated


if __name__ == "__main__":
    asyncio.run(seed_leverage())
```

Match the actual session factory name used by `scripts/seed_patterns.py` — if it differs from `async_session_maker`, use theirs.

- [ ] **Step 3: Run it**

```bash
cd backend && ./venv/Scripts/python.exe -m scripts.seed_leverage
```

Expected: `Seeded 15 bodyweight fractions.` with no skips. A skip means a name in the table does not match the catalogue — fix the table, do not rename the exercise.

Verify:

```bash
docker exec slotfit-db psql -U postgres -d slotfit -c "SELECT name, bodyweight_fraction FROM exercises WHERE bodyweight_fraction IS NOT NULL ORDER BY name;"
```

- [ ] **Step 4: Document the seed**

In `CLAUDE.md`, under the Database quick-commands block, add it beside the pattern seed:

```bash
# REQUIRED after migrations, on every database (dev, e2e, CI):
# seeds movement_patterns and the exercise -> pattern map.
./venv/Scripts/python.exe -m scripts.seed_patterns

# Seeds exercises.bodyweight_fraction for curated bodyweight movements.
# Without it every bodyweight exercise falls back to the default fraction,
# which is usable but undifferentiated.
./venv/Scripts/python.exe -m scripts.seed_leverage
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/leverage.py backend/scripts/seed_leverage.py CLAUDE.md
git commit -m "[SH] feat: curate bodyweight leverage fractions and seed them"
```

---

## Task 3: Resolve effective load against a dated reading

**Files:**
- Create: `backend/app/services/bodyweight_service.py`
- Create: `backend/tests/test_bodyweight_service.py`

**Interfaces:**
- Consumes: `is_bodyweight` from `app/services/exercise_helpers.py`; `fraction_for` from `app/services/leverage.py`.
- Produces:
  - `async bodyweight_at(db, user_id, when: datetime) -> float | None` — the most recent reading at or before `when`; falls back to the earliest later reading if none precedes it; `None` when the user has no readings.
  - `async bodyweight_timeline(db, user_id) -> list[tuple[datetime, float]]` — all readings ascending, for callers resolving many sets without re-querying.
  - `resolve_bodyweight(timeline, when) -> float | None` — pure lookup against a preloaded timeline.
  - `effective_load(exercise, logged_weight, bodyweight) -> float | None` — total load moved.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_bodyweight_service.py`:

```python
"""Tests for bodyweight resolution and effective load."""
from datetime import datetime

import pytest

from app.models.exercise import Exercise
from app.models.bodyweight_reading import BodyweightReading
from app.models.user import User
from app.services.exercise_helpers import BODYWEIGHT_EQUIPMENT_ID
from app.services.bodyweight_service import (
    bodyweight_at,
    bodyweight_timeline,
    effective_load,
    resolve_bodyweight,
)


TIMELINE = [
    (datetime(2026, 1, 1), 200.0),
    (datetime(2026, 6, 1), 190.0),
]


def test_resolve_uses_the_reading_in_effect_on_the_day():
    assert resolve_bodyweight(TIMELINE, datetime(2026, 3, 1)) == 200.0
    assert resolve_bodyweight(TIMELINE, datetime(2026, 7, 1)) == 190.0


def test_resolve_on_an_exact_reading_date_uses_that_reading():
    assert resolve_bodyweight(TIMELINE, datetime(2026, 6, 1)) == 190.0


def test_resolve_before_any_reading_falls_back_to_the_earliest():
    """Sets predating the first weigh-in still need a number; the nearest is it."""
    assert resolve_bodyweight(TIMELINE, datetime(2025, 12, 1)) == 200.0


def test_resolve_with_no_readings_is_none():
    assert resolve_bodyweight([], datetime(2026, 3, 1)) is None


def test_effective_load_scales_bodyweight_by_the_curated_fraction():
    push_up = Exercise(
        name="Bodyweight Push Up",
        primary_equipment_id=BODYWEIGHT_EQUIPMENT_ID,
        bodyweight_fraction=0.64,
    )
    assert effective_load(push_up, None, 200.0) == pytest.approx(128.0)


def test_effective_load_adds_external_load_to_bodyweight():
    """A weighted vest adds to the bodyweight component, it does not replace it."""
    push_up = Exercise(
        name="Bodyweight Push Up",
        primary_equipment_id=BODYWEIGHT_EQUIPMENT_ID,
        bodyweight_fraction=0.64,
    )
    assert effective_load(push_up, 25.0, 200.0) == pytest.approx(153.0)


def test_effective_load_uses_the_default_fraction_when_uncurated():
    unknown = Exercise(
        name="Some Uncurated Bodyweight Move",
        primary_equipment_id=BODYWEIGHT_EQUIPMENT_ID,
        bodyweight_fraction=None,
    )
    assert effective_load(unknown, None, 100.0) == pytest.approx(64.0)


def test_effective_load_of_a_loaded_exercise_is_just_the_logged_weight():
    deadlift = Exercise(name="Trap Bar Deadlift", primary_equipment_id=17)
    assert effective_load(deadlift, 315.0, 200.0) == 315.0


def test_effective_load_without_a_bodyweight_reading_is_none_for_bodyweight_work():
    """Better to score nothing than to invent a bodyweight."""
    push_up = Exercise(
        name="Bodyweight Push Up",
        primary_equipment_id=BODYWEIGHT_EQUIPMENT_ID,
        bodyweight_fraction=0.64,
    )
    assert effective_load(push_up, None, None) is None


@pytest.mark.asyncio
async def test_bodyweight_at_reads_the_latest_prior_reading(test_db):
    user = User(device_id="bw-at-0001")
    test_db.add(user)
    await test_db.flush()
    test_db.add_all([
        BodyweightReading(user_id=user.id, weight=200.0, recorded_at=datetime(2026, 1, 1), source="manual"),
        BodyweightReading(user_id=user.id, weight=190.0, recorded_at=datetime(2026, 6, 1), source="manual"),
    ])
    await test_db.flush()

    assert await bodyweight_at(test_db, user.id, datetime(2026, 3, 1)) == 200.0
    assert await bodyweight_at(test_db, user.id, datetime(2026, 7, 1)) == 190.0


@pytest.mark.asyncio
async def test_bodyweight_timeline_is_ascending(test_db):
    user = User(device_id="bw-timeline-0001")
    test_db.add(user)
    await test_db.flush()
    test_db.add_all([
        BodyweightReading(user_id=user.id, weight=190.0, recorded_at=datetime(2026, 6, 1), source="manual"),
        BodyweightReading(user_id=user.id, weight=200.0, recorded_at=datetime(2026, 1, 1), source="manual"),
    ])
    await test_db.flush()

    timeline = await bodyweight_timeline(test_db, user.id)
    assert [w for _dt, w in timeline] == [200.0, 190.0]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest tests/test_bodyweight_service.py -v`
Expected: FAIL at import — `app.services.bodyweight_service` does not exist.

- [ ] **Step 3: Write the service**

Create `backend/app/services/bodyweight_service.py`:

```python
"""Bodyweight resolution and effective load.

A bodyweight set's load is a function of when it happened, because bodyweight
is a time series. Callers scoring many sets should fetch the timeline once and
use `resolve_bodyweight`, rather than issuing a query per set.
"""
from bisect import bisect_right
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bodyweight_reading import BodyweightReading
from app.models.exercise import Exercise
from app.services.exercise_helpers import is_bodyweight
from app.services.leverage import fraction_for


async def bodyweight_timeline(
    db: AsyncSession, user_id: int
) -> list[tuple[datetime, float]]:
    """All of a user's readings, oldest first."""
    rows = (
        await db.execute(
            select(BodyweightReading.recorded_at, BodyweightReading.weight)
            .where(BodyweightReading.user_id == user_id)
            .order_by(BodyweightReading.recorded_at)
        )
    ).all()
    return [(recorded_at, weight) for recorded_at, weight in rows]


def resolve_bodyweight(
    timeline: list[tuple[datetime, float]], when: datetime
) -> float | None:
    """The reading in effect at `when`.

    Falls back to the earliest reading for sets that predate the first
    weigh-in: those sets still happened at some bodyweight, and the nearest
    known value is a better estimate than discarding them.
    """
    if not timeline:
        return None
    index = bisect_right([dt for dt, _w in timeline], when)
    if index == 0:
        return timeline[0][1]
    return timeline[index - 1][1]


async def bodyweight_at(
    db: AsyncSession, user_id: int, when: datetime
) -> float | None:
    """Convenience single lookup. Prefer the timeline for bulk work."""
    return resolve_bodyweight(await bodyweight_timeline(db, user_id), when)


def effective_load(
    exercise: Exercise, logged_weight: float | None, bodyweight: float | None
) -> float | None:
    """Total load moved by one set.

    Loaded exercises: the logged weight, unchanged. Bodyweight exercises: the
    leverage-scaled bodyweight plus any external load, because a weighted vest
    adds to what you already carry rather than replacing it.

    Returns None for bodyweight work with no reading to resolve against -
    scoring nothing is preferable to inventing a bodyweight.
    """
    if not is_bodyweight(exercise):
        return logged_weight
    if bodyweight is None:
        return None
    fraction = fraction_for(exercise.name, exercise.bodyweight_fraction)
    return bodyweight * fraction + (logged_weight or 0.0)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest tests/test_bodyweight_service.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/bodyweight_service.py backend/tests/test_bodyweight_service.py
git commit -m "[SH] feat: resolve effective load from dated bodyweight and leverage"
```

---

## Task 4: Readings API

**Files:**
- Create: `backend/app/schemas/bodyweight_reading.py`
- Create: `backend/app/api/v1/endpoints/bodyweight.py`
- Modify: `backend/app/api/v1/api.py`
- Create: `backend/tests/test_bodyweight_api.py`

**Interfaces:**
- Produces:
  - `GET /api/v1/bodyweight` → `list[BodyweightReadingResponse]`, newest first.
  - `POST /api/v1/bodyweight` with `{weight: float, recorded_at: datetime | null, source: str}` → `201`. `recorded_at` defaults to now. Re-posting the same `(recorded_at, source)` updates the weight rather than erroring, so a Health Connect resync is idempotent.
  - `DELETE /api/v1/bodyweight/{id}` → `204`.
- `BodyweightReadingResponse`: `id`, `weight`, `recorded_at`, `source`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_bodyweight_api.py`, following the client/auth fixture style of `backend/tests/test_staples.py`:

```python
"""Tests for the bodyweight readings API."""
import pytest


@pytest.mark.asyncio
async def test_create_and_list_readings(client):
    created = await client.post("/api/v1/bodyweight", json={"weight": 198.5})
    assert created.status_code == 201
    assert created.json()["weight"] == 198.5
    assert created.json()["source"] == "manual"

    listed = await client.get("/api/v1/bodyweight")
    assert listed.status_code == 200
    assert len(listed.json()) == 1


@pytest.mark.asyncio
async def test_readings_are_listed_newest_first(client):
    await client.post("/api/v1/bodyweight", json={"weight": 200.0, "recorded_at": "2026-01-01T09:00:00"})
    await client.post("/api/v1/bodyweight", json={"weight": 190.0, "recorded_at": "2026-06-01T09:00:00"})

    body = (await client.get("/api/v1/bodyweight")).json()
    assert [r["weight"] for r in body] == [190.0, 200.0]


@pytest.mark.asyncio
async def test_reposting_the_same_instant_and_source_updates_in_place(client):
    """A Health Connect resync must not duplicate rows."""
    first = await client.post(
        "/api/v1/bodyweight",
        json={"weight": 200.0, "recorded_at": "2026-01-01T09:00:00", "source": "health_connect"},
    )
    second = await client.post(
        "/api/v1/bodyweight",
        json={"weight": 201.0, "recorded_at": "2026-01-01T09:00:00", "source": "health_connect"},
    )
    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]

    body = (await client.get("/api/v1/bodyweight")).json()
    assert len(body) == 1
    assert body[0]["weight"] == 201.0


@pytest.mark.asyncio
async def test_manual_and_synced_readings_at_the_same_instant_coexist(client):
    await client.post(
        "/api/v1/bodyweight",
        json={"weight": 200.0, "recorded_at": "2026-01-01T09:00:00", "source": "manual"},
    )
    await client.post(
        "/api/v1/bodyweight",
        json={"weight": 201.0, "recorded_at": "2026-01-01T09:00:00", "source": "health_connect"},
    )
    assert len((await client.get("/api/v1/bodyweight")).json()) == 2


@pytest.mark.asyncio
async def test_non_positive_weight_is_rejected(client):
    response = await client.post("/api/v1/bodyweight", json={"weight": 0})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_delete_a_reading(client):
    created = await client.post("/api/v1/bodyweight", json={"weight": 198.5})
    deleted = await client.delete(f"/api/v1/bodyweight/{created.json()['id']}")
    assert deleted.status_code == 204
    assert (await client.get("/api/v1/bodyweight")).json() == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest tests/test_bodyweight_api.py -v`
Expected: FAIL with 404s — the router does not exist.

- [ ] **Step 3: Write the schemas**

Create `backend/app/schemas/bodyweight_reading.py`:

```python
"""Schemas for bodyweight readings."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class BodyweightReadingCreate(BaseModel):
    weight: float = Field(gt=0, description="In the user's preferred units")
    # Defaults to now at the endpoint, so a manual entry needs only a weight.
    recorded_at: Optional[datetime] = None
    source: str = "manual"


class BodyweightReadingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    weight: float
    recorded_at: datetime
    source: str
```

- [ ] **Step 4: Write the endpoints**

Create `backend/app/api/v1/endpoints/bodyweight.py`, matching the dependency style of `app/api/v1/endpoints/staples.py`:

```python
"""Bodyweight readings API."""
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.bodyweight_reading import BodyweightReading
from app.models.user import User
from app.schemas.bodyweight_reading import (
    BodyweightReadingCreate,
    BodyweightReadingResponse,
)

router = APIRouter()


@router.get("", response_model=List[BodyweightReadingResponse])
async def list_readings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """A user's bodyweight readings, newest first."""
    rows = (
        await db.execute(
            select(BodyweightReading)
            .where(BodyweightReading.user_id == current_user.id)
            .order_by(BodyweightReading.recorded_at.desc())
        )
    ).scalars().all()
    return rows


@router.post("", response_model=BodyweightReadingResponse, status_code=status.HTTP_201_CREATED)
async def create_reading(
    payload: BodyweightReadingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record a bodyweight reading.

    Upserts on (user, instant, source) so a repeated sync of the same
    measurement updates it instead of failing on the unique constraint.
    """
    recorded_at = payload.recorded_at or datetime.utcnow()
    existing = (
        await db.execute(
            select(BodyweightReading).where(
                BodyweightReading.user_id == current_user.id,
                BodyweightReading.recorded_at == recorded_at,
                BodyweightReading.source == payload.source,
            )
        )
    ).scalar_one_or_none()

    if existing is not None:
        existing.weight = payload.weight
        await db.commit()
        await db.refresh(existing)
        return existing

    reading = BodyweightReading(
        user_id=current_user.id,
        weight=payload.weight,
        recorded_at=recorded_at,
        source=payload.source,
    )
    db.add(reading)
    await db.commit()
    await db.refresh(reading)
    return reading


@router.delete("/{reading_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reading(
    reading_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    reading = (
        await db.execute(
            select(BodyweightReading).where(
                BodyweightReading.id == reading_id,
                BodyweightReading.user_id == current_user.id,
            )
        )
    ).scalar_one_or_none()
    if reading is not None:
        await db.delete(reading)
        await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

- [ ] **Step 5: Register the router**

In `backend/app/api/v1/api.py`, matching the existing registrations:

```python
from app.api.v1.endpoints import bodyweight

api_router.include_router(bodyweight.router, prefix="/bodyweight", tags=["bodyweight"])
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest tests/test_bodyweight_api.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/bodyweight_reading.py backend/app/api/v1/endpoints/bodyweight.py backend/app/api/v1/api.py backend/tests/test_bodyweight_api.py
git commit -m "[SH] feat: bodyweight readings API with idempotent upsert"
```

---

## Task 5: Use effective load in e1RM trends

`pattern_trend` currently skips any set without a logged weight, so bodyweight staples contribute nothing to a pattern's strength trend. With leverage they can.

**Files:**
- Modify: `backend/app/services/progression_service.py:112-176`
- Test: `backend/tests/test_progression_service.py`

**Interfaces:**
- Consumes: `bodyweight_timeline`, `resolve_bodyweight`, `effective_load` from Task 3.

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_pattern_trend_includes_bodyweight_staples_via_leverage(test_db):
    """A push-up-only pattern must produce a trend once bodyweight is known.

    Before leverage, every set had weight=None and was skipped, so the series
    came back empty no matter how much work was logged.
    """
    await seed_movement_patterns(test_db)
    user = User(device_id="trend-bw-0001")
    test_db.add(user)
    await test_db.flush()

    push_up = Exercise(
        name="Trend Push Up",
        primary_equipment_id=BODYWEIGHT_EQUIPMENT_ID,
        bodyweight_fraction=0.64,
    )
    test_db.add(push_up)
    await test_db.flush()
    test_db.add(StapleExercise(user_id=user.id, exercise_id=push_up.id, pattern_id=2, is_active=True))
    test_db.add(BodyweightReading(
        user_id=user.id, weight=200.0,
        recorded_at=_dt(_monday_weeks_ago(4)), source="manual",
    ))
    await test_db.flush()

    # Two weeks of push-ups: 10 reps, then 20 reps at the same bodyweight.
    for weeks_back, reps in ((3, 10), (1, 20)):
        completed = _dt(_monday_weeks_ago(weeks_back))
        session = TrainingSession(
            user_id=user.id, state=SessionState.COMPLETED,
            started_at=completed, completed_at=completed,
        )
        test_db.add(session)
        await test_db.flush()
        rnd = SupersetRound(session_id=session.id, order=1)
        test_db.add(rnd)
        await test_db.flush()
        entry = RoundEntry(round_id=rnd.id, position=1, exercise_id=push_up.id, pattern_id=2)
        test_db.add(entry)
        await test_db.flush()
        test_db.add(EntrySet(entry_id=entry.id, set_number=1, reps=reps, completed=True))
        await test_db.flush()

    series = await pattern_trend(test_db, user.id, pattern_id=2, weeks=12)
    assert len(series) == 2
    # Baseline week normalises to 1.0; more reps at the same load is a higher index.
    assert series[0]["index"] == pytest.approx(1.0)
    assert series[1]["index"] > 1.0
```

Add `BodyweightReading` and `BODYWEIGHT_EQUIPMENT_ID` to the module's imports.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest tests/test_progression_service.py -k trend_includes_bodyweight -v`
Expected: FAIL — `series` is empty because every set has `w is None`.

- [ ] **Step 3: Load the timeline and score with effective load**

In `pattern_trend`, the loop needs the `Exercise` row (for the fraction and the bodyweight test) and the performance date. Load the staples as objects rather than bare ids:

```python
    result = await db.execute(
        select(Exercise)
        .join(StapleExercise, StapleExercise.exercise_id == Exercise.id)
        .where(
            StapleExercise.user_id == user_id,
            StapleExercise.pattern_id == pattern_id,
            StapleExercise.is_active == True,  # noqa: E712
        )
    )
    staples = result.scalars().all()
    if not staples:
        return []

    # Fetched once, not per set: bodyweight resolution is a lookup, not a query.
    timeline = await bodyweight_timeline(db, user_id)
```

Then replace the `best` computation so it scores effective load:

```python
    weekly_best: dict[int, dict[date, float]] = defaultdict(dict)
    for exercise in staples:
        history = await exercise_set_history(
            db,
            user_id,
            exercise.id,
            limit_sessions=PATTERN_TREND_SAFETY_LIMIT_SESSIONS,
            since=cutoff_dt,
        )
        for perf in history:
            week = _week_start(perf["performed_at"].date())
            bodyweight = resolve_bodyweight(timeline, perf["performed_at"])
            candidates = []
            for w, r, _t in perf["sets"]:
                if not r:
                    continue
                load = effective_load(exercise, w, bodyweight)
                if load is None:
                    continue
                candidates.append(estimate_1rm(load, r))
            best = max(candidates, default=None)
            if best is None:
                continue
            if (
                week not in weekly_best[exercise.id]
                or best > weekly_best[exercise.id][week]
            ):
                weekly_best[exercise.id][week] = best
```

Add the imports:

```python
from app.services.bodyweight_service import (
    bodyweight_timeline,
    effective_load,
    resolve_bodyweight,
)
```

Update the function docstring to say that bodyweight staples contribute via leverage-scaled load, and that they are skipped entirely when the user has no readings.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest tests/test_progression_service.py -v`
Expected: PASS, including the pre-existing trend tests — loaded exercises are unaffected because `effective_load` returns the logged weight for them.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/progression_service.py backend/tests/test_progression_service.py
git commit -m "[SH] feat: include bodyweight staples in pattern strength trends"
```

---

## Task 6: Use effective load in volume analytics

`analytics_service.get_exercise_progression` computes `total_volume` as `(s.weight or 0) * (s.reps or 0)`, so bodyweight sets contribute zero tonnage.

**Files:**
- Modify: `backend/app/services/analytics_service.py:226-236`

- [ ] **Step 1: Read the surrounding method**

Read `get_exercise_progression` in full first. It queries legacy `WorkoutSet` rows; confirm whether the `Exercise` row is already loaded in that scope, and load it if not.

- [ ] **Step 2: Score volume with effective load**

Replace the volume computation, resolving bodyweight per session date:

```python
            bodyweight = resolve_bodyweight(timeline, performed_at)
            total_volume = sum(
                (effective_load(exercise, s.weight, bodyweight) or 0) * (s.reps or 0)
                for s in sets
            )
```

`performed_at` is that session's completion timestamp — use whatever the surrounding loop already calls it. If the loop has no per-session date in scope, resolve once against `datetime.utcnow()` and note the approximation in a comment rather than inventing a date per set.

Fetch `timeline = await bodyweight_timeline(self.db, user_id)` once before the loop, and import the three helpers as in Task 5. Keep `avg_weight` reporting the **logged** weight — it is what the user typed and changing its meaning silently would misreport their history.

- [ ] **Step 3: Verify nothing regressed**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest tests/ -q`
Expected: PASS. Loaded exercises are unchanged; bodyweight exercises now contribute volume when readings exist and contribute zero when they do not.

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/analytics_service.py
git commit -m "[SH] feat: count bodyweight work toward volume analytics"
```

---

## Task 7: Bodyweight log in Settings

**Files:**
- Create: `web/src/services/bodyweight.ts`
- Create: `web/src/components/settings/BodyweightLog.tsx`
- Modify: `web/src/pages/Settings.tsx`

- [ ] **Step 1: Write the service client**

Create `web/src/services/bodyweight.ts`, matching the axios instance and header handling used by `web/src/services/staples.ts`:

```ts
import { api } from './api'

export interface BodyweightReading {
  id: number
  weight: number
  recorded_at: string
  source: string
}

export async function listReadings(): Promise<BodyweightReading[]> {
  const { data } = await api.get<BodyweightReading[]>('/bodyweight')
  return data
}

export async function createReading(weight: number, recordedAt?: string): Promise<BodyweightReading> {
  const { data } = await api.post<BodyweightReading>('/bodyweight', {
    weight,
    recorded_at: recordedAt ?? null,
  })
  return data
}

export async function deleteReading(id: number): Promise<void> {
  await api.delete(`/bodyweight/${id}`)
}
```

Use whatever the project's existing client export is actually called — check `web/src/services/api.ts` and follow it.

- [ ] **Step 2: Write the component**

Create `web/src/components/settings/BodyweightLog.tsx`:

```tsx
/**
 * Bodyweight readings, newest first, with a single-field add.
 *
 * A log rather than one editable number: bodyweight drifts, and every past set
 * is scored against the reading in effect when it was performed. Health Connect
 * will write here too, so entries show their source.
 */
import { useEffect, useState } from 'react'
import {
  createReading,
  deleteReading,
  listReadings,
  type BodyweightReading,
} from '../../services/bodyweight'

export default function BodyweightLog() {
  const [readings, setReadings] = useState<BodyweightReading[]>([])
  const [weight, setWeight] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const refresh = async () => {
    try {
      setReadings(await listReadings())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load readings')
    }
  }

  useEffect(() => {
    refresh()
  }, [])

  const add = async () => {
    const value = Number(weight)
    if (!Number.isFinite(value) || value <= 0) {
      setError('Enter a weight greater than zero.')
      return
    }
    setError(null)
    setBusy(true)
    try {
      await createReading(value)
      setWeight('')
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save reading')
    } finally {
      setBusy(false)
    }
  }

  const remove = async (id: number) => {
    setBusy(true)
    try {
      await deleteReading(id)
      await refresh()
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="bg-white rounded-lg shadow p-4">
      <h2 className="text-lg font-semibold mb-1">Bodyweight</h2>
      <p className="text-sm text-gray-500 mb-3">
        Used to score bodyweight exercises. Each set is measured against the
        reading in effect on the day you performed it.
      </p>

      <div className="flex flex-wrap gap-2 items-center mb-3">
        <input
          value={weight}
          onChange={(e) => setWeight(e.target.value)}
          placeholder="weight"
          aria-label="bodyweight"
          inputMode="decimal"
          className="w-28 border rounded-md px-3 py-3 min-h-[44px]"
        />
        <button
          onClick={add}
          disabled={busy}
          className="bg-blue-600 text-white px-5 py-3 min-h-[44px] rounded-md font-medium disabled:opacity-50"
        >
          Add
        </button>
      </div>

      {error && <div className="text-red-600 text-sm mb-2" role="alert">{error}</div>}

      {readings.length === 0 && (
        <p className="text-sm text-gray-400">
          No readings yet. Bodyweight exercises won't be scored until you add one.
        </p>
      )}

      <ul className="divide-y">
        {readings.map((r) => (
          <li key={r.id} className="flex justify-between items-center py-2 gap-2">
            <span className="min-w-0">
              <span className="font-medium">{r.weight}</span>
              <span className="text-sm text-gray-500 ml-2">
                {new Date(r.recorded_at).toLocaleDateString()}
              </span>
              {r.source !== 'manual' && (
                <span className="text-xs text-gray-400 ml-2">{r.source}</span>
              )}
            </span>
            <button
              onClick={() => remove(r.id)}
              disabled={busy}
              className="text-red-500 px-3 py-2 shrink-0"
            >
              Delete
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}
```

- [ ] **Step 3: Mount it in Settings**

Import and render `<BodyweightLog />` in `web/src/pages/Settings.tsx`, following that page's existing section layout.

- [ ] **Step 4: Verify**

Run: `cd web && npx tsc --noEmit`

By hand, with the device identity set to `setup-verify-0001`: add a reading, confirm it lists with today's date, add a second and confirm newest-first ordering, delete one, then check `/analytics` shows non-zero volume for a bodyweight staple that previously showed zero.

- [ ] **Step 5: Commit**

```bash
git add web/src/services/bodyweight.ts web/src/components/settings/BodyweightLog.tsx web/src/pages/Settings.tsx
git commit -m "[SH] feat: bodyweight log in settings"
```

---

## Task 8: Document the design decision

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Add the decision**

Under "Design Decisions", after "Bodyweight Exercises":

```markdown
### Bodyweight Load and Leverage
Bodyweight exercises carry real load, and that load is scored rather than
ignored:

- Bodyweight is a **dated time series** (`bodyweight_readings`), not a profile
  field. Each set resolves against the reading in effect on the day it was
  performed, so a new weigh-in never retroactively rewrites past volume or
  e1RM. Readings carry a `source` (`manual`, `health_connect`) and upsert on
  (user, instant, source) so a sync is idempotent.
- A per-exercise `bodyweight_fraction` scales that reading to the load actually
  moved — a push-up is ~0.64 of bodyweight, a squat ~0.85, an arm circle ~0.05.
  Curated values live in `app/services/leverage.py` and are seeded by
  `scripts.seed_leverage`. Uncurated exercises fall back to
  `DEFAULT_BODYWEIGHT_FRACTION` (0.64), deliberately not 1.0.
- External load **adds** to the bodyweight component: a weighted vest is extra
  load on top of what you already carry.
- With no readings, bodyweight work is **excluded** from e1RM and volume rather
  than assigned a guessed bodyweight.
- Progression targets are unaffected. Bodyweight progression stays rep-based
  (last reps + 1, no ceiling); leverage changes how work is scored, not what is
  prescribed.
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "[SH] docs: bodyweight load and leverage design decision"
```

---

## Final Verification

- [ ] **Full backend suite**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest -q`
Expected: all green.

- [ ] **Typecheck**

Run: `cd web && npx tsc --noEmit`
Expected: only the seven pre-existing unused-variable errors.

- [ ] **Seeds applied**

```bash
cd backend && ./venv/Scripts/python.exe -m scripts.seed_leverage
docker exec slotfit-db psql -U postgres -d slotfit -c "SELECT count(*) FROM exercises WHERE bodyweight_fraction IS NOT NULL;"
```

Expected: 15.

- [ ] **End-to-end check**

1. Add a bodyweight reading in Settings.
2. Log a set of push-ups with no weight, finish the session.
3. `/analytics` reports non-zero volume for that exercise.
4. A pattern whose only staples are bodyweight produces a non-empty strength trend.
5. Delete every reading: bodyweight work drops out of both rather than reporting a guessed number.
6. Confirm the next-session target for a bodyweight movement is still rep-based and unchanged by leverage.

# Set Protocols (AMRAP / EMOM) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Record how each exercise's sets are measured — straight reps, time, AMRAP, or EMOM — so the gym UI prompts for only the fields that matter.

**Architecture:** A `SetProtocol` enum on `Exercise` drives behavior, inferred from the free-text `variant_type` at variant-creation time. It is denormalized onto `RoundEntry` when the entry is created, exactly as `pattern_id` already is, so reclassifying an exercise later cannot rewrite what past sets meant. The web `EntryCard` renders inputs conditionally on the protocol the API returns.

**Tech Stack:** Python 3.11, SQLAlchemy async, Alembic, PostgreSQL, pytest with an in-memory SQLite fixture (`test_db`), React 18 + TypeScript.

## Global Constraints

- Design spec: `docs/superpowers/specs/2026-08-02-set-protocols-design.md`. Read it before starting.
- Protocol values are exactly `reps`, `time`, `amrap`, `emom`. Default is `reps`.
- Field matrix — `reps`: weight optional, reps yes, time not shown. `time`: weight optional, time yes, reps not shown. `amrap`: weight optional, reps yes, time yes. `emom`: weight optional, reps yes, time not shown.
- Inference is a case-insensitive **token scan** over `variant_type`, supporting compound labels: `HIIT AMRAP`→`amrap`, `HIIT EMOM`→`emom`, `AMRAP`→`amrap`, `EMOM`→`emom`, bare `HIIT`→`reps`, anything else→`reps`.
- Bare `HIIT` must NOT imply AMRAP. That guess was deliberately removed; a variant that doesn't state its protocol hasn't got one.
- **The server stays permissive.** Do not add rejection for a protocol's missing field. A set that fails to save mid-workout is worse than a set missing a number.
- `emom` and `reps` log identical columns. Keep them distinct anyway — progression differs and spec 2 needs to tell them apart.
- Never rewrite existing `EntrySet` or `RoundEntry` rows. Existing entries stay on the `reps` default.
- Run backend commands from `backend/`. Tests: `./venv/Scripts/python.exe -m pytest`. Web: `cd web && npx tsc --noEmit`.
- Commit subjects are prefixed `[SH]`.

---

### Task 1: SetProtocol enum, Exercise column, and inference

**Files:**
- Modify: `backend/app/models/exercise.py`
- Create: `backend/tests/test_set_protocols.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `SetProtocol` (str enum with members `REPS`, `TIME`, `AMRAP`, `EMOM` whose values are `"reps"`, `"time"`, `"amrap"`, `"emom"`); `protocol_for_variant_type(variant_type: str | None) -> SetProtocol`; `Exercise.set_protocol` column.

- [ ] **Step 1: Write the failing test**

```python
"""Tests for set protocols (AMRAP / EMOM) - app/models/exercise.py."""

import pytest

from app.models.exercise import SetProtocol, protocol_for_variant_type


def test_protocol_values_are_the_four_agreed_strings():
    assert {p.value for p in SetProtocol} == {"reps", "time", "amrap", "emom"}


@pytest.mark.parametrize(
    "variant_type,expected",
    [
        ("AMRAP", SetProtocol.AMRAP),
        ("EMOM", SetProtocol.EMOM),
        ("HIIT AMRAP", SetProtocol.AMRAP),
        ("HIIT EMOM", SetProtocol.EMOM),
    ],
)
def test_labels_infer_their_protocol(variant_type, expected):
    assert protocol_for_variant_type(variant_type) is expected


def test_inference_is_case_insensitive():
    # variant_type is free text; a lowercase label must not change behaviour.
    assert protocol_for_variant_type("hiit amrap") is SetProtocol.AMRAP
    assert protocol_for_variant_type("HiIt eMoM") is SetProtocol.EMOM


def test_inference_tolerates_extra_whitespace():
    assert protocol_for_variant_type("  HIIT   AMRAP  ") is SetProtocol.AMRAP


def test_bare_hiit_does_not_imply_amrap():
    """Intent without a stated protocol is not a protocol.

    An earlier draft mapped HIIT to AMRAP, which buried a guess about one
    person's training in the code. Compound labels make the guess unnecessary.
    """
    assert protocol_for_variant_type("HIIT") is SetProtocol.REPS


@pytest.mark.parametrize("variant_type", ["Strength", "Volume", "Endurance", "", None])
def test_non_protocol_variant_types_fall_back_to_reps(variant_type):
    assert protocol_for_variant_type(variant_type) is SetProtocol.REPS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/Scripts/python.exe -m pytest tests/test_set_protocols.py -v --no-cov`
Expected: FAIL, `ImportError: cannot import name 'SetProtocol'`

- [ ] **Step 3: Write minimal implementation**

In `backend/app/models/exercise.py`, add after the existing `DifficultyLevel` enum:

```python
class SetProtocol(str, enum.Enum):
    """How an exercise's sets are measured.

    Drives which fields the gym UI prompts for. REPS and EMOM record the same
    columns today, but stay distinct because progression differs and interval
    routines need to tell them apart.
    """

    REPS = "reps"      # weight optional, reps
    TIME = "time"      # weight optional, seconds - rower, plank, carries
    AMRAP = "amrap"    # weight optional, reps, seconds - fixed window, count reps
    EMOM = "emom"      # weight optional, reps - fixed reps per interval


# A label carries two independent things: intent ("HIIT") and protocol
# ("AMRAP"/"EMOM"). Scanning tokens rather than matching whole strings lets
# compound labels like "HIIT AMRAP" work without enumerating combinations.
_PROTOCOL_TOKENS: dict[str, SetProtocol] = {
    "amrap": SetProtocol.AMRAP,
    "emom": SetProtocol.EMOM,
}


def protocol_for_variant_type(variant_type: str | None) -> SetProtocol:
    """Infer a set protocol from a variant's human label.

    "HIIT AMRAP" -> AMRAP, "EMOM" -> EMOM, "Strength" -> REPS.

    A bare "HIIT" yields REPS on purpose. It states an intent, not a
    measurement, and guessing AMRAP from it would be wrong for anyone whose
    intervals are fixed-rep.
    """
    if not variant_type:
        return SetProtocol.REPS
    for token in variant_type.lower().split():
        protocol = _PROTOCOL_TOKENS.get(token)
        if protocol is not None:
            return protocol
    return SetProtocol.REPS
```

Then add the column to the `Exercise` class, next to `variant_type`:

```python
    set_protocol = Column(
        SQLEnum(SetProtocol, values_callable=lambda x: [e.value for e in x]),
        default=SetProtocol.REPS,
        server_default=SetProtocol.REPS.value,
        nullable=False,
    )
```

`SQLEnum` is already imported in this module. `values_callable` matches how `SessionState` is declared in `training_session.py`, so Postgres stores the lowercase values rather than the member names.

- [ ] **Step 4: Run test to verify it passes**

Run: `./venv/Scripts/python.exe -m pytest tests/test_set_protocols.py -v --no-cov`
Expected: PASS, 13 tests

- [ ] **Step 5: Commit**

```bash
git add app/models/exercise.py tests/test_set_protocols.py
git commit -m "[SH] feat: add SetProtocol enum and variant_type inference"
```

---

### Task 2: Denormalize the protocol onto RoundEntry

**Files:**
- Modify: `backend/app/models/training_session.py`
- Modify: `backend/app/schemas/training_session.py:33-43`
- Modify: `backend/app/api/v1/endpoints/training_sessions.py:92-115` and `:300-305`
- Modify: `backend/tests/test_set_protocols.py`

**Interfaces:**
- Consumes: `SetProtocol` from Task 1.
- Produces: `RoundEntry.set_protocol` column; `RoundEntryResponse.set_protocol: str`.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_set_protocols.py`:

```python
from sqlalchemy import select

from app.models import Exercise, MovementPattern, RoundEntry, SupersetRound, TrainingSession, User
from app.models.exercise import SetProtocol as SP
from app.services.pattern_taxonomy import seed_movement_patterns, seed_exercise_pattern_map


async def _session_with_exercise(test_db, protocol):
    """Seed one user, one exercise with the given protocol, and an open round."""
    await seed_movement_patterns(test_db)
    user = User(device_id="protocol-device-01")
    exercise = Exercise(
        name="Kettlebell Swing (HIIT)",
        movement_pattern_1="Hip Hinge",
        mechanics="Compound",
        set_protocol=protocol,
    )
    test_db.add_all([user, exercise])
    await test_db.flush()
    await seed_exercise_pattern_map(test_db)
    session = TrainingSession(user_id=user.id)
    test_db.add(session)
    await test_db.flush()
    rnd = SupersetRound(session_id=session.id, order=1)
    test_db.add(rnd)
    await test_db.flush()
    return user, exercise, rnd


async def test_round_entry_defaults_to_reps(test_db):
    _user, _ex, rnd = await _session_with_exercise(test_db, SP.REPS)
    entry = RoundEntry(round_id=rnd.id, position=1, exercise_id=_ex.id, pattern_id=1)
    test_db.add(entry)
    await test_db.flush()
    assert entry.set_protocol == SP.REPS


async def test_round_entry_can_carry_a_protocol(test_db):
    _user, exercise, rnd = await _session_with_exercise(test_db, SP.AMRAP)
    entry = RoundEntry(
        round_id=rnd.id, position=1, exercise_id=exercise.id, pattern_id=1,
        set_protocol=exercise.set_protocol,
    )
    test_db.add(entry)
    await test_db.flush()
    assert entry.set_protocol == SP.AMRAP


async def test_reclassifying_the_exercise_does_not_rewrite_the_entry(test_db):
    """The denormalization guarantee, matching RoundEntry.pattern_id's contract."""
    _user, exercise, rnd = await _session_with_exercise(test_db, SP.AMRAP)
    entry = RoundEntry(
        round_id=rnd.id, position=1, exercise_id=exercise.id, pattern_id=1,
        set_protocol=exercise.set_protocol,
    )
    test_db.add(entry)
    await test_db.flush()

    exercise.set_protocol = SP.EMOM
    await test_db.flush()

    refreshed = (
        await test_db.execute(select(RoundEntry).where(RoundEntry.id == entry.id))
    ).scalar_one()
    assert refreshed.set_protocol == SP.AMRAP
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/Scripts/python.exe -m pytest tests/test_set_protocols.py -v --no-cov`
Expected: FAIL, `TypeError: 'set_protocol' is an invalid keyword argument for RoundEntry`

- [ ] **Step 3: Add the column**

In `backend/app/models/training_session.py`, import the enum at the top:

```python
from app.models.exercise import SetProtocol
```

Then add to the `RoundEntry` class, immediately after the `pattern_id` column and its comment:

```python
    # Denormalized alongside pattern_id and for the same reason: reclassifying an
    # exercise later must not change what past sets meant.
    set_protocol = Column(
        SQLEnum(SetProtocol, values_callable=lambda x: [e.value for e in x]),
        default=SetProtocol.REPS,
        server_default=SetProtocol.REPS.value,
        nullable=False,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./venv/Scripts/python.exe -m pytest tests/test_set_protocols.py -v --no-cov`
Expected: PASS, 16 tests

- [ ] **Step 5: Capture the protocol when an entry is created**

In `backend/app/api/v1/endpoints/training_sessions.py`, the `create_entry` handler resolves the pattern then builds the entry at roughly line 300. The exercise must now be loaded too. Replace the `mapping` lookup and `RoundEntry(...)` construction with:

```python
    mapping = (
        await db.execute(
            select(ExercisePatternMap).where(
                ExercisePatternMap.exercise_id == data.exercise_id
            )
        )
    ).scalar_one_or_none()
    if mapping is None:
        raise HTTPException(status_code=404, detail="Exercise has no pattern mapping")

    exercise = (
        await db.execute(select(Exercise).where(Exercise.id == data.exercise_id))
    ).scalar_one_or_none()
    if exercise is None:
        raise HTTPException(status_code=404, detail="Exercise not found")

    entry = RoundEntry(
        round_id=rnd.id,
        position=data.position,
        exercise_id=data.exercise_id,
        pattern_id=mapping.pattern_id,
        set_protocol=exercise.set_protocol,
    )
```

Add `Exercise` to the `from app.models import ...` line at the top of the file if it is not already imported.

- [ ] **Step 6: Expose it on the API response**

In `backend/app/schemas/training_session.py`, add to `RoundEntryResponse` after `pattern_slug`:

```python
    set_protocol: str
```

In `backend/app/api/v1/endpoints/training_sessions.py`, add to the `RoundEntryResponse(...)` construction inside `_entry_response`, after `pattern_slug=entry.pattern.slug,`:

```python
        set_protocol=entry.set_protocol.value,
```

- [ ] **Step 7: Pin the permissive-server decision with a test**

The server deliberately does not reject a set whose fields don't match its
protocol. Without a test saying so, a future reader will read it as an
oversight and "fix" it. Append to `backend/tests/test_set_protocols.py`:

```python
from app.models import EntrySet


async def test_a_set_outside_its_protocol_is_still_accepted(test_db):
    """Deliberate: mid-workout, a rejected set loses the rep entirely.

    An EMOM entry has no time field in the UI, but a time value arriving anyway
    must be stored rather than refused. Tighten only if loose proves wrong.
    """
    _user, exercise, rnd = await _session_with_exercise(test_db, SP.EMOM)
    entry = RoundEntry(
        round_id=rnd.id, position=1, exercise_id=exercise.id, pattern_id=1,
        set_protocol=exercise.set_protocol,
    )
    test_db.add(entry)
    await test_db.flush()

    test_db.add(EntrySet(entry_id=entry.id, set_number=1, weight=20, reps=8, time_seconds=60))
    await test_db.flush()

    stored = (
        await test_db.execute(select(EntrySet).where(EntrySet.entry_id == entry.id))
    ).scalar_one()
    assert stored.time_seconds == 60
```

- [ ] **Step 8: Run the training session tests**

Run: `./venv/Scripts/python.exe -m pytest tests/ -k "session or entry or protocol" -q --no-cov`
Expected: PASS, no regressions

- [ ] **Step 9: Commit**

```bash
git add app/models/training_session.py app/schemas/training_session.py app/api/v1/endpoints/training_sessions.py tests/test_set_protocols.py
git commit -m "[SH] feat: denormalize set protocol onto round entries"
```

---

### Task 3: Migration and backfill

**Files:**
- Create: `backend/alembic/versions/<generated>_add_set_protocol.py`

**Interfaces:**
- Consumes: the two columns from Tasks 1 and 2.
- Produces: a migration whose `down_revision` is `59af238ed19e` (the current head).

- [ ] **Step 1: Create the migration file by hand**

Autogenerate is not used here because the enum type needs explicit creation ordering on PostgreSQL. Create `backend/alembic/versions/b7c14e2a9f30_add_set_protocol.py`:

```python
"""add set_protocol to exercises and round_entries

Revision ID: b7c14e2a9f30
Revises: 59af238ed19e
Create Date: 2026-08-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7c14e2a9f30'
down_revision = '59af238ed19e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    set_protocol = sa.Enum('reps', 'time', 'amrap', 'emom', name='setprotocol')
    set_protocol.create(op.get_bind(), checkfirst=True)

    # server_default keeps every existing row valid without a data pass.
    op.add_column(
        'exercises',
        sa.Column('set_protocol', set_protocol, nullable=False, server_default='reps'),
    )
    op.add_column(
        'round_entries',
        sa.Column('set_protocol', set_protocol, nullable=False, server_default='reps'),
    )

    # Two narrow, named backfills. No inference across the catalogue: guessing
    # from default_time_seconds would silently reclassify unreviewed exercises.
    #
    # The six HIIT variants are relabelled as well as reclassified. Bare "HIIT"
    # no longer implies a protocol, so leaving the label alone would silently
    # drop them to 'reps'. Renaming is safe: staples and round entries reference
    # exercises by id, never by name.
    op.execute(
        """
        UPDATE exercises
           SET name = replace(name, ' (HIIT)', ' (HIIT AMRAP)'),
               variant_type = 'HIIT AMRAP',
               set_protocol = 'amrap'
         WHERE variant_type = 'HIIT'
        """
    )
    op.execute("UPDATE exercises SET set_protocol = 'time' WHERE name = 'Rowing Machine'")


def downgrade() -> None:
    op.execute(
        """
        UPDATE exercises
           SET name = replace(name, ' (HIIT AMRAP)', ' (HIIT)'),
               variant_type = 'HIIT'
         WHERE variant_type = 'HIIT AMRAP'
        """
    )
    op.drop_column('round_entries', 'set_protocol')
    op.drop_column('exercises', 'set_protocol')
    sa.Enum(name='setprotocol').drop(op.get_bind(), checkfirst=True)
```

- [ ] **Step 2: Run the migration**

Run: `./venv/Scripts/python.exe -m alembic upgrade head`
Expected: no error; `alembic current` reports `b7c14e2a9f30 (head)`

- [ ] **Step 3: Verify the backfill hit exactly the intended rows**

Run:

```bash
./venv/Scripts/python.exe -c "
import asyncio, sys; sys.path.insert(0,'.')
from sqlalchemy import select, func
from app.core.database import AsyncSessionLocal
from app.models import Exercise
async def m():
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(Exercise.set_protocol, func.count(Exercise.id)).group_by(Exercise.set_protocol))).all()
        for p, n in rows: print(f'{p:8} {n}')
        named = (await db.execute(select(Exercise.name, Exercise.set_protocol).where(Exercise.set_protocol != 'reps').order_by(Exercise.name))).all()
        print()
        for n, p in named: print(f'  {n:52} {p}')
asyncio.run(m())"
```

Expected: 3,257 on `reps`, 6 on `amrap`, 1 on `time` (`Rowing Machine`). The six
amrap rows must now be named `… (HIIT AMRAP)`, not `… (HIIT)`.

- [ ] **Step 4: Update the mapping file to match**

`hevy/exercise_map.yaml` still says `variant_type: HIIT` for the six. Left alone,
a re-run of `hevy_staples apply` would create a second set of `… (HIIT)`
variants beside the renamed ones. Run from the repo root:

```bash
cd .. && ./backend/venv/Scripts/python.exe -c "
import sys; sys.path.insert(0,'backend')
from pathlib import Path
import yaml
from app.services.hevy_import import dump_map
p = Path('hevy/exercise_map.yaml')
doc = yaml.safe_load(p.read_text(encoding='utf-8'))
n = 0
for row in doc['exercises']:
    c = row.get('create') or {}
    if c.get('variant_type') == 'HIIT':
        c['variant_type'] = 'HIIT AMRAP'; n += 1
p.write_text(dump_map(doc), encoding='utf-8')
print(f'relabelled {n} entries')" && cd backend
```

Expected: `relabelled 6 entries`

- [ ] **Step 5: Confirm apply is still a no-op**

Run: `./venv/Scripts/python.exe -m scripts.hevy_staples apply`
Expected: `exercises created : 0`, `already staple : 57` — proving the rename and
the relabel agree, so no duplicate variants would be created.

- [ ] **Step 6: Verify the downgrade works**

Run: `./venv/Scripts/python.exe -m alembic downgrade -1 && ./venv/Scripts/python.exe -m alembic upgrade head`
Expected: both succeed; the Step 3 counts and names are the same afterward

- [ ] **Step 7: Commit**

```bash
git add alembic/versions/b7c14e2a9f30_add_set_protocol.py ../hevy/exercise_map.yaml
git commit -m "[SH] feat: migrate set_protocol columns, relabel HIIT variants as HIIT AMRAP"
```

---

### Task 4: Variant creation infers the protocol

**Files:**
- Modify: `backend/app/api/v1/endpoints/exercises.py:475` (the variant construction)
- Modify: `backend/app/schemas/exercise.py:57,82-83`
- Modify: `backend/app/services/hevy_import.py` (`_create_variant`)
- Modify: `backend/tests/test_set_protocols.py`

**Interfaces:**
- Consumes: `protocol_for_variant_type` from Task 1.
- Produces: both variant-creation paths set `set_protocol`; an explicit `set_protocol` on the request overrides inference.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_set_protocols.py`:

```python
from app.services.hevy_import import apply_map


async def test_hevy_variant_creation_infers_amrap_from_a_compound_label(test_db):
    await seed_movement_patterns(test_db)
    user = User(device_id="protocol-device-02")
    base = Exercise(
        name="Kettlebell Swing", movement_pattern_1="Hip Hinge", mechanics="Compound"
    )
    test_db.add_all([user, base])
    await test_db.flush()
    await seed_exercise_pattern_map(test_db)

    doc = {"exercises": [{
        "hevy": "HIIT KB Swings", "slotfit": None, "candidates": [],
        "create": {"variant_of": "Kettlebell Swing", "variant_type": "HIIT AMRAP",
                   "default_time_seconds": 40},
    }]}
    await apply_map(test_db, doc, user)

    variant = (
        await test_db.execute(
            select(Exercise).where(Exercise.name == "Kettlebell Swing (HIIT AMRAP)")
        )
    ).scalar_one()
    assert variant.set_protocol == SP.AMRAP


async def test_hevy_variant_with_bare_hiit_stays_on_reps(test_db):
    """Guards the removed guess: intent alone must not pick a protocol."""
    await seed_movement_patterns(test_db)
    user = User(device_id="protocol-device-05")
    base = Exercise(
        name="Kettlebell Swing", movement_pattern_1="Hip Hinge", mechanics="Compound"
    )
    test_db.add_all([user, base])
    await test_db.flush()
    await seed_exercise_pattern_map(test_db)

    doc = {"exercises": [{
        "hevy": "HIIT KB Swings", "slotfit": None, "candidates": [],
        "create": {"variant_of": "Kettlebell Swing", "variant_type": "HIIT"},
    }]}
    await apply_map(test_db, doc, user)

    variant = (
        await test_db.execute(
            select(Exercise).where(Exercise.name == "Kettlebell Swing (HIIT)")
        )
    ).scalar_one()
    assert variant.set_protocol == SP.REPS


async def test_hevy_variant_creation_infers_emom(test_db):
    await seed_movement_patterns(test_db)
    user = User(device_id="protocol-device-03")
    base = Exercise(
        name="Kettlebell Swing", movement_pattern_1="Hip Hinge", mechanics="Compound"
    )
    test_db.add_all([user, base])
    await test_db.flush()
    await seed_exercise_pattern_map(test_db)

    doc = {"exercises": [{
        "hevy": "EMOM KB Swings", "slotfit": None, "candidates": [],
        "create": {"variant_of": "Kettlebell Swing", "variant_type": "EMOM"},
    }]}
    await apply_map(test_db, doc, user)

    variant = (
        await test_db.execute(
            select(Exercise).where(Exercise.name == "Kettlebell Swing (EMOM)")
        )
    ).scalar_one()
    assert variant.set_protocol == SP.EMOM


async def test_hevy_plain_create_stays_on_reps(test_db):
    await seed_movement_patterns(test_db)
    user = User(device_id="protocol-device-04")
    test_db.add(user)
    await test_db.flush()

    doc = {"exercises": [{
        "hevy": "Leg Press (Machine)", "slotfit": None, "candidates": [],
        "create": {"name": "Leg Press (Machine)", "pattern": "knee_dominant"},
    }]}
    await apply_map(test_db, doc, user)

    created = (
        await test_db.execute(
            select(Exercise).where(Exercise.name == "Leg Press (Machine)")
        )
    ).scalar_one()
    assert created.set_protocol == SP.REPS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/Scripts/python.exe -m pytest tests/test_set_protocols.py -v --no-cov`
Expected: FAIL on the first two — the variant is created with the `reps` default

- [ ] **Step 3: Set the protocol in the Hevy path**

In `backend/app/services/hevy_import.py`, import the helper alongside the existing model imports:

```python
from app.models.exercise import exercise_muscle_groups, protocol_for_variant_type
```

Then in `_create_variant`, add to the `Exercise(...)` construction, after `variant_type=create["variant_type"],`:

```python
        set_protocol=protocol_for_variant_type(create["variant_type"]),
```

- [ ] **Step 4: Set the protocol in the API path**

In `backend/app/api/v1/endpoints/exercises.py`, add to the variant `Exercise(...)` construction after `variant_type=variant_data.variant_type,`:

```python
        set_protocol=(
            variant_data.set_protocol
            or protocol_for_variant_type(variant_data.variant_type)
        ),
```

Import it at the top of the file:

```python
from app.models.exercise import protocol_for_variant_type
```

In `backend/app/schemas/exercise.py`, add to the variant-create request schema (the one declaring `variant_type: str` at line 83):

```python
    set_protocol: Optional[str] = None  # overrides inference from variant_type
```

and to the exercise response schema (near `variant_type` at line 57):

```python
    set_protocol: str = "reps"
```

- [ ] **Step 5: Run test to verify it passes**

Run: `./venv/Scripts/python.exe -m pytest tests/test_set_protocols.py -v --no-cov`
Expected: PASS, 21 tests

- [ ] **Step 6: Run the full backend suite**

Run: `./venv/Scripts/python.exe -m pytest -q`
Expected: PASS, 194 pre-existing tests plus the new ones

- [ ] **Step 7: Commit**

```bash
git add app/api/v1/endpoints/exercises.py app/schemas/exercise.py app/services/hevy_import.py tests/test_set_protocols.py
git commit -m "[SH] feat: infer set protocol when creating exercise variants"
```

---

### Task 5: Show only the fields the protocol needs

**Files:**
- Modify: `web/src/services/sessions.ts:20` area (the `RoundEntry` type)
- Modify: `web/src/components/session/EntryCard.tsx`

**Interfaces:**
- Consumes: `set_protocol` on the entry payload from Task 2.
- Produces: an `EntryCard` that renders inputs conditionally.

- [ ] **Step 1: Add the field to the client type**

In `web/src/services/sessions.ts`, add to the `RoundEntry` interface, next to `pattern_slug`:

```typescript
  set_protocol: 'reps' | 'time' | 'amrap' | 'emom'
```

- [ ] **Step 2: Render inputs conditionally**

In `web/src/components/session/EntryCard.tsx`, update the header comment and add the field matrix above the component:

```typescript
/**
 * Which inputs each protocol asks for. Weight is always offered - bodyweight
 * work simply leaves it blank, which the API already reads as bodyweight.
 *
 * EMOM and REPS look identical here on purpose: the minute is structural, not
 * a measured result, so there is nothing to type.
 */
const PROTOCOL_FIELDS: Record<string, { reps: boolean; time: boolean }> = {
  reps: { reps: true, time: false },
  time: { reps: false, time: true },
  amrap: { reps: true, time: true },
  emom: { reps: true, time: false },
}
```

Inside the component, replace the `timeSec` initialiser and derive the field set:

```typescript
  const fields = PROTOCOL_FIELDS[entry.set_protocol] ?? PROTOCOL_FIELDS.reps
  const [timeSec, setTimeSec] = useState<string>(
    entry.default_time_seconds != null ? String(entry.default_time_seconds) : ''
  )
```

Then wrap the reps and time inputs so each renders only when its flag is set. The reps input becomes:

```typescript
        {fields.reps && (
          <input
            value={reps}
            onChange={(e) => setReps(e.target.value)}
            placeholder="reps"
            aria-label="reps"
            className="w-20 border rounded-md px-3 py-3 min-h-[44px]"
            inputMode="numeric"
          />
        )}
```

and the time input becomes:

```typescript
        {fields.time && (
          <input
            value={timeSec}
            onChange={(e) => setTimeSec(e.target.value)}
            placeholder="time (sec)"
            aria-label="time (sec)"
            className="w-28 border rounded-md px-3 py-3 min-h-[44px]"
            inputMode="numeric"
          />
        )}
```

In `logSet`, send null for a field the protocol does not use, so a stale value from a protocol change cannot leak into a set:

```typescript
  const logSet = async () => {
    await onLogSet(entry.id, {
      set_number: entry.sets.length + 1,
      weight: parse(weight),
      reps: fields.reps ? parse(reps) : null,
      time_seconds: fields.time ? parse(timeSec) : null,
    })
  }
```

- [ ] **Step 3: Add default_time_seconds to the entry payload**

The AMRAP card pre-fills its seconds box from the exercise's default. Add to `RoundEntryResponse` in `backend/app/schemas/training_session.py`:

```python
    default_time_seconds: Optional[int] = None
```

to `_entry_response` in `backend/app/api/v1/endpoints/training_sessions.py`, after `set_protocol=entry.set_protocol.value,`:

```python
        default_time_seconds=entry.exercise.default_time_seconds,
```

and to the `RoundEntry` interface in `web/src/services/sessions.ts`:

```typescript
  default_time_seconds: number | null
```

- [ ] **Step 4: Typecheck**

Run: `cd ../web && npx tsc --noEmit`
Expected: no errors

- [ ] **Step 5: Run the backend suite once more**

Run: `cd ../backend && ./venv/Scripts/python.exe -m pytest -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add ../web/src/services/sessions.ts ../web/src/components/session/EntryCard.tsx app/schemas/training_session.py app/api/v1/endpoints/training_sessions.py
git commit -m "[SH] feat: prompt only for the fields a set protocol uses"
```

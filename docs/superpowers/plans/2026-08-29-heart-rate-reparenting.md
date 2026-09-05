# Heart Rate Re-Parenting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give heart rate somewhere valid to be written. The tables exist but are wired to the retired routine model, so nothing — not the planned BLE stream, not a Garmin backfill, not Health Connect — can write a single row.

**Architecture:** Heart rate becomes a **per-user physiological time series** (`heart_rate_readings`), mirroring `bodyweight_readings`, with session association held in a separate link table (`hr_session_links`) and summaries in a rebuildable cache (`heart_rate_analytics`). Raw `bpm` is the truth; zones are **derived at compute time and never stored**, so correcting a max-HR estimate recomputes history rather than applying only forward. No endpoints and no writers are added: this plan makes the schema correct and stops there.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy async, Alembic, pytest.

## Global Constraints

- Backend commands must use `backend/venv/Scripts/python.exe`.
- Run backend tests as `cd backend && ./venv/Scripts/python.exe -m pytest`.
- Commit subjects are prefixed `[SH]`.
- `users.max_hr` **already exists** — migration `a3d81b6e4f27`, applied 2026-08-29. Do not re-add it.
- All three heart-rate tables are **empty**. Verified: `HeartRateReading` / `HeartRateAnalytics` / `HeartRateZone` appear nowhere outside `models/workout.py` and the two import lists that register them. No service, no endpoint, no query, nothing in `web/src`. So the migration drops and recreates rather than altering, and no data migration is required.

## Decisions This Plan Implements

Four decisions taken 2026-08-29. The reasoning matters more than the shape, because three of the four look like oversights if you only read the schema.

### 1. A reading belongs to a session, not to an exercise

The retired model attached heart rate to `workout_exercises`, which worked because `WorkoutExercise` carried `started_at` / `stopped_at` — you could slice a 1 Hz stream into per-exercise windows.

The pattern model has no such clock. The only timestamps below the user are `TrainingSession.started_at` and `completed_at`; `SupersetRound` has an `order` and nothing else, `RoundEntry` has no timing, and `EntrySet` has no timestamp at all. Entry-level attribution is not merely unwise, it is **not expressible**.

It would be wrong even with timestamps. **A superset entry is not a time interval.** In a round you rotate A1, B1, C1, A2, B2, C2 — entry A occupies scattered windows interleaved with B and C. There is no single span that is "the pull-up entry." The thing that *is* contiguous is the set, so if sub-session attribution is ever wanted, the grain is `entry_sets`, reached by a time-window join once sets carry timestamps.

### 2. Raw readings are the truth; the summary is a rebuildable cache

The earlier specs said to summarize on-device and drop the raw series. That forecloses features already in the plan — `slotfit_plan.md` asks for rest suggestions "based on heart rate recovery patterns," which needs raw history, as do session charts, HR drift over a long ruck, and any recomputation of zones.

Cost is not the objection: 1 Hz over 75 minutes is ~4,500 rows, roughly 75 MB/year at four sessions a week.

The summary table survives, but as an explicitly derived cache **with a writer**, rebuildable from raw. Note the trap it sits next to: a pre-aggregated table with no writer is exactly what `weekly_volume` is, and per `CLAUDE.md` that made every reported figure zero for months. The rule that follows is not "never pre-aggregate" but "an aggregate must have a writer and must be rebuildable from the truth." It is justified here in a way it was not for volume: `volume_service` computes live over sets, a few dozen per session, while readings are ~100x denser, so a yearly zone chart would scan millions of rows.

### 3. Five zones by %HRmax, plus a below-Z1 bucket

The existing `FAT_BURN / CARDIO / PEAK / MAXIMUM` enum is Fitbit's vocabulary. Garmin and Polar both use five zones, so a 5 to 4 mapping loses a zone on every import and the numbers will not reconcile with what Polar Flow displays.

It also has **no below-zone bucket**. Z1 starts around 50% of max, and a strength session with long rests spends a lot of time under that, so "time in zones" would not sum to session duration.

`heart_rate_readings.zone` is dropped entirely. Storing a zone freezes the threshold that decision 2 committed to being able to change — `bpm` is the fact, zone is an interpretation.

### 4. Readings carry no session FK; a link table owns the association

232 Hevy workouts were imported by `hevy_backfill.py` into `workout_sessions` — the **legacy** tables — so a `training_session_id NOT NULL` FK cannot reference the history heart rate would most usefully attach to. `history_service.py` already warns that the two id sequences are independent and can collide.

The link table is not a workaround for that. **A Garmin or Polar recording exists independently of any SlotFit session** — that is the entire pairing problem. Heart rate is not a child of a session; it is a stream that gets *associated* with one, sometimes wrongly. Modelling it as a child was always slightly false; the legacy tables only hid it because there was one session model.

Consequences: the legacy/new split lands in one table instead of repeating across ~1M reading rows; all three ingestion paths unify (BLE knows its session immediately, Garmin/Polar resolve by time window, Health Connect the same); and a mispair has a place to be **corrected once** rather than by rewriting every reading.

## Scope Boundary

In scope: the models, the migration, and a zone-derivation helper.

Out of scope, deliberately:

- **Endpoints and writers.** They arrive with the first consumer — the Phase E BLE spike or the Garmin backfill, whichever comes first. Adding untested surface with no caller is how these tables reached their current state.
- **The cache writer and rebuild script.** Task 2 provides the pure derivation function; the job that persists into `heart_rate_analytics` belongs with the first writer, which is also the first thing able to test it against real rows.
- **BLE, Garmin/Polar import, Health Connect.** All separate work. See `2026-08-22-android-client-decision.md` Phase E/F.
- **Set-level timestamps.** Decision 1 notes `entry_sets` would need them for sub-session attribution. Not needed here, and they carry their own value (rest-interval tracking) that should justify them on its own.

## File Structure

```
backend/
  alembic/versions/
    <rev>_reparent_heart_rate.py        NEW
  app/
    models/
      heart_rate.py                     NEW  (moved out of workout.py)
      workout.py                        EDIT (remove HR models + relationships)
      __init__.py                       EDIT (re-point imports)
    services/
      zones.py                          NEW
  tests/
    test_zones.py                       NEW
docs/superpowers/plans/
  2026-08-29-heart-rate-reparenting.md  THIS FILE
CLAUDE.md                               EDIT (Task 3)
```

## Task 1: New models module and migration

- [ ] Create `app/models/heart_rate.py` with `HeartRateReading`, `HrSessionLink`, `HeartRateAnalytics`.
- [ ] Delete `HeartRateReading`, `HeartRateAnalytics` and `HeartRateZone` from `app/models/workout.py`, along with the `heart_rate_readings` / `heart_rate_analytics` relationships on `WorkoutSession` and `WorkoutExercise`.
- [ ] Re-point the imports in `app/models/__init__.py` and `alembic/env.py`.
- [ ] Write the migration.

They move out of `workout.py` because that module is retired read-only history, while these tables are user-scoped and forward-looking.

Target schema:

```python
class HeartRateReading(Base):
    """Truth. A per-user physiological time series, mirroring bodyweight_readings.

    No session FK: a Garmin recording exists independently of any SlotFit
    session, and association is a separate, correctable judgement (HrSessionLink).
    No `zone` column: zone is derived from bpm at compute time, so correcting a
    max-HR estimate recomputes history instead of applying only forward.
    """
    __tablename__ = "heart_rate_readings"
    __table_args__ = (
        UniqueConstraint("user_id", "recorded_at", "source",
                         name="uq_hr_user_instant_source"),
    )
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    recorded_at = Column(DateTime, nullable=False, index=True)
    bpm = Column(Integer, nullable=False)
    # ble_live | garmin | polar | health_connect | manual
    source = Column(String, nullable=False)


class HrSessionLink(Base):
    """Which stretch of the stream covers which session.

    Two nullable FKs because 232 imported Hevy workouts live in the legacy
    `workout_sessions`, not `training_sessions`. Confining the split here keeps
    it out of the reading rows, where it would repeat ~1M times.
    """
    __tablename__ = "hr_session_links"
    __table_args__ = (
        CheckConstraint(
            "(training_session_id IS NULL) <> (workout_session_id IS NULL)",
            name="ck_hr_link_exactly_one_session",
        ),
    )
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    training_session_id = Column(Integer, ForeignKey("training_sessions.id"), nullable=True)
    workout_session_id = Column(Integer, ForeignKey("workout_sessions.id"), nullable=True)
    window_start = Column(DateTime, nullable=False)
    window_end = Column(DateTime, nullable=False)
    source = Column(String, nullable=False)
    # A user correction. Time-window pairing is a guess; this says a human
    # settled it, so re-running an import must not overwrite the link.
    confirmed = Column(Boolean, nullable=False, default=False, server_default="false")


class HeartRateAnalytics(Base):
    """Derived cache. Rebuildable from readings whenever max_hr changes.

    Seconds rather than percentages: percentages are derivable, and the buckets
    sum to the window so a missing below_z1 cannot hide time.
    """
    __tablename__ = "heart_rate_analytics"
    id = Column(Integer, primary_key=True, index=True)
    hr_session_link_id = Column(Integer, ForeignKey("hr_session_links.id"),
                                nullable=False, index=True)
    avg_hr = Column(Float, nullable=True)
    peak_hr = Column(Integer, nullable=True)
    min_hr = Column(Integer, nullable=True)
    time_below_z1 = Column(Integer, nullable=True)
    time_in_z1 = Column(Integer, nullable=True)
    time_in_z2 = Column(Integer, nullable=True)
    time_in_z3 = Column(Integer, nullable=True)
    time_in_z4 = Column(Integer, nullable=True)
    time_in_z5 = Column(Integer, nullable=True)
    # The threshold basis this row was computed against, so a stale cache is
    # detectable and a rebuild is auditable.
    max_hr_used = Column(Integer, nullable=True)
    computed_at = Column(DateTime, nullable=True)
```

Dropped from the old `heart_rate_analytics` and not replaced: `workout_exercise_id` and `slot_id` (decision 1), `level` (the discriminator is now the link), `time_in_fat_burn` / `_cardio` / `_peak` / `_maximum` (decision 3), the four `*_percentage` columns (derivable from seconds), and `trend` — a bare `String` that was never defined anywhere.

**Migration gotcha:** `heartratezone` was created as a real PostgreSQL enum type by `5084736020fd`. Dropping the table does not drop the type, and a leftover will collide on a later upgrade. Drop it explicitly:

```python
def upgrade() -> None:
    op.drop_table('heart_rate_readings')
    op.drop_table('heart_rate_analytics')
    op.execute('DROP TYPE IF EXISTS heartratezone')
    # ... create hr_session_links, then heart_rate_readings and
    #     heart_rate_analytics in the shapes above
```

- [ ] `./venv/Scripts/python.exe -m alembic upgrade head`
- [ ] Confirm `downgrade` runs cleanly, then upgrade again.

## Task 2: Zone derivation

- [ ] Create `app/services/zones.py`.
- [ ] Create `tests/test_zones.py`.

Curated constants in code applied at compute time, following the `leverage.py` / `pattern_taxonomy.py` idiom. Percent-of-max boundaries, matching Garmin's and Polar's defaults:

| Zone | % of max |
|---|---|
| below Z1 | < 50 |
| Z1 | 50–60 |
| Z2 | 60–70 |
| Z3 | 70–80 |
| Z4 | 80–90 |
| Z5 | 90+ |

Required behaviour:

- `zone_for(bpm, max_hr)` returns `None` when `max_hr` is `None`. **No guessed default.** A fabricated maximum silently defines every boundary while looking authoritative. Same rule as bodyweight work with no weigh-in: report what is known, guess nothing.
- `summarize(readings, max_hr)` returns avg/peak/min **even when `max_hr` is `None`** — those need no threshold. Only the zone buckets go missing.
- Bucket seconds must sum to the covered window. The below-Z1 bucket exists for exactly this reason.

## Task 3: Document the design decision

- [ ] Add a `### Heart Rate` section to `CLAUDE.md`, after `### Conditioning and Loaded Locomotion`.

Three of the four decisions look like mistakes to a reader who only sees the schema — a per-user table with no session FK, a summary table that duplicates derivable numbers, and a `max_hr` column sitting next to a `bodyweight_readings` *table* that appears inconsistent with it. `CLAUDE.md` already carries several "an earlier version of this note claimed X, and the code implemented exactly that" corrections. This section exists to prevent the next one.

## Final Verification

- [ ] `cd backend && ./venv/Scripts/python.exe -m pytest` — full suite green.
- [ ] `alembic upgrade head`, then `alembic downgrade -1`, then `upgrade head` again — clean each way.
- [ ] `grep -rn "HeartRateZone\|workout_exercise_id" backend/app/models/heart_rate.py` returns nothing.
- [ ] `psql` check: `\d heart_rate_readings` shows no `zone` column and no session FK; `\dT heartratezone` reports no such type.
- [ ] Confirm the tables are still writer-free and endpoint-free — that is the intended end state of this plan, not an omission.

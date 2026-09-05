# Conditioning and Loaded Locomotion — Design

Date: 2026-08-23
Status: Approved (design), implementing

## Motivation

SlotFit's reason to exist is tracking strength **and** conditioning in one app.
The only tool that does both today is Garmin, which needs one of their watches
and handles strength poorly. Conditioning is therefore not a nice-to-have
category — it is half the product thesis, and it is currently unrepresentable.

The gap surfaced through a symptom. Importing three years of Hevy history drops
every rowing set on the floor: `Rowing Machine` logs 500m in 107 seconds, and
the legacy schema has no column for either number, so the importer counts it as
"no reps" and skips it.

The real size of the loss, measured across the export:

```text
429  sets are conditioning-shaped (no reps, but a duration or a distance)
257  of those have a mapped title - silently dropped, not skipped for lack of a mapping
 87  Rowing Machine        every one 500m; times 107s / 114s / 125s
 40  HIIT Mountain Climber
 32  HIIT KB Swings
 29  HIIT DB Step Ups
 22  Plank
```

## What Already Exists

This is deliberately a small change to a model that mostly anticipated it:

- `EntrySet.time_seconds` exists. `SetProtocol.TIME` exists.
- Movement patterns `Conditioning` (10) and `Carry / Locomotion` (8) exist.
- `effective_load()` already computes `bodyweight * fraction + external`, and
  bodyweight is already a dated time series.
- `heart_rate_readings` and `heart_rate_analytics` are fully modelled (0 rows) —
  groundwork for the Garmin-parity story, out of scope here.
  **Correction, 2026-08-29:** "fully modelled" was wrong. They were modelled
  against the *retired* routine tables — `heart_rate_readings` hung off
  `workout_exercises` with a NOT NULL FK — so nothing could write a row at all,
  and the 0 rows were a symptom rather than simply an unstarted feature. Fixed
  by `docs/superpowers/plans/2026-08-29-heart-rate-reparenting.md`.

Three things are missing: a distance column, a protocol that measures distance
against time, and a scoring path that does not corrupt strength tonnage.

## Conditioning Is a Measurement Mode, Not a Pattern

The dropped sets settle this. Mountain Climber is core. KB Swings are hip hinge.
DB Step Ups are knee dominant. They are ordinary strength patterns that happen
to be *measured in time*.

So the fix belongs entirely in `SetProtocol` (how a set is measured) and not in
`MovementPattern` (what it trains). Pattern coverage needs no change at all,
because `RoundEntry.pattern_id` is denormalised per entry: a KB swing logged for
40 seconds still credits hip hinge.

The `Conditioning` pattern row stays, but it means "the movement itself is
locomotion or ergometer work" (rower, ruck, air bike) — not "this set was
measured in time".

### Corollary: the march/carry family is mis-measured

The catalogue holds **80** marches and carries — 45 `% March`, 35 `% Carry`,
with no name matching that pattern outside the `carry` and `conditioning`
patterns (`Double Kettlebell Front Rack March`, `Barbell Zercher Carry`, …) —
and every one is protocoled `reps`. Nobody
performs ten reps of a farmer's carry; they carry it for distance or for time.
Only 1 exercise in 3,264 is currently `TIME`.

Rucking is not a new special case. It is the missing member of a family that is
already 80 strong and already recorded wrong.

## Design

### 1. A `DISTANCE` protocol

Add `SetProtocol.DISTANCE`. It permits distance, time, **and** weight together,
and requires at least one of distance or time.

| protocol | weight | reps | time | distance |
| --- | --- | --- | --- | --- |
| `REPS` | ✓ | ✓ | | |
| `EMOM` | ✓ | ✓ | | |
| `AMRAP` | ✓ | ✓ | ✓ | |
| `TIME` | **✓ (new)** | | ✓ | |
| `DISTANCE` | ✓ | | ✓ | ✓ |

`TIME` gains a weight input. Its absence was a bug, not a decision: it made a
weighted plank, a loaded march and a ruck all unloggable. `EntryCard.tsx`
currently hard-codes `time: { reps: false, time: true, weight: false }`.

One protocol covers rucking rather than a `distance × time × weight` third
protocol. Weight is not a *mode* of measurement; it is a property of the set,
already nullable on every other protocol.

### 2. Rucking load reuses the bodyweight machinery unchanged

A ruck is a bodyweight exercise (equipment `Bodyweight`) with
`bodyweight_fraction = 1.0` — walking carries all of you — and the pack **adds**,
which is exactly what `effective_load()` already does:

```text
effective = bodyweight * 1.0 + pack_weight
```

200 lb athlete, 35 lb pack → 235 lb. Resolved against the reading in effect on
the day, so a later weigh-in never rewrites a past ruck. No change to
`effective_load`. Loaded marches and carries with real equipment (kettlebells,
barbell) keep behaving as loaded exercises: their logged weight *is* the load,
and bodyweight does not enter — the rucksack case is the one where it does.

New curated fractions in `leverage.py` for locomotion, replacing the 0.64
push-up default which is meaningless for walking.

### 3. Conditioning never enters strength tonnage

The one firm prohibition. `weekly_volume_by_muscle_group` computes
`load × reps`. Feeding load-distance into the same `total_volume` would let a
single 5 km ruck at 235 lb effective produce ~1.2M unit-metres against roughly
50k lb for a hard lifting week — a ~20× swamp that makes the chart unreadable.

That is precisely the failure the volume service already documents for muscle
roles ("adding the secondary and tertiary contributors on top would inflate the
chart into noise"). Same mistake, different axis.

Conditioning therefore gets a **parallel metric set**, never merged:

- `sets`, `total_seconds`, `total_meters`
- `load_meters` — effective load × metres, for rucks and loaded carries
- derived `pace_seconds_per_km`

A conditioning set contributes its sets count to muscle-group volume (the work
is real and the target muscle is known) but contributes **zero tonnage**, on the
same principle already applied to bodyweight sets with no weigh-in: report what
is known, invent nothing.

### 4. Pace is progressable; bare time still is not

CLAUDE.md records that `TIME` gets no prescription, because inventing a rep
target for a rowing machine is nonsense. That stays true and unchanged.

`DISTANCE` is different, and better. With distance held constant, pace is a
single ordered variable, so there is a safe, meaningful prescription:

- **Constant distance** (Scott's rower is always 500m) → beat the best time at
  that distance. `500m in 107s` → target `< 107s`.
- **Constant time** → beat the distance covered.
- **Neither constant, or the load changed** → no prescription; report the last
  few performances. Two variables moving at once is not progression, and
  guessing which one the user meant to push is how a rep goal ended up on a
  rowing machine.

A ruck whose pack weight changed between sessions falls in the third case
deliberately: faster at lighter is not an improvement.

### 5. Legacy tables get the columns too

`workout_sets` gains `time_seconds` and `distance_meters`. Forward-only support
was considered and rejected: `history_service` unions both generations, and the
87 rowing sets are the entire baseline that makes pace progression meaningful on
day one. A conditioning feature that starts with an empty conditioning history
cannot prescribe anything.

Recovering them needs care. `backfill_workouts` is idempotent per **session**
(`if started_at in existing_starts: continue`), so re-running will not add sets
to sessions that already exist. The affected sessions must be deleted and
re-imported, scoped to sessions that actually contain conditioning sets.

## Out of Scope

- Heart-rate ingestion and HR-based conditioning load. The tables exist; filling
  them is the Garmin-parity work and is its own change.
- `PersonalRecord` for pace/distance. `recordtype` already has `time`; adding
  `distance` and `pace` is a natural follow-up once conditioning history lands.
- GPS or route capture.
- Unit preferences. Distance is stored in metres and displayed in metres/km,
  matching Hevy's payload. Weight stays in pounds per the existing convention.

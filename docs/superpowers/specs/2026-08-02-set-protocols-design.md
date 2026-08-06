# Set Protocols (AMRAP / EMOM) — Design

Date: 2026-08-02
Status: Approved (design), pending implementation plan

## Motivation

Scott trains some movements as interval work rather than straight sets. In Hevy
he distinguishes them by defining a separate exercise logged as weight and time
instead of weight and reps. SlotFit now carries that distinction structurally:
six HIIT variants exist, linked to their base exercises via `base_exercise_id`
with `variant_type = "HIIT"`.

What is missing is any notion of *how a set is measured*. `EntrySet` has
`weight`, `reps`, and `time_seconds`, all nullable, and `EntryCard` renders all
three inputs for every exercise — including the rower, which has no meaningful
rep count. Nothing records whether a given exercise is measured in reps, in
time, or in reps-within-a-time-window.

Two interval protocols matter, and they measure differently:

- **AMRAP** — time is the constraint (a 40-second window), reps are the result.
  Progress means more reps in the same window. Needs weight, reps, and time.
- **EMOM** — reps are the prescription (8 per minute), the minute is structural
  rather than measured. Progress means more load at the same reps. Needs weight
  and reps.

Note that this changes what gets recorded. The existing Hevy history logged
`{weight_kg: 13.6, duration_seconds: 40}` with **no reps at all**. Capturing
reps on AMRAP work is a deliberate improvement on past practice, not a port of
it. Nobody should later "correct" this back to time-only.

## Scope

This is the first of three related specs. It is deliberately the narrowest of
the three, because the other two depend on it.

1. **This spec.** The protocol on the exercise, which fields each protocol logs,
   and a UI that prompts for only those fields.
2. **Work-rest interval routines.** Building 40s-on/20s-off structures. Decided
   during brainstorming: exercises are prescribed but swappable in the gym, so a
   circuit is repeatable without being blocked by an occupied station.
3. **Time-aware progression.** `history_service.exercise_set_history` returns
   `(weight, reps)` tuples and drops `time_seconds` entirely, so AMRAP work
   currently gets no useful target and a meaningless "last time" line.

## Decisions Made During Brainstorming

1. **An explicit `set_protocol` enum drives behavior; `variant_type` stays a
   free-text label.** Overloading `variant_type` was rejected: a lowercase
   `"amrap"` would silently log the wrong fields, and it would force every
   variant to be a protocol even when it is just `"Volume"`.
2. **Labels are compound — `HIIT AMRAP`, `HIIT EMOM`.** Intent and protocol are
   independent, and stating both removes the need to guess what `HIIT` implies.
   Inference is a token scan rather than an exact-match table.
3. **Protocol lives on the exercise, not the round entry.** Per-entry choice was
   rejected as making you pick a protocol every time you add an exercise to a
   round, rather than once when you define the variant.
4. **`emom` and `reps` stay distinct despite logging identical columns**, because
   progression differs and spec 2's interval structure must tell them apart.
5. **The server stays permissive.** No new rejection for a protocol's missing
   field.

## Data Model

### Exercise.set_protocol

A new non-null enum column with values `reps`, `time`, `amrap`, `emom`,
defaulting to `reps`.

| protocol | weight | reps | time | Used for |
| --- | --- | --- | --- | --- |
| `reps` | optional | yes | not shown | Default. Every one of the 3,264 existing exercises. |
| `time` | optional | not shown | yes | Rower, plank, loaded carries |
| `amrap` | optional | yes | yes | Fixed window, count the reps |
| `emom` | optional | yes | not shown | Fixed reps per interval |

"Optional" on weight is deliberate throughout: bodyweight work has no load, and
the existing codebase already treats a null weight as bodyweight rather than as
missing data.

### RoundEntry.set_protocol

The same enum, denormalized onto `RoundEntry` and captured when the entry is
created.

This mirrors `RoundEntry.pattern_id`, whose existing comment states the rule:
"Denormalized at logging time so later mapping edits don't rewrite history."
The same reasoning applies. Reclassifying an exercise from AMRAP to EMOM must
not retroactively change what last month's sets meant.

## Protocol Inference on Variant Creation

`variant_type` remains free text and human-facing. It carries two independent
things, and a compound label states both: **HIIT** is the training intent
(conditioning-style interval work) and **AMRAP / EMOM** is the measurement
protocol. A strength AMRAP is a real thing and is simply labelled `AMRAP`.

Inference is a token scan over the lowercased label, so no exact-match table is
needed and compound labels work by construction:

| variant_type | set_protocol |
| --- | --- |
| `HIIT AMRAP` | `amrap` |
| `HIIT EMOM` | `emom` |
| `AMRAP` | `amrap` |
| `EMOM` | `emom` |
| `HIIT` | `reps` |
| `Strength`, `Volume`, anything else | `reps` |

Bare `HIIT` deliberately does **not** imply AMRAP. An earlier draft mapped it
that way, which buried a guess about Scott's training in the code and would be
wrong for anyone doing fixed-rep intervals. With compound labels available, a
variant that fails to state its protocol has not stated one, and falls back to
straight reps.

Both creation paths apply it:

- `POST /exercises/{id}/variants` in `app/api/v1/endpoints/exercises.py`
- `_create_variant` in `app/services/hevy_import.py`

A caller may set `set_protocol` explicitly to override the inference.

## API

`RoundEntryResponse` gains `set_protocol: str`, so the client knows which fields
to render without a second lookup. `ExerciseResponse` and the variant-creation
request schema gain the same optional field.

No endpoint changes shape otherwise. Set logging still accepts the same three
nullable values.

## UI

`EntryCard` renders inputs conditionally on `entry.set_protocol`:

| protocol | Inputs shown |
| --- | --- |
| `reps` | weight, reps |
| `time` | weight, seconds |
| `amrap` | weight, reps, seconds (pre-filled from `default_time_seconds`) |
| `emom` | weight, reps |

`formatSet` already handles every combination and needs no change — it omits
whatever is null.

## Validation

The server does not reject a set for missing a protocol-required field.

This is a deliberate trade. Mid-workout, on a phone, a set that fails to save is
worse than a set missing a number: the rep is already done and the data is gone
either way, but a rejection also costs the user a retry while their rest timer
runs. The UI prevents the common case by only prompting for relevant fields, and
tightening this later is a one-line schema change if the loose version proves
wrong in practice.

## Migration and Backfill

One Alembic migration adds both columns with a server default of `reps`, so
every existing exercise and round entry is valid without a data pass.

Two explicit backfills follow, both narrow and named:

| Target | Change | Why |
| --- | --- | --- |
| The 6 exercises where `variant_type = 'HIIT'` | `variant_type` → `HIIT AMRAP`, name `… (HIIT)` → `… (HIIT AMRAP)`, `set_protocol` → `amrap` | Their Hevy sets ran 30–40 second windows, not 60-second intervals |
| `Rowing Machine` | `set_protocol` → `time` | Warm-up conditioning with no meaningful rep count |

The rename is required, not cosmetic: with bare `HIIT` no longer implying a
protocol, leaving the label alone would silently reclassify all six to `reps`.
Renaming is safe because staples and round entries reference exercises by id.

`hevy/exercise_map.yaml` is updated in the same change so its six `variant_type`
values read `HIIT AMRAP`. Without that, re-running `hevy_staples apply` would
try to create a second set of `… (HIIT)` variants alongside the renamed ones.

Nothing else is touched. In particular, no attempt is made to infer protocol
from `default_time_seconds` across the catalogue — that would silently
reclassify exercises nobody reviewed.

## Testing

- The protocol inference map, including case-insensitivity and the unknown-type
  fallback to `reps`.
- Variant creation through both paths sets `set_protocol` from `variant_type`,
  and an explicit value overrides the inference.
- `RoundEntry` captures the exercise's protocol at creation, and **changing the
  exercise's protocol afterward does not alter the existing entry** — the
  denormalization guarantee, tested the same way the `is_override` guarantee is.
- `RoundEntryResponse` carries `set_protocol` through the API.
- The migration's backfill sets exactly the six HIIT variants and the rower, and
  leaves a sample of ordinary exercises on `reps`.
- A set logged with fields outside its protocol is still accepted, documenting
  the permissive-server decision as intended behavior rather than an oversight.

## Non-Goals

**Interval structure.** No work/rest timing, no round auto-advance, no circuit
builder. That is spec 2.

**Progression.** `exercise_set_history` still drops `time_seconds`, so AMRAP
entries will show no target. This spec does not improve that, and adding the
protocol does not make it worse. Spec 3.

**Retrofitting history.** No existing `EntrySet` rows are rewritten. Sets logged
before this change keep whatever fields they were given.

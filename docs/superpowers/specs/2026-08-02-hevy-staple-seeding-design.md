# Hevy Staple Seeding — Design

Date: 2026-08-02
Status: Approved (design), pending implementation plan

## Motivation

The staple pool is the input to every anchor and partner suggestion in a
pattern-based session. A user with an empty pool gets no suggestions at all, so
a new SlotFit install is inert until the pool is populated by hand — one
exercise at a time, from a catalogue of 3,240.

Scott has three years of Hevy history: 229 workouts from 2023-05-15 to
2026-07-18, 4,625 logged sets across 212 distinct exercises. That history is a
direct statement of which exercises he actually does, which is exactly what the
staple pool is supposed to represent. Seeding from it replaces an hour of
manual catalogue search with a reviewed mapping.

A snapshot of the account already exists in `hevy/data/` via
`hevy/pull_hevy.py`. This design covers turning that snapshot into staples.

## The Core Problem: The Catalogues Do Not Align

Naive name matching fails. Of the 116 exercises performed in three or more
sessions, only 7 percent match a SlotFit exercise name even after aggressive
normalization (lowercasing, unwrapping parentheticals, stripping punctuation,
order-insensitive token comparison).

The cause is that the two catalogues describe exercises at different levels of
specificity, and the mismatch runs in both directions.

| Hevy title | SlotFit reality |
| --- | --- |
| `Lat Pulldown (Cable)` | Six candidates: Cable Wide Grip, Cable Reverse Grip, Cable V Grip, Cable V Grip Seated Floor, Single Arm Cable Half Kneeling, Single Arm Cable Seated Floor Lat Pulldown |
| `Goblet Squat` | Three: Dumbbell, Kettlebell, Landmine Goblet Squat |
| `Hack Squat (Machine)` | Only `Single Arm Landmine Hack Squat`, a different movement |
| `Triceps Pushdown` | No equivalent |
| `Rowing Machine` | No equivalent, despite being the most-performed exercise in the window at 50 sessions |

Hevy is often less specific than SlotFit, so a single Hevy title maps to several
SlotFit exercises with no way to tell which one was performed. Separately,
SlotFit's catalogue has genuine gaps, mostly machine variants and conditioning.

A confidence threshold cannot separate these two cases. Both present as "no
exact match," but one needs a human choice among real candidates and the other
needs a new exercise record. This is why the design centers on a reviewed
mapping artifact rather than an automated matcher.

## Decisions Made During Brainstorming

1. **Curated mapping file, not automated matching.** The generator proposes
   ranked candidates; a human resolves. The file is version-controlled and
   re-runnable, so a later Hevy pull surfaces only new exercises.
2. **Staple set is the last 12 months, three or more sessions** — 58 exercises.
   All-time at the same threshold gives 116 but includes lifts abandoned years
   ago; a six-month window gives 28 and risks leaving movement patterns with no
   staples, which would silently degrade partner suggestions.
3. **Unmatched exercises become custom SlotFit exercises**, with a movement
   pattern assigned by hand in the mapping file. Skipping them would leave the
   `conditioning` pattern with no staples at all. Force-mapping to the nearest
   candidate is worse than a gap, because the pool would then suggest exercises
   the user does not do.
4. **Six machine equipment rows are added to the catalogue**, named as specific
   implements rather than one generic `Machine` bucket. See Equipment Catalogue
   Extension.
5. **Staples only. Workout history is out of scope.** See Non-Goals.

## Architecture

Two commands over one curated artifact, following the shape already used by
`seed_patterns.py`: a thin script delegating to a service module that pytest can
exercise directly.

| File | Role |
| --- | --- |
| `backend/app/services/hevy_import.py` | Window and threshold selection, name normalization, candidate ranking, mapping validation, apply logic |
| `backend/scripts/hevy_staples.py` | CLI with `generate` and `apply` subcommands |
| `hevy/exercise_map.yaml` | The curated mapping, committed to git |
| `backend/tests/test_hevy_import.py` | Tests |

`pyyaml` is added to `backend/requirements.txt`. It is already present in the
venv as a transitive dependency but is currently undeclared. YAML is chosen over
JSON because the file is hand-edited and needs comments.

### Flow

1. `python -m scripts.hevy_staples generate` reads `hevy/data/workouts.json` and
   `hevy/data/exercise_templates.json`, queries the SlotFit exercise catalogue,
   and writes `hevy/exercise_map.yaml`.
2. The user edits the file, resolving every entry the generator could not.
3. `python -m scripts.hevy_staples apply` validates the file, prints a plan, and
   writes only when `--commit` is passed.

## Mapping File Format

```yaml
meta:
  generated_from: hevy/data/workouts.json
  generated_at: 2026-08-02
  window_days: 365
  min_sessions: 3

exercises:
  - hevy: Lat Pulldown (Cable)
    hevy_template_id: 6A6C31A5
    sessions: 6
    last_performed: 2026-06-24
    hevy_equipment: machine
    slotfit: Cable V Grip Lat Pulldown
    candidates:
      - Cable V Grip Lat Pulldown
      - Cable Wide Grip Lat Pulldown
      - Cable Reverse Grip Lat Pulldown

  - hevy: Triceps Pushdown
    hevy_template_id: 93A552C6
    sessions: 4
    slotfit: null
    create:
      name: Cable Triceps Pushdown
      pattern: isolation
      equipment: Cable
    candidates: []

  - hevy: Rest
    sessions: 5
    slotfit: SKIP
```

Each entry must resolve exactly one of three ways:

- `slotfit: <exact SlotFit exercise name>` — map to an existing exercise.
- `slotfit: SKIP` — ignore this entry. Used for Hevy artifacts such as `Rest`.
- `create: {name, pattern, equipment?}` — create a custom exercise, then make it
  a staple. `pattern` is required and must be an existing `movement_patterns`
  slug; there is no inference.

`sessions`, `last_performed`, `hevy_equipment`, `hevy_template_id`, and
`candidates` are informational. The generator writes them to support the review;
`apply` ignores them.

### Pre-fill Policy

The generator pre-fills `slotfit` only when the match is unambiguous, defined as
all three of:

- every normalized token of the Hevy title appears in the SlotFit name,
- no equipment contradiction (see Equipment Vocabulary below),
- the top-scoring candidate strictly beats the second.

Otherwise it writes `slotfit: null` and lists up to five ranked candidates.

**Measured against current data, this pre-fills almost nothing: 1 of 58.** That
is not a tuning failure, it is the honest shape of the problem. 30 of the 58
have full token coverage but several equally-plausible candidates, because the
ambiguity is real — `Lat Pulldown (Cable)` has six SlotFit candidates differing
only by grip, and only the user knows which one he does. Relaxing the uniqueness
requirement to pre-fill the top candidate would raise the number substantially
while reintroducing precisely the silent-wrong-guess failure that Decision 1 and
Decision 3 exist to prevent.

The design therefore optimizes review ergonomics rather than automation rate.
Expect to resolve essentially all 58 entries by hand, which the following two
measures keep to a short sitting:

- Entries are ordered by session count, so the exercises that matter most are
  decided first and fatigue lands on the four-session tail.
- `slotfit` accepts a **candidate index** as well as a name, so a decision is
  usually a single keystroke: `slotfit: 2` selects the second listed candidate.
  An exact name string remains valid and is required for any exercise not in the
  candidate list.

### Equipment Vocabulary

The two vocabularies do not align and cannot be compared directly. Hevy uses
five values across the window; SlotFit has 39 equipment names and no typology —
`Equipment.category` exists but is NULL on every row.

| Hevy value | Count in window | SlotFit mapping |
| --- | --- | --- |
| `dumbbell` | 21 | `Dumbbell` |
| `none` | 17 | `Bodyweight` |
| `machine` | 16 | Unreliable, see below |
| `barbell` | 2 | `Barbell` |
| `kettlebell` | 2 | `Kettlebell` |

Note that `none` maps to the explicit `Bodyweight` equipment row (201
exercises), **not** to a NULL `primary_equipment_id`. Zero exercises in the
database have NULL equipment. This contradicts the "Bodyweight Exercises"
decision recorded in CLAUDE.md, which states that bodyweight exercises are
identified by `primary_equipment_id = NULL`. That drift predates this work and
is recorded in Follow-Ups below.

`machine` is treated as unknown: it contributes no scoring bonus and never
counts as a contradiction. Beyond being broad, Hevy's `machine` tag is
demonstrably unreliable — it is applied to `Pull Up` and `Chin Up`, which are
not machine exercises at all. Of the 16 entries carrying it, 6 are Cable
movements and 2 are Pull Up Bar movements that SlotFit already models
correctly. A contradiction requires both sides to be known and different.

## Equipment Catalogue Extension

SlotFit's catalogue is a functional-fitness and unconventional-implement
database — Kettlebell alone accounts for 859 of 3,240 exercises, alongside
Clubbell, Macebell, Bulgarian Bag, and Indian Club. It contains no selectorized
or plate-loaded gym machines, which is the underlying reason seven of Scott's
regular exercises have no match, including the most frequent one in the window.

Six equipment rows are added, following SlotFit's existing convention of naming
specific implements (`Trap Bar`, `EZ Bar`, `Landmine`, `Ab Wheel`) rather than
broad buckets. A single generic `Machine` row was rejected for reproducing
exactly the over-broad bucketing that makes Hevy's own tag unusable: an
equipment profile must be able to distinguish a gym with a rowing erg from one
with a hack squat.

| New equipment | Covers |
| --- | --- |
| `Rowing Machine` | Rowing Machine (50 sessions, the most frequent exercise in the window) |
| `Leg Press Machine` | Leg Press, Leg Press Wide Stance |
| `Hack Squat Machine` | Hack Squat |
| `Chest Press Machine` | Iso-Lateral Chest Press |
| `Pec Deck` | Chest Fly, Rear Delt Reverse Fly |
| `Hyperextension Bench` | Back Extension (Weighted Hyperextension) |

These six rows get `category = "Machine"`, the first use of that column. The 39
existing rows are left NULL; backfilling categories across the whole catalogue
is out of scope and recorded in Follow-Ups.

Adding equipment rows is a data change, not a schema change — `equipment` already
has a `category` column. The rows are inserted idempotently by name, in the same
`apply` run and before any exercise creation that references them.

## Matching Algorithm

Normalization applied to both Hevy titles and SlotFit names:

1. Lowercase.
2. Unwrap parentheticals, so `Incline Bench Press (Dumbbell)` yields the token
   `dumbbell` rather than discarding it.
3. Replace non-alphanumerics with spaces and collapse whitespace.
4. Fold plurals on tokens longer than three characters, so `triceps` and
   `tricep` unify.

Scoring for each SlotFit candidate:

- Token recall: the fraction of Hevy tokens present in the SlotFit name. This is
  the dominant term.
- Equipment adjustment per the Equipment Vocabulary table: a bonus on agreement,
  a penalty on contradiction, and nothing at all when the Hevy value is
  `machine`.
- Length penalty, so `Dumbbell Pullover` outranks
  `Stability Ball Double Dumbbell Seated Pullover` on equal recall.

Top five candidates are recorded per entry, ranked. Ranking quality matters more
than pre-fill rate here, because the user's review is a pick from this list.

## Apply Semantics

**Additive and idempotent.** Existing staples are skipped, nothing is updated or
deleted. A second `apply` run is a no-op. This matches the documented behavior of
`backfill_staples.py`.

**Plan then commit.** `apply` prints what it would do and exits without writing
unless `--commit` is passed.

**User targeting.** `--device-id` selects the user. When exactly one user exists
in the database, it defaults to that user and prints the selection. When several
exist and no `--device-id` is given, it fails rather than guessing.

**Created customs** get `is_custom="True"` and an `exercise_pattern_map` row with
`is_override=True`. The override flag is required, not cosmetic:
`seed_exercise_pattern_map` rewrites any row where `is_override` is false, so a
routine `seed_patterns` run would otherwise silently reclassify every
hand-assigned pattern.

**Matched exercises** take their pattern from the existing `exercise_pattern_map`,
which is how `POST /staples` already resolves it. An exercise with no pattern row
is reported and skipped, mirroring the endpoint's 404 rather than inventing a
pattern.

**Equipment rows first.** The six machine rows are inserted (idempotently, by
name) before any exercise creation, so a `create` entry can reference
`equipment: Rowing Machine` in the same run.

**Validation is all-or-nothing.** The run fails before any write if an entry
names a SlotFit exercise that does not exist, names a pattern slug that does not
exist, names an equipment value that is neither an existing row nor one of the
six added by this run, sets both `slotfit` and `create`, sets neither, or
requests creation of an exercise whose name already exists in the catalogue.

## Error Handling

| Condition | Behavior |
| --- | --- |
| `hevy/data/workouts.json` missing | `generate` fails with a message pointing at `pull_hevy.py` |
| `movement_patterns` empty | `apply` fails, directing the user to `seed_patterns` |
| Unresolved entry (`slotfit: null`, no `create`) | Validation error listing every unresolved entry at once, so the user fixes them in one pass |
| Unknown exercise, pattern, or equipment name | Validation error naming the entry and the bad value |
| Staple already exists | Skipped, counted, and reported |
| Exercise has no pattern mapping | Skipped, counted, and reported |
| Equipment row already exists | Reused, not duplicated |

## Testing

- Normalization and candidate ranking, against fixtures drawn from the real
  mismatch cases in this document.
- Pre-fill policy: an ambiguous title such as `Lat Pulldown (Cable)` must not be
  pre-filled even though six candidates exist.
- Equipment mapping: `none` resolves to the `Bodyweight` row rather than NULL,
  and `machine` produces neither a bonus nor a contradiction.
- Every validation failure path.
- Idempotency: apply twice, assert the second run writes nothing — including
  that the six equipment rows are not duplicated.
- Regression: after seeding, a `seed_exercise_pattern_map` run must not
  reclassify created customs. This guards the `is_override` decision, which is
  the subtlest part of the design.

## Non-Goals

**Importing workout history.** The 4,625 logged sets are not imported into
`workout_sessions` and related tables. The consequence is concrete and worth
stating: `last_performed` will be null on every seeded staple, because
`GET /staples` derives it from SlotFit's own session history via
`history_service.last_performed_map`. The pool will function for suggestions;
recency-based rotation will not have data until sessions are logged in SlotFit.

**Two-way sync.** Nothing is written back to Hevy. The Hevy API supports writes,
but this is a one-directional seed.

**Automatic re-seeding.** Re-running after a future Hevy pull is a manual
`generate` and `apply` cycle. The mapping file makes this cheap by surfacing only
exercises not already resolved.

## Follow-Ups

Discovered while designing this work. Neither blocks it, and neither is fixed by
it.

**CLAUDE.md's bodyweight rule does not match the database.** The documented
decision states that bodyweight exercises are those with
`primary_equipment_id = NULL` and must never be filtered out for equipment
reasons. No exercise in the database has NULL equipment; bodyweight is the
explicit `Bodyweight` equipment row covering 201 exercises. Any filtering logic
written against the NULL rule is inert. This should be resolved by deciding
which representation is canonical and correcting either the code or the
documentation — not by this seeding work, which simply follows the database.

**`Equipment.category` is unpopulated across all 39 existing rows.** This work
sets it on the six rows it adds, making `Machine` the only populated category.
Backfilling the rest (free weight, bodyweight, unconventional implement,
suspension, cardio) would make the column useful for equipment-profile
filtering, but is a separate change with its own design questions.

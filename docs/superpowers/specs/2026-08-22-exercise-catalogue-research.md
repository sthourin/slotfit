# Exercise Catalogue: Licensing Research and Replacement Options

Date: 2026-08-22
Status: Research — informs the licence risk in `2026-08-22-android-client-decision.md`

## Summary

No open dataset is a drop-in replacement, and none needs to be. The research
turned up a bigger finding than the licence question: **the current catalogue is
simultaneously too large and too small.** It carries 3,242 rows, and still fails
to contain 4 out of every 10 exercises actually trained.

The recommendation is therefore not "swap in another list". It is to author a
curated catalogue of roughly 250–400 exercises, seeded from a public-domain
dataset for names and attributes, with the gaps filled from real training
history and the movement patterns assigned by hand.

## The finding that reframes the question

`hevy/exercise_map.yaml` is the record of trying to match a real training
history against the current catalogue. Of the 61 exercises performed at least
three times in a year:

| Outcome | Count |
| --- | --- |
| Matched an existing catalogue entry | 36 |
| Required creating a new exercise | 24 |
| Skipped (not an exercise — "Rest") | 1 |

**A 3,242-exercise database missed 39% of what one user actually does.**

The misses are not random. Excluding eight HIIT entries — which are protocol
variants of existing exercises via `variant_of`, not catalogue gaps — nearly
every genuine miss is a **gym machine**:

> Hack Squat (Machine), Leg Press (Machine), Leg Press Wide Stance,
> Iso-Lateral Chest Press (Machine), Chest Fly (Machine), Rear Delt Reverse Fly
> (Machine), Pec Deck, Rowing Machine, Triceps Pushdown, Hyperextension Bench

The equipment histogram explains why. The current CSV's 32 equipment values
contain **no machine category at all**, and only 95 cable entries — while
devoting 861 rows to kettlebells, 195 to clubbells, 107 to macebells, 39 to
Bulgarian bags and 12 to Indian clubs:

| Primary equipment | Rows |
| --- | --- |
| Kettlebell | 861 |
| Dumbbell | 466 |
| Barbell | 267 |
| Bodyweight | 201 |
| Clubbell | 195 |
| Cable | 95 |
| *Machine (any kind)* | **0** |

It is a specialty implement catalogue. Meanwhile the actual training history is
led by Rowing Machine (66 sessions), Lat Pulldown (52), Iso-Lateral Chest Press
(31), Hack Squat (27) and Leg Press (21). Across 229 logged workouts there are
212 distinct exercises, of which only **53 were performed ten or more times**.

So: the catalogue is unmanageable at 3,242 rows, and the rows it has are the
wrong ones. Both problems have the same fix.

## What SlotFit actually consumes

Before judging candidates, what the code requires — from
`scripts/import_exercises.py`, `services/pattern_taxonomy.py` and the injury
model:

| Field | Consumer | Genuinely needed? |
| --- | --- | --- |
| name | everything, plus Hevy matching | **Required** |
| Target Muscle Group (level 1) | volume, recommendations | **Required** |
| Prime mover / secondary / tertiary (levels 2–4) | stored, displayed | **Barely.** CLAUDE.md is explicit that volume credits the *target* only — counting the hierarchy would double-count one set. Levels 2–4 are close to decorative |
| Primary equipment | equipment profiles, `is_bodyweight()` | **Required**, and the "Bodyweight" row name is load-bearing |
| Movement Pattern #1 | `classify_pattern()` rolls it up into the curated 10 | Required *as an input*, but see below |
| Mechanics (compound/isolation) | `classify_pattern()` | **Required** |
| Force type | injury restrictions | **Required** |
| Posture, plane of motion | injury restrictions (`restriction_type`) | Used, low value — could be dropped with the restriction rows that reference them |
| Difficulty, laterality, classification, YouTube URLs | display only | Optional |

The pattern column deserves attention. `classify_pattern()` exists only to
translate the source CSV's private pattern vocabulary into SlotFit's curated
ten, and it already needs a `NAME_OVERRIDES` table for the cases its rules get
wrong. **On a few-hundred-row catalogue you would assign the ten patterns
directly and delete the rollup**, which is less code and more accurate. Losing
the source column is an improvement, not a loss.

Net: a replacement needs name, one muscle level, equipment, force and mechanics.
Everything distinctive — the ten patterns, `bodyweight_fraction`, `SetProtocol` —
is SlotFit's own curation and comes from no dataset.

## Candidates

| Dataset | Size | Licence | Verdict |
| --- | --- | --- | --- |
| [yuhonas/free-exercise-db](https://github.com/yuhonas/free-exercise-db) | 873 | Unlicense (public domain) | **Best seed.** Text only — see images caveat |
| [wger](https://github.com/wger-project/wger) | ~1,000+ | CC-BY-SA 4.0 | Usable commercially, but share-alike |
| [Glowupp-app/open-exercisedb](https://github.com/Glowupp-app/open-exercisedb) | ~300 | MIT | Good size, undocumented provenance |
| [exercemus/exercises](https://github.com/exercemus/exercises) | — | MIT code, **per-exercise data licences** | Compliance burden |
| [hasaneyldrm/exercises-dataset](https://github.com/hasaneyldrm/exercises-dataset) | 1,324 | MIT data, media © Gym Visual | Media needs a paid licence |
| [wrkout/exercises.json](https://github.com/wrkout/exercises.json) | ~800 | Unlicense | Upstream of free-exercise-db; use that instead |
| [ExerciseDB API](https://github.com/exercisedb/exercisedb-api) | 11,000+ | Unclear | Assets trace to a paid API. Avoid |

### free-exercise-db, measured

Downloaded and counted rather than taken from the README — 873 exercises:

- `force`: pull 371, push 369, static 104, **missing 29**
- `mechanic`: compound 489, isolation 297, **missing 87**
- `level`: beginner 523, intermediate 293, expert 57
- `equipment`: 13 values — barbell 170, dumbbell 123, **other 122**, body only
  111, cable 81, **missing 77**, machine 67, kettlebells 53, bands 20, …
- `primaryMuscles`: 17 flat values (quadriceps 148, shoulders 127, abdominals
  93, chest 84, …), never empty
- Fields: name, force, level, mechanic, equipment, primaryMuscles,
  secondaryMuscles, instructions, category, images

Fit against SlotFit's needs:

- `force` and `mechanic` map straight onto `force_type` and `mechanics`, with
  ~10% missing to fill by hand.
- The 17 flat muscles map onto **level 1 target muscle groups** — which, as
  established, is the only level volume uses. The hierarchy loss is nearly free.
- 199 exercises (23%) have equipment of `other` or nothing, needing manual
  assignment — but that only matters for rows kept after curation.
- `body only` must be renamed to `Bodyweight` on import, because
  `is_bodyweight()` keys on that exact equipment row name.
- Machine coverage (67 machine + 81 cable) is materially better than the
  current CSV's zero machines and 95 cables — it covers actual training more
  faithfully despite being a quarter the size.

### The images caveat

Take the text, not the images. free-exercise-db ships 873 image sets and
declares Unlicense, but the provenance is undocumented, and
[issue #2, "License of Images?"](https://github.com/yuhonas/free-exercise-db/issues/2),
asked exactly this in June 2023 and **has never been answered**. The data
descends from Everkinetic, whose images are CC-BY-SA 3.0 — which would make a
blanket public-domain claim over them wrong.

This costs nothing: SlotFit stores YouTube links (`short_demo_url`,
`in_depth_url`), not bundled images. Skip the `images` field entirely.

### A caveat on "MIT-licensed" data generally

MIT is a software licence, and applying it to a dataset does not establish that
the publisher had the right to release it. Several candidates above declare a
permissive licence over data with no documented upstream. That is the same
weakness as the current CSV, differing only in that someone has *asserted* a
licence.

The distinction that actually matters for a commercial launch: exercise **names
and factual attributes** ("Lat Pulldown", "cable", "lats", "pull") are facts and
are thin-to-unprotectable in most jurisdictions, whereas **instruction prose** is
authored text and is the copyrightable part. Taking structure while writing your
own cues — or omitting cues, which SlotFit does today, having no instructions
column — puts you on much firmer ground than the licence label suggests either
way. Worth a lawyer's confirmation before a paid launch; not worth blocking on
now.

## Recommendation

**Author a curated catalogue; use free-exercise-db as the seed, not the source.**

1. **Seed** from free-exercise-db's JSON (text fields only, no images), filtered
   to `category: strength` plus the useful plyometrics — roughly 600 candidates
   before curation.
2. **Cut to what gets trained.** Target 250–400 exercises. The evidence says 53
   exercises cover ten-or-more-session usage and 212 cover everything ever
   logged; a few hundred is generous, not tight. Judge by "would a real training
   plan reach for this", not by breadth.
3. **Fill the machine gap explicitly** — hack squat, leg press, chest press,
   pec deck, lat pulldown variants, seated row variants, triceps pushdown,
   rowing machine, hyperextension bench. The 24 `create:` entries in
   `hevy/exercise_map.yaml` are a ready-made list of what is missing, already
   validated against real use.
4. **Assign the ten movement patterns by hand** and delete `classify_pattern()`
   and its `NAME_OVERRIDES`. At this size, direct assignment is faster to
   maintain and strictly more accurate than a rollup with a correction table.
5. **Keep the specialty rows that get used.** Kettlebell and clubbell work is
   trained, so those stay — but a few dozen, not 1,056.
6. **Record provenance this time.** A `LICENSE` and a `SOURCES.md` in `assets/`
   noting what came from where. This whole research exists because nobody wrote
   that file the first time.
7. **Extend the curated catalogue into the seed scripts** the same way
   `seed_leverage.py` already seeds `bodyweight_fraction` — the pattern is
   established and works.

### What this costs and buys

Cost: a few days of curation, an import-script rewrite, a data migration mapping
existing history onto new exercise ids (needed for logged sets, staples and
personal records), and re-running the Hevy mapping.

Buys: a redistributable catalogue with documented provenance; a browsable
exercise list; suggestion quality improved by removing thousands of never-chosen
rows from the ranking pool; the machine gap closed; and `classify_pattern()`
plus its override table deleted.

### Sequencing

This is not urgent for the tailnet phases, and it is disruptive — it rewrites
exercise ids that logged history points at. The natural slot is **after Phase C
(offline logging) and before Phase G (going public)**, since it is a hard
prerequisite for distribution but irrelevant while single-user. Doing it before
Phase F also means the store build ships the clean catalogue from its first
release.

One caveat on delay: every workout logged in the meantime is more history to
migrate. If the curation is going to happen anyway, earlier is cheaper.

## Sources

- [yuhonas/free-exercise-db](https://github.com/yuhonas/free-exercise-db) — 873 exercises, Unlicense
- [Issue #2: License of Images?](https://github.com/yuhonas/free-exercise-db/issues/2) — unanswered since 2023
- [wrkout/exercises.json](https://github.com/wrkout/exercises.json) — upstream, Unlicense
- [everkinetic/data](https://github.com/everkinetic/data) — CC-BY-SA 3.0 ancestor
- [wger-project/wger](https://github.com/wger-project/wger) — CC-BY-SA 4.0 catalogue
- [exercemus/exercises](https://github.com/exercemus/exercises) — MIT code, per-exercise data licences
- [hasaneyldrm/exercises-dataset](https://github.com/hasaneyldrm/exercises-dataset) — MIT data, Gym Visual media
- [Glowupp-app/open-exercisedb](https://github.com/Glowupp-app/open-exercisedb) — ~300 exercises, MIT
- [longhaul-fitness/exercises](https://github.com/longhaul-fitness/exercises) — MIT, thinner schema
- [ExerciseDB API](https://github.com/exercisedb/exercisedb-api) — 11,000+, unclear rights

# Pattern-Based Dynamic Sessions — Known Follow-Ups

Date: 2026-08-01
Status: Recorded at merge of `feat/pattern-based-dynamic-sessions`

These were found during implementation review and deliberately deferred. None
blocks merge. They are recorded here so the context is not lost.

## Spec provisions the implementation plan dropped

The final whole-branch review found the implementation plan had silently
narrowed the design spec before implementation began. Because every task and
every task review was scoped to the plan, none could detect the omission. These
spec items are designed but not built:

- **Exercise-search fallback on the anchor picker.** The spec called for full
  exercise search when staples do not cover what is available. Shipped instead:
  an empty-state panel linking to the Exercise Browser.
- **Novelty ("try something new") candidate on the anchor list.** Implemented for
  partner suggestions only.
- **Shared rest timer per superset round-trip.** The old `RestTimer` component
  was deleted with the slot UI and not replaced.
- **Per-exercise PRs and pattern e1RM deltas on the finish summary.** The summary
  currently shows rounds, exercises, set counts, and coverage chips only.
- **Blacklist management UI.** `createPreference`/`listPreferences`/
  `deletePreference` exist and the engine honors the blacklist first in its
  filter chain, but nothing in the UI calls them.
- **Warm-up preference editing.** `warmup_preferences` is modeled, persisted, and
  rendered by the Session page, but the Day Plans editor has no control for it,
  so the warm-up card cannot appear for a plan created in the app.
- **Staple management UI.** `patchStaple`/`deleteStaple` exist; a staple can be
  added but never deactivated or removed.

## Correctness and robustness

- **No session state machine.** Rounds, entries, and sets can be added to a
  `completed` or `discarded` session. `POST /sessions/{id}/discard` accepts a
  completed session and erases it from progression, recency, coverage, and
  weekly volume, with no path back. Not reachable from the UI, but reachable
  via the API on any owned session.
- **`_weekly_sets_by_muscle_group` counts discarded sessions** against the
  20-set weekly guard, unlike every equivalent query in `history_service`,
  which filters to completed.
- **Read-then-write races.** No DB uniqueness on `(round_id, position)` or on
  round `order`; the 409 checks can interleave. Needs two concurrent clients.
- **`ResumeBanner` calls `discard()` un-awaited and un-caught** — a failed
  discard is an unhandled rejection with no UI feedback.
- **Five exercises misclassify** in the taxonomy rollup, all falling to
  `isolation`: `Hip Dominant` (×2 → hip_hinge), `Lateral Flexion` and
  `Anti-Flexion` (→ core), `Lateral Locomotion` (→ conditioning).
- **`description` cannot be cleared** via `PUT /day-plans/{id}` (`None` is the
  "not provided" sentinel). Currently unreachable — the editor has no
  description field.

## Performance

- **`_filter_cards` N+1.** Re-runs four filter queries per pattern group and
  awaits `compute_entry_target` once per surviving card. A six-goal plan issues
  roughly 24 filter queries plus one per card, on the live request path.
- **`_rep_range_for` N+1.** One `PatternGoal` query per entry rather than
  prefetching per session.
- **`_diverse_limit` is applied twice** — per group inside `_filter_cards` and
  again on the concatenation — so each group's rejects are pre-capped before
  merging and the final "why not" list is less diverse than intended.

## Progression semantics worth revisiting

- **`estimate_1rm` ignores sets without a weight**, so a bodyweight staple
  contributes nothing to its pattern's trend. A user whose vertical-pull staple
  is pull-ups gets an empty trend line, which sits awkwardly against the
  project-wide decision that bodyweight exercises are first-class.
- **`pattern_trend`'s baseline is the earliest week inside the sliding window**,
  so "+X% vs baseline" on the Analytics page silently redefines itself as the
  window slides.

## Environment and tooling

- **`npm run build` still cannot bundle.** Seven TypeScript errors predate this
  branch (it had 32; retiring the slot UI removed 25). The feature has only ever
  run under the vite dev server, which skips typechecking.
- **Dead stores.** `web/src/stores/routineStore.ts` and `equipmentStore.ts` are
  referenced only by a re-export line.
- **The e2e database accumulates one day plan per run** — `day_plans` is
  deliberately not truncated by the reset script. Benign but unbounded.
- **`CLAUDE.md` still lists** `RoutineTemplate`/`RoutineSlot` among core models
  and "Enhanced Slot Types"/"Slot Templates" as upcoming work. Stale relative to
  this branch.

## Test coverage gaps

- The e2e covers the happy path only: no position-3 entry, no warm-up card, no
  resume banner, no discard.
- `Session.tsx` computes a new entry's `position` as `entries.length + 1`, so a
  round holding entries at positions 1 and 3 would 409.

## Operational note

The staple backfill script works and is tested, but the development database has
no completed workout history, so it creates zero staples. Staple pools start
empty and must be populated through the Exercise Browser or by training.

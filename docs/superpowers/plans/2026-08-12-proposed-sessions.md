# Proposed Sessions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Starting a session opens with a whole workout proposed — anchor, partner and optional third per round — which the user adjusts by swapping any slot.

**Architecture:** A read-only `GET /sessions/{id}/proposal` computes the workout from current session state and writes nothing, so re-proposal needs no invalidation and coverage keeps counting only what was performed. Pins travel with the request rather than being stored. The proposal reuses the existing suggestion engine's filters and rotation rule rather than introducing a parallel ranking.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy async, pytest; React 18, TypeScript, Vite, Zustand, Tailwind.

**Spec:** `docs/superpowers/specs/2026-08-02-proposed-sessions-design.md` (approved 2026-08-02).

## Global Constraints

- Backend commands use `backend/venv/Scripts/python.exe`; tests run as `cd backend && ./venv/Scripts/python.exe -m pytest`.
- Commit subjects are prefixed `[SH]`.
- The proposal endpoint must not write. Session, round and entry counts are identical before and after any call.
- Every filter the suggestion engine applies today still applies: blacklist, injury restrictions, weekly volume limit, equipment profile.
- Bodyweight is detected via `is_bodyweight(exercise, bodyweight_id)` from `app/services/exercise_helpers.py`, with the id resolved by `bodyweight_equipment_id(db)`. Never hardcode the id.
- Pattern ids: 1 horizontal_pull, 2 horizontal_push, 3 vertical_pull, 4 vertical_push, 5 knee_dominant, 6 hip_hinge, 7 core, 8 carry, 9 isolation, 10 conditioning. 7/8/9/10 are `is_neutral` and have no opposite.
- `RoundEntry.position` is 1-3.

## Cold Start — Resolved

The spec's anchor rule is "least recently performed active staple wins". Today every one of the 57 seeded staples reports `last_performed: null`, because the Hevy seeding created staples but no completed sessions. So the rotation rule has nothing to sort by and ties across the whole pool.

**Resolution: build the spec as written, and make the tie-break explicit and deterministic rather than incidental.** Reasons:

- The existing sort already puts never-performed first; among them, order is whatever the query returned. That is arbitrary but stable, and an arbitrary-yet-sensible first proposal is not a failure — it is a starting point the user swaps from, which is the whole design.
- It self-corrects. Every completed session stamps `last_performed` on what was used, so rotation becomes real as soon as training happens.
- Making item 1 wait on a Hevy history backfill would block the feature on an unresolved units question (see below).

Task 3 therefore sorts never-performed staples by `StapleExercise.added_at`, then `exercise_id`, so the proposal is reproducible across calls and does not shuffle between refreshes. Reproducibility is the property that matters — a proposal that changes every time you reload is worse than one that is merely arbitrary.

**Not in this plan, and blocked:** backfilling real history from `hevy/data/workouts.json` (229 workouts, 2023-05-15 to 2026-07-18) would give the rotation rule three years of genuine `last_performed` data from day one. It is blocked on a units decision: Hevy stores `weight_kg`, while `users.preferred_units` defaults to `"lbs"`. Loading kg values into a lbs-denominated system would corrupt every load figure by 2.2x. That decision is the user's and is recorded as a follow-up, not guessed at here.

## File Structure

**Backend — create**
- `app/services/proposal_service.py` — the algorithm. Separate from `suggestion_service` because it composes that module's per-slot answers into a whole session, and mixing "what could go here" with "what should the workout be" in one file would obscure both.
- `app/schemas/proposal.py` — response schemas.
- `backend/tests/test_proposal_service.py`
- `backend/tests/test_proposal_api.py`

**Backend — modify**
- `app/api/v1/endpoints/training_sessions.py` — add `GET /{session_id}/proposal`.

**Web — create**
- `src/services/proposals.ts` — client + types.
- `src/components/session/ProposedRounds.tsx` — read-ahead rounds with swap controls.

**Web — modify**
- `src/pages/Session.tsx` — render the proposal above the live rounds; hold pins in component state.

---

## Task 1: Proposal schemas

**Files:**
- Create: `backend/app/schemas/proposal.py`

**Interfaces:**
- Produces: `ProposedEntry`, `ProposedRound`, `UnmetGoal`, `ProposalResponse`, exactly matching the spec's JSON.

- [ ] **Step 1: Write the schemas**

```python
"""Schemas for a proposed session.

Mirrors RoundEntryResponse's shape where they overlap (set_protocol,
default_time_seconds) so the client can render log fields for a proposed slot
without a second lookup.
"""
from typing import List, Optional

from pydantic import BaseModel


class ProposedEntry(BaseModel):
    position: int
    pattern_slug: str
    exercise_id: int
    exercise_name: str
    set_protocol: str
    default_time_seconds: Optional[int] = None
    is_bodyweight: bool = False
    pinned: bool = False
    # Short human string. A proposal the user cannot interrogate is a black
    # box, and the design depends on him adjusting it.
    reason: str


class ProposedRound(BaseModel):
    order: int
    started: bool
    entries: List[ProposedEntry] = []


class UnmetGoal(BaseModel):
    pattern_slug: str
    reason: str


class ProposalResponse(BaseModel):
    warmup: Optional[ProposedEntry] = None
    rounds: List[ProposedRound] = []
    # Goals that cannot be filled, e.g. a pattern with no active staples. Named
    # explicitly rather than dropped: the fix is one tap away in the exercise
    # browser and invisible otherwise.
    unmet: List[UnmetGoal] = []
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/schemas/proposal.py
git commit -m "[SH] feat: schemas for proposed sessions"
```

---

## Task 2: Coverage and candidate helpers

The algorithm needs two things the suggestion engine already computes internally: how far each goal is from its target, and the filtered staple list for a pattern. Extract them rather than duplicating the filters.

**Files:**
- Create: `backend/app/services/proposal_service.py`
- Test: `backend/tests/test_proposal_service.py`

**Interfaces:**
- Consumes: `_session_context`, `_staples_with_exercises`, `_filter_cards`, `_goal_covered` from `app.services.suggestion_service`.
- Produces:
  - `async candidates_for_pattern(db, user_id, pattern_id, rep_ranges) -> list[dict]` — filtered staple cards for one pattern, least-recently-performed first, reproducibly ordered.
  - `def shortfall(goal, sets_by_pattern) -> int` — sets still needed for a goal; 0 when covered.

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for the session proposal algorithm."""
import pytest

from app.models import (
    DayPlan, Equipment, Exercise, ExercisePreference, MovementPattern,
    PatternGoal, SessionState, StapleExercise, TrainingSession, User,
)
from app.models.exercise import DifficultyLevel
from app.services.pattern_taxonomy import seed_movement_patterns, seed_exercise_pattern_map
from app.services.proposal_service import candidates_for_pattern, shortfall


def test_shortfall_counts_sets_still_needed():
    goal = PatternGoal(pattern_id=1, required=True, target_sets=3)
    assert shortfall(goal, {}) == 3
    assert shortfall(goal, {1: 1}) == 2
    assert shortfall(goal, {1: 3}) == 0
    # Overshooting a goal is not a negative need.
    assert shortfall(goal, {1: 5}) == 0


def test_shortfall_defaults_target_sets_to_three():
    goal = PatternGoal(pattern_id=1, required=True, target_sets=None)
    assert shortfall(goal, {}) == 3
```

Add an async test that `candidates_for_pattern` applies the blacklist, using the arrangement style already in `tests/test_suggestion_service.py`:

```python
@pytest.mark.asyncio
async def test_candidates_exclude_blacklisted_staples(test_db):
    """The proposal must not offer what the suggestion picker refuses to."""
    await seed_movement_patterns(test_db)
    user = User(device_id="prop-0001")
    cable = Equipment(name="Cable Machine")
    test_db.add_all([user, cable])
    await test_db.flush()
    good = Exercise(name="Prop Cable Row", movement_pattern_1="Horizontal Pull",
                    mechanics="Compound", primary_equipment_id=cable.id,
                    difficulty=DifficultyLevel.NOVICE)
    banned = Exercise(name="Prop Banned Row", movement_pattern_1="Horizontal Pull",
                      mechanics="Compound", primary_equipment_id=cable.id,
                      difficulty=DifficultyLevel.NOVICE)
    test_db.add_all([good, banned])
    await test_db.flush()
    await seed_exercise_pattern_map(test_db)
    test_db.add_all([
        StapleExercise(user_id=user.id, pattern_id=1, exercise_id=good.id),
        StapleExercise(user_id=user.id, pattern_id=1, exercise_id=banned.id),
        ExercisePreference(user_id=user.id, exercise_id=banned.id, preference="never"),
    ])
    await test_db.commit()

    cards = await candidates_for_pattern(test_db, user.id, 1, {})
    names = [c["exercise_name"] for c in cards]
    assert "Prop Cable Row" in names
    assert "Prop Banned Row" not in names
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest tests/test_proposal_service.py -q --no-cov -p no:logging`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.proposal_service'`.

- [ ] **Step 3: Write the helpers**

Create `backend/app/services/proposal_service.py`:

```python
"""Compose a whole proposed session from the suggestion engine's answers.

Kept apart from `suggestion_service`, which answers "what could go in this
slot". This module answers "what should today's workout be", and the two
questions have different inputs: one slot's pattern versus every goal's
shortfall across every round.

Nothing here writes. The endpoint recomputes from current session state on
every call, which is what makes "re-propose as you go" the default rather than
a feature needing invalidation.
"""
from app.models.day_plan import PatternGoal
from app.services.suggestion_service import (
    _filter_cards,
    _staples_with_exercises,
)

DEFAULT_TARGET_SETS = 3


def shortfall(goal: PatternGoal, sets_by_pattern: dict[int, int]) -> int:
    """Sets still needed to cover `goal`. Zero when met or overshot."""
    target = goal.target_sets or DEFAULT_TARGET_SETS
    return max(0, target - sets_by_pattern.get(goal.pattern_id, 0))


async def candidates_for_pattern(
    db, user_id: int, pattern_id: int, rep_ranges: dict[int, tuple[int, int]]
) -> list[dict]:
    """Filtered staples for one pattern, best candidate first.

    Ordering is least-recently-performed first, as the picker already does.
    Never-performed staples all tie, which is every staple until a session is
    completed, so `added_at` then `exercise_id` break the tie - the proposal
    must not reshuffle between two calls that saw the same state.
    """
    staples = await _staples_with_exercises(db, user_id, [pattern_id])
    if not staples:
        return []
    order = {
        staple.exercise_id: (staple.added_at, staple.exercise_id)
        for staple in staples
    }
    cards, _rejected = await _filter_cards(
        db,
        user_id,
        [s.exercise for s in staples],
        {s.exercise_id: s.pattern for s in staples},
        {s.exercise_id for s in staples},
        rep_ranges,
    )
    cards.sort(
        key=lambda card: (
            card["last_performed"] is not None,
            card["last_performed"] or _EPOCH,
            order.get(card["exercise_id"], (None, card["exercise_id"])),
        )
    )
    return cards
```

Add at the top of the module:

```python
from datetime import datetime

_EPOCH = datetime.min
```

`_filter_cards` already sorts least-recently-performed first; re-sorting here is deliberate, because only this module knows the reproducible tie-break the proposal depends on.

- [ ] **Step 4: Run to verify pass**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest tests/test_proposal_service.py -q --no-cov -p no:logging`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/proposal_service.py backend/tests/test_proposal_service.py
git commit -m "[SH] feat: coverage shortfall and reproducible candidate ordering"
```

---

## Task 3: The proposal algorithm

**Files:**
- Modify: `backend/app/services/proposal_service.py`
- Test: `backend/tests/test_proposal_service.py`

**Interfaces:**
- Consumes: `shortfall`, `candidates_for_pattern` from Task 2; `_session_context` and `_goal_covered` from `suggestion_service`.
- Produces: `async propose_session(db, user_id, session_id, pinned) -> dict` matching `ProposalResponse`. `pinned` is `dict[tuple[int, int], int]` keyed by `(round_order, position)` with an exercise id.

- [ ] **Step 1: Write the failing tests**

Cover the spec's test list. Build on a fixture with two opposite goals and staples on each.

```python
@pytest.mark.asyncio
async def test_anchor_is_the_most_under_covered_required_goal(test_db):
    """Round 1 opens on whatever the plan needs most, not an arbitrary pattern."""
    ...


@pytest.mark.asyncio
async def test_partner_is_the_anchor_patterns_opposite(test_db):
    ...


@pytest.mark.asyncio
async def test_neutral_anchor_takes_the_next_uncovered_goal_as_partner(test_db):
    """core/carry/isolation/conditioning have no opposite; the slot must not be empty."""
    ...


@pytest.mark.asyncio
async def test_no_exercise_appears_twice_in_one_proposal(test_db):
    ...


@pytest.mark.asyncio
async def test_pins_survive_reproposal_and_unpinned_slots_do_not(test_db):
    """Swapping round 1 must not discard a swap already made in round 2."""
    ...


@pytest.mark.asyncio
async def test_started_rounds_are_never_reproposed(test_db):
    ...


@pytest.mark.asyncio
async def test_pattern_with_no_staples_is_reported_unmet(test_db):
    """carry has no staples in the seeded pool; a goal that cannot be met is visible."""
    ...


@pytest.mark.asyncio
async def test_a_pinned_exercise_that_is_now_blacklisted_is_replaced(test_db):
    ...


@pytest.mark.asyncio
async def test_session_without_a_day_plan_falls_back_to_all_staple_patterns(test_db):
    ...


@pytest.mark.asyncio
async def test_the_proposal_writes_nothing(test_db):
    """Counts before and after must match, or coverage would read 3/3 unlogged."""
    before = await _counts(test_db)
    await propose_session(test_db, user.id, session.id, pinned={})
    assert await _counts(test_db) == before
```

Replace each `...` with an arrangement following `tests/test_suggestion_service.py`'s `_setup`. Add a `_counts` helper returning `(sessions, rounds, entries, sets)` row counts.

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest tests/test_proposal_service.py -q --no-cov -p no:logging`
Expected: FAIL — `propose_session` is not defined.

- [ ] **Step 3: Implement `propose_session`**

```python
async def propose_session(
    db, user_id: int, session_id: int, pinned: dict[tuple[int, int], int]
) -> dict:
    """A whole workout for this session, computed from current state.

    Rounds already started are returned as-is and never re-proposed; their
    entries exist and the user is working through them. Unstarted rounds are
    filled from the goals that are still short, so swaps and logged sets in
    earlier rounds change what later rounds propose.
    """
    session, goals, sets_by_pattern, rep_ranges = await _session_context(
        db, user_id, session_id
    )
    rounds_target = session.day_plan.rounds_target if session.day_plan else 3
    started_orders = {r.order for r in session.rounds if r.entries}

    # Projected coverage: as the proposal fills slots it must stop asking for
    # patterns it has already assigned, or every round would propose the same
    # under-covered pattern.
    projected = dict(sets_by_pattern)
    used_exercise_ids: set[int] = set()
    unmet: list[dict] = []
    proposed_rounds: list[dict] = []

    for order in range(1, rounds_target + 1):
        if order in started_orders:
            proposed_rounds.append({"order": order, "started": True, "entries": []})
            continue
        entries = await _propose_round(
            db, user_id, goals, projected, rep_ranges, pinned, order,
            used_exercise_ids, unmet,
        )
        proposed_rounds.append({"order": order, "started": False, "entries": entries})

    return {
        "warmup": await _propose_warmup(db, user_id, session, rep_ranges),
        "rounds": proposed_rounds,
        "unmet": _dedupe_unmet(unmet),
    }
```

Then `_propose_round`, which fills positions 1-3:

```python
async def _propose_round(
    db, user_id, goals, projected, rep_ranges, pinned, order, used, unmet
) -> list[dict]:
    """Anchor, partner, and a third only when a goal still needs one."""
    entries: list[dict] = []

    anchor_goal = _neediest_goal(goals, projected)
    if anchor_goal is None:
        return entries
    anchor = await _pick(
        db, user_id, anchor_goal.pattern_id, rep_ranges, pinned, order, 1, used, unmet,
        reason=f"least recently performed {await _slug(db, anchor_goal.pattern_id)}",
    )
    if anchor is None:
        return entries
    entries.append(anchor)
    projected[anchor_goal.pattern_id] = projected.get(anchor_goal.pattern_id, 0) + 1

    partner_pattern_id = await _opposite_or_next(db, anchor_goal, goals, projected)
    if partner_pattern_id is not None:
        partner = await _pick(
            db, user_id, partner_pattern_id, rep_ranges, pinned, order, 2, used, unmet,
            reason=f"opposite of {await _slug(db, anchor_goal.pattern_id)}",
        )
        if partner is not None:
            entries.append(partner)
            projected[partner_pattern_id] = projected.get(partner_pattern_id, 0) + 1

    # A third slot only when a goal is still short after the first two, so an
    # ordinary round is two entries as the spec intends.
    third_goal = _neediest_goal(goals, projected)
    if third_goal is not None:
        third = await _pick(
            db, user_id, third_goal.pattern_id, rep_ranges, pinned, order, 3, used, unmet,
            reason=f"{await _slug(db, third_goal.pattern_id)} still short",
        )
        if third is not None:
            entries.append(third)
            projected[third_goal.pattern_id] = projected.get(third_goal.pattern_id, 0) + 1

    return entries
```

`_pick` resolves one slot, honouring a pin when the pinned exercise still passes the filters:

```python
async def _pick(
    db, user_id, pattern_id, rep_ranges, pinned, order, position, used, unmet, reason
) -> dict | None:
    cards = await candidates_for_pattern(db, user_id, pattern_id, rep_ranges)
    available = [c for c in cards if c["exercise_id"] not in used]
    if not cards:
        unmet.append({"pattern_slug": await _slug(db, pattern_id),
                      "reason": "no active staples"})
        return None
    if not available:
        return None

    pinned_id = pinned.get((order, position))
    if pinned_id is not None:
        match = next((c for c in available if c["exercise_id"] == pinned_id), None)
        if match is not None:
            return _entry(match, position, pinned=True, reason="your choice")
        # A pin that no longer passes the filters is not honoured silently:
        # the user is told what replaced it and why.
        reason = f"{reason} (your pinned choice is no longer available)"

    chosen = available[0]
    used.add(chosen["exercise_id"])
    return _entry(chosen, position, pinned=False, reason=reason)
```

Add `_neediest_goal` (largest `shortfall`, ties to lowest `display_order`, required goals before optional), `_opposite_or_next` (the anchor pattern's `opposite_pattern_id`, else the next needy goal that is not the anchor's own pattern), `_slug`, `_entry` (projects a card dict into the `ProposedEntry` shape, carrying `set_protocol`, `default_time_seconds` and `is_bodyweight`), `_dedupe_unmet`, and `_propose_warmup` (first id in `DayPlan.warmup_preferences` whose exercise exists and passes the filters; `None` when the list is empty).

- [ ] **Step 4: Run to verify pass**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest tests/test_proposal_service.py -v --no-cov -p no:logging`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/proposal_service.py backend/tests/test_proposal_service.py
git commit -m "[SH] feat: propose a whole session from goal coverage"
```

---

## Task 4: The proposal endpoint

**Files:**
- Modify: `backend/app/api/v1/endpoints/training_sessions.py`
- Test: `backend/tests/test_proposal_api.py`

**Interfaces:**
- Produces: `GET /api/v1/sessions/{session_id}/proposal?pinned=1:2:118&pinned=2:1:245` → `ProposalResponse`.

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.asyncio
async def test_proposal_returns_rounds_for_the_day_plan(client, ...):
    response = await client.get(f"/api/v1/sessions/{session_id}/proposal", headers=headers)
    assert response.status_code == 200
    assert len(response.json()["rounds"]) == 3


@pytest.mark.asyncio
async def test_malformed_pinned_triple_is_rejected(client, ...):
    response = await client.get(
        f"/api/v1/sessions/{session_id}/proposal?pinned=nonsense", headers=headers
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_another_device_cannot_read_this_proposal(client, ...):
    other = {"X-Device-ID": "other-device-99999"}
    response = await client.get(f"/api/v1/sessions/{session_id}/proposal", headers=other)
    assert response.status_code == 404
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest tests/test_proposal_api.py -q --no-cov -p no:logging`
Expected: FAIL with 404 — the route does not exist.

- [ ] **Step 3: Add the endpoint**

```python
def _parse_pinned(raw: list[str]) -> dict[tuple[int, int], int]:
    """Parse `round:position:exercise_id` triples.

    Malformed input is rejected rather than ignored: silently dropping a pin
    would look identical to the proposal overriding the user's choice.
    """
    pinned: dict[tuple[int, int], int] = {}
    for item in raw:
        parts = item.split(":")
        if len(parts) != 3:
            raise HTTPException(status_code=422, detail=f"Malformed pinned value: {item}")
        try:
            order, position, exercise_id = (int(p) for p in parts)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Malformed pinned value: {item}")
        pinned[(order, position)] = exercise_id
    return pinned


@router.get("/{session_id}/proposal", response_model=ProposalResponse)
async def get_proposal(
    session_id: int,
    pinned: List[str] = Query(default=[]),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Propose a whole workout for this session. Writes nothing."""
    await _load_session(db, user, session_id)  # 404s for another user's session
    return await propose_session(db, user.id, session_id, _parse_pinned(pinned))
```

Import `ProposalResponse`, `propose_session` and `Query` at the top of the module.

- [ ] **Step 4: Run to verify pass, then the full suite**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest tests/test_proposal_api.py -q --no-cov -p no:logging`
Run: `cd backend && ./venv/Scripts/python.exe -m pytest -q --no-cov -p no:logging`

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/endpoints/training_sessions.py backend/tests/test_proposal_api.py
git commit -m "[SH] feat: GET /sessions/{id}/proposal"
```

---

## Task 5: Client service and types

**Files:**
- Create: `web/src/services/proposals.ts`

- [ ] **Step 1: Write the client**

```ts
/**
 * Session proposal API service.
 *
 * Pins are held in client state and sent with each request: a pin is a
 * statement about today's gym, not a lasting preference. Persisting one is
 * what marking a staple is for.
 */
import { apiClient } from './api'

export interface ProposedEntry {
  position: number
  pattern_slug: string
  exercise_id: number
  exercise_name: string
  set_protocol: 'reps' | 'time' | 'amrap' | 'emom'
  default_time_seconds: number | null
  is_bodyweight: boolean
  pinned: boolean
  reason: string
}

export interface ProposedRound {
  order: number
  started: boolean
  entries: ProposedEntry[]
}

export interface Proposal {
  warmup: ProposedEntry | null
  rounds: ProposedRound[]
  unmet: { pattern_slug: string; reason: string }[]
}

/** Pins keyed "round:position" -> exercise id. */
export type Pins = Record<string, number>

export async function getProposal(sessionId: number, pins: Pins): Promise<Proposal> {
  const pinned = Object.entries(pins).map(([key, id]) => `${key}:${id}`)
  const { data } = await apiClient.get(`/sessions/${sessionId}/proposal`, {
    params: { pinned },
    paramsSerializer: {
      // Repeat the key rather than sending pinned[]=, which FastAPI's
      // List[str] Query does not read.
      indexes: null,
    },
  })
  return data
}
```

- [ ] **Step 2: Typecheck and commit**

Run: `cd web && npx tsc --noEmit` — expect only the 7 known pre-existing errors.

```bash
git add web/src/services/proposals.ts
git commit -m "[SH] feat: proposal API client"
```

---

## Task 6: Render the proposal

**Files:**
- Create: `web/src/components/session/ProposedRounds.tsx`
- Modify: `web/src/pages/Session.tsx`

- [ ] **Step 1: Build the component**

Render each proposed round as a card. Round 1 is actionable; later rounds are dimmed (`opacity-60`) until reached. Each entry shows the exercise name, its pattern, the `reason` in small grey text, and a Swap control. Started rounds are skipped by this component — the live round rendering already owns them.

Stack on narrow screens the same way the session header does (`flex flex-col gap-3 sm:flex-row sm:items-center`), since this is read on a phone mid-session.

Show `unmet` entries as an explicit prompt, not a silent omission:

```tsx
{proposal.unmet.length > 0 && (
  <div className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-md p-3 mb-3">
    {proposal.unmet.map((u) => (
      <div key={u.pattern_slug}>
        No staples for {u.pattern_slug.replace(/_/g, ' ')} yet &mdash;{' '}
        <Link to="/exercises" className="underline">add some</Link>.
      </div>
    ))}
  </div>
)}
```

- [ ] **Step 2: Wire pins and refetch into Session.tsx**

Hold `const [pins, setPins] = useState<Pins>({})`. Fetch the proposal when a session is active, and refetch after a round is started or a set is logged so later rounds reflect what happened. Swapping a slot opens the existing picker scoped to that slot's pattern; choosing sets `pins[`${order}:${position}`] = exerciseId` and refetches.

- [ ] **Step 3: Verify by hand**

Start Docker, backend and web per `CLAUDE.md`. Open `http://localhost:3000` and set the device identity first:

```js
localStorage.setItem('slotfit_device_id','setup-verify-0001')
```

Confirm: starting a session shows a proposed workout rather than an empty round; round 1 is actionable and later rounds dimmed; swapping a slot in round 2 then swapping round 1 leaves the round 2 choice intact; starting round 1 materialises exactly those entries and coverage still reads 0/3 until sets are logged.

- [ ] **Step 4: Commit**

```bash
git add web/src/components/session/ProposedRounds.tsx web/src/pages/Session.tsx
git commit -m "[SH] feat: open a session with a proposed workout"
```

---

## Task 7: Correct the design record

The spec notes CLAUDE.md's wording would otherwise read as a prohibition on this feature. That section was already softened on 2026-08-11; this task confirms it matches what was built and adds the proposal's own rules.

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update "Pattern-Based Dynamic Sessions"**

Confirm the section states that a session opens with a proposed workout, that the proposal is computed and never stored, that pins live for the session only, and that coverage counts only performed sets. Add:

```markdown
The proposal is computed by `app/services/proposal_service.py` and returned by
`GET /sessions/{id}/proposal`, which writes nothing. Persisting proposed entries
would make coverage read 3/3 before a set was logged, so entries are still
created only when a round is actually started.

Rotation depends on `last_performed`, which only completed SlotFit sessions
stamp. Until a pattern's staples have been trained in the app they all tie, and
the proposal falls back to a reproducible order (`added_at`, then exercise id)
rather than reshuffling between refreshes.
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "[SH] docs: record how sessions are proposed"
```

---

## Final Verification

- [ ] **Backend suite** — `cd backend && ./venv/Scripts/python.exe -m pytest -q --no-cov -p no:logging`, all green.
- [ ] **Typecheck** — `cd web && npx tsc --noEmit`, only the 7 known pre-existing errors.
- [ ] **E2E** — the suite needs `E2E_DATABASE_URL` exported and its own migrations. `dynamic-session.spec.ts` starts a session and will now meet a proposal first; update it to reflect the new opening state rather than deleting the assertions.

```bash
cd backend && DATABASE_URL=postgresql+asyncpg://postgres:slotfit@localhost:5432/slotfit_e2e ./venv/Scripts/python.exe -m alembic upgrade head
cd web && E2E_DATABASE_URL=postgresql+asyncpg://postgres:slotfit@localhost:5432/slotfit_e2e npx playwright test
```

- [ ] **The proposal writes nothing** — with a session open, call the endpoint twice and confirm `training_sessions`, `superset_rounds`, `round_entries` and `entry_sets` row counts are unchanged.

## Follow-ups Not In This Plan

- **Backfill history from `hevy/data/workouts.json`** (229 workouts, 2023-05-15 to 2026-07-18) so rotation has three years of real `last_performed` from day one instead of ties. Blocked on a units decision: Hevy stores `weight_kg`, `users.preferred_units` defaults to `"lbs"`.
- **Backfill bodyweight from `hevy/data/body_measurements.json`**, which holds dated real readings and would make the leverage system live without manual weigh-ins. Same units question — the file is explicitly `weight_kg`.

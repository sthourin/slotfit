# Session Flow Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the progression, bodyweight-detection, suggestion and phone-layout defects found by driving the pattern-based session flow by hand on 2026-08-10.

**Architecture:** Progression becomes protocol-aware: `next_target` receives the entry's `SetProtocol` and stops applying rep-range logic to work it does not describe. `exercise_set_history` is widened to carry `time_seconds` so time-based work is no longer invisible to the math. Bodyweight detection moves behind a single predicate keyed on the "Bodyweight" equipment row rather than a NULL check that is never true. Slot 3 of a superset round gains a real selection rule; the anchor picker gains an escape hatch for off-plan patterns. The web shell gets a phone-viable nav.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy async, Alembic, pytest; React 18, TypeScript, Vite, Zustand, Tailwind.

## Global Constraints

- Backend commands must use `backend/venv/Scripts/python.exe` — a bare `python`/`pytest` resolves to the wrong venv.
- Run backend tests as `cd backend && ./venv/Scripts/python.exe -m pytest`.
- Commit subjects are prefixed `[SH]`.
- No new features beyond what is specified here; every task is a defect fix or a decided refinement.
- Progression increment stays `DEFAULT_INCREMENT = 5.0`, in the user's preferred units (`users.preferred_units`, default `"lbs"`).
- `SetProtocol` values are `reps`, `time`, `amrap`, `emom` (`app/models/exercise.py`).
- Bodyweight exercises are identified by `primary_equipment_id == 2` (the `Bodyweight` equipment row). No rows have `primary_equipment_id IS NULL`.
- Movement pattern ids: 1 horizontal_pull, 2 horizontal_push, 3 vertical_pull, 4 vertical_push, 5 knee_dominant, 6 hip_hinge, 7 core, 8 carry, 9 isolation, 10 conditioning. 7/8/9/10 are `is_neutral = true`.
- Do not modify `assets/slotfit_exercise_database_with_urls.csv`.

## Decisions This Plan Implements

Taken from the 2026-08-11 standup:

| Area | Decision |
|---|---|
| Bodyweight progression | Target is last reps + 1, no ceiling, never regresses |
| AMRAP progression | Beat last rep count at the same load; load never auto-increments |
| Time-only progression | No prescription; show last duration only |
| Bodyweight detection | Fix the predicate, keep equipment id 2, correct CLAUDE.md |
| Slot 3 | Protocol-matched finisher |
| Slot 2 | Stays pattern-only, deliberately |
| Anchor picker | Add an "other patterns" section at the bottom |
| Weight field | Driven by protocol + loadability, labelled `+ weight` on bodyweight movements |
| Empty pattern goals | Show staple count, warn on save, still selectable |
| Misfiled staples | Skater Jump → conditioning, Copenhagen Plank → core |
| Phone nav | Hamburger below the `sm` breakpoint |

Explicitly **not** in scope: leverage coefficients, the weigh-in log, and bodyweight-aware e1RM. Those are a separate subsystem — see `2026-08-11-bodyweight-leverage-and-weighins.md`.

Explicitly **dropped** after verification: a per-pattern `target_sets` input. It already exists at `web/src/pages/DayPlans.tsx:174-208` and works; the original finding was wrong. Only `rep_range_min`/`rep_range_max` are genuinely unexposed, and Task 10 adds those.

## Execution Order

**Task 5 must be done first.** It creates `app/services/exercise_helpers.py`, and Tasks 3 and 4 both need `is_bodyweight` from it. The phases below are grouped by subject rather than by order; execute as:

**5 → 1 → 2 → 3 → 4 → 6 → 7 → 8 → 9 → 10 → 11**

Tasks 8 through 11 are independent of each other and of everything before them; they can be done in any order once the earlier work is committed.

## File Structure

**Backend — modify**
- `app/services/history_service.py` — widen `exercise_set_history` sets to `(weight, reps, time_seconds)` triples.
- `app/services/progression_service.py` — protocol-aware `next_target`; update `pattern_trend` unpacking.
- `app/services/exercise_helpers.py` — **create**; home for `is_bodyweight`, so the rule lives in exactly one place.
- `app/services/suggestion_service.py` — use `is_bodyweight`; pass protocol into targets; slot-3 finisher rule; anchor "other patterns" group.
- `app/schemas/training_session.py` — `TargetResponse` gains `time_seconds` and `reps_goal`; `reps` becomes optional.
- `app/schemas/suggestion.py` — `AnchorSuggestionsResponse` gains `other_groups`.
- `app/api/v1/endpoints/training_sessions.py` — pass `entry.set_protocol` into `compute_entry_target`.
- `app/services/pattern_taxonomy.py` — recategorise the two misfiled exercises.

**Web — modify**
- `src/components/session/EntryCard.tsx` — render the new target shape; protocol/loadability-driven fields.
- `src/services/sessions.ts` — target type gains `time_seconds`, `reps_goal`; `reps` optional.
- `src/services/suggestions.ts` — anchor response gains `other_groups`.
- `src/components/session/AnchorPicker.tsx` (or the component that renders anchor groups) — render `other_groups` in a collapsed section.
- `src/components/Layout.tsx` (the nav shell) — hamburger below `sm`.
- `src/pages/DayPlans.tsx` — rep range inputs; staple counts; empty-goal warning; card layout fix.
- `src/pages/Session.tsx` — header layout fix; set-count pluralisation.

**Tests — modify/create**
- `backend/tests/test_progression_service.py`
- `backend/tests/test_history_service.py`
- `backend/tests/test_suggestion_service.py`
- `backend/tests/test_exercise_helpers.py` — **create**
- `backend/tests/test_pattern_taxonomy.py`

---

## Phase A — Progression correctness

### Task 1: Carry `time_seconds` through exercise history

`next_target` cannot reason about the rower because `exercise_set_history` never selects `time_seconds`. Widen it first; everything in Phase A depends on it.

Legacy `workout_sets` has no time column (only `rest_seconds`), so legacy rows always yield `None` for the third element.

**Files:**
- Modify: `backend/app/services/history_service.py:84-160`
- Modify: `backend/app/services/progression_service.py:152` (unpacking site)
- Test: `backend/tests/test_history_service.py`

**Interfaces:**
- Produces: `exercise_set_history(...) -> list[dict]` where each dict is `{"performed_at": datetime, "sets": list[tuple[float | None, int | None, int | None]]}`. The third element is `time_seconds`.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_history_service.py`:

```python
@pytest.mark.asyncio
async def test_exercise_set_history_includes_time_seconds(test_db):
    """Time-based work must survive into history or progression cannot see it."""
    await seed_movement_patterns(test_db)
    user = User(device_id="hist-time-0001")
    test_db.add(user)
    await test_db.flush()

    rower = Exercise(name="Test Rower", set_protocol=SetProtocol.TIME)
    test_db.add(rower)
    await test_db.flush()

    session = TrainingSession(
        user_id=user.id,
        state=SessionState.COMPLETED,
        started_at=datetime(2026, 8, 1, 9, 0),
        completed_at=datetime(2026, 8, 1, 10, 0),
    )
    test_db.add(session)
    await test_db.flush()
    rnd = SupersetRound(session_id=session.id, order=1)
    test_db.add(rnd)
    await test_db.flush()
    entry = RoundEntry(
        round_id=rnd.id, position=1, exercise_id=rower.id,
        pattern_id=10, set_protocol=SetProtocol.TIME,
    )
    test_db.add(entry)
    await test_db.flush()
    test_db.add_all([
        EntrySet(entry_id=entry.id, set_number=1, time_seconds=300, completed=True),
        EntrySet(entry_id=entry.id, set_number=2, time_seconds=240, completed=True),
    ])
    await test_db.flush()

    history = await exercise_set_history(test_db, user.id, rower.id)
    assert len(history) == 1
    assert history[0]["sets"] == [(None, None, 300), (None, None, 240)]
```

Ensure the module imports include `SetProtocol`:

```python
from app.models.exercise import SetProtocol
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest tests/test_history_service.py::test_exercise_set_history_includes_time_seconds -v`
Expected: FAIL — sets are 2-tuples, so the equality assertion fails with `[(None, None), (None, None)] != [(None, None, 300), (None, None, 240)]`.

- [ ] **Step 3: Widen the query and the returned tuples**

In `backend/app/services/history_service.py`, update the docstring's return contract and both queries.

Change the legacy select to pad a `None` time column so both branches produce the same arity:

```python
    legacy_query = (
        select(
            WorkoutSession.id, WorkoutSession.completed_at,
            WorkoutSet.weight, WorkoutSet.reps, WorkoutSet.set_number,
        )
        ...
```

stays as-is; the padding happens in the Python loop. Change the new-table select to add `EntrySet.time_seconds`:

```python
    new_query = (
        select(
            TrainingSession.id, TrainingSession.completed_at,
            EntrySet.weight, EntrySet.reps, EntrySet.time_seconds, EntrySet.set_number,
        )
        .join(SupersetRound, SupersetRound.session_id == TrainingSession.id)
        .join(RoundEntry, RoundEntry.round_id == SupersetRound.id)
        .join(EntrySet, EntrySet.entry_id == RoundEntry.id)
        .where(
            TrainingSession.user_id == user_id,
            TrainingSession.state == SessionState.COMPLETED,
            RoundEntry.exercise_id == exercise_id,
            EntrySet.completed == True,  # noqa: E712
        )
    )
```

Replace the accumulation loop and the return so tuples carry time. Legacy rows have no time column, hence the explicit `None`:

```python
    # (set_number, weight, reps, time_seconds)
    sets_by_session: dict[tuple[str, int], list[tuple[int, float | None, int | None, int | None]]] = defaultdict(list)
    completed_at_by_session: dict[tuple[str, int], datetime] = {}

    for session_id, completed_at, weight, reps, set_number in legacy_rows:
        if completed_at is None:
            continue
        key = ("legacy", session_id)
        # workout_sets has no duration column; legacy time is unknowable.
        sets_by_session[key].append((set_number, weight, reps, None))
        completed_at_by_session[key] = completed_at

    for session_id, completed_at, weight, reps, time_seconds, set_number in new_rows:
        if completed_at is None:
            continue
        key = ("new", session_id)
        sets_by_session[key].append((set_number, weight, reps, time_seconds))
        completed_at_by_session[key] = completed_at
```

And the final projection:

```python
    performances: list[dict] = []
    for key in ordered_keys:
        ordered_sets = sorted(sets_by_session[key], key=lambda t: t[0])
        performances.append({
            "performed_at": completed_at_by_session[key],
            "sets": [(weight, reps, time_seconds) for _n, weight, reps, time_seconds in ordered_sets],
        })
    return performances
```

Update the docstring's stated return to `[{"performed_at": datetime, "sets": [(weight, reps, time_seconds), ...]}]`.

- [ ] **Step 4: Fix the one existing unpacking site**

`pattern_trend` in `backend/app/services/progression_service.py:152` destructures 2-tuples and will raise. e1RM needs weight and reps only, so discard time:

```python
            best = max(
                (
                    estimate_1rm(w, r)
                    for w, r, _t in perf["sets"]
                    if w is not None and r
                ),
                default=None,
            )
```

- [ ] **Step 5: Run the full backend suite**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest tests/test_history_service.py tests/test_progression_service.py -v`
Expected: the new test PASSES. Existing tests that assert on `next_target(...)` inputs still pass because they call `next_target` directly with hand-built tuples — Task 2 updates those.

Any failure here means a `perf["sets"]` consumer was missed. Search for it:

Run: `cd backend && ./venv/Scripts/python.exe -m pytest -x -q`

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/history_service.py backend/app/services/progression_service.py backend/tests/test_history_service.py
git commit -m "[SH] fix: carry time_seconds through exercise set history"
```

---

### Task 2: Make `next_target` protocol-aware

Three defects, one root cause: `next_target` applies rep-range double progression to every protocol.

Verified current behaviour:

```
next_target([(None,15),(None,15)])       -> reps 12   # regression: told to do fewer than 15
next_target([(35.0,22),(35.0,22)])       -> weight 40 # runaway: +5 every session forever
next_target([(None,None),(None,None)])   -> reps 9, last_summary '0@bw, 0@bw'  # fabricated
```

**Files:**
- Modify: `backend/app/services/progression_service.py:35-105`
- Test: `backend/tests/test_progression_service.py`

**Interfaces:**
- Consumes: `exercise_set_history` 3-tuples from Task 1.
- Produces:
  - `next_target(last_sets, rep_min=8, rep_max=12, increment=5.0, protocol=SetProtocol.REPS) -> dict` with keys `weight: float | None`, `reps: int | None`, `sets: int`, `time_seconds: int | None`, `reps_goal: str | None`, `last_summary: str | None`. `reps_goal` is `"target"` (do exactly this many), `"beat"` (exceed this many), or `None` (no rep prescription).
  - `compute_entry_target(db, user_id, exercise_id, rep_min=8, rep_max=12, protocol=SetProtocol.REPS) -> dict | None`.

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_progression_service.py`, and add `SetProtocol` to its imports:

```python
from app.models.exercise import SetProtocol
```

```python
def test_next_target_bodyweight_never_regresses_past_rep_max():
    """Bodyweight has no load to add, so reps must keep climbing past rep_max.

    Regression guard: this returned 12 after a logged 15, i.e. prescribed less
    work than was just performed.
    """
    target = next_target([(None, 15), (None, 15)], rep_max=12)
    assert target["reps"] == 16
    assert target["reps_goal"] == "target"
    assert target["weight"] is None
    assert target["sets"] == 2
    assert target["last_summary"] == "2x15"


def test_next_target_bodyweight_below_rep_max_still_adds_one():
    target = next_target([(None, 9), (None, 9)], rep_max=12)
    assert target["reps"] == 10


def test_next_target_amrap_beats_last_count_without_touching_load():
    """AMRAP always clears a 12-rep ceiling, so rep-range logic must not drive load.

    Regression guard: this returned weight 40 from a logged 35, and escalated
    5 units per session indefinitely.
    """
    target = next_target(
        [(35.0, 22), (35.0, 22)], rep_max=12, protocol=SetProtocol.AMRAP
    )
    assert target["weight"] == 35.0
    assert target["reps"] == 22
    assert target["reps_goal"] == "beat"
    assert target["last_summary"] == "2x22 @ 35"


def test_next_target_amrap_uses_best_set_as_the_bar():
    """The number to beat is the best set performed, not the worst."""
    target = next_target(
        [(35.0, 22), (35.0, 18)], protocol=SetProtocol.AMRAP
    )
    assert target["reps"] == 22
    assert target["reps_goal"] == "beat"


def test_next_target_time_only_prescribes_nothing():
    """A rower logged in seconds gets no rep target and no invented load.

    Regression guard: this returned reps 9 and 'Last: 0@bw, 0@bw'.
    """
    target = next_target(
        [(None, None, 300), (None, None, 240)], protocol=SetProtocol.TIME
    )
    assert target["reps"] is None
    assert target["reps_goal"] is None
    assert target["weight"] is None
    assert target["time_seconds"] is None
    assert target["last_summary"] == "300s, 240s"


def test_next_target_time_only_uniform_durations_summarise_compactly():
    target = next_target(
        [(None, None, 300), (None, None, 300)], protocol=SetProtocol.TIME
    )
    assert target["last_summary"] == "2x300s"


def test_next_target_emom_behaves_like_reps():
    """EMOM reps are prescribed, so double progression still applies."""
    target = next_target(
        [(50.0, 12), (50.0, 12)], rep_max=12, increment=5.0, protocol=SetProtocol.EMOM
    )
    assert target["weight"] == 55.0
    assert target["reps"] == 8
    assert target["reps_goal"] == "target"
```

Existing tests assert exact dict equality (e.g. `test_next_target_adds_rep_below_range_top`). The return shape gains two keys, so update those three assertions to the new shape:

```python
def test_next_target_adds_rep_below_range_top():
    target = next_target([(120.0, 10), (120.0, 10), (120.0, 10)])
    assert target == {
        "weight": 120.0, "reps": 11, "sets": 3, "time_seconds": None,
        "reps_goal": "target", "last_summary": "3x10 @ 120",
    }


def test_next_target_bumps_weight_at_range_top():
    target = next_target([(120.0, 12), (120.0, 12), (120.0, 12)], increment=5.0)
    assert target == {
        "weight": 125.0, "reps": 8, "sets": 3, "time_seconds": None,
        "reps_goal": "target", "last_summary": "3x12 @ 120",
    }


def test_next_target_no_history():
    target = next_target([])
    assert target == {
        "weight": None, "reps": 8, "sets": 3, "time_seconds": None,
        "reps_goal": "target", "last_summary": None,
    }
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest tests/test_progression_service.py -v`
Expected: the new tests FAIL — `next_target` has no `protocol` parameter, so `TypeError: next_target() got an unexpected keyword argument 'protocol'`.

- [ ] **Step 3: Rewrite `next_target`**

Replace `next_target` in `backend/app/services/progression_service.py`. Accept both 2- and 3-tuples so hand-built call sites and tests stay readable:

```python
def _normalise(
    last_sets: list[tuple],
) -> list[tuple[float | None, int | None, int | None]]:
    """Accept (weight, reps) or (weight, reps, time_seconds); always return triples."""
    return [
        (s[0], s[1], s[2] if len(s) > 2 else None)
        for s in last_sets
    ]


def _summarise(sets: list[tuple[float | None, int | None, int | None]]) -> str:
    """Human summary of a performance, honest about what was actually recorded.

    Time-only sets summarise by duration; a set with no reps must never be
    rendered as '0 reps', which reads as a data-loss bug rather than as work
    measured a different way.
    """
    reps = [r for _w, r, _t in sets if r is not None]
    times = [t for _w, _r, t in sets if t is not None]
    weights = [w for w, _r, _t in sets if w is not None]

    if not reps and times:
        if len(set(times)) == 1:
            return f"{len(sets)}x{times[0]}s"
        return ", ".join(f"{t}s" for t in times)

    all_weighted = len(weights) == len(sets)
    all_bodyweight = len(weights) == 0

    if reps and all_weighted and len(set(weights)) == 1 and len(set(reps)) == 1:
        return f"{len(sets)}x{reps[0]} @ {_fmt_weight(weights[0])}"
    if reps and all_bodyweight and len(set(reps)) == 1:
        return f"{len(sets)}x{reps[0]}"
    parts = []
    for w, r, t in sets:
        if r is None and t is not None:
            parts.append(f"{t}s")
        else:
            parts.append(f"{r if r is not None else 0}@{_fmt_weight(w) if w is not None else 'bw'}")
    return ", ".join(parts)


def next_target(
    last_sets: list[tuple],
    rep_min: int = DEFAULT_REP_MIN,
    rep_max: int = DEFAULT_REP_MAX,
    increment: float = DEFAULT_INCREMENT,
    protocol: SetProtocol = SetProtocol.REPS,
) -> dict:
    """The next performance to aim for, interpreted through the set protocol.

    REPS / EMOM: double progression — add a rep until every set is at rep_max,
    then add load and reset to rep_min. Bodyweight work has no load to add, so
    it keeps adding reps past rep_max rather than being clamped back down to it.

    AMRAP: the goal is to beat the best rep count at the same load. Rep ranges
    do not apply — an AMRAP always clears a 12-rep ceiling, so feeding it
    through double progression escalates load every single session forever.

    TIME: no prescription at all. Duration progression needs intent this
    function does not have, and inventing a rep target from rep_min produced
    targets for a rower.
    """
    empty = {
        "weight": None,
        "reps": None if protocol is SetProtocol.TIME else rep_min,
        "sets": DEFAULT_SETS,
        "time_seconds": None,
        "reps_goal": None if protocol is SetProtocol.TIME else "target",
        "last_summary": None,
    }
    if not last_sets:
        return empty

    sets = _normalise(last_sets)
    last_summary = _summarise(sets)
    weights = [w for w, _r, _t in sets if w is not None]
    reps = [r for _w, r, _t in sets if r is not None]
    top_weight = max(weights) if weights else None

    if protocol is SetProtocol.TIME:
        return {
            "weight": None,
            "reps": None,
            "sets": len(sets),
            "time_seconds": None,
            "reps_goal": None,
            "last_summary": last_summary,
        }

    if protocol is SetProtocol.AMRAP:
        return {
            "weight": top_weight,
            "reps": max(reps) if reps else None,
            "sets": len(sets),
            "time_seconds": None,
            "reps_goal": "beat" if reps else None,
            "last_summary": last_summary,
        }

    # REPS / EMOM: double progression.
    min_reps = min(reps) if reps else rep_min
    all_at_top = bool(reps) and all(r is not None and r >= rep_max for _w, r, _t in sets)

    if all_at_top and top_weight is not None:
        return {
            "weight": top_weight + increment,
            "reps": rep_min,
            "sets": len(sets),
            "time_seconds": None,
            "reps_goal": "target",
            "last_summary": last_summary,
        }

    # Bodyweight at or past the ceiling: keep climbing. Clamping to rep_max here
    # is what prescribed 12 reps after a logged 15.
    next_reps = min_reps + 1 if top_weight is None else min(min_reps + 1, rep_max)
    return {
        "weight": top_weight,
        "reps": next_reps,
        "sets": len(sets),
        "time_seconds": None,
        "reps_goal": "target",
        "last_summary": last_summary,
    }
```

Add the import at the top of the module:

```python
from app.models.exercise import SetProtocol
```

- [ ] **Step 4: Thread the protocol through `compute_entry_target`**

```python
async def compute_entry_target(
    db: AsyncSession,
    user_id: int,
    exercise_id: int,
    rep_min: int = DEFAULT_REP_MIN,
    rep_max: int = DEFAULT_REP_MAX,
    protocol: SetProtocol = SetProtocol.REPS,
) -> dict | None:
    """Target for the next performance of an exercise, from its own history."""
    history = await exercise_set_history(db, user_id, exercise_id, limit_sessions=1)
    if not history:
        return None
    return next_target(
        history[0]["sets"], rep_min=rep_min, rep_max=rep_max, protocol=protocol
    )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest tests/test_progression_service.py -v`
Expected: PASS, all tests including the three updated equality assertions.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/progression_service.py backend/tests/test_progression_service.py
git commit -m "[SH] fix: make progression targets protocol-aware"
```

---

### Task 3: Pass the protocol in at both call sites and widen the API schema

`compute_entry_target` now takes a protocol but nothing supplies one. Two call sites: the session entry endpoint (which has the denormalised `RoundEntry.set_protocol` — historically correct) and the suggestion service (which has `Exercise.set_protocol`).

**Files:**
- Modify: `backend/app/api/v1/endpoints/training_sessions.py:102-105`
- Modify: `backend/app/services/suggestion_service.py:277-279`, `:659-661`
- Modify: `backend/app/schemas/training_session.py:26-30`
- Test: `backend/tests/test_suggestions_api.py`, `backend/tests/test_training_sessions.py`

**Interfaces:**
- Consumes: `compute_entry_target(..., protocol=...)` from Task 2; `is_bodyweight` from Task 5.
- Produces: `TargetResponse` with fields `weight: float | None`, `reps: int | None`, `sets: int`, `time_seconds: int | None`, `reps_goal: str | None`, `last_summary: str | None`.
- Produces: `RoundEntryResponse.is_bodyweight: bool` — the web card needs it to label the weight input `+ weight`, and nothing else on the response exposes equipment.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_suggestions_api.py`:

```python
@pytest.mark.asyncio
async def test_time_only_staple_target_has_no_rep_prescription(client, test_db):
    """A rower staple with history must not come back with an invented rep target."""
    # Arrange: a completed session logging two time-only sets on a conditioning
    # staple, then ask for anchors on a fresh session.
    # (Follow the arrange pattern already used by the tests above in this file.)
    ...
    body = response.json()
    cards = [c for g in body["groups"] for c in g["staples"]]
    rower = next(c for c in cards if c["exercise_name"] == "Test Rower")
    assert rower["target"]["reps"] is None
    assert rower["target"]["reps_goal"] is None
    assert rower["target"]["last_summary"] == "2x300s"
```

Replace the `...` with the same arrangement used by the existing target-shape test in this file (`test_suggestion_card_target_shape` around line 175), substituting a `SetProtocol.TIME` exercise and `EntrySet(time_seconds=300)` rows.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest tests/test_suggestions_api.py -k time_only -v`
Expected: FAIL — `reps` comes back as an integer because the suggestion service still calls `compute_entry_target` without a protocol.

- [ ] **Step 3: Widen `TargetResponse`**

In `backend/app/schemas/training_session.py`:

```python
class TargetResponse(BaseModel):
    weight: Optional[float]
    reps: Optional[int]
    sets: int
    time_seconds: Optional[int] = None
    # "target" = do exactly this many reps; "beat" = exceed this many (AMRAP);
    # None = no rep prescription (time-only work).
    reps_goal: Optional[str] = None
    last_summary: Optional[str]  # e.g. "3x10 @ 120", "2x300s"
```

- [ ] **Step 4: Pass the protocol at the entry endpoint and expose `is_bodyweight`**

Add the field to `RoundEntryResponse` in `backend/app/schemas/training_session.py`:

```python
    # The web card labels the weight input "+ weight" for bodyweight movements,
    # and nothing else on this response exposes equipment.
    is_bodyweight: bool
```

In `backend/app/api/v1/endpoints/training_sessions.py`, inside `_entry_response`. Use the entry's denormalised protocol, not the exercise's, so reclassifying an exercise later cannot rewrite what past sets meant:

```python
    rep_min, rep_max = await _rep_range_for(db, session, entry.pattern_id)
    target = await compute_entry_target(
        db, user.id, entry.exercise_id, rep_min, rep_max, protocol=entry.set_protocol
    )
```

and populate the new field in the returned `RoundEntryResponse(...)`, importing the helper at the top of the module:

```python
from app.services.exercise_helpers import is_bodyweight
```

```python
        is_bodyweight=is_bodyweight(entry.exercise),
```

`entry.exercise` is already loaded here — the function reads `entry.exercise.name` and `entry.exercise.default_time_seconds` — so this adds no query.

- [ ] **Step 5: Pass the protocol in the suggestion service**

`backend/app/services/suggestion_service.py`, in `_filter_cards` (~line 277) — the `Exercise` row is in scope:

```python
                "target": await compute_entry_target(
                    db, user_id, exercise.id, rep_min, rep_max,
                    protocol=exercise.set_protocol,
                ),
```

And in `_novelty_candidate` (~line 659):

```python
            "target": await compute_entry_target(
                db, user_id, exercise.id, rep_min, rep_max,
                protocol=exercise.set_protocol,
            ),
```

- [ ] **Step 6: Run the backend suite**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest -q`
Expected: PASS. If a test asserts the old `TargetResponse` shape, update it to include the two new keys.

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/v1/endpoints/training_sessions.py backend/app/services/suggestion_service.py backend/app/schemas/training_session.py backend/tests/
git commit -m "[SH] fix: supply set protocol when computing progression targets"
```

---

### Task 4: Render the new target shape and protocol-driven fields

The card currently hardcodes `Target: {sets}x{reps}`, so a time-only target renders `Target: 2xnull`. It also always shows a weight box.

Field rule: weight is shown when the protocol records load **and** the exercise is loadable; on bodyweight movements it is labelled `+ weight` to make clear it means added load.

**Files:**
- Modify: `web/src/components/session/EntryCard.tsx`
- Modify: `web/src/services/sessions.ts`

**Interfaces:**
- Consumes: `TargetResponse` from Task 3.
- Produces: `EntryCard` renders `Beat 22 @ 35` for AMRAP, `Last: 2x300s` with no target line for time-only, `Target: 3x11 @ 65` for reps.

- [ ] **Step 1: Update the TypeScript types**

In `web/src/services/sessions.ts`, find the target type on `RoundEntry` and widen it:

```ts
export interface Target {
  weight: number | null
  reps: number | null
  sets: number
  time_seconds: number | null
  reps_goal: 'target' | 'beat' | null
  last_summary: string | null
}
```

Set `RoundEntry.target` to `Target | null`, and add `is_bodyweight: boolean` to the `RoundEntry` interface — Task 3 Step 4 added that field to the API response.

- [ ] **Step 2: Write the target line renderer**

Replace the target block in `EntryCard.tsx` (currently lines 99-106):

```tsx
      {target && (
        <div className="text-sm text-gray-500 mt-1">
          {target.last_summary ? `Last: ${target.last_summary}` : ''}
          {target.reps_goal && target.last_summary ? ' → ' : ''}
          {target.reps_goal === 'beat' && (
            <>Beat {target.reps}{target.weight != null ? ` @ ${target.weight}` : ''}</>
          )}
          {target.reps_goal === 'target' && (
            <>Target: {target.sets}x{target.reps}{target.weight != null ? ` @ ${target.weight}` : ''}</>
          )}
        </div>
      )}
      {!target && <div className="text-sm text-gray-400 mt-1">No history yet — log your first set.</div>}
```

A time-only target has `reps_goal === null`, so this renders `Last: 2x300s` and nothing else — no prescription, which is the decision.

- [ ] **Step 3: Drive the weight field off protocol and loadability**

Extend the protocol table to say whether load is recorded, and gate the input:

```tsx
/**
 * Which inputs each protocol asks for. `weight` is about whether load is a
 * meaningful measurement for the protocol at all — a rower's resistance is not
 * a load you progress, so asking for it is noise on a phone.
 *
 * EMOM and REPS look identical here on purpose: for EMOM the minute is
 * structural, not a measured result, so there is nothing to type.
 */
const PROTOCOL_FIELDS: Record<string, { reps: boolean; time: boolean; weight: boolean }> = {
  reps: { reps: true, time: false, weight: true },
  time: { reps: false, time: true, weight: false },
  amrap: { reps: true, time: true, weight: true },
  emom: { reps: true, time: false, weight: true },
}
```

Then wrap the weight input, and label it for bodyweight movements:

```tsx
        {fields.weight && (
          <input
            value={weight}
            onChange={(e) => setWeight(e.target.value)}
            placeholder={entry.is_bodyweight ? '+ weight' : 'weight'}
            aria-label={entry.is_bodyweight ? 'added weight' : 'weight'}
            className="w-24 border rounded-md px-3 py-3 min-h-[44px]"
            inputMode="decimal"
          />
        )}
```

And in `logSet`, stop sending a weight the protocol does not record:

```tsx
      weight: fields.weight ? parse(weight) : null,
```

- [ ] **Step 4: Update `formatSet` so a time-only set never prints as reps**

```tsx
/** "8 @ 135", "12", "300s" — never "null" or a misleading 0. */
function formatSet(s: { weight: number | null; reps: number | null; time_seconds: number | null }): string {
  const bits: string[] = []
  if (s.reps != null) bits.push(s.weight != null ? `${s.reps} @ ${s.weight}` : `${s.reps}`)
  else if (s.weight != null) bits.push(`@ ${s.weight}`)
  if (s.time_seconds != null) bits.push(`${s.time_seconds}s`)
  return bits.length > 0 ? bits.join(' · ') : '—'
}
```

This is already correct — verify it is unchanged and that a `(null, null, 300)` set renders `300s`.

- [ ] **Step 5: Typecheck and verify in the browser**

Run: `cd web && npx tsc --noEmit`
Expected: no NEW errors. Seven pre-existing unused-variable errors in unrelated files are known and acceptable.

Then drive it by hand. Docker, backend and web must be running per `CLAUDE.md`; open `http://localhost:3000` (not `127.0.0.1`), and in devtools set the device identity before testing or the app looks empty:

```js
localStorage.setItem('slotfit_device_id','setup-verify-0001')
```

Confirm: a plain lift shows weight + reps; an AMRAP shows weight + reps + seconds; the rower shows seconds only and its card reads `Last: 2x300s` with no target.

- [ ] **Step 6: Commit**

```bash
git add web/src/components/session/EntryCard.tsx web/src/services/sessions.ts
git commit -m "[SH] fix: render protocol-appropriate targets and set fields"
```

---

## Phase B — Bodyweight detection

### Task 5: Replace the NULL bodyweight check with a real predicate

`CLAUDE.md` states bodyweight exercises are those with `primary_equipment_id = NULL` and must always be available regardless of equipment profile. Zero rows satisfy that: all 209 bodyweight exercises point at equipment id 2, named `Bodyweight`. So `is_bodyweight` is always `False`, and the always-available rule never fires. It is latent only because no equipment profile exists yet — the moment one is created without ticking Bodyweight, every push-up, plank, squat jump and pull-up is filtered out as "Equipment not in your current profile".

**Files:**
- Create: `backend/app/services/exercise_helpers.py`
- Create: `backend/tests/test_exercise_helpers.py`
- Modify: `backend/app/services/suggestion_service.py:234`, `:632`
- Modify: `CLAUDE.md` (the "Bodyweight Exercises" design decision)

**Interfaces:**
- Produces: `BODYWEIGHT_EQUIPMENT_ID: int` and `is_bodyweight(exercise: Exercise) -> bool`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_exercise_helpers.py`:

```python
"""Tests for the bodyweight predicate."""
from app.models.exercise import Exercise
from app.services.exercise_helpers import BODYWEIGHT_EQUIPMENT_ID, is_bodyweight


def test_bodyweight_equipment_row_is_bodyweight():
    assert is_bodyweight(Exercise(name="Push Up", primary_equipment_id=BODYWEIGHT_EQUIPMENT_ID))


def test_null_equipment_is_treated_as_bodyweight():
    """No catalogue row has NULL today, but a hand-created exercise might."""
    assert is_bodyweight(Exercise(name="Handstand", primary_equipment_id=None))


def test_loaded_exercise_is_not_bodyweight():
    assert not is_bodyweight(Exercise(name="Trap Bar Deadlift", primary_equipment_id=17))
```

Add to `backend/tests/test_suggestion_service.py` — the regression that matters:

```python
@pytest.mark.asyncio
async def test_bodyweight_staples_survive_an_equipment_profile_without_bodyweight(test_db):
    """A profile that omits the Bodyweight equipment row must not hide push-ups.

    CLAUDE.md: bodyweight exercises are ALWAYS available regardless of
    equipment profile. This failed silently because the check tested for NULL
    and every bodyweight row points at equipment id 2 instead.
    """
    await seed_movement_patterns(test_db)
    user = User(device_id="bw-profile-0001")
    test_db.add(user)
    await test_db.flush()

    push_up = Exercise(name="Profile Test Push Up", primary_equipment_id=BODYWEIGHT_EQUIPMENT_ID)
    test_db.add(push_up)
    await test_db.flush()
    test_db.add(ExercisePatternMap(exercise_id=push_up.id, pattern_id=2))
    test_db.add(StapleExercise(user_id=user.id, exercise_id=push_up.id, pattern_id=2, is_active=True))
    # A profile listing only a barbell — deliberately no Bodyweight row.
    test_db.add(EquipmentProfile(user_id=user.id, name="Garage", equipment_ids=[1], is_default=True))
    await test_db.flush()

    plan = DayPlan(user_id=user.id, name="Push", rounds_target=3)
    test_db.add(plan)
    await test_db.flush()
    test_db.add(PatternGoal(day_plan_id=plan.id, pattern_id=2, required=True, target_sets=3))
    session = TrainingSession(user_id=user.id, day_plan_id=plan.id, state=SessionState.ACTIVE)
    test_db.add(session)
    await test_db.flush()

    result = await anchor_suggestions(test_db, user.id, session.id)
    names = [c["exercise_name"] for g in result["groups"] for c in g["staples"]]
    assert "Profile Test Push Up" in names
```

Import `BODYWEIGHT_EQUIPMENT_ID`, `EquipmentProfile`, `ExercisePatternMap`, `DayPlan` and `PatternGoal` as needed, matching the import style already in that test module.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest tests/test_exercise_helpers.py tests/test_suggestion_service.py -k "bodyweight" -v`
Expected: `test_exercise_helpers.py` fails at import (`ModuleNotFoundError`); the suggestion test fails because the push-up is rejected as "Equipment not in your current profile".

- [ ] **Step 3: Create the helper**

Create `backend/app/services/exercise_helpers.py`:

```python
"""Shared exercise predicates.

Bodyweight identity lives here rather than being open-coded, because it is
load-bearing in two unrelated places (equipment filtering and progression) and
was wrong in both: the catalogue represents bodyweight as an equipment row
named "Bodyweight", not as a NULL primary_equipment_id.
"""

from app.models.exercise import Exercise

# The "Bodyweight" row in the equipment table. Every one of the 209 bodyweight
# exercises in the catalogue points at this id; none use NULL.
BODYWEIGHT_EQUIPMENT_ID = 2


def is_bodyweight(exercise: Exercise) -> bool:
    """True when an exercise carries no external load by default.

    NULL is accepted alongside the Bodyweight row so a hand-created exercise
    that omits equipment is not silently treated as loaded.
    """
    return exercise.primary_equipment_id in (None, BODYWEIGHT_EQUIPMENT_ID)
```

- [ ] **Step 4: Use it in the suggestion service**

Add the import:

```python
from app.services.exercise_helpers import is_bodyweight
```

Replace line 234 in `_filter_cards`:

```python
        is_bw = is_bodyweight(exercise)
        if (
            not is_bw
            and available is not None
            and exercise.primary_equipment_id not in available
        ):
```

and the card field:

```python
                "is_bodyweight": is_bw,
```

Replace the same construct in `_novelty_candidate` (~line 632):

```python
        if (
            not is_bodyweight(exercise)
            and available is not None
            and exercise.primary_equipment_id not in available
        ):
            continue
```

and its card field:

```python
            "is_bodyweight": is_bodyweight(exercise),
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest tests/test_exercise_helpers.py tests/test_suggestion_service.py -v`
Expected: PASS.

- [ ] **Step 6: Correct the CLAUDE.md design decision**

Replace the "Bodyweight Exercises" section under "Design Decisions" so the documented contract matches reality:

```markdown
### Bodyweight Exercises
Bodyweight exercises are identified by `is_bodyweight()` in
`app/services/exercise_helpers.py`, which matches the `Bodyweight` equipment
row (id 2) and also treats `NULL` equipment as bodyweight. All 209 bodyweight
rows in the catalogue use the equipment row; none use `NULL`. An earlier
version of this note claimed `primary_equipment_id = NULL` was the marker,
which no row satisfied, so the rule below silently never applied.

These exercises are **ALWAYS** available regardless of equipment profile
selection. They must never be filtered out for equipment reasons in
recommendations or exercise selection. Use the predicate — do not open-code an
equipment comparison.
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/exercise_helpers.py backend/tests/test_exercise_helpers.py backend/app/services/suggestion_service.py backend/tests/test_suggestion_service.py CLAUDE.md
git commit -m "[SH] fix: detect bodyweight by equipment row, not a NULL that never occurs"
```

---

## Phase C — Suggestion engine

### Task 6: Make slot 3 a protocol-matched finisher

Slot 3 currently returns every neutral-pattern staple plus uncovered goals — 30 ungrouped, unlabelled candidates, half of them isolation (isolation holds 12 of the 24 neutral staples). It should propose a finisher that suits the round it is closing.

Rule: prefer candidates whose protocol matches the round's character. If the anchor is interval work (`AMRAP`/`EMOM`/`TIME`), a finisher should be interval work too; if the anchor is straight sets, the finisher may be straight sets or time-based, but not AMRAP. Within that, keep the existing least-recently-performed ordering and cap each pattern so no single pattern dominates.

Slot 2 is deliberately left pattern-only.

**Files:**
- Modify: `backend/app/services/suggestion_service.py:479-551`
- Test: `backend/tests/test_suggestion_service.py`

**Interfaces:**
- Consumes: `is_bodyweight` from Task 5.
- Produces: `partner_suggestions(db, user_id, session_id, anchor_exercise_id, position)` unchanged in signature; for `position == 3` the returned `candidates` are protocol-compatible and capped per pattern.
- Produces: `PROTOCOL_FAMILY: dict[SetProtocol, str]` and `finisher_is_compatible(anchor: SetProtocol, candidate: SetProtocol) -> bool`, both module-level in `suggestion_service.py`.

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_suggestion_service.py`:

```python
def test_finisher_compatibility_matrix():
    """Interval anchors want interval finishers; straight sets never want AMRAP."""
    assert finisher_is_compatible(SetProtocol.AMRAP, SetProtocol.AMRAP)
    assert finisher_is_compatible(SetProtocol.AMRAP, SetProtocol.TIME)
    assert finisher_is_compatible(SetProtocol.AMRAP, SetProtocol.EMOM)
    assert not finisher_is_compatible(SetProtocol.AMRAP, SetProtocol.REPS)

    assert finisher_is_compatible(SetProtocol.REPS, SetProtocol.REPS)
    assert finisher_is_compatible(SetProtocol.REPS, SetProtocol.TIME)
    assert not finisher_is_compatible(SetProtocol.REPS, SetProtocol.AMRAP)


@pytest.mark.asyncio
async def test_slot_three_excludes_protocol_incompatible_staples(test_db):
    """A straight-set anchor must not be offered an AMRAP variant as a finisher."""
    # Arrange a user with: a REPS anchor in a plan goal, one REPS isolation
    # staple and one AMRAP isolation staple. Follow the arrangement style used
    # by the existing partner tests in this module.
    ...
    result = await partner_suggestions(
        test_db, user.id, session.id, anchor_exercise_id=anchor.id, position=3
    )
    names = [c["exercise_name"] for c in result["candidates"]]
    assert "Test Cable Face Pull" in names
    assert "Test Front Raise (HIIT AMRAP)" not in names


@pytest.mark.asyncio
async def test_slot_three_caps_candidates_per_pattern(test_db):
    """Isolation holds half the neutral pool; it must not fill the whole list."""
    # Arrange 6 isolation staples and 2 core staples, all REPS, anchor REPS.
    ...
    result = await partner_suggestions(
        test_db, user.id, session.id, anchor_exercise_id=anchor.id, position=3
    )
    by_pattern: dict[int, int] = {}
    for c in result["candidates"]:
        by_pattern[c["pattern_id"]] = by_pattern.get(c["pattern_id"], 0) + 1
    assert max(by_pattern.values()) <= FINISHER_PER_PATTERN_CAP
```

Import `finisher_is_compatible`, `FINISHER_PER_PATTERN_CAP`, `partner_suggestions` and `SetProtocol`. Replace each `...` with the arrangement pattern already used by the partner-suggestion tests in this file.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest tests/test_suggestion_service.py -k "finisher or slot_three" -v`
Expected: FAIL — `ImportError` for `finisher_is_compatible` and `FINISHER_PER_PATTERN_CAP`.

- [ ] **Step 3: Add the compatibility rule and the cap**

Near the top of `backend/app/services/suggestion_service.py`, after the existing constants:

```python
from app.models.exercise import DifficultyLevel, Exercise, SetProtocol

# Most candidates any one pattern may contribute to a finisher list. Isolation
# holds 12 of the 24 neutral staples, so without a cap it fills slot 3 outright.
FINISHER_PER_PATTERN_CAP = 4

# Interval work and straight sets are different jobs. AMRAP and EMOM are
# clock-driven; REPS is not. TIME sits in both families - a plank or a carry
# closes a strength round as happily as a conditioning one.
_INTERVAL_PROTOCOLS = {SetProtocol.AMRAP, SetProtocol.EMOM}


def finisher_is_compatible(anchor: SetProtocol, candidate: SetProtocol) -> bool:
    """Whether `candidate` suits closing a round anchored by `anchor`.

    Pattern opposition alone proposed a barbell front squat to finish a
    40-second kettlebell swing AMRAP. Nobody supersets those, so protocol is a
    filter here even though slot 2 deliberately ignores it.
    """
    if candidate is SetProtocol.TIME:
        return True
    if anchor in _INTERVAL_PROTOCOLS or anchor is SetProtocol.TIME:
        return candidate in _INTERVAL_PROTOCOLS
    return candidate is SetProtocol.REPS
```

- [ ] **Step 4: Apply the rule in `partner_suggestions`**

The function already loads `staples` for `target_pattern_ids`. For `position == 3`, filter by protocol before `_filter_cards`, then cap per pattern after sorting. Replace the block that builds `exercises` with:

```python
    staples = await _staples_with_exercises(db, user_id, target_pattern_ids)
    # The anchor is never its own partner. It can reach the target set when it
    # is neutral (its own pattern is in the neutral list at position 3, or is
    # an uncovered goal at position 2), so screen it out explicitly.
    candidate_staples = [s for s in staples if s.exercise_id != anchor_exercise_id]

    if position == 3:
        anchor_protocol = (
            await db.execute(
                select(Exercise.set_protocol).where(Exercise.id == anchor_exercise_id)
            )
        ).scalar_one()
        candidate_staples = [
            s
            for s in candidate_staples
            if finisher_is_compatible(anchor_protocol, s.exercise.set_protocol)
        ]

    exercises = [s.exercise for s in candidate_staples]
    pattern_by_exercise = {s.exercise_id: s.pattern for s in staples}
    staple_ids = {s.exercise_id for s in staples}
    cards, rejected = await _filter_cards(
        db, user_id, exercises, pattern_by_exercise, staple_ids, rep_ranges
    )

    if position == 3:
        cards = _cap_per_pattern(cards, FINISHER_PER_PATTERN_CAP)
```

Add the cap helper beside `_diverse_limit`:

```python
def _cap_per_pattern(cards: list[dict], cap: int) -> list[dict]:
    """At most `cap` cards per pattern, preserving the incoming order.

    `cards` arrives least-recently-performed first, so truncating per pattern
    keeps each pattern's stalest options and drops its freshest.
    """
    taken: dict[int, int] = defaultdict(int)
    kept: list[dict] = []
    for card in cards:
        pattern_id = card["pattern_id"]
        if taken[pattern_id] >= cap:
            continue
        taken[pattern_id] += 1
        kept.append(card)
    return kept
```

Update the module docstring's "Partners" sentence to mention the protocol filter and the cap.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest tests/test_suggestion_service.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/suggestion_service.py backend/tests/test_suggestion_service.py
git commit -m "[SH] feat: slot 3 proposes a protocol-matched finisher"
```

---

### Task 7: Offer off-plan patterns at the bottom of the anchor picker

The anchor picker only lists patterns in the day plan. If the squat rack is taken and the only free station is a pull-up bar, vertical pull is unreachable — which contradicts "swap any slot for whatever station is free".

Plan goals stay on top; everything else the user has staples for goes into a separate trailing group.

**Files:**
- Modify: `backend/app/services/suggestion_service.py:412-476`
- Modify: `backend/app/schemas/suggestion.py:39-41`
- Modify: `web/src/services/suggestions.ts`
- Modify: the component rendering anchor groups (`web/src/components/session/AnchorPicker.tsx`)
- Test: `backend/tests/test_suggestion_service.py`

**Interfaces:**
- Produces: `anchor_suggestions(...)` returns `{"groups": [...], "other_groups": [...], "not_recommended": [...]}`. `other_groups` has the same `AnchorGroup` shape and holds patterns not in the plan's goals, in taxonomy display order, each with `covered: False`.

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_anchor_suggestions_offer_off_plan_patterns_separately(test_db):
    """A staple in a pattern the plan omits must still be reachable."""
    # Arrange: a plan whose only goal is horizontal_push (2), plus an active
    # vertical_pull (3) staple. Follow the arrangement style used by the
    # existing anchor tests in this module.
    ...
    result = await anchor_suggestions(test_db, user.id, session.id)

    goal_patterns = [g["pattern"]["id"] for g in result["groups"]]
    other_patterns = [g["pattern"]["id"] for g in result["other_groups"]]
    assert goal_patterns == [2]
    assert 3 in other_patterns
    # An off-plan pattern must never be duplicated into the goal groups.
    assert 3 not in goal_patterns
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest tests/test_suggestion_service.py -k off_plan -v`
Expected: FAIL with `KeyError: 'other_groups'`.

- [ ] **Step 3: Build the other-groups list**

In `anchor_suggestions`, the goal branch already computes `ordered_patterns` from goals. After the existing `groups` loop, add a second pass over the patterns the user has staples for that no goal covers. Extract the per-pattern card building into a local helper first so both passes share it:

```python
    staples_by_pattern: dict[int, list] = defaultdict(list)
    for staple in staples:
        staples_by_pattern[staple.pattern_id].append(staple)

    all_rejected: list[dict] = []

    async def _build_group(pattern_id: int, covered: bool) -> dict | None:
        pattern_staples = staples_by_pattern.get(pattern_id, [])
        if not pattern_staples:
            return None
        pattern = pattern_staples[0].pattern
        exercises = [s.exercise for s in pattern_staples]
        pattern_by_exercise = {s.exercise_id: s.pattern for s in pattern_staples}
        staple_ids = {s.exercise_id for s in pattern_staples}
        cards, rejected = await _filter_cards(
            db, user_id, exercises, pattern_by_exercise, staple_ids, rep_ranges
        )
        all_rejected.extend(rejected)
        return {
            "pattern": {"id": pattern.id, "slug": pattern.slug, "name": pattern.name},
            "covered": covered,
            "staples": cards,
        }

    groups = []
    for pattern_id, covered in ordered_patterns:
        group = await _build_group(pattern_id, covered)
        if group is not None:
            groups.append(group)
```

Then, still inside `anchor_suggestions`, load the off-plan staples and build the trailing groups. Note this needs a second `_staples_with_exercises` call, because the first was narrowed to goal patterns:

```python
    # Patterns outside the plan. Reachable but deliberately subordinate: the
    # plan is still the point, this is the "the rack is taken" escape hatch.
    other_groups: list[dict] = []
    planned_ids = {pattern_id for pattern_id, _covered in ordered_patterns}
    off_plan = await _staples_with_exercises(db, user_id, None)
    off_plan = [s for s in off_plan if s.pattern_id not in planned_ids]
    if off_plan:
        for staple in off_plan:
            staples_by_pattern[staple.pattern_id].append(staple)
        seen: dict[int, MovementPattern] = {}
        for staple in off_plan:
            seen.setdefault(staple.pattern_id, staple.pattern)
        for pattern_id, _pattern in sorted(
            seen.items(), key=lambda item: (item[1].display_order, item[1].id)
        ):
            group = await _build_group(pattern_id, False)
            if group is not None:
                other_groups.append(group)

    return {
        "groups": groups,
        "other_groups": other_groups,
        "not_recommended": _diverse_limit(all_rejected),
    }
```

In the free-form branch (no goals), every pattern is already offered as a goal group, so set `other_groups = []` there — return the same three keys from both paths.

- [ ] **Step 4: Widen the response schema**

`backend/app/schemas/suggestion.py`:

```python
class AnchorSuggestionsResponse(BaseModel):
    groups: List[AnchorGroup]
    # Patterns the day plan does not ask for, offered below the plan's own
    # groups so a taken station never blocks the session.
    other_groups: List[AnchorGroup] = []
    not_recommended: List[NotRecommendedEntry]
```

- [ ] **Step 5: Render it in the picker**

In `web/src/services/suggestions.ts`, add `other_groups: AnchorGroup[]` to the anchor response type.

In the anchor picker component, after the existing goal groups, render the off-plan groups under a heading that makes their status obvious:

```tsx
      {data.other_groups.length > 0 && (
        <div className="mt-4 pt-3 border-t">
          <div className="text-xs uppercase tracking-wide text-gray-400 mb-2">
            Other patterns — not in this day plan
          </div>
          {data.other_groups.map((group) => (
            <PatternGroup key={group.pattern.id} group={group} onPick={onPick} />
          ))}
        </div>
      )}
```

Reuse whatever component already renders a single goal group; if the existing code maps groups inline, extract that JSX into a `PatternGroup` component first so both lists share it.

- [ ] **Step 6: Verify**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest tests/test_suggestion_service.py tests/test_suggestions_api.py -q`
Run: `cd web && npx tsc --noEmit`

Then by hand: start a session from a plan that omits vertical pull, open the anchor picker, and confirm a vertical pull staple appears under "Other patterns" at the bottom and is selectable.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/suggestion_service.py backend/app/schemas/suggestion.py backend/tests/ web/src/services/suggestions.ts web/src/components/session/
git commit -m "[SH] feat: offer off-plan patterns at the bottom of the anchor picker"
```

---

## Phase D — Web shell, forms and polish

### Task 8: Collapse the nav to a hamburger below `sm`

Measured at a 390px viewport: `document.scrollWidth` is 525px, `Records` ends at x=434 and `Settings` at x=525. Both are off-screen and every page scrolls sideways.

**Files:**
- Modify: `web/src/components/Layout.tsx`

- [ ] **Step 1: Add the menu state and the toggle button**

In the nav component, add state and a button that only exists below `sm`:

```tsx
  const [menuOpen, setMenuOpen] = useState(false)
```

```tsx
        <button
          onClick={() => setMenuOpen((open) => !open)}
          className="sm:hidden p-2 -mr-2 min-h-[44px] min-w-[44px]"
          aria-label="Toggle navigation"
          aria-expanded={menuOpen}
        >
          <span aria-hidden="true">{menuOpen ? '✕' : '☰'}</span>
        </button>
```

- [ ] **Step 2: Make the link list responsive**

Wrap the existing links so they stack when open on a phone and sit inline from `sm` up:

```tsx
        <div
          className={`${menuOpen ? 'flex' : 'hidden'} flex-col gap-1 w-full pb-2 sm:flex sm:flex-row sm:items-center sm:gap-4 sm:w-auto sm:pb-0`}
        >
```

Give the nav container `flex-wrap` so the stacked list drops below the brand rather than overflowing, and close the menu on navigation by adding `onClick={() => setMenuOpen(false)}` to each `Link`.

- [ ] **Step 3: Verify no horizontal overflow**

With the app running, at a 390px viewport confirm `document.documentElement.scrollWidth === document.documentElement.clientWidth` and that Settings is reachable after tapping the hamburger. Confirm the inline nav is unchanged at `sm` and above.

- [ ] **Step 4: Commit**

```bash
git add web/src/components/Layout.tsx
git commit -m "[SH] fix: collapse nav to a hamburger on phone widths"
```

---

### Task 9: Fix the two overlapping headers and the set-count plural

On a phone the day-plan card's action buttons overlap the pattern list, and `Finish Session` overlaps the `Active Session` heading. Both are `flex justify-between` rows whose text side has no `min-w-0` and whose button side can shrink. Set counts also read `1 sets` and `0 sets`.

**Files:**
- Modify: `web/src/pages/DayPlans.tsx:108-129`
- Modify: `web/src/pages/Session.tsx` (the `Active Session` header, and round summary text)
- Modify: `web/src/components/session/EntryCard.tsx:96`

- [ ] **Step 1: Fix the day-plan card row**

Let the card stack on narrow screens and stop the text block from being crushed:

```tsx
        <div key={plan.id} className="bg-white rounded-lg shadow p-4 mb-3 flex flex-col gap-3 sm:flex-row sm:justify-between sm:items-center">
          <div className="min-w-0">
```

and keep the buttons from shrinking:

```tsx
          <div className="flex items-center gap-2 shrink-0">
```

- [ ] **Step 2: Fix the session header the same way**

```tsx
      <div className="flex flex-col gap-3 sm:flex-row sm:justify-between sm:items-center mb-4">
        <h1 className="text-2xl font-bold min-w-0">Active Session</h1>
        <div className="flex items-center gap-2 shrink-0">
```

- [ ] **Step 3: Pluralise set counts**

Add a helper next to `formatSet` in `EntryCard.tsx`:

```tsx
/** "1 set", "2 sets" — a count the user reads mid-session shouldn't be sloppy. */
function setCountLabel(count: number): string {
  return `${count} ${count === 1 ? 'set' : 'sets'}`
}
```

and use it at line 96:

```tsx
        <span className="text-sm text-gray-500 whitespace-nowrap">{setCountLabel(entry.sets.length)}</span>
```

Apply the same helper to the round summary on the session-complete screen in `Session.tsx`, which renders `(1 sets)`. While there, omit entries with zero sets from that summary — a slot picked but never logged should not be reported as part of the round:

```tsx
              {round.entries
                .filter((e) => e.sets.length > 0)
                .map((e) => `${e.exercise_name} (${setCountLabel(e.sets.length)})`)
                .join(' + ')}
```

- [ ] **Step 4: Verify**

Run: `cd web && npx tsc --noEmit`

At 390px confirm the day-plan card stacks with no overlap, the session header stacks, a single logged set reads `1 set`, and a round with an unlogged slot omits it from the completion summary.

- [ ] **Step 5: Commit**

```bash
git add web/src/pages/DayPlans.tsx web/src/pages/Session.tsx web/src/components/session/EntryCard.tsx
git commit -m "[SH] fix: stack card and session headers on phone; pluralise set counts"
```

---

### Task 10: Expose rep ranges and warn about goals with no staples

`PatternGoal.rep_range_min`/`max` exist and drive every progression target, but nothing sets them — they stay NULL and the service defaults to 8-12. Now that progression is protocol-aware, these are the knob that matters.

Separately, the form offers all ten patterns including `carry`, which has zero staples, so a goal can be created that no suggestion can ever satisfy.

**Files:**
- Modify: `web/src/pages/DayPlans.tsx:159-212`
- Modify: `web/src/services/dayPlans.ts` (if `PatternGoal` omits the rep range fields)
- Modify: `web/src/stores/dayPlanStore.ts` (to expose staple counts per pattern)

**Interfaces:**
- Consumes: `GET /api/v1/staples` (already used elsewhere) to count active staples per pattern.

- [ ] **Step 1: Load staple counts per pattern**

In `dayPlanStore`, alongside `patterns`, fetch staples and derive counts. Add to the store's state:

```ts
  stapleCountsByPattern: Record<number, number>
```

populate it in `fetchAll` from the staples endpoint:

```ts
    const staples = await listStaples()
    const stapleCountsByPattern: Record<number, number> = {}
    for (const s of staples) {
      if (s.is_active) {
        stapleCountsByPattern[s.pattern_id] = (stapleCountsByPattern[s.pattern_id] ?? 0) + 1
      }
    }
```

- [ ] **Step 2: Show the count and add rep range inputs**

In the pattern goals list, render the count beside each pattern name and rep range inputs for checked goals:

```tsx
                    <label className="flex items-center gap-2 flex-1 min-w-0">
                      <input type="checkbox" checked={!!goal} onChange={() => toggleGoal(p.id)} />
                      <span className="truncate">{p.name}</span>
                      <span className={count === 0 ? 'text-xs text-amber-600' : 'text-xs text-gray-400'}>
                        ({count} {count === 1 ? 'staple' : 'staples'})
                      </span>
                    </label>
```

where `const count = stapleCountsByPattern[p.id] ?? 0`.

Then, inside the existing `{goal && (<> ... </>)}` block, after the target-sets input, add the range:

```tsx
                        <input
                          type="number"
                          min={1}
                          max={50}
                          value={goal.rep_range_min ?? 8}
                          onChange={(e) => {
                            if (e.target.value === '') return
                            setDraft({
                              ...draft,
                              goals: draft.goals.map((g) =>
                                g.pattern_id === p.id ? { ...g, rep_range_min: Number(e.target.value) } : g
                              ),
                            })
                          }}
                          className="w-14 border rounded-md px-2 py-1 text-sm"
                          title="Rep range min"
                        />
                        <span className="text-xs text-gray-400">-</span>
                        <input
                          type="number"
                          min={1}
                          max={50}
                          value={goal.rep_range_max ?? 12}
                          onChange={(e) => {
                            if (e.target.value === '') return
                            setDraft({
                              ...draft,
                              goals: draft.goals.map((g) =>
                                g.pattern_id === p.id ? { ...g, rep_range_max: Number(e.target.value) } : g
                              ),
                            })
                          }}
                          className="w-14 border rounded-md px-2 py-1 text-sm"
                          title="Rep range max"
                        />
```

Give the row `flex-wrap` so these fit at 390px.

- [ ] **Step 3: Warn on save, but still allow it**

In `submit`, before calling `save`, warn about goals with no staples. It stays allowed on purpose — ticking `carry` before adding carries is a legitimate way to state intent:

```tsx
    const empty = draft.goals
      .filter((g) => (stapleCountsByPattern[g.pattern_id] ?? 0) === 0)
      .map((g) => patterns.find((p) => p.id === g.pattern_id)?.name ?? String(g.pattern_id))
    if (empty.length > 0) {
      const proceed = window.confirm(
        `No staples yet for: ${empty.join(', ')}. ` +
          `These goals can't be filled until you add staples for them. Save anyway?`
      )
      if (!proceed) return
    }
```

- [ ] **Step 4: Validate the range**

Reject an inverted range before saving:

```tsx
    const inverted = draft.goals.find(
      (g) => (g.rep_range_min ?? 8) > (g.rep_range_max ?? 12)
    )
    if (inverted) {
      setLocalError('Rep range minimum cannot exceed the maximum.')
      return
    }
```

- [ ] **Step 5: Verify**

Run: `cd web && npx tsc --noEmit`

By hand: create a plan with `carry` ticked and confirm the `(0 staples)` marker and the save warning; set a pattern's range to 5-8 and confirm a subsequent session's target for that pattern respects it (a set at 8 reps should bump load rather than target 9).

- [ ] **Step 6: Commit**

```bash
git add web/src/pages/DayPlans.tsx web/src/stores/dayPlanStore.ts web/src/services/dayPlans.ts
git commit -m "[SH] feat: expose rep ranges and flag pattern goals with no staples"
```

---

### Task 11: Recategorise the two misfiled staples

`Bodyweight Skater Jump (HIIT AMRAP)` and `Bodyweight Copenhagen Plank` are both mapped to `isolation` (pattern 9). The skater jump is a plyometric conditioning movement; the Copenhagen plank is core.

**Files:**
- Modify: `backend/app/services/pattern_taxonomy.py`
- Test: `backend/tests/test_pattern_taxonomy.py`

- [ ] **Step 1: Find how these exercises are mapped**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest tests/test_pattern_taxonomy.py -q` to confirm the suite is green first, then locate the mapping rules:

```bash
grep -n "Skater\|Copenhagen\|isolation" backend/app/services/pattern_taxonomy.py
```

The map is keyed by exercise name or by a rule over exercise fields; the fix depends on which. If explicit name entries exist, retarget them. If the classification is rule-derived, add explicit overrides — a rule change risks silently moving other exercises.

- [ ] **Step 2: Write the failing test**

```python
@pytest.mark.asyncio
async def test_plyometric_and_core_movements_are_not_isolation(test_db):
    """Two staples were filed under isolation that are conditioning and core."""
    await seed_movement_patterns(test_db)
    await seed_exercise_pattern_map(test_db)

    conditioning = await _pattern_id_for(test_db, "Bodyweight Skater Jump (HIIT AMRAP)")
    core = await _pattern_id_for(test_db, "Bodyweight Copenhagen Plank")
    assert conditioning == 10
    assert core == 7
```

Add `_pattern_id_for` as a local helper that selects `ExercisePatternMap.pattern_id` joined to `Exercise.name`, matching the query style already used in this test module. Use whatever the module's real seeding entry point is named in place of `seed_exercise_pattern_map`.

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest tests/test_pattern_taxonomy.py -k plyometric -v`
Expected: FAIL — both resolve to 9.

- [ ] **Step 4: Add the overrides**

Add explicit name-keyed entries so the two movements resolve correctly, with a comment explaining why they are exceptions rather than a rule change.

- [ ] **Step 5: Re-seed and verify against the dev database**

The pattern seed is not run by app startup, Alembic, or CI, so it must be run by hand:

```bash
cd backend && ./venv/Scripts/python.exe -m scripts.seed_patterns
```

Then confirm the two rows moved:

```bash
docker exec slotfit-db psql -U postgres -d slotfit -c "SELECT e.name, m.pattern_id FROM exercises e JOIN exercise_pattern_map m ON m.exercise_id = e.id WHERE e.name IN ('Bodyweight Skater Jump (HIIT AMRAP)','Bodyweight Copenhagen Plank');"
```

Expected: `10` and `7` respectively.

Note: existing `staple_exercises` rows carry their own `pattern_id`, denormalised at creation. Re-seeding the map does **not** move an existing staple. Check whether the two staples need updating too:

```bash
docker exec slotfit-db psql -U postgres -d slotfit -c "SELECT s.id, e.name, s.pattern_id FROM staple_exercises s JOIN exercises e ON e.id = s.exercise_id WHERE e.name IN ('Bodyweight Skater Jump (HIIT AMRAP)','Bodyweight Copenhagen Plank');"
```

If they still read 9, update those two rows to 10 and 7. Do not bulk-resync staple patterns from the map — `RoundEntry.pattern_id` is deliberately denormalised so history keeps its original meaning, and staples follow the same principle.

- [ ] **Step 6: Run the full suite and commit**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest -q`

```bash
git add backend/app/services/pattern_taxonomy.py backend/tests/test_pattern_taxonomy.py
git commit -m "[SH] fix: file skater jump as conditioning and copenhagen plank as core"
```

---

## Final Verification

- [ ] **Full backend suite**

Run: `cd backend && ./venv/Scripts/python.exe -m pytest -q`
Expected: all green.

- [ ] **Typecheck**

Run: `cd web && npx tsc --noEmit`
Expected: exactly the seven pre-existing unused-variable errors in unrelated files, no new ones.

- [ ] **Drive the flow by hand**

Start Docker, backend and web per `CLAUDE.md`. Open `http://localhost:3000` and set the device identity first:

```js
localStorage.setItem('slotfit_device_id','setup-verify-0001')
```

Then walk the same path that produced these findings and confirm each fix:

1. A plain lift shows weight + reps; an AMRAP shows weight + reps + seconds; the rower shows seconds only.
2. Log 2x15 on a bodyweight movement, finish the session, start another: its target reads 16, not 12.
3. Log an AMRAP at a given load, finish, restart: the target reads `Beat <reps> @ <same load>` — the load has not moved.
4. Log the rower in seconds only, finish, restart: its card reads `Last: 2x300s` with no target and no `0@bw`.
5. Anchor a round with a straight-set lift and open slot 3: no AMRAP variants offered, no pattern contributing more than four candidates.
6. Anchor a round with an AMRAP and open slot 3: only interval and time-based work offered.
7. Open the anchor picker on a plan omitting vertical pull: a vertical pull staple appears under "Other patterns".
8. At 390px: no horizontal page scroll, Settings reachable via the hamburger, no overlapping buttons on the day-plan card or session header.

- [ ] **Confirm no regression in the known-benign list**

These were known before this work and are expected to remain: `/sessions/active` returning 404 several times per page load is benign; `carry` still has no staples.

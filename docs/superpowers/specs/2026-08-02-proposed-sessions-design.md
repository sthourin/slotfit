# Proposed Sessions — Design

Date: 2026-08-02
Status: Approved (design), pending implementation plan

## Motivation

Starting a session today opens an empty round and an anchor picker listing every
staple in the pattern. Nothing is suggested; the whole workout is assembled tap
by tap. Driving a real session against the seeded pool confirmed the cost: even
knowing the design intimately, the first decision is "which of these 57 do I
start with", with no answer offered.

The user's actual want is a workout proposed on arrival, which he then adjusts
for whatever is free or whatever he feels like that day. Not a blank slate, and
not a fixed program either.

## A Correction to the Design Record

CLAUDE.md currently records this decision:

> Nothing is pre-filled from a previous workout, and there is no "save as new
> routine" prompt: the session is composed on the spot, so there is no template
> to diverge from.

That wording overshot the intent. What it was protecting against is **blindly
repeating the last workout** — copying last Tuesday forward, which is how the
retired routine-template model behaved. It was never meant to require starting
from nothing.

The actual intent, stated correctly:

> Every session is **informed by many previous workouts** without being a copy
> of any one of them. Proposals come from evidence accumulated across history —
> which staples are least recently performed, which patterns are under-covered,
> what progression the logged sets support — never from replaying the most
> recent session.

This spec implements that intent. CLAUDE.md's "Pattern-Based Dynamic Sessions"
section is updated to match, because the old wording would otherwise read as a
prohibition on the feature being built here.

## Decisions Made During Brainstorming

1. **The whole session is proposed up front**, all rounds visible, rather than
   one round at a time or merely pre-selecting an anchor. Seeing the workout is
   the point; a single pre-picked anchor would not have answered the request.
2. **Unstarted rounds re-propose as the session progresses**, so coverage stays
   honest after swaps and logged sets.
3. **No upfront equipment step.** Availability is handled by swapping a slot
   when a station is taken. A "what's busy today" gate would sit between the
   user and starting, and gym availability changes minute to minute anyway.
4. **The proposal is computed, never stored.**

## Why the Proposal Is Not Persisted

`GET /sessions/{id}/proposal` returns a structure and writes nothing. Entries
are still created through the existing `POST /rounds/{round_id}/entries` when a
round actually starts.

Three consequences, all wanted:

- Pattern coverage keeps counting only what was performed. Persisting proposed
  entries would make the coverage chips read 3/3 before a single set was logged.
- Re-proposal needs no invalidation logic. The endpoint recomputes from current
  session state on every call, so "re-propose as you go" is the default
  behaviour rather than a feature.
- An abandoned session leaves no phantom rounds in history.

## Proposal Algorithm

For each round from 1 to `DayPlan.rounds_target`:

1. **Anchor** — from the most under-covered required pattern goal, measured as
   sets logged against `PatternGoal.target_sets`. Ties break toward the pattern
   with the earliest `display_order`. Within the pattern, the least recently
   performed active staple wins, which is the rotation rule
   `anchor_suggestions` already applies.
2. **Partner** — a staple from the anchor pattern's `opposite_pattern_id`. When
   the pattern has no opposite (`core`, `carry`, `isolation`, `conditioning`),
   the slot takes the next under-covered required pattern instead.
3. **Third slot** — only when an uncovered required goal remains after the first
   two. Rounds are otherwise two entries, matching how the round entry
   `position` field is already used (1-3).

No exercise appears twice in one proposal. Every filter the suggestion engine
applies today still applies: blacklist, injury restrictions, weekly volume
limit, equipment profile, and the novelty rules.

**Warm-up.** `DayPlan.warmup_preferences` holds an ordered list of exercise ids,
and `Session.tsx` already resolves them client-side into a list of warm-up
options for the user to choose from. The proposal therefore does **not** need to
introduce warm-up handling; it only needs to name a default. It reports the
first entry in the list whose exercise still exists and passes the filters, and
the existing client list remains available for choosing a different one. Where
`warmup_preferences` is empty, no warm-up is proposed and the client behaves as
it does today.

## Pinning

The failure mode this avoids: swapping round 1 causes rounds 2 and 3 to
recompute, discarding swaps already made there. That would be worse than a blank
slate, because the user's explicit choices would evaporate.

Any slot the user chooses explicitly becomes **pinned**. The client sends pinned
slots back with the proposal request; re-proposal fills only unpinned slots in
unstarted rounds. Rounds already started are never altered.

Pins live in client state for the session's duration. They are not persisted:
a pin is a statement about today's gym, not a lasting preference. A user who
wants a choice to persist marks the exercise a staple, which already exists.

## Empty Patterns

A pattern with no active staples — `carry`, in the current seeded pool — renders
the slot as an explicit "no staples for carry yet" prompt rather than being
skipped silently. A goal that cannot be met should be visible, because the fix
is one tap away in the exercise browser and invisible otherwise.

## API

`GET /sessions/{session_id}/proposal`

Query parameter `pinned` carries zero or more `round:position:exercise_id`
triples. Response:

```json
{
  "warmup": {"exercise_id": 42, "exercise_name": "Rowing Machine",
             "set_protocol": "time", "default_time_seconds": 600},
  "rounds": [
    {"order": 1, "started": false, "entries": [
      {"position": 1, "pattern_slug": "horizontal_pull",
       "exercise_id": 118, "exercise_name": "Cable V Grip Seated Low Row",
       "set_protocol": "reps", "default_time_seconds": null,
       "pinned": false, "reason": "least recently performed horizontal pull"},
      {"position": 2, "pattern_slug": "horizontal_push",
       "exercise_id": 245, "exercise_name": "Double Dumbbell Incline Bench Press",
       "set_protocol": "reps", "default_time_seconds": null,
       "pinned": false, "reason": "opposite of horizontal pull"}
    ]},
    {"order": 2, "started": false, "entries": [...]}
  ],
  "unmet": [{"pattern_slug": "carry", "reason": "no active staples"}]
}
```

`set_protocol` and `default_time_seconds` ride along so the client can render
the right log fields without a second lookup, matching what `RoundEntryResponse`
already carries.

`reason` is a short human string. A proposal the user cannot interrogate is a
black box, and the whole point is that he adjusts it — which is easier when the
app says why it picked something.

## UI

The session page opens with the proposal rendered as read-ahead rounds. Round 1
is actionable; later rounds are visible but dimmed until reached. Each slot
carries a swap control opening the existing picker scoped to that slot's
pattern, and choosing from it pins the slot.

Starting a round materializes exactly that round's entries via the existing
endpoint, then refetches the proposal so later rounds reflect what was logged.

## Error Handling

| Condition | Behavior |
| --- | --- |
| Session has no day plan | Propose from the user's staples across all patterns with active staples, matching `anchor_suggestions`' existing free-form fallback |
| Day plan has no pattern goals | Same free-form fallback |
| A pattern goal has no active staples | Slot reported in `unmet`, not silently dropped |
| No staples at all | Empty `rounds`, and `unmet` lists every goal, so the UI can point at the exercise browser |
| A pinned exercise no longer exists or is now blacklisted | Pin ignored, slot re-proposed, and the substitution noted in `reason` |

## Testing

- Anchor selection picks the most under-covered required pattern, and the least
  recently performed staple within it.
- Partner is the anchor pattern's opposite; a pattern with no opposite falls
  through to the next uncovered goal instead of producing an empty slot.
- No exercise appears twice in one proposal.
- Pins survive re-proposal, and an unpinned slot in the same round does not.
- A started round is never re-proposed.
- A pattern with no staples appears in `unmet` rather than being skipped.
- A pinned exercise that has since been blacklisted is replaced, not honoured.
- Sessions with no day plan fall back to the free-form pattern list.
- The proposal writes nothing: session, round, and entry counts are unchanged
  after a call.

## Non-Goals

**Persisted proposals.** No table, no accept step that materializes all rounds
at once. Rounds are created as they are started, exactly as today.

**Equipment availability input.** No "what's busy" screen. Swapping covers it.

**Progression targets inside the proposal.** The proposal names exercises; the
target on each card still comes from `compute_entry_target` once the entry
exists. Time-based progression remains broken for AMRAP work regardless — that
is the separate spec 3, and this design neither fixes nor worsens it.

**Cross-session learning.** Proposals read history through the existing rotation
and coverage rules. No new model of user preference is introduced.

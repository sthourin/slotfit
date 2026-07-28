# SlotFit Web Feature Matrix

Date started: 2026-07-27
Environment: local dev, backend on slotfit_e2e database (dev seeding verified on slotfit)

Status values: Working, Broken, Missing, Untested. Severity: P0, P1, P2 (see Phase 0 plan rubric).

## Environment Notes

- Exercise import yields 3,240 exercises from 3,242 CSV rows (docs claim 3,244; 2-row gap unexplained, P2).
- API 307-redirects collection routes without trailing slash (e.g., `/api/v1/exercises` -> `/exercises/`).
- Device user auto-creation via `X-Device-ID` verified working at the API level.
- `.env.e2e` keeps AI keys blank so recommendations exercise the rule-based fallback provider deterministically.

## Flows

| Flow | Status | Severity | Notes |
| --- | --- | --- | --- |
| App shell and navigation | Working | - | e2e: app-shell.spec.ts (nav links, device id generation) |
| Settings: device user auto-created | Working | - | e2e: settings.spec.ts; profile renders for device user |
| Settings: edit display name persists | Working | - | e2e: settings.spec.ts; persists across reload |
| Settings: equipment profile CRUD | Working | - | API-level: create/rename/set-default/delete verified; UI modal automation deferred (P2) |
| Settings: injuries add/heal | Working | - | API-level: 12 injury types listed, add + mark-healed verified; UI modal automation deferred (P2) |
| Exercise browser: list and search | Working | - | e2e: exercise-browser.spec.ts; list renders, search narrows to Bench Press |
| Routine designer: create routine with slots | Working | - | e2e: routine-designer.spec.ts; create + add slot |
| Routine designer: save to backend | Working | - | e2e: routine-designer.spec.ts; POST /routines 2xx, ID displayed |
| Workout start: select routine and equipment profile | Working | - | e2e: workout-critical-path.spec.ts; routine selection + start verified (equipment profile defaulting untested with no profile present) |
| Workout start: quick-fill / copy last workout | Untested | - | Modal flows not yet automated; backlog |
| Active workout: set logging | Working | - | e2e: add set via SetTracker verified |
| Active workout: rest timer | Untested | - | Renders during in_progress slot; behavior not asserted; backlog |
| Active workout: slot navigation and skip | Untested | - | Test routine has a single slot; multi-slot navigation not exercised; backlog |
| Active workout: exercise selection + AI recommendations + Why Not | Working | - | e2e: search tab select verified; recommendations + Why Not (9 entries, diverse reasons) verified via API after P0 fix (see below) |
| Workout completion: summary, volume, PR detection | Working | - | e2e: complete → 2xx → "Workout Complete" summary modal; PR detection untested (no weights logged); backlog |
| History: list and detail | Untested | - | |
| Analytics: charts render with data | Untested | - | |
| Personal records page | Untested | - | |

## CLAUDE.md Design Decisions

| Decision | Status | Notes |
| --- | --- | --- |
| Workout resume banner on app load | Untested | |
| Save-as-new-routine prompt at completion | Untested | |
| Bodyweight exercises always available | Untested | |
| Injury filtering with not-medical-advice disclaimer | Untested | |

## Defect Backlog (deferred to Phase 1)

| Defect | Severity | Flow | Notes |
| --- | --- | --- | --- |
| Exercise count discrepancy (3,240 imported vs 3,244 documented) | P2 | Data seeding | Verify CSV row expectations |
| Quick-fill / copy-last-workout modals unautomated | P2 | Workout start | Add e2e coverage in Phase 1 |
| Rest timer behavior unasserted | P2 | Active workout | Add e2e coverage in Phase 1 |
| Multi-slot navigation/skip unautomated | P2 | Active workout | Add multi-slot e2e routine in Phase 1 |
| PR detection untested | P2 | Workout completion | Log weighted sets in e2e and assert PR notification in Phase 1 |

## Fixed During Phase 0

| Defect | Severity | Fix |
| --- | --- | --- |
| Recommendations endpoint 500s (KeyError 'workout_exercises') for any user with a completed workout in the last 30 days | P0 | Renamed relationship access to 'exercises' in recommendations.py; regression test added (test_get_recommendations_with_completed_workout_history) |

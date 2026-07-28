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
| App shell and navigation | Untested | - | |
| Settings: device user auto-created | Untested | - | Working at API level; UI untested |
| Settings: edit display name persists | Untested | - | |
| Settings: equipment profile CRUD | Untested | - | |
| Settings: injuries add/heal | Untested | - | |
| Exercise browser: list and search | Untested | - | |
| Routine designer: create routine with slots | Untested | - | |
| Routine designer: save to backend | Untested | - | |
| Workout start: select routine and equipment profile | Untested | - | |
| Workout start: quick-fill / copy last workout | Untested | - | |
| Active workout: set logging | Untested | - | |
| Active workout: rest timer | Untested | - | |
| Active workout: slot navigation and skip | Untested | - | |
| Active workout: exercise selection + AI recommendations + Why Not | Untested | - | |
| Workout completion: summary, volume, PR detection | Untested | - | |
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

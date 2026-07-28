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
| History: list and detail | Working | - | e2e: read-pages.spec.ts; renders without console errors (detail view automation deferred, P2) |
| Analytics: charts render with data | Working | - | e2e: read-pages.spec.ts; page renders with routine data after SlotPerformance fix (see Fixed) |
| Personal records page | Working | - | e2e: read-pages.spec.ts; renders without console errors |

## CLAUDE.md Design Decisions

| Decision | Status | Notes |
| --- | --- | --- |
| Workout resume banner on app load | Missing | No banner UI exists. Foundation present: workoutStore persists draft/active workouts to localStorage. Phase 1 backlog (P1) |
| Save-as-new-routine prompt at completion | Missing | No trace of the Save as New / Update Original / Don't Save prompt in web/src. Phase 1 backlog (P1) |
| Bodyweight exercises always available | Broken | Rule is implemented (fallback_provider checks primary_equipment_id IS NULL) but matches ZERO exercises: the CSV import assigns bodyweight exercises equipment id 2 ("Bodyweight", 201 exercises). Bodyweight is filtered out unless the profile includes that equipment. Phase 1 backlog (P1): either treat "Bodyweight" equipment as always available or import those rows with NULL equipment |
| Injury filtering with not-medical-advice disclaimer | Working | Disclaimer present in AddInjuryModal (with acknowledgment checkbox) and InjuriesSection banner; injury CRUD verified at API level (Task 4) |

## Defect Backlog (deferred to Phase 1)

| Defect | Severity | Flow | Notes |
| --- | --- | --- | --- |
| Exercise count discrepancy (3,240 imported vs 3,244 documented) | P2 | Data seeding | Verify CSV row expectations |
| Quick-fill / copy-last-workout modals unautomated | P2 | Workout start | Add e2e coverage in Phase 1 |
| Rest timer behavior unasserted | P2 | Active workout | Add e2e coverage in Phase 1 |
| Multi-slot navigation/skip unautomated | P2 | Active workout | Add multi-slot e2e routine in Phase 1 |
| PR detection untested | P2 | Workout completion | Log weighted sets in e2e and assert PR notification in Phase 1 |
| npm run build fails: 4 pre-existing TS errors (ProgressionChart, VolumeChart recharts Formatter typing; RoutineHeader select value typing) | P1 | Web build | Blocks production deploy; must fix in Phase 1 before Phase 3 |
| Bodyweight-always-available rule matches zero exercises (data uses "Bodyweight" equipment id 2, not NULL) | P1 | Recommendations | Decide fix approach in Phase 1: special-case the Bodyweight equipment or import with NULL |
| Workout resume banner missing (CLAUDE.md design decision) | P1 | App shell | Store persistence exists; add banner UI in Phase 1 |
| Save-as-new-routine prompt missing (CLAUDE.md design decision) | P1 | Workout completion | Implement in Phase 1 |
| Completed workouts show 0 sets / 0/0 exercises in History; sets logged in UI may never persist to backend | P1 | Workout data | Investigate workoutStore sync on complete; copy-last-workout and pre-fill depend on this (ui-design-review.md item 3) |
| Route changes do not reset scroll; nav can be hidden after navigation | P1 | App shell | Add ScrollRestoration (ui-design-review.md item 2) |
| Timestamps render in UTC with raw formatting | P2 | History | Localize + date-fns formatting (ui-design-review.md item 4) |
| Slot-performance API returns most_used_exercise_id but no exercise name; UI shows "Exercise #id" | P2 | Analytics | Backend should join exercise name |
| e2e database accumulates data across runs (duplicate E2E Push Day routines) | P2 | Test infra | Add Playwright global setup to reset slotfit_e2e schema per run |

## Fixed During Phase 0

| Defect | Severity | Fix |
| --- | --- | --- |
| Recommendations endpoint 500s (KeyError 'workout_exercises') for any user with a completed workout in the last 30 days | P0 | Renamed relationship access to 'exercises' in recommendations.py; regression test added (test_get_recommendations_with_completed_workout_history) |
| Analytics page crashes blank (undefined.toFixed in SlotPerformance) for any user with a routine | P0 | Frontend SlotPerformanceMetric interface matched to actual API fields (avg_sets_per_workout, total_workouts); numeric guards added; covered by read-pages.spec.ts |

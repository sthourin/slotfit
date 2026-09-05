# SlotFit Web and Mobile Build-Out Design

Date: 2026-07-26
Status: Approved

## Summary

SlotFit's backend is MVP-complete (all Phase 1-2 tasks in TASKS.md done, 51 tests passing, device-ID user system, AI recommendations with Claude, Gemini, and rule-based fallback). The web app is substantially built - all workout execution, history, analytics, and personal records pages exist and are routed - despite TASKS.md marking them "Not Started." A native Kotlin Android scaffold exists but will be retired.

This design covers the path from the current state to a production web app and a React Native (Expo) Android app, in six sequential phases. Each phase ships something usable.

## Decisions

These were made explicitly during design review:

1. Mobile stack: React Native with Expo (custom dev build). The Kotlin scaffold in `android/` is retired. iOS is architected for but not shipped in this plan (Android first, iOS fast follow).
2. Authentication is in scope: JWT email/password auth with device-to-account linking, added before mobile launch. Anonymous device-ID mode continues to work.
3. Sequencing: finish and deploy the web app to production before starting mobile.
4. Hosting: Railway or Render (managed FastAPI + PostgreSQL + static web hosting).
5. BLE heart-rate monitoring (Polar H10) is a core feature of mobile v1, not a follow-up.
6. Offline depth for mobile v1: workout execution works fully offline with outbound sync of completed workouts; exercise database and routines cached locally. No bidirectional sync.

## Phase 0: Ground Truth and Web Verification

TASKS.md is stale relative to the codebase. Before new feature work:

- Run backend and web locally; exercise every flow end-to-end: routine design, workout start (quick-fill, copy-last-workout), active workout (set logging, rest timer, slot navigation, exercise selection with AI recommendations and Why Not), workout completion (summary, PR detection), history, analytics, personal records, settings (profile, equipment profiles, injuries).
- Build a Playwright smoke suite covering the critical paths above. This suite becomes the regression gate for all later phases.
- Fix defects found during verification.
- Verify the design decisions recorded in CLAUDE.md are implemented: workout resume banner, save-as-new-routine prompt at completion, bodyweight exercises always available, injury-aware filtering with disclaimer.
- Reconcile TASKS.md statuses to reality.

Deliverables: verified feature matrix; green Playwright smoke suite; corrected TASKS.md.

## Phase 1: Web Polish and Mobile-Responsive

The current layout is desktop-oriented (horizontal top nav, wide grids).

- Responsive layouts for every page. Navigation collapses to a mobile pattern (bottom nav or hamburger). The active workout screen must be usable one-handed on a phone: large touch targets for set logging, rest timer, and slot navigation.
- Consistent loading, error, and empty states; toast feedback where actions currently fail silently.
- PWA baseline: manifest, icons, service worker for app-shell caching so the app is installable from the browser. Full offline behavior is not required here; it arrives with the mobile app.

Deliverables: all pages usable on a phone browser; Lighthouse PWA installability passes; smoke suite still green.

## Phase 2: Accounts and Auth

The backend was architected for this swap: the `users` table already has nullable `email` and `hashed_password`, and all user-scoped endpoints resolve identity through the `get_current_user` dependency.

- Backend: password hashing (bcrypt/argon2), JWT access + refresh tokens, endpoints for signup, login, refresh, and logout. `get_current_user` accepts either a Bearer JWT or the legacy `X-Device-ID` header during the transition; JWT wins when both are present.
- Device-to-account linking: when a client with an existing device-ID user signs up or logs in, that device user's data is claimed by (merged into) the account, so nothing is lost. Linking is explicit in the API (the client sends its device ID at signup/login).
- Web: signup/login UI, session persistence, token refresh handling. Anonymous mode remains the default first-run experience; the UI prompts account creation as the way to sync across devices.
- Hardening: rate limiting on auth endpoints, CORS restricted to known origins. Password reset via email is deferred to a follow-up (requires an email provider); the UI states this limitation at signup.

Deliverables: a user can start anonymous on one browser, create an account, log in on a second browser, and see the same data. Auth test coverage added to pytest suite.

## Phase 3: Production Deployment

- Railway is the default platform: FastAPI service, managed PostgreSQL, static hosting for the web build. Fall back to Render only if a concrete blocker appears during setup.
- Alembic migrations run on deploy. Seed scripts for the exercise CSV (3,244 exercises) and injury data run once per environment.
- CI via GitHub Actions: pytest, web build, and Playwright smoke on pull requests; auto-deploy on merge to main.
- Operations baseline: health endpoint wired to platform checks, Sentry (free tier) for backend and web, automated database backups, environment-variable config audit (no secrets in repo).

Deliverables: public production URL; CI pipeline green; documented deploy/rollback procedure.

## Phase 4: Shared API Client Extraction

Done only now, when a second client is imminent:

- Extract TypeScript API types and endpoint functions from `web/src/services/` into a shared workspace package (npm workspaces) consumed by web and, next phase, mobile.
- Scope is deliberately thin: types, fetch wrapper (auth header injection, error normalization), endpoint functions. No UI, no state management, no broader monorepo restructuring.

Deliverables: web app consumes the shared package with no behavior change; smoke suite green.

## Phase 5: Mobile v1 (Android, React Native + Expo)

Stack: Expo with a custom development build (required for BLE), TypeScript, Zustand, expo-router for navigation, the shared API client, expo-sqlite for local storage.

Do a BLE spike first: pair a Polar H10 and stream heart rate in a throwaway screen before committing to the full build, since this is the highest-risk dependency.

- Offline model: local SQLite caches the exercise database, muscle groups, equipment, routines, and equipment profiles (refreshed when online). Workout execution reads and writes only local storage, so a full workout works with zero connectivity. Completed workouts enter an outbound sync queue keyed by client-generated UUIDs; a new idempotent backend sync endpoint upserts them. Outbound-only sync keeps conflict handling trivial (server data is never edited from two places).
- BLE heart rate: Polar H10 via react-native-ble-plx. Pairing flow, live heart rate and zone display during the active workout, HR summary (avg/max, time in zones) on the completion screen. Backend gains heart-rate summary models and endpoints (per the original plan's deferred tables). ~~Raw 1Hz time series is kept locally only until summarized, then dropped.~~ **Superseded 2026-08-29:** the raw series is uploaded and kept server-side; dropping it would foreclose HR-recovery learning, session charts, and recomputing zones after a max-HR correction. Summaries became a rebuildable cache over raw rather than the only copy. See `docs/superpowers/plans/2026-08-29-heart-rate-reparenting.md`.
- Screens mirror the validated web flows adapted to touch: start flow, active workout (set tracker, rest timer, slot navigation), exercise selection with AI recommendations and Why Not, history, personal records, settings, auth/link-device.
- Housekeeping: archive or delete the Kotlin `android/` scaffold; document the decision in its place.
- Release: EAS build, Play Store internal testing track, then production.

Deliverables: installable Android app; a full workout completed in airplane mode syncs correctly when connectivity returns; live Polar H10 heart rate during a workout.

## Phase 6: iOS Fast Follow

Out of detailed scope. Constraints honored throughout Phase 5: no Android-only native modules without an iOS equivalent, react-native-ble-plx supports iOS, EAS handles iOS builds without a local Mac. Shipping iOS is a follow-on plan.

## Testing Strategy

- Backend: existing pytest suite (51 tests) extended with auth, linking, sync, and heart-rate endpoint tests.
- Web: Playwright smoke suite (Phase 0) as the primary regression gate; targeted component tests only where logic is dense (workout store, set tracker).
- Mobile: unit tests for sync queue and stores; manual test checklist on physical devices for BLE and offline; store-track rollout provides staged exposure.

## Risks and Mitigations

- BLE on Expo requires custom dev builds and physical devices; mitigated by the Phase 5 spike before full commitment.
- Auth migration could strand device data; mitigated by explicit device-to-account linking and a transition period accepting both identity headers.
- Sync conflicts; mitigated by outbound-only sync with client UUIDs and idempotent upserts.
- Stale TASKS.md hides unknown gaps; mitigated by Phase 0 verification before any scheduling assumptions.

## Out of Scope

- iOS release (Phase 6 placeholder only)
- Bidirectional/offline-first sync for routine editing and analytics
- Push notifications, Android Health / Health Connect integration
- PubMed injury research integration and free-text injury input (CLAUDE.md future phases)
- Payments, social features, multi-user coaching

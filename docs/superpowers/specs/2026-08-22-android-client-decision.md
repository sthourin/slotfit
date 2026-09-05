# SlotFit Android Client: Restart Decision and Plan

Date: 2026-08-22
Status: Approved (revisits Phase 5 of `2026-07-26-web-mobile-buildout-design.md`)

## Verdict

Restart. There is nothing in `android/` to continue, and the stack decision
recorded in the July design deserves to be re-made, because the domain it was
written against no longer exists.

## Decisions taken

Confirmed 2026-08-22, and they shape every phase below:

1. **Public distribution is the destination.** Not a personal-tool-forever
   build. Multi-user concerns are deferred, never designed out.
2. **Private first, on a tailnet.** A spare laptop stays persistently connected
   and hosts the API and database over Tailscale. Auth is deferred until the
   app leaves the tailnet.
3. **The Kotlin scaffold is deleted**, not archived.

Deferring auth is safe here only because the identity seam already exists:
every user-scoped endpoint resolves through `get_current_user` in
`backend/app/core/deps.py`, and `users` already carries nullable `email` and
`hashed_password`. The July design's device-to-account linking plugs into that
seam without touching endpoint code. What must not happen in the meantime is
new code that reaches around the seam — see "Keeping the public door open".

## What is actually in `android/`

Seventeen files, all from commit `a2c5bb4` ("Initial commit"), untouched since.
`git log -- android` returns exactly one commit.

| Area | What is there |
| --- | --- |
| `MainActivity.kt` | 10 lines: `setContentView(R.layout.activity_main)` |
| `activity_main.xml` | one centered `TextView`: "SlotFit Android App - Coming Soon" |
| `data/__init__.kt` | a package declaration and two comment lines. No entities, no DAOs, no database |
| `bluetooth/__init__.kt` | a package declaration and two comment lines. No BLE code |
| `ui/__init__.kt` | a package declaration and two comment lines |
| gradle, manifest, res | boilerplate from the new-project template |

The `__init__.kt` files are Python habits transplanted into Kotlin — Kotlin has
no package-initializer file, so those three files exist only to make the folders
non-empty. That is a fair summary of the whole module: it is a directory
structure, not an implementation.

### It does not build

Four independent blockers, none of them touched since the initial commit:

1. `gradle/wrapper/gradle-wrapper.jar` is absent — only the `.properties` file
   was committed, so `gradlew` cannot bootstrap.
2. There is no POSIX `gradlew`, only `gradlew.bat`.
3. `AndroidManifest.xml` references `@mipmap/ic_launcher` and
   `@mipmap/ic_launcher_round`; `res/` contains only `layout/` and `values/`.
   Resource linking fails.
4. `app/build.gradle` names `proguard-rules.pro`, which does not exist.

Beyond that the toolchain has aged: AGP 8.13.2 against Kotlin 1.9.20, `kapt`
for Room where KSP is now standard, and `jvmTarget = '1.8'`.

### Its stated purpose is retired

`android/README.md` advertises "Slot-based workout routines", "Slot navigation
(skip, re-order, return to skipped slots)" and "Superset support (shared rest
timer)". Routine templates with pre-planned muscle-group slots were retired on
2026-07-28 in favour of pattern-based dynamic sessions (see CLAUDE.md and
`specs/2026-07-28-pattern-based-dynamic-sessions-design.md`). Even the
scaffold's README describes a product that no longer exists — so there is no
"continue" available, only a rewrite against the current domain.

## What the July design decided, and what has changed since

`specs/2026-07-26-web-mobile-buildout-design.md` (approved) already reached the
same conclusion about the scaffold — "A native Kotlin Android scaffold exists
but will be retired" — and chose React Native + Expo, gated behind five
sequential phases. Three things have changed since it was written:

- **The domain pivoted.** Its Phase 5 screen list ("start flow, active workout
  with set tracker, rest timer, slot navigation") names retired concepts. The
  mobile screens would have to be re-derived from the pattern-session flow
  regardless of stack.
- **The web app kept moving.** Six more plans landed (pattern sessions, set
  protocols, Hevy import, bodyweight leverage, session-flow fixes, proposed
  sessions). `web/src/services/` is now 19 modules; the Phase 4 "deliberately
  thin" extraction is no longer thin.
- **The verification baseline went stale.** `docs/verification/feature-matrix.md`
  and `ui-design-review.md` are written against Routine Designer / Workout Start
  / Active Workout pages that no longer exist.

## Prerequisite status, measured today

The July design gates mobile behind Phases 0–4. Where those actually stand:

| Phase | Status | Evidence |
| --- | --- | --- |
| 0 — Verification baseline | Done, now stale | feature matrix + `ui-design-review.md` exist; 9 Playwright specs in `web/e2e/`; 281 backend tests pass (6m59s, 68% coverage) |
| 1 — Web polish / responsive / PWA | Partial | Phone nav collapse landed (`web/src/App.tsx`), `ResumeBanner` exists, session layout fixed 2026-08-11. **No PWA at all**: `web/public/` is empty, no manifest, no service worker, favicon is still `vite.svg` |
| 1 — blocker | **Broken** | `npm run build` fails with 7 TypeScript errors (2 real recharts `Formatter` typings in `ProgressionChart`/`VolumeChart`, 5 unused-symbol errors). Flagged P1 during Phase 0 and never fixed. Nothing can be deployed until this is green |
| 2 — Auth | Not started | `backend/app/core/deps.py` is still `X-Device-ID` only; `users.email` / `users.hashed_password` exist and are unused |
| 3 — Deploy / CI | Not started | no `.github/`, no API Dockerfile, no hosting config. Only `backend/docker-compose.yml` (local Postgres) |
| 4 — Shared API client | Not started | no npm workspace; 19 service modules in `web/src/services/` |
| 5 — Mobile | Not started | the dead scaffold above |

### Two findings that matter more than the stack choice

**Session logging has no offline path.** `web/src/stores/sessionStore.ts` (139
lines) is purely server-backed: `start`, `addRound`, `addEntry`, `logSet` and
`complete` are each a single `await` on the API with a `catch` that records an
error. No `persist` middleware, no local queue, no optimistic write. A dropped
connection mid-session stalls the workout. For an app whose entire premise is
being used live in a gym — frequently a concrete basement with no signal — this
is the real blocker to phone use, and no native shell fixes it. It is
client-architecture work that has to happen in whichever codebase ships.

**Heart-rate tables exist but are wired to the retired model.**
`heart_rate_readings` hangs off `workout_exercises`, and `heart_rate_analytics`
off `workout_sessions` / `routine_slots` — all legacy, read-only history now.
They arrived with `5084736020fd_initial_schema` and have no endpoints and no
writers. Before BLE has anywhere to write they need re-parenting.

**Resolved 2026-08-29** — and not to `training_sessions` / `round_entries` as
guessed here. `round_entries` is wrong because a superset entry is interleaved
rather than contiguous, and nothing below `TrainingSession` carries a timestamp
to slice a stream with. `training_sessions` is wrong as a hard FK because the
232 imported Hevy workouts live in the legacy `workout_sessions`. Readings
became a per-user time series with association held in a separate link table.
Plan: `docs/superpowers/plans/2026-08-29-heart-rate-reparenting.md`; it is a
prerequisite for Phase E, and `users.max_hr` (migration `a3d81b6e4f27`) is
already in place.

Conversely `bodyweight_readings.source`
already anticipates `health_connect`, which is the one capability with a
genuinely native-only requirement.

## Recommendation: climb a ladder, do not start a second codebase

Rather than the July design's Expo rewrite, ship the phone experience as
progressive steps on the code that already works, and go native only where a
native API is actually required:

**PWA (installable + offline) → Capacitor shell only if a native API demands it
→ Expo/native rewrite only if the mobile UX must diverge from web.**

Why this beats the recorded Expo decision now:

- The pattern pivot erased the "port the validated screens" advantage. Expo
  means designing the session flow a second time, in a second codebase, for one
  user.
- Phase 4's shared-client extraction exists only to serve a second client. Skip
  the second client and the phase disappears.
- Capacitor wraps the *existing* React app, so Play Store distribution, native
  BLE and Health Connect stay reachable without a rewrite — the same end state
  the Expo path promises, at a fraction of the work.
- Web Bluetooth in Chrome on Android can read the standard Heart Rate Service
  (0x180D) that the Polar H10 exposes, so even BLE may not require native.
  Caveats: a secure context (HTTPS) and a user gesture are required, and a
  backgrounded or screen-off tab may be suspended and drop the connection. That
  is a spike, not an assumption.

### Does "distribute eventually" reinstate Expo?

No — but it does change where the ladder ends. Distribution means the app must
reach a Play Store listing, not just a home screen, and Capacitor gets there
with the same React codebase: it produces a real signed APK/AAB from the
existing web build. What distribution genuinely reinstates is **auth**, which
becomes a required phase rather than a skipped one, plus the multi-user
concerns in "Going public" below. Those are backend concerns; they are
orthogonal to the client stack.

The argument against Expo is unchanged and is about the pivot, not about
ambition: the session flow would have to be designed a second time, in a second
codebase, and then kept in step with the first one forever. One developer
maintaining two clients is how both of them rot.

Honest limits of the Capacitor end-state, so they are chosen and not
discovered: a WebView app feels like a WebView app, animation and scroll polish
are harder to win, and over-the-air updates mean Play Store releases rather than
EAS-style instant pushes. If mobile UX ever needs to diverge substantially from
web, that is the signal to reconsider — and by then Phases C and E will have
built the offline and BLE layers whose designs port either way. Note iOS too:
Safari does not support Web Bluetooth, so the ladder's HR feature is
Android-only until a native shell exists.

## Plan

### Phase A — Clear the ground — **COMPLETE (2026-09-05)**

1. ~~Delete `android/`.~~ **Done** — `e50c978`. Replace it with nothing; record
   the decision here rather than leaving a scaffold that looks like progress.
   (Recoverable from `a2c5bb4` if ever wanted — but there is nothing there to
   want.)
2. ~~Fix the 7 TypeScript build errors so `npm run build` is green.~~ **Done** —
   `a461972`. This unblocks every later phase.
3. ~~Reconcile the stale docs.~~ **Done** — `feature-matrix.md` and
   `ui-design-review.md` now carry a "HISTORICAL — pre-pivot" banner, and
   `TASKS.md` is marked "RETIRED — historical record, not the plan of record"
   in favour of the `docs/superpowers/` plans that have actually driven the work.

Exit: `npm run build` and `pytest` both green; no dead Android module; no
document claiming a retired feature is the plan of record.

### Phase B — Make the web app a phone app

> **Prerequisite, added 2026-09-05: do step 12 (`tailscale serve` + HTTPS) from
> Phase D first.** Phase D is described below as parallel to B and C. That holds
> for steps 13–16, but *not* for step 12: every item in this phase needs a
> secure context, which `http://100.x.y.z` is not. Attempting Phase B without it
> produces a page that cannot install and a Wake Lock call that will not run —
> and you will spend the time debugging the app rather than the URL. Step 12 is
> the cheap half of Phase D (an admin-console toggle and one command); the
> containerising and laptop-persistence work stays parallel.

4. PWA baseline: `manifest.webmanifest`, real icons (maskable included), theme
   colour, `vite-plugin-pwa` for an app-shell service worker. Installable from
   Chrome on Android to the home screen.
5. Screen Wake Lock during an active session — a phone that sleeps between sets
   is unusable in the gym.
6. Re-verify every page at 390px by hand (the pre-pivot review is no longer
   evidence), with the session flow first: touch targets, one-handed reach for
   set logging, no horizontal scroll.

Exit: installed from the home screen; a full session driven one-handed on a real
phone with the screen staying awake.

### Phase C — Offline session logging (the load-bearing phase)

7. Give `sessionStore` local durability: persist session state to IndexedDB and
   write optimistically, so set logging never blocks on the network.
8. Outbound queue keyed by client-generated UUIDs; flush on reconnect.
9. Backend: idempotent upsert endpoints for session / round / entry / set keyed
   on the client UUID, so a replayed flush cannot duplicate work. This is the
   same outbound-only, no-conflict model the July design chose — worth keeping.
10. Cache the read-only catalogue (exercises, patterns, equipment, staples, day
    plans) locally so exercise selection and proposals work with no signal.
11. Tests: unit tests for the queue and the idempotency keys; a Playwright run
    with the network offline that completes a session and syncs on reconnect.

Exit: a full session logged in airplane mode syncs correctly when signal
returns.

### Phase D — The tailnet host

The spare laptop becomes the always-on host. ~~This phase can run in parallel
with B and C; nothing in it blocks them~~ — **corrected 2026-09-05: steps 13–16
run in parallel with B and C, but step 12 does not. It gates them**, as step 12
itself says a few lines down; the original framing contradicted its own detail.
Do step 12 first, then treat the rest as parallel. Having a real
phone-reachable URL early makes B and C much easier to test.

Note the split in effort, because it is lopsided: step 12 is an admin-console
toggle plus one command, while 13–16 are the substantial half (containerising
the stack, wiring the un-skippable seeds, Windows persistence, backups). Being
blocked on the cheap step is the thing to avoid.

12. **HTTPS on the tailnet, via `tailscale serve`.** This is not a nicety, it is
    the enabler for the two phases around it. Service workers, PWA
    installability, Screen Wake Lock and Web Bluetooth all require a secure
    context, and `http://100.x.y.z` is not one — only `localhost` gets the
    exemption. Enable MagicDNS and HTTPS certificates in the tailnet admin
    console, then `tailscale serve` fronts the app at
    `https://<machine>.<tailnet>.ts.net` with a real Let's Encrypt certificate.
    Without this step, Phase B produces a page that will not install and Phase E
    cannot even request a device.
13. **Containerise the whole stack** — API, Postgres, and the built web assets —
    with `docker compose`, extending `backend/docker-compose.yml`, which today
    is Postgres only. Containerising now is what makes "go public later" a
    redeploy rather than a rebuild.
14. **Deploy steps that cannot be skipped**: Alembic, then
    `scripts.seed_patterns`, then `scripts.seed_leverage`. CLAUDE.md is explicit
    that a database without the pattern seed leaves the entire session feature
    inert — entry creation and staple creation both 404. Wire them into the
    container's start-up so a fresh environment cannot come up half-seeded.
15. **Make the laptop actually persistent**: disable sleep and hibernate on AC
    (`powercfg /change standby-timeout-ac 0`, and disable lid-close sleep),
    Docker Desktop set to start on login with the compose stack restarting
    automatically, and the Tailscale service running at boot rather than at
    user login.
16. **Backups.** A single laptop is a single point of failure holding the only
    copy of the training history. A nightly `pg_dump` to a second location, with
    a restore verified at least once. `Restore-SlotFit.ps1` and `RESTORE.md`
    already do this work for the migration case — the scheduled job is a thin
    wrapper over what exists.
17. **Minimal CI** in GitHub Actions: `pytest`, `npm run build`, Playwright
    smoke. There is no CI at all today, and it is the cheapest guard on a
    codebase that is about to grow an offline layer.

Exit: the phone, joined to the tailnet, loads the app over HTTPS from the
laptop, with a database that survives a reboot and a backup that has been
restored once in anger.

### Phase E — Heart rate, spike first

18. Throwaway spike: Web Bluetooth against a Polar H10 in Chrome on Android,
    served over the tailnet HTTPS URL from Phase D. Measure the thing that
    actually matters — does the connection survive a backgrounded tab and a
    locked screen for 60 minutes?
19. Re-parent the heart-rate tables to `training_sessions` / `round_entries`, or
    drop them and model fresh against the session domain. Add the endpoints
    (none exist).
20. Live BPM and zone display during a session; avg/max and time-in-zone on the
    completion summary. Keep raw 1Hz data local until summarised, then drop it,
    as the original design intended.

Exit: live heart rate during a real workout, with a summary that outlives the
session.

### Phase F — The native shell

Distribution makes this phase certain rather than conditional: a Play Store
listing needs a package, not a URL. Phase E only decides *how much* it has to
do — if Web Bluetooth held its connection, the shell is a thin wrapper; if it
did not, the shell also owns BLE.

21. Capacitor wrap of the existing web build: Android project, signed AAB,
    Play Store internal testing track.
22. Native BLE plugin if the spike failed; Health Connect plugin writing into
    `bodyweight_readings` with `source='health_connect'` — the column is already
    there waiting for it.

Exit: an installable build on the internal testing track, doing what the PWA
could not.

### Phase G — Going public

Everything here is deferred, not designed away. It is the phase that turns a
tailnet app into a product, and it is mostly backend work.

23. **Auth**, as the July design specified: password hashing, JWT access and
    refresh, signup / login / refresh / logout, and `get_current_user` accepting
    either a Bearer token or the legacy `X-Device-ID` during the transition,
    JWT winning when both are present. Device-to-account linking claims an
    anonymous device user's data at signup so nothing is lost — including your
    own history, which will have been accumulating on a device ID for months by
    then.
24. **Move off the laptop** to a managed host (Railway or Render per the July
    design). If Phase D containerised honestly, this is a redeploy plus a
    `pg_dump` restore, not a rebuild.
25. **Multi-tenant hardening**: rate limiting on auth and on the AI
    recommendation endpoints, CORS restricted to known origins, Sentry, managed
    backups, and a secrets audit.
26. **Cost control on AI.** Recommendations currently call Claude or Gemini per
    request. One user is a rounding error; a thousand is a bill. Per-user quotas
    and caching, or a rule-based default with AI as an opt-in, need deciding
    before the store listing rather than after the first invoice.
27. **Resolve the exercise-database licence** (see Risks). This is the one item
    that can block distribution outright, so check it early rather than at
    launch.
28. **Store compliance**: privacy policy, data-deletion path, and the Health
    Connect declared-permissions review if Phase F shipped that plugin. Google
    reviews health-data access specifically.

Exit: a public listing, with accounts, that does not depend on a laptop lid
staying open.

## Keeping the public door open

Cheap now, expensive later. These are the constraints that let Phase G stay
small while Phases A–F ignore auth entirely:

- **Never reach around `get_current_user`.** It is the single identity seam.
  New endpoints take the dependency; nothing reads `X-Device-ID` directly.
- **Scope the Phase C sync UUIDs per user**, not globally. A client-generated
  UUID unique only within a user is correct and stays correct multi-tenant; a
  globally-unique assumption quietly becomes a cross-user collision surface.
- **Keep the API base URL environment-driven.** The tailnet hostname must never
  be baked into the web build — `VITE_`-prefixed config already exists for this.
- **No secrets in the client.** AI keys stay server-side, as they are today.
- **Every new query filters by user.** Single-user hosting hides missing
  `WHERE user_id = ...` clauses perfectly, right up until it does not.

## Still open

- **When to start the Play Store track.** Phase F can ship to internal testing
  long before Phase G's auth exists — a single-user build on your own device is
  a legitimate internal test. Doing so early surfaces store-review surprises
  while they are cheap to fix.
- **iOS.** Out of scope here, unchanged from the July design. Capacitor targets
  it from the same codebase, but Web Bluetooth does not exist on Safari, so an
  iOS build inherits Phase F's native BLE plugin as a hard requirement rather
  than a fallback.

## Risks

- **Phase C is the real work.** Offline-first client state is where the effort
  actually sits, and it is unavoidable in every stack. Anything that looks like
  progress while skipping it — a Capacitor wrap of an online-only app — produces
  a phone app that fails in the gym.
- **Web Bluetooth backgrounding** is the one technical unknown that could force
  native BLE. Spike it before promising HR.
- **The exercise database may not be redistributable, and is the wrong data
  anyway.** Researched separately in
  `2026-08-22-exercise-catalogue-research.md`. The CSV has no licence file and
  no recorded provenance, which is a distribution blocker on its own — but the
  research found a sharper problem: the catalogue holds 3,242 rows and still
  missed 39% of the exercises actually trained (24 of 61 needed creating in
  `hevy/exercise_map.yaml`), because it contains **zero machine entries** while
  spending 861 rows on kettlebells. The recommendation is a curated 250–400
  exercise catalogue seeded from the public-domain `free-exercise-db`,
  scheduled after Phase C and before Phase G.
- **The laptop is a single point of failure** holding the only copy of the
  training history. Phase D step 16 is the mitigation; treat it as required, not
  as housekeeping.
- **Distribution raises the stakes on injury filtering.** The
  not-medical-advice disclaimer already exists in the UI, which is the right
  instinct; giving movement restrictions to strangers deserves a deliberate
  second look at Phase G rather than inheriting the personal-use posture by
  default.
- **Stale docs mislead planning.** Three documents in this repo currently
  describe retired features as current. Phase A step 3 is cheap and prevents the
  next planning pass from re-deriving all of this.

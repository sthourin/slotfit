# Phase 0: Ground Truth and Web Verification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Verify every existing SlotFit web flow end-to-end against a seeded database, capture ground truth in a feature matrix, build a Playwright smoke suite as the permanent regression gate, and fix critical-path blockers.

**Architecture:** No new features. A dedicated `slotfit_e2e` PostgreSQL database isolates test data from the dev database. Playwright drives the real web app (Vite on port 3000) against the real backend (uvicorn on port 8000, proxied via Vite). Findings land in `docs/verification/feature-matrix.md`; defects are triaged by severity and only critical-path blockers are fixed in this phase.

**Tech Stack:** Existing FastAPI + PostgreSQL backend, React 18 + Vite web app. New: `@playwright/test` (Chromium only) in `web/`.

**Spec:** `docs/superpowers/specs/2026-07-26-web-mobile-buildout-design.md` (Phase 0 section)

## Global Constraints

- Dev machine is Windows 11; run commands from PowerShell unless noted. Paths in this plan are relative to the repo root `c:\projects\slotfit`.
- Backend requires Python 3.10+ and a running local PostgreSQL. Web dev server runs on port 3000 and proxies `/api` to `http://localhost:8000` (see `web/vite.config.ts`).
- E2E tests must NEVER run against the developer's main database. They use a dedicated database named `slotfit_e2e`, selected via the `E2E_DATABASE_URL` environment variable.
- Commit subjects are prefixed `[SH]` (project convention).
- Phase 0 adds no features. If a verification step reveals a missing feature, record it in the feature matrix — do not build it.
- Defect severity rubric (used in Tasks 9-10): **P0** = crash, data loss, or a broken step on the critical path (create routine → start workout → log sets → complete → appears in history). **P1** = a feature exists but misbehaves off the critical path. **P2** = cosmetic, styling, copy. Only P0 gets fixed in Phase 0.
- Playwright selectors in this plan are derived from the components read during planning. Each UI test task includes a step to confirm selectors against the named component files before running; adjust the test to the real accessible names rather than changing the app.

---

### Task 1: E2E database and backend bring-up

**Files:**
- Create: `backend/.env.e2e` (gitignored; verify `.gitignore` covers `.env*`)
- Test: manual verification via HTTP (no code tests in this task)

**Interfaces:**
- Produces: a running backend at `http://localhost:8000` backed by `slotfit_e2e`, with 3,244 exercises and injury seed data loaded. Later tasks assume this database exists and is seeded.

- [ ] **Step 1: Install backend dependencies**

```powershell
cd backend
python -m venv venv          # skip if venv already exists
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

- [ ] **Step 2: Create the e2e database**

Read the credentials from the existing `backend/.env` `DATABASE_URL`, then:

```powershell
# Adjust user to match your local PostgreSQL
psql -U postgres -c "CREATE DATABASE slotfit_e2e;"
```

- [ ] **Step 3: Create backend/.env.e2e with the e2e URL**

Copy `backend/.env` to `backend/.env.e2e` and change only the database name in `DATABASE_URL` to `slotfit_e2e`. Confirm `git status` shows no new tracked file (it must be gitignored; if `.env.e2e` appears untracked-but-listable, add `.env.e2e` to `.gitignore` and include that change in this task's commit — otherwise no commit is needed for this task).

- [ ] **Step 4: Run migrations against the e2e database**

```powershell
cd backend
$env:DATABASE_URL = (Select-String -Path .env.e2e -Pattern '^DATABASE_URL=(.+)$').Matches[0].Groups[1].Value
alembic upgrade head
```

Expected: migrations apply cleanly to head. If `alembic upgrade head` fails, that is a P0 finding — record it and fix before proceeding (nothing else works without a schema).

- [ ] **Step 5: Seed exercises and injuries**

```powershell
# Same PowerShell session ($env:DATABASE_URL still set)
python scripts/import_exercises.py
python -m app.data.seed_injuries
```

Expected: import reports ~3,244 exercises; injury seeding completes without error. Record actual counts for the feature matrix.

- [ ] **Step 6: Start the backend and verify**

```powershell
python -m uvicorn app.main:app --port 8000
```

In a second terminal:

```powershell
curl.exe -s "http://localhost:8000/api/v1/exercises?limit=1" -H "X-Device-ID: e2e-manual-check-0001"
```

Expected: HTTP 200 with one exercise JSON object. Also confirm `http://localhost:8000/docs` renders. Leave this server running for Task 2; later tasks start it automatically via Playwright.

---

### Task 2: Web bring-up and feature matrix skeleton

**Files:**
- Create: `docs/verification/feature-matrix.md`

**Interfaces:**
- Produces: the feature matrix document that every later task appends findings to. Row format: `| Flow | Status | Severity | Notes |` where Status is one of `Working`, `Broken`, `Missing`, `Untested`.

- [ ] **Step 1: Install and start the web app**

```powershell
cd web
npm install
npm run dev
```

Expected: Vite serves on `http://localhost:3000`. Open it in a browser with the backend from Task 1 still running; the nav bar (SlotFit, Routine Designer, Start Workout, Exercise Browser, History, Analytics, Records, Settings) renders.

- [ ] **Step 2: Create the feature matrix skeleton**

Create `docs/verification/feature-matrix.md`:

```markdown
# SlotFit Web Feature Matrix

Date started: 2026-07-26
Environment: local dev, backend on slotfit_e2e database

Status values: Working, Broken, Missing, Untested. Severity: P0, P1, P2 (see Phase 0 plan rubric).

## Flows

| Flow | Status | Severity | Notes |
| --- | --- | --- | --- |
| App shell and navigation | Untested | - | |
| Settings: device user auto-created | Untested | - | |
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
```

- [ ] **Step 3: Commit**

```powershell
git add docs/verification/feature-matrix.md
git commit -m "[SH] Add Phase 0 feature matrix skeleton"
```

---

### Task 3: Playwright setup and app-shell smoke test

**Files:**
- Modify: `web/package.json` (add devDependency and `e2e` script)
- Create: `web/playwright.config.ts`
- Create: `web/e2e/app-shell.spec.ts`

**Interfaces:**
- Produces: `npm run e2e` (run from `web/`) which auto-starts backend (with `E2E_DATABASE_URL`) and Vite, then runs everything in `web/e2e/`. All later test tasks add spec files under `web/e2e/` and rely on this config. Also produces the shared constant `DEVICE_ID` convention: tests seed `localStorage.slotfit_device_id` via `addInitScript` so UI and API calls share one user.

- [ ] **Step 1: Install Playwright**

```powershell
cd web
npm install -D @playwright/test
npx playwright install chromium
```

- [ ] **Step 2: Create playwright.config.ts**

```typescript
import { defineConfig } from '@playwright/test'

if (!process.env.E2E_DATABASE_URL) {
  throw new Error(
    'E2E_DATABASE_URL is not set. Set it to the slotfit_e2e connection string ' +
    '(copy DATABASE_URL from backend/.env.e2e). Refusing to run against the dev database.'
  )
}

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  fullyParallel: false,
  workers: 1,
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'retain-on-failure',
  },
  webServer: [
    {
      command: 'python -m uvicorn app.main:app --port 8000',
      cwd: '../backend',
      url: 'http://localhost:8000/docs',
      reuseExistingServer: true,
      timeout: 60_000,
      env: { DATABASE_URL: process.env.E2E_DATABASE_URL },
    },
    {
      command: 'npm run dev',
      url: 'http://localhost:3000',
      reuseExistingServer: true,
      timeout: 60_000,
    },
  ],
})
```

Note: `reuseExistingServer: true` means if you already have servers running from Tasks 1-2, Playwright uses them — make sure the running backend was started with the e2e `DATABASE_URL`, or stop it and let Playwright start its own.

- [ ] **Step 3: Add the e2e script to web/package.json**

In the `scripts` block add:

```json
"e2e": "playwright test"
```

- [ ] **Step 4: Write the app-shell smoke test**

Create `web/e2e/app-shell.spec.ts`:

```typescript
import { test, expect } from '@playwright/test'

test('app shell loads with all navigation links', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('link', { name: 'SlotFit' })).toBeVisible()
  for (const label of [
    'Routine Designer',
    'Start Workout',
    'Exercise Browser',
    'History',
    'Analytics',
    'Records',
    'Settings',
  ]) {
    await expect(page.getByRole('link', { name: label })).toBeVisible()
  }
})

test('device id is generated in localStorage', async ({ page }) => {
  await page.goto('/')
  await expect
    .poll(async () => page.evaluate(() => localStorage.getItem('slotfit_device_id')))
    .toBeTruthy()
})
```

- [ ] **Step 5: Run the suite**

```powershell
cd web
$env:E2E_DATABASE_URL = (Select-String -Path ..\backend\.env.e2e -Pattern '^DATABASE_URL=(.+)$').Matches[0].Groups[1].Value
npm run e2e
```

Expected: 2 passed. If the device-id test fails, check `web/src/services/api.ts` — the key may differ from `slotfit_device_id`; fix the test to match the code.

- [ ] **Step 6: Update matrix and commit**

Mark "App shell and navigation" as Working in `docs/verification/feature-matrix.md`.

```powershell
git add web/package.json web/package-lock.json web/playwright.config.ts web/e2e/app-shell.spec.ts docs/verification/feature-matrix.md
git commit -m "[SH] Add Playwright e2e harness and app-shell smoke test"
```

---

### Task 4: Settings and device-user smoke test

**Files:**
- Create: `web/e2e/helpers/device.ts`
- Create: `web/e2e/settings.spec.ts`
- Read first: `web/src/pages/Settings.tsx`, `web/src/components/settings/ProfileSection.tsx`

**Interfaces:**
- Consumes: Playwright harness from Task 3.
- Produces: `web/e2e/helpers/device.ts` exporting `const E2E_DEVICE_ID: string` and `async function useDevice(page: Page): Promise<void>` (calls `page.addInitScript` to pin the device id). All later specs import these so every test run acts as the same user.

- [ ] **Step 1: Confirm selectors**

Read `web/src/pages/Settings.tsx` and `web/src/components/settings/ProfileSection.tsx`. Note the heading text, the display-name input's label/placeholder, and the save control's accessible name. Substitute the real names into the test below if they differ.

- [ ] **Step 2: Write the device helper**

Create `web/e2e/helpers/device.ts`:

```typescript
import type { Page } from '@playwright/test'

export const E2E_DEVICE_ID = 'e2e-0000-4000-8000-fixed-device-01'

export async function useDevice(page: Page): Promise<void> {
  await page.addInitScript(
    ([key, value]) => localStorage.setItem(key, value),
    ['slotfit_device_id', E2E_DEVICE_ID]
  )
}
```

- [ ] **Step 3: Write the failing test**

Create `web/e2e/settings.spec.ts`:

```typescript
import { test, expect } from '@playwright/test'
import { useDevice } from './helpers/device'

test.beforeEach(async ({ page }) => {
  await useDevice(page)
})

test('settings page loads profile for device user', async ({ page }) => {
  await page.goto('/settings')
  await expect(page.getByRole('heading', { name: /settings/i })).toBeVisible()
  // Profile section should render with the default display name from the backend
  await expect(page.getByText(/athlete/i).first()).toBeVisible({ timeout: 10_000 })
})

test('editing display name persists across reload', async ({ page }) => {
  await page.goto('/settings')
  // Adjust to the real edit control found in Step 1
  const nameInput = page.getByLabel(/display name/i)
  await nameInput.fill('E2E Tester')
  await page.getByRole('button', { name: /save/i }).click()
  await page.reload()
  await expect(page.getByDisplayValue('E2E Tester')).toBeVisible({ timeout: 10_000 })
})
```

- [ ] **Step 4: Run, fix selectors, re-run until green or defect confirmed**

```powershell
cd web
npm run e2e -- settings.spec.ts
```

If a test fails because the selector was wrong, fix the test. If it fails because the app is broken (e.g., save doesn't persist), record the defect in the feature matrix with severity and keep the failing expectation as `test.fixme(...)` with a comment naming the matrix row.

- [ ] **Step 5: Update matrix and commit**

Update the two Settings rows (user auto-created, display name persists). Manually exercise equipment-profile CRUD and injury add/heal in the browser (5 minutes each), and update those two rows too — they get automated only if time permits; manual verification is acceptable for Phase 0.

```powershell
git add web/e2e/helpers/device.ts web/e2e/settings.spec.ts docs/verification/feature-matrix.md
git commit -m "[SH] Add settings e2e smoke tests and record findings"
```

---

### Task 5: Exercise browser smoke test

**Files:**
- Create: `web/e2e/exercise-browser.spec.ts`
- Read first: `web/src/pages/ExerciseBrowser.tsx`

**Interfaces:**
- Consumes: harness (Task 3), `useDevice` (Task 4).
- Produces: proof the seeded exercise data flows through the API to the UI.

- [ ] **Step 1: Confirm selectors**

Read `web/src/pages/ExerciseBrowser.tsx`. Note the search input's placeholder and how result rows/cards render (what text is visible per exercise). Substitute real names below.

- [ ] **Step 2: Write the test**

Create `web/e2e/exercise-browser.spec.ts`:

```typescript
import { test, expect } from '@playwright/test'
import { useDevice } from './helpers/device'

test.beforeEach(async ({ page }) => {
  await useDevice(page)
})

test('exercise browser lists seeded exercises', async ({ page }) => {
  await page.goto('/exercises')
  // 3,244 exercises are seeded; something must render
  await expect(page.getByText(/push[- ]?up/i).first()).toBeVisible({ timeout: 15_000 })
})

test('search narrows results', async ({ page }) => {
  await page.goto('/exercises')
  const search = page.getByPlaceholder(/search/i)
  await search.fill('bench press')
  await expect(page.getByText(/bench press/i).first()).toBeVisible({ timeout: 10_000 })
})
```

- [ ] **Step 3: Run and record**

```powershell
cd web
npm run e2e -- exercise-browser.spec.ts
```

Update the "Exercise browser" matrix row. Green here also confirms Task 1 seeding end-to-end.

- [ ] **Step 4: Commit**

```powershell
git add web/e2e/exercise-browser.spec.ts docs/verification/feature-matrix.md
git commit -m "[SH] Add exercise browser e2e smoke test"
```

---

### Task 6: Routine designer smoke test

**Files:**
- Create: `web/e2e/routine-designer.spec.ts`
- Read first: `web/src/components/RoutineHeader.tsx`, `web/src/components/SlotList.tsx`, `web/src/components/SlotEditor.tsx`, `web/src/components/MuscleGroupSelector.tsx`, `web/src/stores/routineStore.ts`

**Interfaces:**
- Consumes: harness, `useDevice`.
- Produces: a saved routine named `E2E Push Day` in the e2e database, which Task 7 reuses. Task 7 depends on this exact name.

- [ ] **Step 1: Confirm the create/save flow**

Read the five files listed above. Establish: how a slot is added (button name), how muscle groups are assigned to a slot, how the routine is named, and which control persists the routine to the backend (`POST /api/v1/routines` in `web/src/services/routines.ts`). Substitute real accessible names below.

- [ ] **Step 2: Write the test**

Create `web/e2e/routine-designer.spec.ts`:

```typescript
import { test, expect } from '@playwright/test'
import { useDevice } from './helpers/device'

test.beforeEach(async ({ page }) => {
  await useDevice(page)
})

test('create a routine with one slot and save it', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Create New Routine' }).click()

  // Name the routine (adjust to the RoutineHeader control found in Step 1)
  const nameInput = page.getByDisplayValue('New Routine')
  await nameInput.fill('E2E Push Day')

  // Add a slot (adjust to the SlotList control found in Step 1)
  await page.getByRole('button', { name: /add slot/i }).click()

  // Save to backend and confirm the API succeeds
  const [response] = await Promise.all([
    page.waitForResponse(
      (r) => r.url().includes('/api/v1/routines') && r.request().method() === 'POST'
    ),
    page.getByRole('button', { name: /save/i }).click(),
  ])
  expect(response.status()).toBeLessThan(300)
})
```

- [ ] **Step 3: Run, adjust, record**

```powershell
cd web
npm run e2e -- routine-designer.spec.ts
```

Selector mismatches: fix the test. App defects: matrix + `test.fixme` as in Task 4. A broken save here is P0 (critical path).

- [ ] **Step 4: Commit**

```powershell
git add web/e2e/routine-designer.spec.ts docs/verification/feature-matrix.md
git commit -m "[SH] Add routine designer e2e smoke test"
```

---

### Task 7: Critical path smoke test — start, execute, complete a workout

**Files:**
- Create: `web/e2e/workout-critical-path.spec.ts`
- Read first: `web/src/pages/WorkoutStart.tsx`, `web/src/components/workout/SetTracker.tsx`, `web/src/components/workout/WorkoutControls.tsx`, `web/src/components/workout/WorkoutSummary.tsx`, `web/src/stores/workoutStore.ts`

**Interfaces:**
- Consumes: harness, `useDevice`, and the `E2E Push Day` routine saved by Task 6 (this spec file must sort after `routine-designer.spec.ts`; with `workers: 1` and alphabetical order, `workout-critical-path` runs after `routine-designer` — do not rename either file).
- Produces: a completed workout in the e2e database, which Task 8's history test displays.

- [ ] **Step 1: Confirm the flow**

Read the five files listed above. Establish: how a routine is chosen on `/workout/start`, how an exercise gets assigned to a slot during the workout (ExerciseSelector opens from CurrentSlot or SetTracker), the accessible names for logging a set (reps/weight inputs, add-set button), and the complete-workout control (WorkoutControls) plus what the summary screen shows.

- [ ] **Step 2: Write the test**

Create `web/e2e/workout-critical-path.spec.ts` (adjust names per Step 1):

```typescript
import { test, expect } from '@playwright/test'
import { useDevice } from './helpers/device'

test.beforeEach(async ({ page }) => {
  await useDevice(page)
})

test('start a workout from routine, log a set, complete it', async ({ page }) => {
  await page.goto('/workout/start')

  // Select the routine created in routine-designer.spec.ts
  await page.getByText('E2E Push Day').click()
  await page.getByRole('button', { name: /start workout/i }).click()

  // Active workout page
  await expect(page.getByRole('heading', { name: 'Active Workout' })).toBeVisible()

  // Pick an exercise for the empty slot (opens ExerciseSelector)
  await page.getByRole('button', { name: /select exercise/i }).click()
  await page.getByPlaceholder(/search/i).fill('push up')
  await page.getByText(/push[- ]?up/i).first().click()

  // Log one set
  await page.getByLabel(/reps/i).fill('10')
  await page.getByRole('button', { name: /add set|complete set/i }).click()

  // Complete the workout
  await page.getByRole('button', { name: /complete/i }).click()
  // Confirm dialog or summary appears
  await expect(page.getByText(/summary|duration|volume/i).first()).toBeVisible({ timeout: 10_000 })
})
```

- [ ] **Step 3: Run and iterate**

```powershell
cd web
npm run e2e -- workout-critical-path.spec.ts
```

This is the highest-value test in Phase 0 and the most likely to surface real defects (TASKS.md claimed this whole area was "Not Started"). Budget time to iterate: selector fixes go in the test; every app defect goes in the matrix. Any break in this chain is P0.

- [ ] **Step 4: Verify AI recommendations panel (manual)**

While the servers are up, open the exercise selector in a real browser and confirm the recommendations panel and Why Not section render (rule-based fallback provider works without API keys). Record the "exercise selection + AI recommendations + Why Not" matrix row. Also record "rest timer" and "slot navigation and skip" rows from quick manual checks.

- [ ] **Step 5: Commit**

```powershell
git add web/e2e/workout-critical-path.spec.ts docs/verification/feature-matrix.md
git commit -m "[SH] Add critical-path workout e2e test and record findings"
```

---

### Task 8: History, analytics, and records smoke test

**Files:**
- Create: `web/e2e/read-pages.spec.ts`

**Interfaces:**
- Consumes: harness, `useDevice`. Note: `read-pages.spec.ts` sorts alphabetically BEFORE `workout-critical-path.spec.ts`, so on a fresh database no completed workout exists yet when it runs. The test is therefore written to assert only that pages render without console errors; data presence (the Task 7 workout appearing in history) is verified manually in Step 2 after the full ordered run.

- [ ] **Step 1: Write the test**

Create `web/e2e/read-pages.spec.ts`:

```typescript
import { test, expect } from '@playwright/test'
import { useDevice } from './helpers/device'

test.beforeEach(async ({ page }) => {
  await useDevice(page)
})

for (const [path, heading] of [
  ['/history', /history/i],
  ['/analytics', /analytics/i],
  ['/records', /records/i],
] as const) {
  test(`page ${path} renders without console errors`, async ({ page }) => {
    const errors: string[] = []
    page.on('pageerror', (e) => errors.push(e.message))
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(msg.text())
    })
    await page.goto(path)
    await expect(page.getByRole('heading', { name: heading }).first()).toBeVisible({
      timeout: 10_000,
    })
    // Allow network 404s for optional data but no crashes
    expect(errors.filter((e) => !/404|Failed to load resource/i.test(e))).toEqual([])
  })
}
```

- [ ] **Step 2: Run the FULL suite (ordering matters now)**

```powershell
cd web
npm run e2e
```

Expected: all specs pass in order (app-shell, exercise-browser, read-pages, routine-designer, settings, workout-critical-path). After the run, manually open `/history` and confirm the Task 7 workout appears; record the History/Analytics/Records matrix rows including whether real data displays.

- [ ] **Step 3: Commit**

```powershell
git add web/e2e/read-pages.spec.ts docs/verification/feature-matrix.md
git commit -m "[SH] Add read-page e2e smoke tests"
```

---

### Task 9: Verify CLAUDE.md design decisions

**Files:**
- Modify: `docs/verification/feature-matrix.md` (Design Decisions section)

**Interfaces:**
- Consumes: running app; grep access to the codebase.
- Produces: Implemented/Missing verdicts for the four recorded design decisions. Missing items become Phase 1 backlog entries, not Phase 0 work.

- [ ] **Step 1: Workout resume banner**

```powershell
# Search for the banner implementation
cd web
Select-String -Path src -Pattern "unfinished|Resume.*Discard|resume" -Recurse
```

Then verify behaviorally: start a workout (reuse Task 7 flow manually), navigate to `/` mid-workout, reload the page. Per CLAUDE.md a banner must offer Resume/Discard. Record Implemented or Missing.

- [ ] **Step 2: Save-as-new-routine prompt**

```powershell
Select-String -Path src -Pattern "Save as New|Update Original" -Recurse
```

Behavioral check: during a workout, change a pre-filled exercise, complete the workout, and look for the prompt. Requires a routine with a previous completed workout (Task 7 created one — run the same routine a second time and swap the exercise). Record verdict.

- [ ] **Step 3: Bodyweight exercises always available**

Backend check (this rule lives in the recommendation service):

```powershell
cd ..\backend
Select-String -Path app\services\ai -Pattern "primary_equipment_id.is_\(None\)|is_(None)" -Recurse
```

Behavioral check: in the exercise selector with a restrictive equipment profile active, confirm bodyweight exercises (e.g., Push Up) still appear and are never in the Why Not list for equipment reasons. Record verdict.

- [ ] **Step 4: Injury disclaimer**

```powershell
cd ..\web
Select-String -Path src -Pattern "not medical advice" -Recurse
```

Behavioral check: add an injury in Settings; the disclaimer must be visible in that flow. Record verdict.

- [ ] **Step 5: Commit matrix updates**

```powershell
git add docs/verification/feature-matrix.md
git commit -m "[SH] Record design-decision verification results in feature matrix"
```

---

### Task 10: Defect triage and P0 fixes

**Files:**
- Modify: `docs/verification/feature-matrix.md` (Defect Backlog section)
- Modify: whatever files each P0 fix requires (determined by the defect)

**Interfaces:**
- Consumes: all matrix findings from Tasks 3-9.
- Produces: zero P0 defects outstanding; P1/P2 defects listed in the backlog table for Phase 1.

- [ ] **Step 1: Triage**

Review every `Broken` or `Missing` row in the matrix. Assign P0/P1/P2 per the Global Constraints rubric. Move P1/P2 into the Defect Backlog table. Anything `Missing` that CLAUDE.md or the spec expects becomes a P1 backlog entry (feature work belongs to Phase 1), unless it breaks the critical path, in which case it is P0.

- [ ] **Step 2: Fix each P0 using systematic debugging**

For each P0, use the superpowers:systematic-debugging skill: reproduce via the failing Playwright test (convert any `test.fixme` back to a live test), find the root cause, write/adjust the test to capture the expected behavior, fix, and verify the test passes. One commit per defect:

```powershell
git add <files>
git commit -m "[SH] Fix <defect summary> found in Phase 0 verification"
```

- [ ] **Step 3: Full suite green**

```powershell
cd web
npm run e2e
cd ..\backend
python -m pytest
```

Expected: all Playwright specs pass with no remaining `test.fixme` for P0 items; all 51+ backend tests pass.

---

### Task 11: Reconcile TASKS.md and close out Phase 0

**Files:**
- Modify: `TASKS.md`
- Modify: `docs/verification/feature-matrix.md` (final statuses)

**Interfaces:**
- Consumes: completed matrix.
- Produces: TASKS.md statuses that match reality; the Phase 1 plan consumes the matrix's Defect Backlog and design-decision verdicts as its input.

- [ ] **Step 1: Update TASKS.md**

For each task in TASKS.md Phases 4-5 (currently all "[ ] Not Started"), set the status to match the matrix: `[x] Complete` if the flow is Working, or `[~] Partially complete - see docs/verification/feature-matrix.md` with a one-line note of what remains. Add a line under each corrected task: `**Verified**: 2026-07-26 via Playwright e2e (docs/verification/feature-matrix.md)`.

- [ ] **Step 2: Final matrix pass**

Confirm no row is left `Untested`. Any row that genuinely could not be tested gets a Notes explanation.

- [ ] **Step 3: Commit**

```powershell
git add TASKS.md docs/verification/feature-matrix.md
git commit -m "[SH] Reconcile TASKS.md with verified feature matrix; close Phase 0"
```

---

## Follow-On Plans (not in this document)

Per the spec, each subsequent phase gets its own implementation plan written when the phase starts, informed by Phase 0's feature matrix:

1. `2026-XX-XX-phase-1-web-polish-responsive.md` — responsive layouts, PWA baseline, defect backlog from the matrix, missing design decisions (resume banner, save-as-new) if Phase 0 finds them absent.
2. `2026-XX-XX-phase-2-auth.md` — JWT auth, device-to-account linking.
3. `2026-XX-XX-phase-3-deploy.md` — Railway deployment, CI, Sentry, backups.
4. `2026-XX-XX-phase-4-shared-client.md` — npm workspaces extraction of `web/src/services/`.
5. `2026-XX-XX-phase-5-mobile-v1.md` — Expo Android app: BLE spike first, then offline workout execution, sync queue, heart-rate features, EAS release.

# Hevy Data Import & MVP Verification Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Import real workout history from Hevy into SlotFit, then verify all remaining MVP features work end-to-end with real data.

**Architecture:** Use the Hevy MCP server to pull full workout history, transform it into SlotFit's import format, run the existing import script, then smoke-test Analytics, Personal Records, and the full workout flow.

**Tech Stack:** Hevy MCP (Node.js, stdio), Python import script, PostgreSQL, React/TypeScript frontend

---

## Phase 1: Fresh Hevy Data Pull & Import

### Task 1: Pull Full Workout History from Hevy MCP

**Files:**
- Create: `backend/scripts/hevy_import/pull_from_hevy.py`
- Modify: `backend/scripts/hevy_import/hevy_workouts_data.json`

**Context:** The Hevy MCP at `C:\Projects\hevy-mcp-clone` exposes `get-workouts` (paginated, max 10/page), `get-workout-count`, and `get-exercise-templates`. We need to pull ALL workouts and transform them into our import format. The existing `hevy_workouts_data.json` has 13 workouts from Nov 2025–Jan 2026, but we want the full history.

**Step 1: Use Hevy MCP to get workout count and fetch all workouts**

Use the Hevy MCP tools to:
1. Call `get-workout-count` to know total workouts
2. Call `get-workouts` page by page (page_size=10) to get all workouts
3. Save the raw response data

**Step 2: Transform Hevy API format to SlotFit import format**

The import script expects this format:
```json
{
  "date_range": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"},
  "workouts": [
    {
      "title": "...",
      "started_at": "ISO8601",
      "completed_at": "ISO8601",
      "exercises": [
        {
          "name": "...",
          "notes": "...",
          "sets": [
            {
              "set_number": 1,
              "reps": 10,
              "weight_kg": 50.0,
              "rpe": 7.0,
              "duration_sec": null,
              "distance_m": null
            }
          ]
        }
      ]
    }
  ]
}
```

The Hevy API returns workouts with `start_time`/`end_time`, exercises with `exercise_template_id`/`title`, and sets with `weight_kg`/`reps`/`rpe`/`duration_seconds`/`distance_meters`.

Write a Python script that:
1. Reads raw Hevy API responses
2. Maps `start_time` → `started_at`, `end_time` → `completed_at`
3. Maps exercise `title` → `name`
4. Maps set fields: `weight_kg`, `reps`, `rpe`, `duration_seconds` → `duration_sec`, `distance_meters` → `distance_m`
5. Numbers sets sequentially per exercise
6. Saves to `hevy_workouts_data.json`

**Step 3: Run import script in dry-run mode**

Run: `cd backend && python scripts/hevy_import/import_hevy_workouts.py --dry-run --verbose`
Expected: Summary of workouts/exercises/sets to import, list of exercises needing creation, no DB changes

**Step 4: Review exercise mapping and fix any issues**

Check the dry-run output for:
- Exercises that couldn't be matched (will be created as new)
- Any obvious mapping mistakes
- Adjust `NAME_NORMALIZATIONS` in the import script if needed

**Step 5: Run actual import**

Run: `cd backend && python scripts/hevy_import/import_hevy_workouts.py --verbose`
Expected: All workouts imported, exercise mapping saved

**Step 6: Verify import**

Run: `cd backend && python -c "import asyncio; ..."`  (quick query to count workouts, exercises, sets in DB)

Or check via API:
```
curl http://localhost:8000/api/v1/workouts/?limit=5
```

**Step 7: Commit**

```bash
git add backend/scripts/hevy_import/
git commit -m "feat: pull full workout history from Hevy and import into SlotFit"
```

---

## Phase 2: Verify Analytics with Real Data

### Task 2: Smoke-test Analytics Backend Endpoints

**Files:**
- Test: `backend/app/api/v1/endpoints/analytics.py`
- Test: `backend/app/services/analytics_service.py`

**Step 1: Start backend server**

Run: `.\restart-server.bat` (or `cd backend && uvicorn app.main:app --reload --port 8000`)

**Step 2: Test weekly volume endpoint**

Run: `curl http://localhost:8000/api/v1/analytics/weekly-volume -H "X-Device-ID: hevy-import-device"`
Expected: JSON with muscle group volumes from imported workouts

**Step 3: Test exercise progression endpoint**

Pick an exercise ID from the import and test:
Run: `curl "http://localhost:8000/api/v1/analytics/exercise-progression/{exercise_id}" -H "X-Device-ID: hevy-import-device"`
Expected: JSON with progression data points

**Step 4: Test slot performance endpoint**

Run: `curl "http://localhost:8000/api/v1/analytics/slot-performance/{routine_id}" -H "X-Device-ID: hevy-import-device"`
Expected: JSON with slot performance data (may be empty if no routines were used, which is fine)

**Step 5: Note any issues and fix**

If endpoints return errors or empty data, investigate and fix the analytics service queries.

---

### Task 3: Verify Analytics Frontend Renders Charts

**Files:**
- Verify: `web/src/pages/Analytics.tsx`
- Verify: `web/src/components/analytics/VolumeChart.tsx`
- Verify: `web/src/components/analytics/MovementBalance.tsx`
- Verify: `web/src/components/analytics/SlotPerformance.tsx`

**Step 1: Start frontend dev server**

Run: `cd web && npm run dev`

**Step 2: Open Analytics page in browser**

Navigate to `http://localhost:3000/analytics`
Verify:
- Weekly Volume chart renders with bars (recharts BarChart)
- Movement Balance section renders
- No console errors

**Step 3: If charts don't render, check recharts is installed**

Run: `cd web && npm list recharts`
If missing: `npm install recharts`

**Step 4: Fix any rendering issues found**

Common issues:
- Empty data causing chart crash (need null checks)
- Device ID mismatch (frontend uses auto-generated UUID, not "hevy-import-device")

**Step 5: If device ID is the issue, update the import user**

The imported data uses `X-Device-ID: hevy-import-device`. The frontend generates its own device ID. We either need to:
- Option A: Update the import script to use the frontend's device ID (check localStorage)
- Option B: Add a way to set device ID in settings
- Option C: Create an API endpoint to merge/link device IDs

**Step 6: Commit any fixes**

```bash
git add -A
git commit -m "fix: analytics page rendering with real workout data"
```

---

## Phase 3: Verify Personal Records

### Task 4: Test Personal Records Page

**Files:**
- Verify: `web/src/pages/PersonalRecords.tsx`
- Verify: `web/src/components/records/PRCard.tsx`
- Verify: `web/src/components/records/PRHistory.tsx`

**Step 1: Check Personal Records API with imported data**

Run: `curl http://localhost:8000/api/v1/personal-records/ -H "X-Device-ID: hevy-import-device"`
Expected: List of PRs (may be empty if PRs aren't auto-calculated during import)

**Step 2: If PRs are empty, they need to be calculated from workout history**

The current PR system is manual (CRUD). For imported data, we may need a one-time script to calculate PRs from workout history. Check if this is a gap.

**Step 3: Open Personal Records page in browser**

Navigate to `http://localhost:3000/records`
Verify: Page renders without crashing. If no PRs, it should show an empty state.

**Step 4: Fix any issues found**

---

## Phase 4: End-to-End Workout Flow Test

### Task 5: Full Workout Smoke Test

**Step 1: Create a routine via UI**

Navigate to `http://localhost:3000/routines`
- Click "New Routine"
- Name it "Test Routine"
- Add 3 slots: Chest (standard), Back (standard), Shoulders (warmup)
- Save

**Step 2: Start a workout from the routine**

Navigate to `http://localhost:3000/workout/start`
- Select the test routine
- Select an equipment profile (or skip)
- Start the workout

**Step 3: Complete the workout**

- Select exercises for each slot
- Log 3 sets per exercise (10 reps, various weights)
- Complete each slot
- Finish workout

**Step 4: Verify workout appears in history**

Navigate to `http://localhost:3000/history`
- Verify the workout appears
- Click into detail view
- Verify exercises and sets are shown

**Step 5: Verify dashboard updates**

Navigate to `http://localhost:3000/`
- Verify "Last Workout" section shows the just-completed workout
- Verify AI next-workout suggestion works

**Step 6: Document any issues found**

Create a list of bugs/issues for follow-up.

---

## Phase 5: Device ID Resolution

### Task 6: Ensure imported data is visible to the frontend user

**Files:**
- Modify: `backend/scripts/hevy_import/import_hevy_workouts.py`

**Context:** This is the most likely blocker. The frontend auto-generates a device ID (UUID) stored in localStorage. The import script uses "hevy-import-device". The data won't be visible to the frontend user unless they share the same device ID.

**Step 1: Check how the frontend generates device ID**

Read `web/src/services/api.ts` to find the device ID generation logic.

**Step 2: Choose a resolution approach**

Best approach: Update the import script to accept a `--device-id` argument so you can pass the frontend's device ID. Then re-run the import with matching IDs.

**Step 3: Implement and test**

Update the import script's `get_or_create_import_user` to use the provided device ID.

**Step 4: Commit**

```bash
git add backend/scripts/hevy_import/import_hevy_workouts.py
git commit -m "feat: allow custom device ID for Hevy import to match frontend user"
```

---

## Success Criteria

After completing this plan:
- [ ] All Hevy workout history imported into SlotFit DB
- [ ] Analytics page shows charts with real data
- [ ] Personal Records page functional
- [ ] Full workout flow works end-to-end (create → execute → complete → view)
- [ ] Dashboard shows last workout and AI suggestions
- [ ] Imported data visible to the frontend user (device ID resolved)
- [ ] All 51+ backend tests still pass
- [ ] Frontend builds without TypeScript errors

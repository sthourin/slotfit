# Test Fix Plan - 8 Remaining Failures

**Status**: 36 passing, 7 skipped, 8 failing  
**Goal**: Fix all 8 remaining test failures

## Overview

After fixing 23 of 32 initial failures, we have 8 remaining test failures to address. This document outlines the plan to fix each one.

---

## Failure 1: `test_filter_exercises_by_muscle_group`
**Error**: `assert 0 > 0` - Returns empty list when filtering by muscle group

**Root Cause**: The exercise filter endpoint may not be correctly filtering by muscle group, or the seed data doesn't have exercises properly linked to muscle groups.

**Fix Plan**:
1. Check `backend/tests/test_exercises.py::test_filter_exercises_by_muscle_group`
2. Verify seed data creates exercises with proper muscle group associations
3. Check the exercises endpoint filter logic in `backend/app/api/v1/endpoints/exercises.py`
4. Ensure `exercise_muscle_groups` association table is populated in seed data

**Files to Check**:
- `backend/tests/test_exercises.py`
- `backend/tests/seed_data.py` (exercise seeding)
- `backend/app/api/v1/endpoints/exercises.py` (filter logic)

---

## Failure 2: `test_list_user_injuries`
**Error**: `assert 0 >= 1` - Returns empty list after creating an injury

**Root Cause**: The user injury is created but not returned in the list, possibly due to:
- User ID mismatch
- Active filter excluding the injury
- Transaction/commit issue

**Fix Plan**:
1. Check `backend/tests/test_injuries.py::test_list_user_injuries`
2. Verify user ID is consistent between create and list calls
3. Check if `active_only` query parameter is filtering out the injury
4. Verify the injury is properly committed to the database

**Files to Check**:
- `backend/tests/test_injuries.py`
- `backend/app/api/v1/endpoints/injuries.py` (list endpoint)

---

## Failure 3: `test_update_user_injury`
**Error**: `assert 500 == 200` - Internal Server Error when updating injury

**Root Cause**: Server error during update, likely:
- Missing relationship loading (injury_type)
- Database constraint violation
- Missing field in update schema

**Fix Plan**:
1. Check server logs for the actual error
2. Review `backend/app/api/v1/endpoints/injuries.py::update_user_injury`
3. Ensure `injury_type` relationship is loaded after update
4. Verify `UserInjuryUpdate` schema matches what's being sent

**Files to Check**:
- `backend/tests/test_injuries.py::test_update_user_injury`
- `backend/app/api/v1/endpoints/injuries.py`
- `backend/app/schemas/injury.py`

---

## Failure 4: `test_delete_user_injury`
**Error**: `assert 200 == 204` - Returns 200 instead of 204 (No Content)

**Root Cause**: The delete endpoint returns a JSON response instead of 204 status code.

**Fix Plan**:
1. Check `backend/app/api/v1/endpoints/injuries.py::delete_user_injury`
2. Change return to `None` or remove return statement
3. Ensure `status_code=204` is set on the route decorator

**Files to Check**:
- `backend/app/api/v1/endpoints/injuries.py` (delete endpoint)

---

## Failure 5-7: Recommendation Tests (3 failures)
**Errors**: All return `422 Unprocessable Entity`

**Tests**:
- `test_get_recommendations_basic`
- `test_get_recommendations_with_equipment_profile`
- `test_get_recommendations_with_routine_slot`

**Root Cause**: The recommendations endpoint requires `available_equipment_ids` as a required query parameter, but tests may be:
- Not providing it
- Providing it incorrectly (empty list vs None)
- Using wrong parameter format

**Fix Plan**:
1. Check `backend/app/api/v1/endpoints/recommendations.py` - verify query parameter requirements
2. Review all three test cases in `backend/tests/test_recommendations.py`
3. Ensure `available_equipment_ids` is provided as a list (even if empty)
4. Check if empty list `[]` is valid or if we need to make it optional

**Files to Check**:
- `backend/tests/test_recommendations.py`
- `backend/app/api/v1/endpoints/recommendations.py`

---

## Failure 8: `test_update_slot_template`
**Error**: `AssertionError: assert None == 'Updated description'` - Notes field is None

**Root Cause**: The test is trying to update a `notes` field with value "Updated description", but the update isn't being applied or the field isn't being returned.

**Fix Plan**:
1. Check `backend/tests/test_slot_templates.py::test_update_slot_template`
2. Verify the update request includes `notes: "Updated description"`
3. Check `backend/app/api/v1/endpoints/slot_templates.py` update endpoint
4. Ensure `SlotTemplateUpdate` schema includes `notes` field
5. Verify the update logic applies the `notes` field

**Files to Check**:
- `backend/tests/test_slot_templates.py`
- `backend/app/api/v1/endpoints/slot_templates.py`
- `backend/app/schemas/slot_template.py`

---

## Implementation Order

### Phase 1: Quick Wins (30 min)
1. **Failure 4** - Delete endpoint status code (simple fix)
2. **Failure 8** - Slot template notes update (likely schema/update logic)

### Phase 2: Data/Seed Issues (45 min)
3. **Failure 1** - Exercise filtering (check seed data associations)
4. **Failure 2** - User injuries list (check user ID consistency)

### Phase 3: Server Errors (60 min)
5. **Failure 3** - Update user injury (debug 500 error)
6. **Failures 5-7** - Recommendations endpoint (fix query parameters)

---

## Testing Strategy

After each fix:
1. Run the specific test: `pytest backend/tests/test_<module>.py::test_<name> -v`
2. Verify it passes
3. Run full test suite to ensure no regressions
4. Commit fix with descriptive message

---

## Success Criteria

- All 8 tests pass
- Full test suite: 44+ passing, 7 skipped, 0 failing
- No regressions in previously passing tests

---

## Notes

- Most failures appear to be:
  - Missing or incorrect seed data associations
  - Query parameter validation issues
  - Status code mismatches
  - Missing relationship loading after updates

- The recommendations endpoint failures are likely all the same root cause (query parameter format)

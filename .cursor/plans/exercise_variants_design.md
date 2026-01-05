# Exercise Variants & Multi-Style Support Design

## Problem Statement

Users want to use the same exercise (e.g., "Dumbbell Lateral Raise") with different parameters for different workout styles:
- **Strength routine**: Heavy weights, low reps (e.g., 3 sets × 8 reps at 25 lbs)
- **HIIT routine**: Light weights, high reps or for time (e.g., 3 sets × 20 reps at 10 lbs, or 30 seconds AMRAP)

**Critical Requirement**: History tracking must be **context-aware**. When viewing an exercise in a HIIT routine, users want to see their HIIT-specific history (light weights, high reps), not their Strength routine history (heavy weights, low reps). This enables proper progression tracking and recommendations within each workout style.

## Solution: Exercise Variants (Primary Approach)

**Primary Solution**: Use exercise variants to create separate exercise entries for different workout styles/modes. This provides clean history separation while maintaining the relationship to the original exercise.

### Exercise Variants for Context-Aware History

**Concept**: Create separate exercise entries (variants) for different workout styles/modes. Each variant maintains its own history, enabling context-specific tracking and recommendations.

**Implementation**:
- Add fields to `exercises` table:
  - `base_exercise_id` (Integer, ForeignKey to exercises.id, nullable)
    - NULL for original exercises from database
    - References original exercise for user-created variants
  - `variant_type` (String, nullable)
    - Examples: "HIIT", "Strength", "Volume", "Endurance", "Custom"
    - Used to categorize variants by workout style
  - `is_custom` (Boolean, default False)
    - True for user-created variants
    - False for original database exercises
  - `default_sets` (Integer, nullable) - Suggested default for this variant
  - `default_reps` (Integer, nullable) - Suggested default for this variant
  - `default_weight` (Float, nullable) - Suggested default for this variant
  - `default_time_seconds` (Integer, nullable) - For time-based exercises
  - `default_rest_seconds` (Integer, nullable) - Suggested rest time
  - `user_id` (Integer, ForeignKey to users.id, nullable) - For future authentication
- Variants inherit all properties from base exercise (muscle groups, equipment, etc.)
- Users can modify variant properties (name, description, defaults)
- History is tracked per variant: `workout_sets.exercise_id` references the variant
- When querying history, filter by the specific variant ID

**Benefits**:
- **Clean history separation**: Each variant has its own performance history
- **Context-aware recommendations**: AI can recommend based on variant-specific history
- **Progression tracking**: Track progression separately for HIIT vs Strength
- **Clear organization**: Variants grouped by base exercise, categorized by type
- **Flexibility**: Users can create custom variants for any purpose

**Example**:
```
Base Exercise: "Dumbbell Lateral Raise" (id: 123)
  ↓ User creates variants
  
Variant 1: "Dumbbell Lateral Raise (Strength)" (id: 1001)
  base_exercise_id: 123
  variant_type: "Strength"
  default_sets: 3
  default_reps: 8
  default_weight: 25.0
  default_rest_seconds: 90
  History: [Workout 1: 3×8@25lbs, Workout 2: 3×8@27.5lbs, ...]

Variant 2: "Dumbbell Lateral Raise (HIIT)" (id: 1002)
  base_exercise_id: 123
  variant_type: "HIIT"
  default_sets: 3
  default_reps: 20
  default_weight: 10.0
  default_rest_seconds: 30
  History: [Workout 1: 3×20@10lbs, Workout 2: 3×22@10lbs, ...]

When user selects exercise in HIIT routine → shows Variant 2
  → History shows only HIIT-specific performance
  → Recommendations based on HIIT history
  → Progression tracked separately from Strength variant
```

### Approach 2: Slot-Level Parameters (Supplementary)

**Concept**: Allow users to duplicate exercises and create custom variants with modified names/properties.

**Implementation**:
- Add fields to `exercises` table:
  - `base_exercise_id` (Integer, ForeignKey to exercises.id, nullable)
  - `is_custom` (Boolean, default False)
  - `user_id` (Integer, ForeignKey to users.id, nullable) - for future authentication
- API endpoint: `POST /api/v1/exercises/{exercise_id}/duplicate`
  - Creates new exercise with all properties copied
  - Sets `base_exercise_id` to original exercise
  - Sets `is_custom` to True
  - User can then modify name, description, etc.
- Custom exercises appear in exercise list with indicator (e.g., "Custom" badge)
- Custom exercises can be edited/deleted by user

**Benefits**:
- Clear separation when exercise form/technique differs significantly
- Useful for tracking different variations separately in analytics
- Good for exercises where the variant is conceptually different (e.g., "Dumbbell Lateral Raise (Seated)" vs "Dumbbell Lateral Raise (Standing)")

**Example**:
```
Original: "Dumbbell Lateral Raise"
  ↓ User duplicates
Custom: "Dumbbell Lateral Raise (Strength)" - modified description, different default weight
Custom: "Dumbbell Lateral Raise (HIIT)" - modified description, different default reps
```

## Recommended Usage

**Use Exercise Variants** (Primary) when:
- **You need context-aware history tracking** (HIIT vs Strength history separation)
- Different workout styles require different progression tracking
- You want style-specific recommendations from AI
- The exercise is used in fundamentally different ways (HIIT vs Strength vs Volume)

**Use Slot-Level Parameters** (Supplementary) when:
- You want to fine-tune variant defaults for a specific routine
- Parameters are routine-specific but history should still be grouped by variant
- Temporary adjustments that don't warrant a new variant

## History Tracking Architecture

**Key Principle**: History is tracked per exercise variant, enabling context-aware queries.

**Query Examples**:
```sql
-- Get history for "Dumbbell Lateral Raise (HIIT)" variant
SELECT * FROM workout_sets 
WHERE exercise_id = 1002  -- HIIT variant ID
ORDER BY workout_session.started_at DESC;

-- Get history for "Dumbbell Lateral Raise (Strength)" variant  
SELECT * FROM workout_sets
WHERE exercise_id = 1001  -- Strength variant ID
ORDER BY workout_session.started_at DESC;

-- Get all variants of a base exercise
SELECT * FROM exercises
WHERE base_exercise_id = 123;  -- Base exercise ID

-- Get user's history across all variants of an exercise
SELECT e.variant_type, ws.* 
FROM workout_sets ws
JOIN exercises e ON ws.exercise_id = e.id
WHERE e.base_exercise_id = 123
ORDER BY e.variant_type, ws.workout_exercise_id;
```

**AI Recommendations**:
- When recommending exercises for a HIIT routine, use HIIT variant history
- When recommending exercises for a Strength routine, use Strength variant history
- This ensures recommendations are contextually relevant

## Database Schema Changes

### routine_slots table additions:
```sql
ALTER TABLE routine_slots ADD COLUMN target_sets INTEGER;
ALTER TABLE routine_slots ADD COLUMN target_reps INTEGER;
ALTER TABLE routine_slots ADD COLUMN target_weight FLOAT;
ALTER TABLE routine_slots ADD COLUMN target_time_seconds INTEGER;
ALTER TABLE routine_slots ADD COLUMN target_rest_seconds INTEGER;
```

### exercises table additions:
```sql
ALTER TABLE exercises ADD COLUMN base_exercise_id INTEGER REFERENCES exercises(id);
ALTER TABLE exercises ADD COLUMN variant_type VARCHAR(50);  -- "HIIT", "Strength", "Volume", etc.
ALTER TABLE exercises ADD COLUMN is_custom BOOLEAN DEFAULT FALSE;
ALTER TABLE exercises ADD COLUMN default_sets INTEGER;
ALTER TABLE exercises ADD COLUMN default_reps INTEGER;
ALTER TABLE exercises ADD COLUMN default_weight FLOAT;
ALTER TABLE exercises ADD COLUMN default_time_seconds INTEGER;
ALTER TABLE exercises ADD COLUMN default_rest_seconds INTEGER;
-- user_id will be added when authentication is implemented

-- Index for efficient variant queries
CREATE INDEX idx_exercises_base_exercise ON exercises(base_exercise_id);
CREATE INDEX idx_exercises_variant_type ON exercises(variant_type);
```

## API Changes

### New Endpoints:
- `POST /api/v1/exercises/{exercise_id}/duplicate` - Create custom exercise variant
  - Request body: `{ "variant_type": "HIIT", "name": "Dumbbell Lateral Raise (HIIT)", "default_sets": 3, "default_reps": 20, ... }`
  - Creates new exercise with all properties copied from base
  - Sets `base_exercise_id` to original exercise
  - Sets `is_custom` to True
- `GET /api/v1/exercises/{exercise_id}/variants` - List all variants of an exercise
- `GET /api/v1/exercises?custom=true` - List custom exercises
- `GET /api/v1/exercises?variant_type=HIIT` - List exercises filtered by variant type
- `GET /api/v1/exercises?base_exercise_id=123` - List all variants of a base exercise
- `PUT /api/v1/exercises/{exercise_id}` - Update custom exercise (only if is_custom=true)
- `DELETE /api/v1/exercises/{exercise_id}` - Delete custom exercise (only if is_custom=true)

### Updated Endpoints:
- `GET /api/v1/exercises/{exercise_id}/history` - Get exercise history
  - Returns history for the specific variant
  - Can filter by date range, workout style, etc.
- `GET /api/v1/recommendations/` - AI recommendations
  - When routine has workout_style="HIIT", prioritize HIIT variants
  - Use variant-specific history for recommendations

### Updated Endpoints:
- `POST /api/v1/routines/{routine_id}/slots` - Accept exercise parameters
- `PUT /api/v1/routines/{routine_id}/slots/{slot_id}` - Update exercise parameters

## UI/UX Considerations

### Web Interface (Routine Designer):
- **Exercise Selection**:
  - Show base exercises with variant indicators
  - Allow creating new variant on-the-fly ("Create HIIT variant")
  - Filter variants by workout style when routine style is set
  - Show variant defaults in selection preview
- **Variant Management**:
  - "Create Variant" button on exercise detail page
  - Variant creation wizard: select type (HIIT, Strength, etc.), set defaults
  - List of existing variants for each exercise
  - Edit/delete custom variants
- **Slot Configuration**:
  - When exercise variant selected, show variant defaults
  - Allow slot-level parameter overrides
  - Show parameter summary in slot preview

### Mobile App (Workout):
- **Exercise Selection**:
  - Filter to show variants matching routine's workout style
  - Show variant name clearly (e.g., "Dumbbell Lateral Raise (HIIT)")
  - Display variant defaults when selecting
- **Workout Execution**:
  - Display variant defaults when starting a slot
  - Show variant-specific history ("Last time: 3×20@10lbs")
  - Allow user to adjust before/during workout
  - Track actual performance vs. variant defaults
  - Show progress indicators (e.g., "2/3 sets completed")
- **History View**:
  - Filter history by variant type
  - Show variant-specific progression charts
  - Compare performance across variants (optional)

## Implementation Priority

**Phase 1 (MVP)**: Exercise Variants (Required for History Tracking)
- **Critical**: Needed for context-aware history tracking
- Database schema changes (add variant fields to exercises table)
- Variant creation API endpoint
- Variant filtering in exercise selection
- History queries filtered by variant

**Phase 2 (Enhancement)**: Slot-Level Parameter Overrides
- Allows fine-tuning variant defaults per slot
- Optional feature for advanced customization
- History still tracked by variant, overrides are just suggestions

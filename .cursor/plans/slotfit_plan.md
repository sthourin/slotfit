---
name: SlotFit - Workout Planning Web & Android App
overview: Build SlotFit - a workout app with flexible slot-based routines, AI exercise recommendations, and comprehensive workout tracking. Web-first development strategy to refine UI/UX before Android native development. SlotFit uses a novel approach where users select exercises on-the-fly during workouts based on available equipment.
todos: []
---

# SlotFit - Workout Planning and Tracking App

## Overview

SlotFit is a novel workout app that uses flexible slot-based routines instead of prescriptive exercise lists. Users define routine types (anterior, posterior, full body) and workout styles (5x5, HIIT), then select exercises on-the-fly during workouts based on available equipment. SlotFit includes AI-powered exercise recommendations, intelligent slot management, and comprehensive analytics.

## Development Strategy: Web-First

**Goal**: Build a fully-featured web application first to refine functionality and UI/UX before investing in Android native development.

### Web-First Rationale

- **Rapid Iteration**: Faster development cycles, easier debugging, instant updates
- **UI/UX Refinement**: Test and refine user flows before committing to native implementation
- **Feature Validation**: Validate slot-based approach with real usage before mobile build
- **Shared Backend**: Same API serves both web and future mobile clients
- **Lower Risk**: Identify and fix design issues early when changes are cheap

### Web App Limitations (Acknowledged)

The web app will NOT include features that require native capabilities:
- ❌ Bluetooth heart rate monitoring (Polar H10) - requires native BLE APIs
- ❌ True offline-first with background sync - limited to browser storage
- ❌ Push notifications for workout reminders
- ❌ Native gesture controls and haptic feedback
- ❌ Integration with Android Health APIs

These features are deferred to the Android app phase.

### Web App WILL Include

- ✅ Full workout execution (start, track, complete workouts)
- ✅ All slot-based features (navigation, reordering, supersets)
- ✅ AI exercise recommendations
- ✅ Manual heart rate entry (optional)
- ✅ Complete analytics and history
- ✅ Routine design and management
- ✅ Equipment profiles and filtering
- ✅ All intelligent slot features
- ✅ Browser-based local storage for session persistence

---

## Architecture Decision: New Workspace

**Recommendation: Start fresh in a new workspace**

**Database Choice**: PostgreSQL with proper relational modeling (many-to-many for exercises-muscle groups) is sufficient for MVP. Can migrate to graph database later if complex relationship queries are needed.

---

## Technology Stack

### Backend API

- **Framework**: Python FastAPI
  - Async support for concurrent requests
  - Automatic OpenAPI documentation
  - Easy integration with AI services
  - PostgreSQL with SQLAlchemy ORM

### Web Interface (Primary Development Focus)

- **Framework**: React with TypeScript
  - Component-based architecture
  - Reusable UI components
  - Modern development experience
- **State Management**: Zustand
- **Styling**: Tailwind CSS
- **Build Tool**: Vite

### Mobile App (Android) - Future Phase

- **Framework**: Native Android with Kotlin
  - Better performance for Bluetooth/BLE operations
  - Native UI/UX
  - Direct access to Android Health APIs
  - Room database for offline-first architecture

### AI Service Integration

- **Primary**: Anthropic Claude API
- **Future**: Ollama (self-hosted) support
- **Architecture**: Abstract AI provider behind interface for easy switching

### Database

- **Primary**: PostgreSQL
  - Relational data (users, routines, workouts, exercises)
  - JSONB columns for flexible exercise metadata
  - Full-text search for exercise discovery

---

## Core Data Models

### Exercise Database

- **Source**: Initial exercise database provided in `assets/slotfit_exercise_database_with_urls.csv`
- **Format**: CSV with comprehensive exercise data (3,244 exercises)
- **Fields**: 
  - Exercise name, description, difficulty level
  - Muscle groups: hierarchical 4-level structure (Target Muscle Group → Prime Mover → Secondary → Tertiary)
  - Equipment: Primary Equipment and Secondary Equipment fields
  - YouTube demonstration URLs (short and in-depth)
  - Movement patterns, planes of motion, body region, force type, mechanics, laterality
  - Exercise classification (Bodybuilding, Calisthenics, Postural, etc.)
- **Muscle Group Hierarchy**: 
  - Level 1: Target Muscle Group (e.g., "Abdominals", "Back", "Chest", "Glutes")
  - Level 2: Prime Mover Muscle (e.g., "Rectus Abdominis", "Latissimus Dorsi")
  - Level 3: Secondary Muscle
  - Level 4: Tertiary Muscle
- **Difficulty Levels**: Beginner, Novice, Intermediate, Advanced, Expert
- **Equipment**: Extracted from Primary and Secondary Equipment fields in CSV

### Exercise Variants (User-Created)

- **Purpose**: Enable context-aware history tracking (HIIT vs Strength history separation)
- Users can duplicate any exercise from the database to create custom variants
- Variants are categorized by `variant_type` (e.g., "HIIT", "Strength", "Volume", "Endurance")
- Duplicated exercises can be renamed (e.g., "Dumbbell Lateral Raise (Strength)")
- Custom exercises inherit all properties from the original (muscle groups, equipment, etc.)
- Variants can have default parameters: `default_sets`, `default_reps`, `default_weight`, `default_time_seconds`, `default_rest_seconds`
- Custom exercises are linked to the original via `base_exercise_id` for tracking
- **History Tracking**: Each variant maintains its own performance history
- Custom exercises are user-specific (when authentication is added)

### Equipment Profiles (NEW)

- **Purpose**: Save equipment configurations tied to locations for quick selection
- **Fields**:
  - `id`: Unique identifier
  - `name`: Profile name (e.g., "Home Gym", "Work Gym", "Hotel", "Outdoor")
  - `equipment_ids`: Array of available equipment IDs
  - `is_default`: Boolean - auto-select this profile when starting workout
  - `user_id`: Owner (when auth added)
- **Usage**: 
  - User selects profile at workout start → auto-applies equipment filter
  - Can still modify equipment per-slot during workout
  - Reduces friction of re-selecting equipment every session

### Slot Templates (NEW - Reusable)

- **Purpose**: Define reusable slot configurations that can be imported into multiple routines
- **Fields**:
  - `id`: Unique identifier
  - `name`: Template name (e.g., "My Back Slot", "HIIT Finisher")
  - `muscle_group_ids`: Array of muscle group IDs for slot scope
  - `slot_type`: "standard" | "warmup" | "finisher" | "active_recovery" | "wildcard"
  - `time_limit_seconds`: Optional time cap for the slot
  - `default_exercise_id`: Optional pre-selected exercise
  - `target_parameters`: Default target sets/reps/weight/time/rest
  - `notes`: User notes about this slot template
- **Benefits**:
  - "My Back Slot" can be imported into multiple routines
  - Standardizes slot configurations across routines
  - Easier routine creation

### Routine Template

- Routine type: anterior, posterior, full body, custom
- Workout style: 5x5, HIIT, volume, strength, custom
- Slots: Array of slot definitions
  - Each slot: muscle group(s) scope, order, optional name
  - **Slot-to-Exercise**: One exercise per slot (1:1 relationship)
  - **Muscle Group Scope**: Defined at slot creation time
  - **Slot Types** (NEW):
    - `standard`: Regular exercise slot
    - `warmup`: Auto-suggests mobility/activation exercises for subsequent slots
    - `finisher`: High-rep burnout exercises for underworked muscle groups
    - `active_recovery`: Stretching/foam rolling cues between heavy slots
    - `wildcard`: No muscle group scope - full exercise database available
  - **Exercise Parameters at Slot Level**: 
    - Each slot can store target parameters for the selected exercise
    - **Parameter Ranges** (NEW): Support min/max ranges (e.g., `target_reps_min: 8`, `target_reps_max: 12`)
    - **Progression Rules** (NEW): Optional auto-progression (e.g., "Increase weight by 2.5lbs when max reps achieved on all sets")
    - Parameters are optional - if not set, user enters during workout
  - **Time Constraints** (NEW):
    - Optional `time_limit_seconds` per slot
    - Visual countdown during workout
    - Auto-suggest moving to next slot when time expires
    - Useful for HIIT or circuit-style workouts
  - **Conditional Visibility** (NEW):
    - `required_equipment_ids`: Only show slot if user has this equipment
    - Reduces clutter when equipment is limited
  - **Superset Linking**: Slots can be linked together for supersets
    - Can be linked when creating routine template OR on-the-fly during workout
    - Linked slots: exercises performed back-to-back with minimal rest
    - **Superset Templates** (NEW): Pre-defined pairings (e.g., "Antagonist Pairs": Biceps/Triceps)
    - Constraint: A slot can only be part of one superset
  - **Slot Ordering**: Order is mutable - user can re-order slots during workout

### Workout Session

- Based on routine template
- **Workout States**: draft, active, paused, completed, abandoned
- **Editing Rules**: Fully editable in all states
- **Auto-Save & Recovery**: Progress saved automatically, recovers after browser refresh/crash
- **Completion**: Slots are NOT required for workout completion
- **Slot Behavior**:
  - User can skip slots during workout
  - Can return to skipped slots later
  - Can re-order slots during workout (dynamic slot sequencing)
  - Slot states: not_started, in_progress, completed, skipped
- **Smart Features** (NEW):
  - **Quick-Fill Mode**: Auto-select exercises for all slots based on equipment profile
  - **"Last Workout" Template**: One-tap to pre-populate with exercises from most recent workout using same routine
  - **Progressive Overload Suggestions**: When auto-filling, suggest slightly higher weight/reps than last session
- Exercise performance (sets, reps, weight, rest time)
- Start/stop timestamps for exercises within slots
- Manual heart rate entry (web) / BLE heart rate (Android future)

### User Account

- **MVP**: Authentication deferred - browser local storage for session persistence
- **Future**: Authentication (JWT tokens), profile data, workout history sync

---

## Key Features

### 1. Slot-Based Routine System

#### Routine Design (Web)
- Create/edit routine templates with flexible slots
- Define slot order and muscle group scope
- Each slot can target: single muscle group, multiple groups, or full body
- **Slot Type Selection**: Choose from standard, warmup, finisher, active_recovery, wildcard
- **Time Constraints**: Set optional time limits per slot
- **Conditional Slots**: Mark slots as equipment-dependent
- Link slots for supersets with superset templates
- Import reusable slot templates
- Preview routine structure

#### Exercise Selection (During Workout)
- SlotFit filters exercises by slot's muscle group scope
- **Equipment Profile**: Select profile at workout start, auto-applies filter
- **Per-Slot Equipment Override**: Can modify equipment for individual slots
- **Equipment Substitution Intelligence** (NEW):
  - When preferred exercise unavailable, show "Similar Alternatives"
  - Rank alternatives by muscle activation similarity (using movement patterns, planes of motion data)
  - Track substitution patterns to improve future recommendations
- User selects from filtered, AI-prioritized list
- Can switch exercises mid-workout if equipment unavailable

### 2. AI Exercise Recommendations

#### Standard Recommendations
- **Context**: Slot's muscle group scope, user's workout history, available equipment
- **Provider**: Claude API (swappable to Ollama)
- **Response Format**: Structured JSON
  ```json
  {
    "recommendations": [
      {
        "exercise_id": "uuid",
        "exercise_name": "string",
        "priority_score": 0.0-1.0,
        "reasoning": "brief explanation",
        "factors": {
          "frequency": "low|medium|high",
          "last_performed": "ISO8601 date or null",
          "progression_opportunity": true/false,
          "variety_boost": true/false,
          "movement_balance": "string (NEW)",
          "weekly_volume_status": "string (NEW)"
        }
      }
    ],
    "not_recommended": [  // NEW
      {
        "exercise_id": "uuid",
        "exercise_name": "string",
        "reason": "performed 2 days ago (recovery)" | "equipment not available" | "weekly volume exceeded"
      }
    ],
    "total_candidates": 15,
    "filtered_by_equipment": 8
  }
  ```
- **Count**: Top 5 recommendations per request
- **Caching**: Cache recommendations per slot+equipment combo for 1 hour

#### Enhanced AI Features (NEW)

- **"Why Not" Explanations**: Expandable section showing exercises NOT recommended and why
- **Periodization Awareness**: 
  - Track weekly volume per muscle group
  - Factor weekly load into recommendations
  - "You've done 15 sets of chest this week" → deprioritize or suggest lighter volume
- **Movement Pattern Balance**:
  - Balance Horizontal Push vs. Pull
  - Balance Sagittal vs. Transverse plane movements
  - Balance Compound vs. Isolation ratio
- **Goal-Based Slot Generation** (NEW):
  - User input: "I have 30 minutes and dumbbells"
  - AI generates appropriate number of slots with muscle group scopes
  - Creates ad-hoc routine based on constraints

#### Fallback (When AI Unavailable)
- Return exercises filtered by muscle group + equipment
- Sort by recency (least recent first for variety)
- Random if no history available

### 3. Intelligent Slot Features (NEW)

#### Slot Types

**Warm-Up Slots**
- Dedicated slot type for workout preparation
- Auto-suggests mobility/activation exercises specific to muscle groups in subsequent slots
- Examples: Hip circles before squats, band pull-aparts before bench press

**Finisher Slots**
- Optional slot type at routine end
- Suggests high-rep, burnout exercises
- Prioritizes muscle groups with least total volume in session
- Examples: 21s for biceps, drop sets for triceps

**Active Recovery Slots**
- Insert between heavy compound slots
- Suggests stretching, foam rolling, or light mobility work
- Helps manage fatigue during long workouts

**Wildcard Slots**
- No muscle group scope restriction
- Full exercise database available
- Use case: "Finish with whatever feels good"

#### Smart Auto-Population

**Quick-Fill Mode**
- At workout start, auto-select exercises for all slots
- Based on: equipment profile, workout history, AI recommendations
- User reviews and confirms or swaps individual exercises
- Dramatically reduces workout setup time

**"Last Workout" Template**
- One-tap to pre-populate slots with exercises from most recent workout using same routine
- Useful for consistent training programs
- Still allows per-slot modifications

**Progressive Overload Suggestions**
- When auto-filling or viewing exercise history
- Suggest slightly higher weight/reps than last session
- Based on progression rules defined at slot level

#### Dynamic Slot Management

**Fatigue-Aware Slot Ordering** (Future Enhancement)
- Re-order remaining slots based on real-time data
- Move to lower-intensity slots if fatigue indicators present
- Web: Based on time between sets, user feedback
- Android: Will include HR data

**Slot Navigation**
- Visual progress bar showing: completed | in-progress | upcoming | skipped
- Click/tap any slot to jump directly
- Swipe gestures for next/previous (on touch devices)
- Keyboard shortcuts for power users (web)

### 4. Rest Period Intelligence (NEW)

- **Context-Aware Rest Timers**:
  - Different defaults based on workout style (longer for strength, shorter for HIIT)
  - Superset rest: slightly longer (both muscle groups fatigued)
  - Straight set rest: based on exercise type
- **Smart Rest Suggestions** (Android future):
  - "Your HR is still at 85%, consider extending rest"
  - Based on heart rate recovery patterns
- **Rest Timer Features**:
  - Audible alerts (configurable)
  - Visual countdown
  - Skip rest option
  - Extend rest option

### 5. Workout Tracking

- **Exercise Performance**: Sets, reps, weight, rest time
- **Exercise Timing**: Start/stop timestamps for each exercise
- **Personal Records** (NEW):
  - Track PRs per exercise variant
  - "HIIT Lateral Raise PR: 25 reps @ 10lbs"
  - "Strength Lateral Raise PR: 8 reps @ 30lbs"
  - PR notifications during workout
- **Analytics**: Performance trends, volume progression
- **Exercise Parameters**: 
  - Target parameters with min/max ranges
  - Actual performance tracked in WorkoutSet
  - Progression rule evaluation

### 6. Analytics & Reporting (NEW Enhanced)

#### Slot-Level Analytics
- Track metrics at the slot level across workouts
- "Back Slot Performance": avg exercises used, avg sets completed, volume trends
- Identify slots that frequently get skipped → suggest removal or re-scoping
- Slot completion rates by routine

#### Exercise Analytics
- **Exercise Fatigue Patterns**: Identify exercises that consistently extend rest times
- **Substitution Tracking**: Which exercises get swapped most often and for what
- **Progression Curves**: Visualize strength gains per exercise over time

#### Workout Analytics
- Volume per muscle group (weekly, monthly)
- Workout duration trends
- Completion rates (full vs. partial workouts)
- Most/least used exercises
- Movement pattern distribution

#### Export Capabilities
- CSV export for workout history
- PDF workout summaries (future)

### 7. Heart Rate Monitoring

#### Web App (MVP)
- **Manual Entry**: Optional HR logging during workout
- **Basic Zones**: Display zone based on entered HR
- **No Real-Time Tracking**: Deferred to Android

#### Android App (Future)
- **Device**: Polar H10 (Bluetooth Low Energy)
- **Features**:
  - Real-time heart rate display during workout
  - Heart rate zones (fat burn, cardio, peak, maximum)
  - Time-series recording per exercise and slot (1Hz)
  - **Data Retention**: Raw time-series kept until analysis complete, then dropped
  - **Analytics**: Comprehensive metrics at exercise/slot/workout levels
  - **HR-Based Rest Suggestions**: Extend rest if HR elevated

---

## Implementation Plan

### Phase 1: Backend Foundation ✅ (Partially Complete)

1. **Project Setup** ✅
   - FastAPI project structure
   - PostgreSQL database setup
   - Alembic migrations
   - API Versioning (`/api/v1/`)

2. **Core Models** ✅
   - Exercise model (with muscle group relationships)
   - Routine template model
   - Workout session model
   - Equipment model

3. **New Models Required**
   - Equipment Profile model
   - Slot Template model (reusable)
   - Enhanced Slot model (types, time limits, conditions)
   - Personal Records model

4. **API Endpoints** (all under `/api/v1/`)
   - Exercise CRUD (`/api/v1/exercises`)
   - Exercise variants (`/api/v1/exercises/{id}/duplicate`)
   - Routine template CRUD (`/api/v1/routines`)
   - Slot templates CRUD (`/api/v1/slot-templates`) - NEW
   - Equipment profiles CRUD (`/api/v1/equipment-profiles`) - NEW
   - Workout session endpoints (`/api/v1/workouts`)
   - AI recommendation endpoint (`/api/v1/recommendations`)
   - Analytics endpoints (`/api/v1/analytics`) - NEW
   - Personal records (`/api/v1/personal-records`) - NEW

### Phase 2: AI Integration

1. **AI Service Abstraction**
   - Interface for AI providers
   - Claude API implementation
   - Ollama implementation (future)
   - Configuration for switching providers

2. **Exercise Recommendation Service**
   - Context building (slot scope, user history, equipment)
   - Prompt engineering for recommendations
   - Response parsing and validation
   - **Enhanced features**:
     - "Why Not" explanations
     - Periodization awareness (weekly volume tracking)
     - Movement pattern balance
   - Fallback mechanism (rule-based when AI unavailable)
   - Response caching (1 hour per slot+equipment combo)

3. **Goal-Based Slot Generation Service** (NEW)
   - Parse user constraints (time, equipment)
   - Generate appropriate slot structure
   - AI-powered routine creation

### Phase 3: Web App - Routine Designer

1. **Routine Management**
   - Create/edit routine templates
   - Define slots with muscle group scopes
   - **Slot type selection**: standard, warmup, finisher, active_recovery, wildcard
   - **Time constraints**: Set time limits per slot
   - **Conditional slots**: Equipment requirements
   - Link slots for supersets
   - **Superset templates**: Pre-defined antagonist pairs
   - Preview routine structure

2. **Slot Template Management** (NEW)
   - Create reusable slot templates
   - Import slot templates into routines
   - Share slot templates (future)

3. **Exercise Database Browser**
   - Search and filter exercises
   - View exercise details (muscles, equipment, videos)
   - Create exercise variants
   - Equipment filter interface

4. **Equipment Profile Management** (NEW)
   - Create/edit equipment profiles
   - Set default profile
   - Quick equipment selection

### Phase 4: Web App - Workout Execution (PRIMARY FOCUS)

1. **Workout Start Flow**
   - Select routine
   - **Equipment profile selection**: Auto-apply or choose
   - **Quick-Fill option**: Auto-populate all slots
   - **"Last Workout" option**: Copy from previous session
   - Review and confirm slot exercises

2. **Active Workout Interface**
   - **Slot Navigation**:
     - Visual progress bar (completed | in-progress | upcoming | skipped)
     - Click to jump to any slot
     - Keyboard shortcuts (←/→ for prev/next, S to skip, Enter to complete)
   - **Exercise Display**:
     - Current exercise with target parameters
     - YouTube video links
     - Historical performance for this exercise
     - **Progressive overload suggestion**
   - **Set Tracking**:
     - Log reps, weight, rest time
     - Quick increment/decrement buttons
     - Auto-advance to next set
   - **Rest Timer**:
     - Context-aware default duration
     - Visual countdown
     - Audio alert option
     - Extend/skip buttons
   - **Slot Actions**:
     - Complete slot
     - Skip slot
     - Change exercise (with AI recommendations)
     - Reorder slots (drag-and-drop)

3. **Superset Handling**
   - Visual grouping of linked slots
   - Back-to-back exercise flow
   - Shared rest timer after superset complete

4. **Workout State Management**
   - Auto-save on every action
   - Browser storage for crash recovery
   - Pause/resume functionality
   - Abandon with confirmation
   - Complete workout summary

5. **In-Workout AI Features**
   - **Exercise recommendations** with "Why Not" explanations
   - **Alternative suggestions** when equipment changes
   - **Equipment substitution intelligence**

### Phase 5: Web App - Analytics & History

1. **Workout History**
   - List of past workouts
   - Workout detail view
   - Edit completed workouts

2. **Analytics Dashboard**
   - **Workout Analytics**:
     - Volume per muscle group (charts)
     - Workout duration trends
     - Completion rates
   - **Slot Analytics** (NEW):
     - Slot completion rates
     - Frequently skipped slots
     - Exercise variety per slot
   - **Exercise Analytics**:
     - Progression curves
     - Personal records
     - Exercise frequency
   - **Movement Balance** (NEW):
     - Push/Pull ratio
     - Plane of motion distribution
     - Compound/Isolation ratio

3. **Personal Records**
   - PR list by exercise (and variant)
   - PR history and dates
   - PR notifications

4. **Export Features**
   - CSV export for workout history
   - Date range filtering

### Phase 6: Web App - Polish & Refinement

1. **UI/UX Improvements**
   - Responsive design (desktop, tablet, mobile web)
   - Dark mode
   - Accessibility improvements
   - Loading states and error handling
   - Keyboard navigation

2. **Performance Optimization**
   - API response caching
   - Optimistic updates
   - Lazy loading for exercise lists

3. **User Preferences**
   - Units (metric/imperial)
   - Default rest times
   - Audio preferences
   - Theme selection

4. **Testing & Quality**
   - Unit tests
   - Integration tests
   - E2E tests (Playwright)
   - User testing feedback incorporation

### Phase 7: Android App (Future)

1. **Core App Structure**
   - Kotlin project setup
   - Room database schema (mirroring backend models)
   - Navigation architecture
   - Offline-first data layer

2. **Bluetooth Heart Rate**
   - BLE scanning and connection
   - Polar H10 protocol implementation
   - Real-time HR data capture (1Hz)
   - Heart rate zone calculations
   - **HR-based rest suggestions**
   - **Fatigue-aware slot reordering**

3. **Workout Interface**
   - Port web workout flow to native
   - Native gesture controls (swipe, long-press)
   - Haptic feedback
   - **Voice control**: "Next slot", "Skip", "Mark complete"
   - Keep screen awake during workout

4. **Offline Sync**
   - Queue-based sync
   - Conflict resolution (user-driven)
   - Background sync service

5. **Native Features**
   - Push notifications (workout reminders)
   - Android Health integration
   - Widget for quick workout start
   - Wear OS companion (future)

---

## Database Schema

```sql
-- Equipment Profiles (NEW)
equipment_profiles (
  id SERIAL PRIMARY KEY,
  name VARCHAR NOT NULL,
  equipment_ids JSONB NOT NULL,  -- Array of equipment IDs
  is_default BOOLEAN DEFAULT FALSE,
  user_id INTEGER  -- NULL for MVP
)

-- Slot Templates (NEW - Reusable)
slot_templates (
  id SERIAL PRIMARY KEY,
  name VARCHAR NOT NULL,
  slot_type VARCHAR DEFAULT 'standard',  -- standard, warmup, finisher, active_recovery, wildcard
  muscle_group_ids JSONB NOT NULL,
  time_limit_seconds INTEGER,
  default_exercise_id INTEGER REFERENCES exercises(id),
  target_sets INTEGER,
  target_reps_min INTEGER,
  target_reps_max INTEGER,
  target_weight FLOAT,
  target_rest_seconds INTEGER,
  notes TEXT,
  user_id INTEGER  -- NULL for MVP
)

-- Superset Templates (NEW)
superset_templates (
  id SERIAL PRIMARY KEY,
  name VARCHAR NOT NULL,  -- e.g., "Antagonist Pairs"
  description TEXT,
  slot_pairings JSONB NOT NULL  -- Array of muscle group pairs
)

-- Enhanced Routine Slots
routine_slots (
  id SERIAL PRIMARY KEY,
  routine_template_id INTEGER REFERENCES routine_templates(id),
  slot_template_id INTEGER REFERENCES slot_templates(id),  -- Optional, if using template
  name VARCHAR,
  slot_type VARCHAR DEFAULT 'standard',
  order_index INTEGER NOT NULL,
  muscle_group_ids JSONB NOT NULL,
  superset_tag VARCHAR,
  selected_exercise_id INTEGER REFERENCES exercises(id),
  time_limit_seconds INTEGER,
  required_equipment_ids JSONB,  -- NEW: Conditional visibility
  target_sets INTEGER,
  target_reps_min INTEGER,
  target_reps_max INTEGER,
  target_weight FLOAT,
  target_time_seconds INTEGER,
  target_rest_seconds INTEGER,
  progression_rule JSONB  -- NEW: Auto-progression config
)

-- Personal Records (NEW)
personal_records (
  id SERIAL PRIMARY KEY,
  exercise_id INTEGER REFERENCES exercises(id),
  record_type VARCHAR NOT NULL,  -- 'weight', 'reps', 'volume', 'time'
  value FLOAT NOT NULL,
  context JSONB,  -- Additional context (reps for weight PR, weight for rep PR)
  achieved_at TIMESTAMP NOT NULL,
  workout_session_id INTEGER REFERENCES workout_sessions(id),
  user_id INTEGER  -- NULL for MVP
)

-- Weekly Volume Tracking (NEW - for periodization)
weekly_volume (
  id SERIAL PRIMARY KEY,
  muscle_group_id INTEGER REFERENCES muscle_groups(id),
  week_start DATE NOT NULL,
  total_sets INTEGER DEFAULT 0,
  total_reps INTEGER DEFAULT 0,
  total_volume FLOAT DEFAULT 0,  -- weight × reps
  user_id INTEGER,  -- NULL for MVP
  UNIQUE(muscle_group_id, week_start, user_id)
)

-- Exercise Substitution History (NEW)
exercise_substitutions (
  id SERIAL PRIMARY KEY,
  original_exercise_id INTEGER REFERENCES exercises(id),
  substituted_exercise_id INTEGER REFERENCES exercises(id),
  reason VARCHAR,  -- 'equipment', 'preference', 'fatigue'
  workout_session_id INTEGER REFERENCES workout_sessions(id),
  created_at TIMESTAMP DEFAULT NOW()
)

-- Existing tables (enhanced)
exercises (...)  -- As defined previously
muscle_groups (...)
exercise_muscle_groups (...)
equipment (...)
routine_templates (...)
workout_sessions (...)
workout_exercises (...)
workout_sets (...)
heart_rate_readings (...)  -- For Android future
heart_rate_analytics (...)  -- For Android future
```

---

## File Structure

```
slotfit/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── endpoints/
│   │   │       │   ├── exercises.py
│   │   │       │   ├── routines.py
│   │   │       │   ├── workouts.py
│   │   │       │   ├── slot_templates.py      # NEW
│   │   │       │   ├── equipment_profiles.py  # NEW
│   │   │       │   ├── recommendations.py
│   │   │       │   ├── analytics.py           # NEW
│   │   │       │   └── personal_records.py    # NEW
│   │   │       └── api.py
│   │   ├── models/
│   │   │   ├── exercise.py
│   │   │   ├── routine.py
│   │   │   ├── workout.py
│   │   │   ├── equipment.py
│   │   │   ├── slot_template.py      # NEW
│   │   │   ├── equipment_profile.py  # NEW
│   │   │   ├── personal_record.py    # NEW
│   │   │   └── analytics.py          # NEW
│   │   ├── schemas/
│   │   ├── services/
│   │   │   ├── ai/
│   │   │   │   ├── base.py
│   │   │   │   ├── claude_provider.py
│   │   │   │   ├── recommendation_service.py
│   │   │   │   └── slot_generation_service.py  # NEW
│   │   │   ├── analytics_service.py    # NEW
│   │   │   ├── progression_service.py  # NEW
│   │   │   └── personal_records_service.py  # NEW
│   │   └── core/
│   ├── alembic/
│   └── tests/
├── web/
│   ├── src/
│   │   ├── components/
│   │   │   ├── common/           # Buttons, inputs, modals
│   │   │   ├── exercises/        # Exercise browser, cards
│   │   │   ├── routines/         # Routine designer components
│   │   │   ├── slots/            # Slot components, templates
│   │   │   ├── workout/          # Active workout components
│   │   │   │   ├── SlotProgressBar.tsx
│   │   │   │   ├── ExercisePanel.tsx
│   │   │   │   ├── SetTracker.tsx
│   │   │   │   ├── RestTimer.tsx
│   │   │   │   ├── QuickFillModal.tsx      # NEW
│   │   │   │   └── RecommendationsPanel.tsx
│   │   │   ├── analytics/        # Charts, stats displays
│   │   │   └── equipment/        # Equipment profiles
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Routines.tsx
│   │   │   ├── RoutineDesigner.tsx
│   │   │   ├── SlotTemplates.tsx         # NEW
│   │   │   ├── EquipmentProfiles.tsx     # NEW
│   │   │   ├── Workout.tsx               # Active workout page
│   │   │   ├── WorkoutHistory.tsx
│   │   │   ├── Analytics.tsx
│   │   │   ├── PersonalRecords.tsx       # NEW
│   │   │   └── ExerciseLibrary.tsx
│   │   ├── services/
│   │   │   └── api.ts
│   │   ├── stores/
│   │   │   ├── workoutStore.ts
│   │   │   ├── routineStore.ts
│   │   │   └── equipmentStore.ts
│   │   ├── hooks/
│   │   │   ├── useWorkout.ts
│   │   │   ├── useRestTimer.ts
│   │   │   └── useKeyboardShortcuts.ts   # NEW
│   │   ├── utils/
│   │   ├── App.tsx
│   │   └── main.tsx
│   └── public/
├── android/                      # Future phase
│   └── ... (existing structure)
├── assets/
│   └── slotfit_exercise_database_with_urls.csv
└── docs/
    ├── API.md
    ├── WORKOUT_FLOW.md           # NEW
    └── SLOT_TYPES.md             # NEW
```

---

## Feature Priority Matrix

| Priority | Feature | Phase | Impact | Effort |
|----------|---------|-------|--------|--------|
| **P0 - Core** | Basic workout execution | 4 | Critical | High |
| **P0 - Core** | Slot navigation & management | 4 | Critical | Medium |
| **P0 - Core** | Exercise selection with filters | 4 | Critical | Medium |
| **P0 - Core** | Set/rep/weight tracking | 4 | Critical | Medium |
| **P1 - High** | Equipment profiles | 3 | High | Medium |
| **P1 - High** | Quick-Fill mode | 4 | High | Medium |
| **P1 - High** | AI recommendations | 2 | High | Medium |
| **P1 - High** | Rest timer | 4 | High | Low |
| **P1 - High** | Workout history | 5 | High | Medium |
| **P2 - Medium** | Slot types (warmup, finisher, etc.) | 3 | Medium | Low |
| **P2 - Medium** | "Last Workout" template | 4 | Medium | Low |
| **P2 - Medium** | Movement pattern balance in AI | 2 | Medium | Low |
| **P2 - Medium** | Progressive overload suggestions | 4 | Medium | Medium |
| **P2 - Medium** | Slot-level analytics | 5 | Medium | Medium |
| **P2 - Medium** | Personal records tracking | 5 | Medium | Medium |
| **P2 - Medium** | Wildcard slots | 3 | Medium | Low |
| **P2 - Medium** | Time-constrained slots | 3 | Medium | Low |
| **P3 - Lower** | "Why Not" explanations | 2 | Medium | Low |
| **P3 - Lower** | Superset templates | 3 | Medium | Low |
| **P3 - Lower** | Slot templates (reusable) | 3 | Medium | Medium |
| **P3 - Lower** | Periodization awareness | 2 | Medium | Medium |
| **P3 - Lower** | Keyboard shortcuts | 6 | Low | Low |
| **P3 - Lower** | Exercise substitution tracking | 5 | Low | Low |
| **Future** | Voice control | 7 | Medium | High |
| **Future** | Bluetooth HR monitoring | 7 | High | High |
| **Future** | Routine marketplace | 7+ | High | High |
| **Future** | Offline sync | 7 | High | High |

---

## Next Steps (Updated)

### Immediate (Phase 1-2 Completion)
1. ✅ Backend project structure
2. ✅ Core database models
3. [ ] Add new models: EquipmentProfile, SlotTemplate, PersonalRecord, WeeklyVolume
4. [ ] Create Alembic migrations for new models
5. [ ] Implement equipment profiles API
6. [ ] Implement slot templates API
7. [ ] Enhance AI recommendation service with periodization awareness
8. [ ] Add "Why Not" explanations to AI responses

### Short-term (Phase 3-4)
9. [ ] Build routine designer with enhanced slot features
10. [ ] Implement equipment profile UI
11. [ ] Build active workout interface (PRIMARY FOCUS)
12. [ ] Implement slot navigation with progress bar
13. [ ] Add Quick-Fill mode
14. [ ] Implement rest timer with context-aware defaults
15. [ ] Add progressive overload suggestions

### Medium-term (Phase 5-6)
16. [ ] Build analytics dashboard
17. [ ] Implement personal records tracking
18. [ ] Add slot-level analytics
19. [ ] Polish UI/UX based on usage
20. [ ] Implement keyboard shortcuts
21. [ ] Add dark mode

### Long-term (Phase 7)
22. [ ] Port to Android native
23. [ ] Implement Bluetooth HR monitoring
24. [ ] Add offline-first with sync
25. [ ] Voice control
26. [ ] Push notifications

---

## Success Metrics

### Web App Launch Criteria
- [ ] Can create routines with all slot types
- [ ] Can execute full workout with slot navigation
- [ ] Can track sets/reps/weight accurately
- [ ] Can view workout history and basic analytics
- [ ] Auto-save prevents data loss
- [ ] AI recommendations working with fallback
- [ ] Equipment profiles reduce setup friction
- [ ] Quick-Fill mode works for repeat workouts

### User Experience Goals
- Workout setup time < 30 seconds (with Quick-Fill)
- Zero data loss from browser issues
- Intuitive slot navigation without training
- Clear visual feedback for workout progress
- Responsive on desktop and mobile web

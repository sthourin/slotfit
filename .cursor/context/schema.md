# Database Schema Quick Reference

## Current Tables

### exercises
```sql
id SERIAL PRIMARY KEY
name VARCHAR NOT NULL
description TEXT
difficulty VARCHAR  -- Beginner, Novice, Intermediate, Advanced, Expert
primary_equipment VARCHAR
secondary_equipment VARCHAR
base_exercise_id INTEGER REFERENCES exercises(id)  -- For variants
variant_type VARCHAR  -- HIIT, Strength, Volume, Endurance, Custom
is_custom BOOLEAN DEFAULT FALSE
default_sets INTEGER
default_reps INTEGER
default_weight FLOAT
default_time_seconds INTEGER
default_rest_seconds INTEGER
user_id INTEGER  -- NULL for MVP
created_at TIMESTAMP
updated_at TIMESTAMP
```

### muscle_groups
```sql
id SERIAL PRIMARY KEY
name VARCHAR NOT NULL
parent_id INTEGER REFERENCES muscle_groups(id)
level INTEGER  -- 1=Target, 2=Prime, 3=Secondary, 4=Tertiary
```

### equipment
```sql
id SERIAL PRIMARY KEY
name VARCHAR NOT NULL UNIQUE
category VARCHAR
```

### routine_templates
```sql
id SERIAL PRIMARY KEY
name VARCHAR NOT NULL
routine_type VARCHAR  -- anterior, posterior, full_body, custom
workout_style VARCHAR  -- 5x5, HIIT, volume, strength, custom
description TEXT
user_id INTEGER  -- NULL for MVP
created_at TIMESTAMP
updated_at TIMESTAMP
```

### routine_slots
```sql
id SERIAL PRIMARY KEY
routine_template_id INTEGER REFERENCES routine_templates(id) NOT NULL
name VARCHAR
order_index INTEGER NOT NULL  -- Renamed from 'order' to avoid SQL keyword
muscle_group_ids JSONB NOT NULL  -- Array of muscle group IDs
superset_tag VARCHAR
selected_exercise_id INTEGER REFERENCES exercises(id)
workout_style VARCHAR  -- Override routine's workout_style

-- NEW FIELDS TO ADD:
slot_type VARCHAR DEFAULT 'standard'  -- standard, warmup, finisher, active_recovery, wildcard
slot_template_id INTEGER REFERENCES slot_templates(id)
time_limit_seconds INTEGER
required_equipment_ids JSONB
target_sets INTEGER
target_reps_min INTEGER
target_reps_max INTEGER
target_weight FLOAT
target_time_seconds INTEGER
target_rest_seconds INTEGER
progression_rule JSONB
```

### workout_sessions
```sql
id SERIAL PRIMARY KEY
routine_template_id INTEGER REFERENCES routine_templates(id)
state VARCHAR NOT NULL DEFAULT 'draft'  -- draft, active, paused, completed, abandoned
started_at TIMESTAMP
paused_at TIMESTAMP
completed_at TIMESTAMP
user_id INTEGER  -- NULL for MVP
```

### workout_exercises
```sql
id SERIAL PRIMARY KEY
workout_session_id INTEGER REFERENCES workout_sessions(id) NOT NULL
slot_id INTEGER REFERENCES routine_slots(id)
exercise_id INTEGER REFERENCES exercises(id) NOT NULL
slot_state VARCHAR DEFAULT 'not_started'  -- not_started, in_progress, completed, skipped
started_at TIMESTAMP
stopped_at TIMESTAMP
```

### workout_sets
```sql
id SERIAL PRIMARY KEY
workout_exercise_id INTEGER REFERENCES workout_exercises(id) NOT NULL
set_number INTEGER NOT NULL
reps INTEGER
weight FLOAT
rest_seconds INTEGER
notes TEXT
```

---

## NEW TABLES TO CREATE

### equipment_profiles
```sql
id SERIAL PRIMARY KEY
name VARCHAR NOT NULL
equipment_ids JSONB NOT NULL  -- Array of equipment IDs
is_default BOOLEAN DEFAULT FALSE
user_id INTEGER  -- NULL for MVP
created_at TIMESTAMP DEFAULT NOW()
updated_at TIMESTAMP DEFAULT NOW()
```

### slot_templates
```sql
id SERIAL PRIMARY KEY
name VARCHAR NOT NULL
slot_type VARCHAR DEFAULT 'standard'
muscle_group_ids JSONB NOT NULL
time_limit_seconds INTEGER
default_exercise_id INTEGER REFERENCES exercises(id)
target_sets INTEGER
target_reps_min INTEGER
target_reps_max INTEGER
target_weight FLOAT
target_rest_seconds INTEGER
notes TEXT
user_id INTEGER  -- NULL for MVP
created_at TIMESTAMP DEFAULT NOW()
updated_at TIMESTAMP DEFAULT NOW()
```

### superset_templates
```sql
id SERIAL PRIMARY KEY
name VARCHAR NOT NULL
description TEXT
slot_pairings JSONB NOT NULL  -- Array of muscle group pairs
```

### personal_records
```sql
id SERIAL PRIMARY KEY
exercise_id INTEGER REFERENCES exercises(id) NOT NULL
record_type VARCHAR NOT NULL  -- weight, reps, volume, time
value FLOAT NOT NULL
context JSONB  -- e.g., {"reps": 8} for weight PR
achieved_at TIMESTAMP NOT NULL
workout_session_id INTEGER REFERENCES workout_sessions(id)
user_id INTEGER  -- NULL for MVP
```

### weekly_volume
```sql
id SERIAL PRIMARY KEY
muscle_group_id INTEGER REFERENCES muscle_groups(id) NOT NULL
week_start DATE NOT NULL
total_sets INTEGER DEFAULT 0
total_reps INTEGER DEFAULT 0
total_volume FLOAT DEFAULT 0
user_id INTEGER  -- NULL for MVP
UNIQUE(muscle_group_id, week_start, user_id)
```

### exercise_substitutions
```sql
id SERIAL PRIMARY KEY
original_exercise_id INTEGER REFERENCES exercises(id) NOT NULL
substituted_exercise_id INTEGER REFERENCES exercises(id) NOT NULL
reason VARCHAR  -- equipment, preference, fatigue
workout_session_id INTEGER REFERENCES workout_sessions(id)
created_at TIMESTAMP DEFAULT NOW()
```

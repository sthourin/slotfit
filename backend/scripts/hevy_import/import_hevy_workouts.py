"""
Import Hevy workout data into Slotfit database

This script:
1. Queries existing Slotfit exercises and builds a mapping
2. Creates new exercises for any Hevy exercises not found in Slotfit
3. Gets or creates an import user
4. Imports all workout sessions with exercises and sets

Usage:
    cd backend
    python scripts/hevy_import/import_hevy_workouts.py
    
    # Dry run (no database changes):
    python scripts/hevy_import/import_hevy_workouts.py --dry-run
    
    # Verbose output:
    python scripts/hevy_import/import_hevy_workouts.py --verbose
"""
import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher
import argparse

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select, func

from app.core.config import settings
from app.models import Exercise, Equipment, MuscleGroup, User
from app.models.workout import (
    WorkoutSession, WorkoutExercise, WorkoutSet,
    WorkoutState, SlotState, WeightUnit
)
from app.models.exercise import DifficultyLevel


# Hevy exercise name normalization patterns
NAME_NORMALIZATIONS = {
    # Hevy name -> Slotfit name (exact matches first)
    "Pull Up": "Pull-up",
    "Chin Up": "Chin-up", 
    "Push Up": "Push-up",
    "V Up": "V-up",
    # Add more as needed
}

# Equipment keywords to help identify equipment
EQUIPMENT_KEYWORDS = {
    "Dumbbell": ["dumbbell", "db"],
    "Barbell": ["barbell", "bb"],
    "Cable": ["cable"],
    "Machine": ["machine"],
    "Kettlebell": ["kettlebell", "kb"],
    "Smith Machine": ["smith"],
    "Trap Bar": ["trap bar"],
    "Resistance Band": ["band", "resistance band"],
}


def normalize_exercise_name(name: str) -> str:
    """Normalize exercise name for comparison"""
    # Check exact mappings first
    if name in NAME_NORMALIZATIONS:
        return NAME_NORMALIZATIONS[name]
    
    # Basic normalization
    normalized = name.strip()
    
    return normalized


def similarity_score(a: str, b: str) -> float:
    """Calculate similarity between two strings (0.0 to 1.0)"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def find_best_match(hevy_name: str, slotfit_exercises: Dict[str, int], threshold: float = 0.8) -> Optional[Tuple[str, int, float]]:
    """
    Find the best matching Slotfit exercise for a Hevy exercise name.
    Returns (slotfit_name, exercise_id, similarity_score) or None if no match above threshold.
    """
    normalized_hevy = normalize_exercise_name(hevy_name).lower()
    
    # Check for exact match first (case-insensitive)
    for slotfit_name, exercise_id in slotfit_exercises.items():
        if slotfit_name.lower() == normalized_hevy:
            return (slotfit_name, exercise_id, 1.0)
    
    # Find best fuzzy match
    best_match = None
    best_score = 0.0
    
    for slotfit_name, exercise_id in slotfit_exercises.items():
        score = similarity_score(normalized_hevy, slotfit_name)
        if score > best_score and score >= threshold:
            best_score = score
            best_match = (slotfit_name, exercise_id, score)
    
    return best_match


def extract_equipment_from_name(name: str) -> Optional[str]:
    """Extract equipment type from exercise name"""
    name_lower = name.lower()
    
    for equipment, keywords in EQUIPMENT_KEYWORDS.items():
        for keyword in keywords:
            if keyword in name_lower:
                return equipment
    
    return None


def infer_body_region(name: str) -> str:
    """Infer body region from exercise name"""
    name_lower = name.lower()
    
    upper_body_keywords = ["press", "row", "pull", "fly", "raise", "curl", "extension", "pushdown", 
                          "chest", "back", "shoulder", "bicep", "tricep", "arm", "lat"]
    lower_body_keywords = ["squat", "deadlift", "lunge", "leg", "calf", "glute", "hip", "hamstring",
                          "quad", "step up"]
    core_keywords = ["core", "ab", "plank", "crunch", "twist", "palloff"]
    
    for keyword in core_keywords:
        if keyword in name_lower:
            return "Core"
    
    for keyword in lower_body_keywords:
        if keyword in name_lower:
            return "Lower Body"
    
    for keyword in upper_body_keywords:
        if keyword in name_lower:
            return "Upper Body"
    
    return "Full Body"


def infer_force_type(name: str) -> str:
    """Infer force type from exercise name"""
    name_lower = name.lower()
    
    push_keywords = ["press", "push", "extension", "raise", "fly", "dip"]
    pull_keywords = ["pull", "row", "curl", "chin", "pulldown", "face pull"]
    
    for keyword in pull_keywords:
        if keyword in name_lower:
            return "Pull"
    
    for keyword in push_keywords:
        if keyword in name_lower:
            return "Push"
    
    return "Other"


async def get_or_create_import_user(session: AsyncSession, device_id: str = "hevy-import-device") -> User:
    """Get or create a user for importing workouts"""
    result = await session.execute(
        select(User).where(User.device_id == device_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        user = User(
            device_id=device_id,
            display_name="Hevy Import User",
            preferred_units="kg"  # Hevy data is in kg
        )
        session.add(user)
        await session.flush()
        print(f"  Created import user with id={user.id}")
    else:
        print(f"  Using existing import user with id={user.id}")
    
    return user


async def load_slotfit_exercises(session: AsyncSession) -> Dict[str, int]:
    """Load all Slotfit exercises into a name -> id mapping"""
    result = await session.execute(select(Exercise))
    exercises = result.scalars().all()
    
    return {ex.name: ex.id for ex in exercises}


async def load_equipment_mapping(session: AsyncSession) -> Dict[str, int]:
    """Load equipment name -> id mapping"""
    result = await session.execute(select(Equipment))
    equipment = result.scalars().all()
    
    return {eq.name: eq.id for eq in equipment}


async def create_exercise(
    session: AsyncSession,
    name: str,
    equipment_mapping: Dict[str, int],
    verbose: bool = False
) -> Exercise:
    """Create a new exercise in Slotfit"""
    # Infer properties from name
    equipment_name = extract_equipment_from_name(name)
    equipment_id = equipment_mapping.get(equipment_name) if equipment_name else None
    
    body_region = infer_body_region(name)
    force_type = infer_force_type(name)
    
    # Determine mechanics based on exercise type
    mechanics = "Compound"  # Default to compound
    isolation_keywords = ["curl", "extension", "raise", "fly", "kickback", "pushdown"]
    if any(keyword in name.lower() for keyword in isolation_keywords):
        mechanics = "Isolation"
    
    # Check if it's a HIIT exercise
    is_hiit = "HIIT" in name
    
    exercise = Exercise(
        name=name,
        description=f"Imported from Hevy app",
        difficulty=DifficultyLevel.INTERMEDIATE,
        primary_equipment_id=equipment_id,
        body_region=body_region,
        force_type=force_type,
        mechanics=mechanics,
        laterality="Bilateral",
        is_custom="True",  # Mark as custom exercise
    )
    
    session.add(exercise)
    await session.flush()
    
    if verbose:
        print(f"    Created exercise: {name} (id={exercise.id}, equipment={equipment_name}, region={body_region})")
    
    return exercise


async def build_exercise_mapping(
    session: AsyncSession,
    hevy_data: dict,
    dry_run: bool = False,
    verbose: bool = False
) -> Dict[str, int]:
    """
    Build a mapping from Hevy exercise names to Slotfit exercise IDs.
    Creates new exercises for any that don't exist in Slotfit.
    """
    # Load existing exercises and equipment
    slotfit_exercises = await load_slotfit_exercises(session)
    equipment_mapping = await load_equipment_mapping(session)
    
    print(f"\nLoaded {len(slotfit_exercises)} existing Slotfit exercises")
    print(f"Loaded {len(equipment_mapping)} equipment types")
    
    # Extract all unique Hevy exercises
    hevy_exercises = set()
    for workout in hevy_data["workouts"]:
        for exercise in workout["exercises"]:
            hevy_exercises.add(exercise["name"])
    
    print(f"\nFound {len(hevy_exercises)} unique exercises in Hevy data")
    
    # Build mapping
    mapping = {}
    exercises_to_create = []
    matched_count = 0
    
    for hevy_name in sorted(hevy_exercises):
        match = find_best_match(hevy_name, slotfit_exercises)
        
        if match:
            slotfit_name, exercise_id, score = match
            mapping[hevy_name] = exercise_id
            matched_count += 1
            if verbose:
                if score < 1.0:
                    print(f"  Matched: '{hevy_name}' -> '{slotfit_name}' (score: {score:.2f})")
        else:
            exercises_to_create.append(hevy_name)
    
    print(f"\nMatched {matched_count} exercises to existing Slotfit exercises")
    print(f"Need to create {len(exercises_to_create)} new exercises")
    
    # Create missing exercises
    if exercises_to_create:
        print(f"\nExercises to create:")
        for name in exercises_to_create:
            print(f"  - {name}")
        
        if not dry_run:
            print("\nCreating new exercises...")
            for name in exercises_to_create:
                exercise = await create_exercise(session, name, equipment_mapping, verbose)
                mapping[name] = exercise.id
            
            await session.flush()
            print(f"Created {len(exercises_to_create)} new exercises")
        else:
            print("\n[DRY RUN] Would create these exercises")
    
    return mapping


async def import_workouts(
    session: AsyncSession,
    hevy_data: dict,
    exercise_mapping: Dict[str, int],
    user: User,
    dry_run: bool = False,
    verbose: bool = False
) -> Tuple[int, int, int]:
    """
    Import workouts from Hevy data into Slotfit.
    Returns (workouts_imported, exercises_imported, sets_imported)
    """
    workouts_imported = 0
    exercises_imported = 0
    sets_imported = 0
    
    print(f"\nImporting {len(hevy_data['workouts'])} workouts...")
    
    for workout_data in hevy_data["workouts"]:
        # Parse timestamps (strip timezone for naive datetime columns)
        started_at = datetime.fromisoformat(workout_data["started_at"]).replace(tzinfo=None)
        completed_at = datetime.fromisoformat(workout_data["completed_at"]).replace(tzinfo=None)
        
        if verbose:
            print(f"\n  Workout: {workout_data['title']} ({started_at.date()})")
        
        if not dry_run:
            # Create workout session
            workout_session = WorkoutSession(
                user_id=user.id,
                state=WorkoutState.COMPLETED,
                started_at=started_at,
                completed_at=completed_at,
            )
            session.add(workout_session)
            await session.flush()
            
            # Import exercises
            for ex_data in workout_data["exercises"]:
                exercise_id = exercise_mapping.get(ex_data["name"])
                
                if not exercise_id:
                    print(f"    WARNING: No mapping for exercise '{ex_data['name']}', skipping")
                    continue
                
                # Create workout exercise
                workout_exercise = WorkoutExercise(
                    workout_session_id=workout_session.id,
                    exercise_id=exercise_id,
                    slot_state=SlotState.COMPLETED,
                    weight_unit=WeightUnit.KG,  # Hevy data is in kg
                    started_at=started_at,  # Using workout start time
                    stopped_at=completed_at,  # Using workout end time
                )
                session.add(workout_exercise)
                await session.flush()
                exercises_imported += 1
                
                # Create sets
                for set_data in ex_data["sets"]:
                    workout_set = WorkoutSet(
                        workout_exercise_id=workout_exercise.id,
                        set_number=set_data["set_number"],
                        reps=set_data.get("reps"),
                        weight=set_data.get("weight_kg"),  # Keeping in kg
                        rpe=set_data.get("rpe"),
                        notes=ex_data.get("notes", ""),
                        # Note: duration_sec and distance_m are in the data but not in Slotfit schema yet
                    )
                    session.add(workout_set)
                    sets_imported += 1
                
                if verbose:
                    print(f"    {ex_data['name']}: {len(ex_data['sets'])} sets")
            
            workouts_imported += 1
        else:
            # Dry run - just count
            workouts_imported += 1
            for ex_data in workout_data["exercises"]:
                exercises_imported += 1
                sets_imported += len(ex_data["sets"])
    
    return workouts_imported, exercises_imported, sets_imported


async def main():
    """Main import function"""
    parser = argparse.ArgumentParser(description="Import Hevy workouts into Slotfit")
    parser.add_argument("--dry-run", action="store_true", help="Don't make any database changes")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--data-file", default=None, help="Path to Hevy data JSON file")
    args = parser.parse_args()
    
    # Load Hevy data
    if args.data_file:
        data_path = Path(args.data_file)
    else:
        data_path = Path(__file__).parent / "hevy_workouts_data.json"
    
    if not data_path.exists():
        print(f"Error: Data file not found at {data_path}")
        sys.exit(1)
    
    print(f"Loading Hevy data from: {data_path}")
    with open(data_path, "r", encoding="utf-8") as f:
        hevy_data = json.load(f)
    
    print(f"Found {len(hevy_data['workouts'])} workouts from {hevy_data['date_range']['start']} to {hevy_data['date_range']['end']}")
    
    if args.dry_run:
        print("\n*** DRY RUN MODE - No database changes will be made ***\n")
    
    # Connect to database
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            # Get or create import user
            print("\nSetting up import user...")
            user = await get_or_create_import_user(session, "hevy-import-device")
            
            # Build exercise mapping (and create missing exercises)
            print("\nBuilding exercise mapping...")
            exercise_mapping = await build_exercise_mapping(
                session, hevy_data, 
                dry_run=args.dry_run, 
                verbose=args.verbose
            )
            
            # Import workouts
            workouts, exercises, sets = await import_workouts(
                session, hevy_data, exercise_mapping, user,
                dry_run=args.dry_run,
                verbose=args.verbose
            )
            
            if not args.dry_run:
                await session.commit()
                print("\n✅ Import completed successfully!")
            else:
                print("\n✅ Dry run completed!")
            
            print(f"\nSummary:")
            print(f"  Workouts: {workouts}")
            print(f"  Exercise entries: {exercises}")
            print(f"  Sets: {sets}")
            
            # Save exercise mapping for reference
            mapping_path = Path(__file__).parent / "exercise_mapping.json"
            if not args.dry_run:
                with open(mapping_path, "w", encoding="utf-8") as f:
                    json.dump(exercise_mapping, f, indent=2)
                print(f"\nExercise mapping saved to: {mapping_path}")
            
        except Exception as e:
            print(f"\n❌ Error during import: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()
            sys.exit(1)
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

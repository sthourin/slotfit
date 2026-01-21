"""
Import exercise database from CSV file
"""
import asyncio
import csv
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select

from app.core.config import settings
from app.models import (
    MuscleGroup,
    Equipment,
    Exercise,
)
from app.models.exercise import DifficultyLevel


# CSV column mapping
CSV_COLUMNS = {
    "Exercise": "name",
    "Short YouTube Demonstration": "short_demo_url",
    "In-Depth YouTube Explanation": "in_depth_url",
    "Difficulty Level": "difficulty",
    "Target Muscle Group ": "target_muscle_group",
    "Prime Mover Muscle": "prime_mover_muscle",
    "Secondary Muscle": "secondary_muscle",
    "Tertiary Muscle": "tertiary_muscle",
    "Primary Equipment ": "primary_equipment",
    "# Primary Items": "primary_equipment_count",
    "Secondary Equipment": "secondary_equipment",
    "# Secondary Items": "secondary_equipment_count",
    "Posture": "posture",
    "Movement Pattern #1": "movement_pattern_1",
    "Movement Pattern #2": "movement_pattern_2",
    "Movement Pattern #3": "movement_pattern_3",
    "Plane Of Motion #1": "plane_of_motion_1",
    "Plane Of Motion #2": "plane_of_motion_2",
    "Plane Of Motion #3": "plane_of_motion_3",
    "Body Region": "body_region",
    "Force Type": "force_type",
    "Mechanics": "mechanics",
    "Laterality": "laterality",
    "Primary Exercise Classification": "exercise_classification",
}


async def get_or_create_muscle_group(
    session: AsyncSession, name: str, level: int, parent_id: Optional[int] = None
) -> MuscleGroup:
    """Get existing muscle group or create new one"""
    if not name or name.strip() == "":
        return None
    
    # Check if exists
    result = await session.execute(
        select(MuscleGroup).where(
            MuscleGroup.name == name.strip(),
            MuscleGroup.level == level,
            MuscleGroup.parent_id == parent_id,
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        return existing
    
    # Create new
    muscle_group = MuscleGroup(
        name=name.strip(),
        level=level,
        parent_id=parent_id,
    )
    session.add(muscle_group)
    await session.flush()
    return muscle_group


async def get_or_create_equipment(session: AsyncSession, name: str) -> Optional[Equipment]:
    """Get existing equipment or create new one"""
    if not name or name.strip() == "" or name.strip().lower() == "none":
        return None
    
    name_clean = name.strip()
    
    # Check if exists
    result = await session.execute(select(Equipment).where(Equipment.name == name_clean))
    existing = result.scalar_one_or_none()
    
    if existing:
        return existing
    
    # Create new
    equipment = Equipment(name=name_clean)
    session.add(equipment)
    await session.flush()
    return equipment


def parse_difficulty(difficulty_str: str) -> Optional[DifficultyLevel]:
    """Parse difficulty string to enum, consolidating into Easy, Intermediate, Advanced"""
    if not difficulty_str:
        return None
    
    difficulty_str = difficulty_str.strip()
    
    # Map old difficulty levels to new consolidated levels
    # Easy: Beginner, Novice
    if difficulty_str in ("Beginner", "Novice"):
        return DifficultyLevel.EASY
    # Intermediate: Intermediate
    elif difficulty_str == "Intermediate":
        return DifficultyLevel.INTERMEDIATE
    # Advanced: Advanced, Expert, Master, Grand Master, Legendary
    elif difficulty_str in ("Advanced", "Expert", "Master", "Grand Master", "Legendary"):
        return DifficultyLevel.ADVANCED
    
    return None


async def import_exercises_from_csv(csv_path: str):
    """Import exercises from CSV file"""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    muscle_group_cache: Dict[str, MuscleGroup] = {}
    equipment_cache: Dict[str, Equipment] = {}
    
    async with async_session() as session:
        print(f"Reading CSV file: {csv_path}")
        
        with open(csv_path, "r", encoding="utf-8-sig") as f:  # utf-8-sig handles BOM
            reader = csv.DictReader(f)
            total_rows = 0
            imported = 0
            errors = 0
            
            for row in reader:
                total_rows += 1
                
                try:
                    # Get or create muscle groups (hierarchical)
                    target_mg = None
                    prime_mg = None
                    secondary_mg = None
                    tertiary_mg = None
                    
                    # Level 1: Target Muscle Group
                    if row.get("Target Muscle Group "):
                        target_mg = await get_or_create_muscle_group(
                            session, row["Target Muscle Group "], level=1
                        )
                        if target_mg:
                            muscle_group_cache[f"1:{target_mg.name}"] = target_mg
                    
                    # Level 2: Prime Mover
                    if row.get("Prime Mover Muscle") and target_mg:
                        prime_mg = await get_or_create_muscle_group(
                            session, row["Prime Mover Muscle"], level=2, parent_id=target_mg.id
                        )
                        if prime_mg:
                            muscle_group_cache[f"2:{prime_mg.name}:{target_mg.id}"] = prime_mg
                    
                    # Level 3: Secondary
                    if row.get("Secondary Muscle") and target_mg:
                        secondary_mg = await get_or_create_muscle_group(
                            session, row["Secondary Muscle"], level=3, parent_id=target_mg.id
                        )
                        if secondary_mg:
                            muscle_group_cache[f"3:{secondary_mg.name}:{target_mg.id}"] = secondary_mg
                    
                    # Level 4: Tertiary
                    if row.get("Tertiary Muscle") and target_mg:
                        tertiary_mg = await get_or_create_muscle_group(
                            session, row["Tertiary Muscle"], level=4, parent_id=target_mg.id
                        )
                        if tertiary_mg:
                            muscle_group_cache[f"4:{tertiary_mg.name}:{target_mg.id}"] = tertiary_mg
                    
                    # Get or create equipment
                    primary_equipment = None
                    secondary_equipment = None
                    
                    if row.get("Primary Equipment "):
                        primary_equipment = await get_or_create_equipment(
                            session, row["Primary Equipment "]
                        )
                        if primary_equipment:
                            equipment_cache[primary_equipment.name] = primary_equipment
                    
                    if row.get("Secondary Equipment"):
                        secondary_equipment = await get_or_create_equipment(
                            session, row["Secondary Equipment"]
                        )
                        if secondary_equipment:
                            equipment_cache[secondary_equipment.name] = secondary_equipment
                    
                    # Check if exercise already exists
                    # Handle BOM in column name
                    exercise_name = row.get("Exercise", row.get("\ufeffExercise", "")).strip()
                    if not exercise_name:
                        if total_rows <= 3:
                            print(f"  Row {total_rows}: Empty exercise name, keys: {list(row.keys())[:3]}")
                        continue
                    
                    result = await session.execute(
                        select(Exercise).where(Exercise.name == exercise_name)
                    )
                    existing_exercise = result.scalar_one_or_none()
                    
                    if existing_exercise:
                        if total_rows <= 3:
                            print(f"  Skipping existing exercise: {exercise_name}")
                        continue
                    
                    if total_rows <= 3:
                        print(f"  Row {total_rows}: Creating exercise: {exercise_name}")
                    
                    # Parse combination exercise field (handle various formats)
                    # Column name is "Combination Exercises" (plural)
                    # Values are: "Single Exercise" or "Combo Exercise"
                    combination_value = row.get("Combination Exercises", "").strip()
                    is_combination = None
                    if combination_value:
                        # Handle "Combo Exercise" vs "Single Exercise" values
                        if combination_value.lower() in ("combo exercise", "combination exercise", "combination", "true", "1", "yes"):
                            is_combination = "True"
                        elif combination_value.lower() in ("single exercise", "single", "false", "0", "no", ""):
                            is_combination = "False"
                    
                    # Create exercise
                    exercise = Exercise(
                        name=exercise_name,
                        short_demo_url=row.get("Short YouTube Demonstration"),
                        in_depth_url=row.get("In-Depth YouTube Explanation"),
                        difficulty=parse_difficulty(row.get("Difficulty Level")),
                        primary_equipment_id=primary_equipment.id if primary_equipment else None,
                        secondary_equipment_id=secondary_equipment.id if secondary_equipment else None,
                        primary_equipment_count=int(row.get("# Primary Items", 1) or 1),
                        secondary_equipment_count=int(row.get("# Secondary Items", 0) or 0),
                        posture=row.get("Posture"),
                        movement_pattern_1=row.get("Movement Pattern #1"),
                        movement_pattern_2=row.get("Movement Pattern #2"),
                        movement_pattern_3=row.get("Movement Pattern #3"),
                        plane_of_motion_1=row.get("Plane Of Motion #1"),
                        plane_of_motion_2=row.get("Plane Of Motion #2"),
                        plane_of_motion_3=row.get("Plane Of Motion #3"),
                        body_region=row.get("Body Region"),
                        force_type=row.get("Force Type"),
                        mechanics=row.get("Mechanics"),
                        laterality=row.get("Laterality"),
                        exercise_classification=row.get("Primary Exercise Classification"),
                        is_combination=is_combination,
                    )
                    
                    session.add(exercise)
                    await session.flush()
                    
                    # Link muscle groups to exercise via association table
                    from sqlalchemy import insert
                    from app.models.exercise import exercise_muscle_groups
                    
                    muscle_groups_to_link = []
                    if target_mg:
                        muscle_groups_to_link.append((target_mg, "target"))
                    if prime_mg:
                        muscle_groups_to_link.append((prime_mg, "prime_mover"))
                    if secondary_mg:
                        muscle_groups_to_link.append((secondary_mg, "secondary"))
                    if tertiary_mg:
                        muscle_groups_to_link.append((tertiary_mg, "tertiary"))
                    
                    for mg, role in muscle_groups_to_link:
                        stmt = insert(exercise_muscle_groups).values(
                            exercise_id=exercise.id,
                            muscle_group_id=mg.id,
                            role=role,
                        )
                        await session.execute(stmt)
                    
                    imported += 1
                    
                    if imported % 100 == 0:
                        await session.commit()
                        print(f"  Imported {imported} exercises...")
                
                except Exception as e:
                    errors += 1
                    import traceback
                    print(f"  Error importing row {total_rows}: {e}")
                    if total_rows <= 3:  # Show full traceback for first few errors
                        traceback.print_exc()
                    continue
            
            # Final commit
            await session.commit()
            
            print(f"\nImport complete!")
            print(f"  Total rows processed: {total_rows}")
            print(f"  Exercises imported: {imported}")
            print(f"  Errors: {errors}")
    
    await engine.dispose()


async def main():
    """Main entry point"""
    csv_path = Path(__file__).parent.parent.parent / "assets" / "slotfit_exercise_database_with_urls.csv"
    
    if not csv_path.exists():
        print(f"Error: CSV file not found at {csv_path}")
        sys.exit(1)
    
    print("Starting exercise database import...")
    await import_exercises_from_csv(str(csv_path))
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())

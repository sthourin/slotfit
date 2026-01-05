"""
Clear all exercises from the database
Used for re-seeding the database
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import delete, update

from app.core.config import settings
from app.models.exercise import Exercise, exercise_muscle_groups
from app.models.workout import WorkoutExercise
from app.models.personal_record import PersonalRecord
from app.models.routine import RoutineSlot
from app.models.slot_template import SlotTemplate


async def clear_exercises():
    """Delete all exercises from the database"""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        print("Clearing exercises from database...")
        
        # 1. Delete personal records (references exercises.id)
        print("  Deleting personal records...")
        pr_result = await session.execute(delete(PersonalRecord))
        print(f"    Deleted {pr_result.rowcount} personal records")
        
        # 2. Delete workout exercises (references exercises.id)
        # This will cascade delete workout_sets, heart_rate_readings, etc.
        print("  Deleting workout exercises...")
        we_result = await session.execute(delete(WorkoutExercise))
        print(f"    Deleted {we_result.rowcount} workout exercises")
        
        # 3. Clear nullable foreign keys that reference exercises
        print("  Clearing exercise references in routine slots...")
        rs_result = await session.execute(
            update(RoutineSlot).values(selected_exercise_id=None)
        )
        print(f"    Updated {rs_result.rowcount} routine slots")
        
        print("  Clearing exercise references in slot templates...")
        st_result = await session.execute(
            update(SlotTemplate).values(default_exercise_id=None)
        )
        print(f"    Updated {st_result.rowcount} slot templates")
        
        # 4. Clear self-referential base_exercise_id (variants)
        print("  Clearing exercise variants...")
        ex_variant_result = await session.execute(
            update(Exercise).values(base_exercise_id=None)
        )
        print(f"    Updated {ex_variant_result.rowcount} exercises")
        
        # 5. Delete all exercise-muscle group associations
        print("  Deleting exercise-muscle group associations...")
        await session.execute(delete(exercise_muscle_groups))
        
        # 6. Finally delete all exercises
        print("  Deleting exercises...")
        ex_result = await session.execute(delete(Exercise))
        deleted_count = ex_result.rowcount
        
        await session.commit()
        
        print(f"\n  Deleted {deleted_count} exercises")
        print("Done!")
    
    await engine.dispose()


async def main():
    """Main entry point"""
    await clear_exercises()


if __name__ == "__main__":
    asyncio.run(main())

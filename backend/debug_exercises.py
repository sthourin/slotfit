"""Direct async test to debug exercises endpoint"""
import asyncio
import sys
import traceback

async def test_exercises_query():
    """Run the actual database query to see the real error"""
    try:
        # Import everything needed
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        from app.core.config import settings
        from app.models import Exercise, MuscleGroup, Equipment, WorkoutExercise
        from app.schemas.exercise import Exercise as ExerciseSchema, ExerciseListResponse

        print(f"Database URL: {settings.DATABASE_URL}")

        # Create async engine
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as db:
            print("Connected to database")

            # Simple query first
            query = select(Exercise).options(
                selectinload(Exercise.primary_equipment),
                selectinload(Exercise.secondary_equipment),
                selectinload(Exercise.muscle_groups),
            ).limit(5)

            print("Executing query...")
            result = await db.execute(query)
            exercises = result.scalars().unique().all()

            print(f"Found {len(exercises)} exercises")

            if exercises:
                print("\nFirst exercise:")
                ex = exercises[0]
                print(f"  ID: {ex.id}")
                print(f"  Name: {ex.name}")
                print(f"  Primary equipment: {ex.primary_equipment}")
                print(f"  Muscle groups: {[mg.name for mg in ex.muscle_groups]}")

                # Try to create schema
                print("\nAttempting schema validation...")
                ex_schema = ExerciseSchema.model_validate(ex)
                print(f"  Schema validated successfully")

                ex_dict = ex_schema.model_dump()
                print(f"  Schema dumped successfully")
                ex_dict['last_performed'] = None

                validated = ExerciseSchema.model_validate(ex_dict)
                print(f"  Re-validated successfully")

            # Now try building the full response
            print("\nBuilding ExerciseListResponse...")
            exercise_list = []
            for ex in exercises:
                ex_schema = ExerciseSchema.model_validate(ex)
                ex_dict = ex_schema.model_dump()
                ex_dict['last_performed'] = None
                exercise_list.append(ExerciseSchema.model_validate(ex_dict))

            response = ExerciseListResponse(
                exercises=exercise_list,
                total=len(exercise_list),
                page=1,
                page_size=5,
            )
            print(f"Response built successfully with {len(response.exercises)} exercises")

    except Exception as e:
        print(f"\n*** ERROR ***")
        print(f"Exception type: {type(e).__name__}")
        print(f"Exception message: {e}")
        print(f"\nFull traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    print("Starting debug test...")
    asyncio.run(test_exercises_query())
    print("\nDone.")

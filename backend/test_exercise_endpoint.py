"""Test the exercise endpoint directly"""
import asyncio
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select
from app.core.config import settings
from app.models import Exercise
from app.api.v1.endpoints.exercises import list_exercises
from fastapi import Request
from unittest.mock import MagicMock

async def test():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = async_sessionmaker(engine)
    
    async with async_session() as db:
        # Test basic query
        result = await db.execute(select(Exercise).limit(1))
        exercises = result.scalars().all()
        print(f"Found {len(exercises)} exercises in DB")
        
        # Test the endpoint function
        try:
            # Create a mock request
            request = MagicMock()
            
            # Call the endpoint function
            response = await list_exercises(
                skip=0,
                limit=5,
                search=None,
                muscle_group_id=None,
                muscle_group_ids=None,
                equipment_id=None,
                difficulty=None,
                body_region=None,
                mechanics=None,
                routine_type=None,
                workout_style=None,
                variant_type=None,
                base_exercise_id=None,
                include_variants=False,
                sort_by="name",
                sort_order="asc",
                db=db
            )
            print(f"Success! Got {len(response.exercises)} exercises")
            print(f"Total: {response.total}")
            if response.exercises:
                print(f"First exercise: {response.exercises[0].name}")
        except Exception as e:
            import traceback
            print(f"ERROR: {e}")
            traceback.print_exc()
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test())

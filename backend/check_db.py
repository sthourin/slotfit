"""Quick script to check database status"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select, text
from app.core.config import settings
from app.models import Exercise, MuscleGroup, Equipment

async def check():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = async_sessionmaker(engine)
    
    async with async_session() as s:
        # Check exercises
        result = await s.execute(select(Exercise))
        exercises = result.scalars().all()
        print(f"Exercises in DB: {len(exercises)}")
        
        # Check muscle groups
        result = await s.execute(select(MuscleGroup))
        muscle_groups = result.scalars().all()
        print(f"Muscle groups in DB: {len(muscle_groups)}")
        
        # Check equipment
        result = await s.execute(select(Equipment))
        equipment = result.scalars().all()
        print(f"Equipment in DB: {len(equipment)}")
        
        if exercises:
            print(f"\nFirst exercise: {exercises[0].name}")
        if muscle_groups:
            print(f"First muscle group: {muscle_groups[0].name} (level {muscle_groups[0].level})")
        if equipment:
            print(f"First equipment: {equipment[0].name}")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check())

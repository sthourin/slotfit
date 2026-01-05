"""
List all equipment in the database
"""
import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select, func

from app.core.config import settings
from app.models import Equipment


async def list_equipment():
    """List all equipment in the database"""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Get all equipment ordered by name
        query = select(Equipment).order_by(Equipment.name)
        result = await session.execute(query)
        equipment_list = result.scalars().all()
        
        # Count exercises using each equipment
        from app.models import Exercise
        equipment_counts = {}
        
        # Count primary equipment usage
        primary_query = select(
            Exercise.primary_equipment_id,
            func.count(Exercise.id).label('count')
        ).where(
            Exercise.primary_equipment_id.isnot(None)
        ).group_by(Exercise.primary_equipment_id)
        
        primary_result = await session.execute(primary_query)
        for row in primary_result:
            equipment_counts[row.primary_equipment_id] = equipment_counts.get(row.primary_equipment_id, 0) + row.count
        
        # Count secondary equipment usage
        secondary_query = select(
            Exercise.secondary_equipment_id,
            func.count(Exercise.id).label('count')
        ).where(
            Exercise.secondary_equipment_id.isnot(None)
        ).group_by(Exercise.secondary_equipment_id)
        
        secondary_result = await session.execute(secondary_query)
        for row in secondary_result:
            equipment_counts[row.secondary_equipment_id] = equipment_counts.get(row.secondary_equipment_id, 0) + row.count
        
        print(f"\nTotal Equipment: {len(equipment_list)}\n")
        print(f"{'ID':<6} {'Name':<50} {'Exercise Count':<15}")
        print("-" * 75)
        
        for eq in equipment_list:
            count = equipment_counts.get(eq.id, 0)
            print(f"{eq.id:<6} {eq.name:<50} {count:<15}")
        
        print("-" * 75)
        print(f"\nTotal: {len(equipment_list)} equipment items")
    
    await engine.dispose()


async def main():
    """Main entry point"""
    await list_equipment()


if __name__ == "__main__":
    asyncio.run(main())

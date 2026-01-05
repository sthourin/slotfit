"""
Add equipment to the database
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
from sqlalchemy import select

from app.core.config import settings
from app.models import Equipment


async def add_equipment(name: str, category: str = None):
    """Add equipment to the database if it doesn't exist"""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Check if equipment already exists
        query = select(Equipment).where(Equipment.name == name)
        result = await session.execute(query)
        existing = result.scalar_one_or_none()
        
        if existing:
            print(f"Equipment '{name}' already exists (ID: {existing.id})")
            return existing
        
        # Create new equipment
        equipment = Equipment(name=name, category=category)
        session.add(equipment)
        await session.commit()
        await session.refresh(equipment)
        
        print(f"Added equipment '{name}' (ID: {equipment.id})")
        return equipment
    
    await engine.dispose()


async def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python add_equipment.py <equipment_name> [category]")
        print("Example: python add_equipment.py BOSU")
        sys.exit(1)
    
    name = sys.argv[1]
    category = sys.argv[2] if len(sys.argv) > 2 else None
    
    await add_equipment(name, category)


if __name__ == "__main__":
    asyncio.run(main())

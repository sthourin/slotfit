"""
Database initialization script
Can be used to create tables (for development) or run migrations
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings
from app.models.base import Base


async def init_db():
    """Create all tables (use Alembic migrations in production)"""
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    await engine.dispose()
    print("Database tables created successfully!")


if __name__ == "__main__":
    asyncio.run(init_db())

"""
Pytest configuration and shared fixtures
"""
import os
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import event
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.dialects.postgresql import JSONB

from app.main import app
from app.core.database import get_db
from app.core.config import settings
from app.models.base import Base


# Test database URL - use production DB if USE_PROD_DB env var is set
USE_PROD_DB = os.getenv("USE_PROD_DB", "false").lower() == "true"
if USE_PROD_DB:
    TEST_DATABASE_URL = settings.DATABASE_URL
    print("⚠️  WARNING: Using PRODUCTION database for tests!")
else:
    TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="function")
async def test_db():
    """Create a test database session"""
    # Create in-memory database
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Map JSONB to JSON for SQLite compatibility
    @event.listens_for(engine.sync_engine, "connect", insert=True)
    def set_sqlite_pragma(dbapi_conn, connection_record):
        # Replace JSONB with JSON for SQLite
        pass
    
    # Override JSONB type for SQLite
    from sqlalchemy import TypeDecorator
    class JSONBCompat(TypeDecorator):
        impl = SQLiteJSON
        cache_ok = True
        
        def load_dialect_impl(self, dialect):
            if dialect.name == 'sqlite':
                return dialect.type_descriptor(SQLiteJSON())
            else:
                return dialect.type_descriptor(JSONB())
    
    # Replace JSONB columns with JSON for SQLite
    # This is done by SQLAlchemy automatically, but we need to ensure it works
    # Create tables
    async with engine.begin() as conn:
        # Temporarily replace JSONB with JSON in metadata
        original_types = {}
        for table in Base.metadata.tables.values():
            for column in table.columns:
                if isinstance(column.type, JSONB):
                    original_types[column] = column.type
                    column.type = SQLiteJSON()
        
        await conn.run_sync(Base.metadata.create_all)
        
        # Restore original types
        for column, original_type in original_types.items():
            column.type = original_type
    
    # Create session
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session_maker() as session:
        yield session
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture(scope="function")
async def client(test_db: AsyncSession):
    """Create a test HTTP client"""
    from httpx import ASGITransport
    
    # Override database dependency
    async def override_get_db():
        yield test_db
    
    app.dependency_overrides[get_db] = override_get_db
    
    # Use ASGITransport for FastAPI app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture
def device_id():
    """Generate a test device ID"""
    return "test-device-12345"


@pytest.fixture(scope="function")
async def seeded_db(test_db: AsyncSession):
    """Test database with seed data"""
    from tests.seed_data import seed_all_data
    
    # Seed all data
    seed_result = await seed_all_data(test_db)
    
    yield test_db, seed_result
    
    # Data is automatically cleaned up when test_db fixture cleans up


@pytest.fixture(scope="function")
async def client_with_data(seeded_db):
    """Client with seeded database"""
    from httpx import ASGITransport
    
    test_db, seed_result = seeded_db
    
    # Override database dependency
    async def override_get_db():
        yield test_db
    
    app.dependency_overrides[get_db] = override_get_db
    
    # Use ASGITransport for FastAPI app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac, seed_result
    
    # Cleanup
    app.dependency_overrides.clear()
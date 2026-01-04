import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from config import config
from database.models import Base

# Create async engine for working with database
database_url = os.getenv("DATABASE_URL") or config.db.get_url()
async_engine = create_async_engine(
    database_url,
    echo=False,
    poolclass=NullPool,
)

# Create session factory for getting database sessions
SessionLocal = sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncSession:
    """Dependency for getting async session"""
    async with SessionLocal() as session:
        yield session


async def init_models():
    """Initialize database models"""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

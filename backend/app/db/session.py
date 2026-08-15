"""
SQLAlchemy async engine and session factory.
All application code obtains a database session via the `get_db` dependency.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

engine = create_async_engine(
    settings.async_database_url,
    echo=False,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:  # type: ignore[override]
    """FastAPI dependency that yields an async database session."""
    async with AsyncSessionLocal() as session:
        yield session

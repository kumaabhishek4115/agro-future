"""
Shared pytest fixtures.

Tests use an in-process SQLite database via aiosqlite so that they can run
without a real PostgreSQL server.  The FastAPI dependency `get_db` is
overridden to yield sessions from this test database.

Key design choice: `StaticPool` is used so that every async session within a
single test shares the **same underlying connection**, which is required for
SQLite `:memory:` databases – otherwise each new connection gets its own
empty database and data written by one session is invisible to another.
"""

from __future__ import annotations

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.models import Base
from app.db.session import get_db
from app.main import app


@pytest_asyncio.fixture
async def session_factory() -> async_sessionmaker[AsyncSession]:
    """
    Spin up a fresh in-memory SQLite database for each test, override the
    `get_db` dependency so every request in that test hits the same DB, then
    tear everything down afterwards.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        # StaticPool: all sessions reuse the single connection, which is
        # essential for SQLite in-memory to remain visible across sessions.
        poolclass=StaticPool,
        echo=False,
    )

    # Create all tables inside the engine's single connection
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    yield session_factory

    await engine.dispose()


@pytest_asyncio.fixture
async def client(session_factory: async_sessionmaker[AsyncSession]) -> AsyncClient:
    async def _override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    # Teardown: restore overrides and close engine
    app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture
async def db_session(session_factory: async_sessionmaker[AsyncSession]) -> AsyncSession:
    async with session_factory() as session:
        yield session

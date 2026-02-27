"""
Shared test fixtures.

Swaps the production async PostgreSQL engine/session with an in-memory
SQLite database so tests run without external services.
"""
import asyncio
from collections.abc import AsyncGenerator

import pytest
from unittest.mock import patch, AsyncMock

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.database import Base
import app.models  # noqa: F401 — register models on Base.metadata


async def _no_op_rate_limiter() -> None:
    """Bypass rate limiting in tests."""


@pytest.fixture()
def auth_client():
    """
    FastAPI TestClient backed by an in-memory SQLite database.

    * Creates all tables before each test.
    * Overrides the get_session dependency so route code uses the test DB.
    * Patches the engine used by the lifespan for create_all.
    * Mocks rag_service.initialize so RAG/ChromaDB/Ollama are skipped.
    * Disables all rate limiters so tests never hit 429.
    """
    test_engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
    )
    TestSession = async_sessionmaker(test_engine, expire_on_commit=False)

    loop = asyncio.new_event_loop()
    loop.run_until_complete(_create_tables(test_engine))

    async def _override_get_session() -> AsyncGenerator[AsyncSession, None]:
        async with TestSession() as session:
            yield session

    with (
        patch("main.engine", test_engine),
        patch("app.services.rag_service.rag_service.initialize", new_callable=AsyncMock),
        patch("app.services.document_service.document_service.initialize", new_callable=AsyncMock),
    ):
        from starlette.testclient import TestClient
        from main import app
        from app.database import get_session
        from app.rate_limit import (
            login_rate_limiter,
            register_rate_limiter,
            query_rate_limiter,
            upload_rate_limiter,
        )

        app.dependency_overrides[get_session] = _override_get_session
        app.dependency_overrides[login_rate_limiter] = _no_op_rate_limiter
        app.dependency_overrides[register_rate_limiter] = _no_op_rate_limiter
        app.dependency_overrides[query_rate_limiter] = _no_op_rate_limiter
        app.dependency_overrides[upload_rate_limiter] = _no_op_rate_limiter

        with TestClient(app) as client:
            yield client

        app.dependency_overrides.clear()

    loop.run_until_complete(test_engine.dispose())
    loop.close()


async def _create_tables(engine: object) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

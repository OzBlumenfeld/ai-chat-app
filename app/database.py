from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession as _AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(settings.DATABASE_URL)
AsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False)

# Keep backward-compatible alias used by existing code
AsyncSession = AsyncSessionFactory


async def get_session() -> AsyncGenerator[_AsyncSession, None]:
    """FastAPI dependency that yields a database session."""
    async with AsyncSessionFactory() as session:
        yield session

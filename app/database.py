"""
Database engine + session management.

Design choices (and why):
- Async engine (asyncpg) because the brief requires async API design and
  this is an I/O-bound app (every request waits on Postgres) — async lets
  one worker handle many concurrent Vapi calls without blocking.
- pool_pre_ping=True: production Postgres (Railway/Render free tiers, Neon)
  silently drops idle connections. Without this, the FIRST request after
  any idle period throws a confusing "connection closed" error. This
  setting tests the connection before handing it out and reconnects if dead.
- expire_on_commit=False: we often return ORM objects in API responses
  right after committing; without this SQLAlchemy would force a reload.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings
from app.logger import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


# Ensure we're using asyncpg driver by converting the URL
DATABASE_URL = settings.database_url_async

engine = create_async_engine(
    DATABASE_URL,
    echo=settings.DEBUG,          # log raw SQL only in debug mode
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=1800,             # recycle connections every 30 min, avoids stale TCP conns
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency. Yields a session per request and guarantees
    rollback-on-error + close, so a failed request never leaves a
    half-committed transaction or a leaked connection.
    Usage: db: AsyncSession = Depends(get_db)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            logger.exception("DB session rolled back due to unhandled exception")
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Same guarantees as get_db(), but as a context manager for use OUTSIDE
    FastAPI's dependency injection — e.g. the seed script and the
    evaluation harness, which run as standalone scripts.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_connection() -> bool:
    """
    Used by a startup event / health endpoint to fail fast and loudly
    if the DB is unreachable, instead of letting every request 500
    with a cryptic error.
    """
    from sqlalchemy import text
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection verified successfully with asyncpg")
        return True
    except Exception as exc:
        logger.error(f"Database connection check failed: {exc}")
        return False
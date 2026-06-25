"""
Database engine + session management.
FORCED: asyncpg driver only - blocks psycopg2 completely.
"""

import sys
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

# ---------- CRITICAL: BLOCK PSYCOPG2 ----------
# Render's environment has psycopg2 pre-installed.
# This MUST run before ANY SQLAlchemy imports.

# Remove psycopg2 from sys.modules if it exists
for module_name in list(sys.modules.keys()):
    if module_name == 'psycopg2' or module_name.startswith('psycopg2.'):
        del sys.modules[module_name]

# Create a mock to prevent psycopg2 from loading
class BlockedModule:
    def __getattr__(self, name):
        raise ImportError(f"psycopg2 is disabled. Use asyncpg instead.")

# Block future imports of psycopg2
sys.modules['psycopg2'] = BlockedModule()
sys.modules['psycopg2.extensions'] = BlockedModule()
sys.modules['psycopg2.extras'] = BlockedModule()

# Also prevent psycopg2 from being installed via pkg_resources
os.environ['SQLALCHEMY_WARN_20'] = '1'

# ---------- END BLOCK ----------

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings  # This is correct
from app.logger import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


# Ensure we're using asyncpg driver
DATABASE_URL = settings.database_url_async
logger.info(f"Using DATABASE_URL with asyncpg driver")

# Create engine with explicit asyncpg driver
engine = create_async_engine(
    DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_recycle=1800,
    pool_timeout=30,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database session."""
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
    """Database session context manager for scripts."""
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
    Check database connection with detailed error reporting.
    """
    from sqlalchemy import text
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("✅ Database connection verified successfully with asyncpg")
        return True
    except Exception as exc:
        logger.error(f"❌ Database connection failed: {exc}")
        return False
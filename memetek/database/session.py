"""Database session and engine management."""

import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy import event
from memetek.config import settings
from memetek.database.models import Base

logger = logging.getLogger(__name__)

# Engine configuration
engine_kwargs = {
    "echo": False,
    "future": True,
}

if "sqlite" in settings.DATABASE_URL:
    # SQLite specific args
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # PostgreSQL pool tuning
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20
    engine_kwargs["pool_pre_ping"] = True

engine: AsyncEngine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

# For SQLite, ensure foreign keys are enforced
if "sqlite" in settings.DATABASE_URL:
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for providing an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables."""
    logger.info("Initializing database schema...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schema initialized.")

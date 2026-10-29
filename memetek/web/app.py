"""FastAPI application factory for MEMETEK Web Dashboard & API."""

import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from memetek.config import settings
from memetek.database.session import init_db, get_session
from memetek.database.crud import seed_initial_data_if_empty
from memetek.database.session import async_session_factory
from memetek.services.cache import cache
from memetek.web.routes import pages, api

logger = logging.getLogger(__name__)

# Base directory for web assets
WEB_DIR = Path(__file__).resolve().parent
STATIC_DIR = WEB_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown hooks."""
    logger.info("Starting MEMETEK Web Service...")
    # Initialize DB schema only in non-serverless environments or test mode
    # (Schema is pre-provisioned via migrations on Supabase in production)
    try:
        if settings.APP_ENV != "serverless" or settings.TEST_MODE:
            await init_db()
            async with async_session_factory() as session:
                await seed_initial_data_if_empty(session)
    except Exception as e:
        logger.warning("Database schema check failed on startup (non-fatal): %s", e)

    # Connect cache gracefully
    try:
        await cache.connect()
    except Exception as e:
        logger.warning("Cache connect failed on startup (non-fatal): %s", e)

    yield

    logger.info("Shutting down MEMETEK Web Service...")
    try:
        await cache.close()
    except Exception:
        pass


def create_app() -> FastAPI:
    """Create and configure FastAPI application instance."""
    app = FastAPI(
        title="MEMETEK Community Bot & Admin Dashboard",
        description="Admin dashboard and healthcheck API for MEMETEK Telegram Community",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Mount static files using resolved absolute path
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # Healthcheck directly at root /health
    @app.get("/health", tags=["Monitoring"], include_in_schema=True)
    async def root_health(session: AsyncSession = Depends(get_session)):
        db_status = "connected"
        try:
            await session.execute(text("SELECT 1"))
        except Exception as e:
            db_status = f"unhealthy ({type(e).__name__})"

        return {
            "status": "ok" if db_status == "connected" else "degraded",
            "version": "1.0.0",
            "database": db_status,
            "cache": "redis" if cache.is_redis else "in-memory",
        }

    # Routers
    app.include_router(pages.router)
    app.include_router(api.router)

    return app

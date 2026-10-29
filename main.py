"""Vercel Serverless & FastAPI Application Entrypoint for MEMETEK."""

import os
import sys
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from aiogram.types import Update

# Root directory
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from memetek.config import settings
from memetek.database.session import init_db, get_session, async_session_factory
from memetek.database.crud import seed_initial_data_if_empty
from memetek.services.cache import cache
from memetek.web.routes import pages, api
from memetek.bot.instance import create_bot, create_dispatcher

logger = logging.getLogger(__name__)

# Base directory for web assets
WEB_DIR = ROOT_DIR / "memetek" / "web"
STATIC_DIR = WEB_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown hooks."""
    try:
        if settings.APP_ENV != "serverless" or settings.TEST_MODE:
            await init_db()
            async with async_session_factory() as session:
                await seed_initial_data_if_empty(session)
    except Exception as e:
        logger.warning("Database schema check failed on startup (non-fatal): %s", e)

    try:
        await cache.connect()
    except Exception as e:
        logger.warning("Cache connect failed on startup (non-fatal): %s", e)

    yield

    try:
        await cache.close()
    except Exception:
        pass


# Top-level FastAPI instance required by Vercel
app = FastAPI(
    title="MEMETEK Community Bot & Admin Dashboard",
    description="Admin dashboard and Telegram webhook for MEMETEK",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount static assets
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# Healthcheck endpoint
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


# Include web dashboard and REST API routes
app.include_router(pages.router)
app.include_router(api.router)

# Initialize bot & dispatcher safely
bot = None
dp = None

try:
    bot = create_bot()
    dp = create_dispatcher()
except Exception as e:
    logger.error("Failed to initialize Bot: %s", e)


@app.post("/api/webhook", tags=["Telegram Webhook"])
async def telegram_webhook(request: Request):
    """Handle incoming Telegram webhook updates on Vercel."""
    if not bot or not dp:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"ok": False, "error": "Bot is not configured properly on server."},
        )

    if settings.WEBHOOK_SECRET:
        secret_header = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if secret_header != settings.WEBHOOK_SECRET:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"ok": False, "error": "Unauthorized secret token"},
            )

    try:
        payload = await request.json()
        update = Update.model_validate(payload, context={"bot": bot})
        await dp.feed_update(bot=bot, update=update)
    except Exception as e:
        return {"ok": False, "error": str(e)}

    return {"ok": True}

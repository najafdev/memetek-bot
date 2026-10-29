"""Vercel Serverless Entrypoint for MEMETEK Bot & Web Dashboard."""

import os
import sys
import logging
import traceback

# Ensure root package is in sys.path for Vercel serverless environment
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from aiogram.types import Update

logger = logging.getLogger(__name__)

# Fallback diagnostic container
startup_error = None
startup_traceback = None

try:
    from memetek.config import settings
    from memetek.web.app import create_app
    from memetek.bot.instance import create_bot, create_dispatcher

    app = create_app()

    bot = None
    dp = None

    try:
        bot = create_bot()
        dp = create_dispatcher()
    except Exception as b_err:
        logger.error("Bot/Dispatcher initialization error: %s", b_err)

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

except Exception as err:
    startup_error = str(err)
    startup_traceback = traceback.format_exc()
    logger.critical("Fatal error starting MEMETEK on Vercel: %s\n%s", err, startup_traceback)

    # Diagnostic app so Vercel does not crash with generic 500
    app = FastAPI(title="MEMETEK Diagnostic Fallback")

    @app.api_route("/{path_name:path}", methods=["GET", "POST", "PUT", "DELETE"])
    async def diagnostic_route(path_name: str):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "fatal_startup_error",
                "error": startup_error,
                "traceback": startup_traceback.splitlines() if startup_traceback else [],
            },
        )

# WSGI/ASGI handler alias for Vercel
handler = app

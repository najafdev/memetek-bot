"""Vercel Serverless Entrypoint for MEMETEK Bot & Web Dashboard."""

import os
import sys

# Ensure root package is in sys.path for Vercel serverless environment
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import Request, status
from fastapi.responses import JSONResponse
from aiogram.types import Update

from memetek.config import settings
from memetek.web.app import create_app
from memetek.bot.instance import create_bot, create_dispatcher

app = create_app()

bot = create_bot()
dp = create_dispatcher()


@app.post("/api/webhook", tags=["Telegram Webhook"])
async def telegram_webhook(request: Request):
    """Handle incoming Telegram webhook updates on Vercel."""
    # Verify secret token if configured
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
        # Return 200 OK so Telegram doesn't retry failed payload forever
        return {"ok": False, "error": str(e)}

    return {"ok": True}

"""MEMETEK Bot & Dashboard Main Application Entrypoint."""

import asyncio
import logging
import signal
import sys
import uvicorn

from memetek.config import settings, setup_logging
from memetek.database.session import init_db, async_session_factory
from memetek.database.crud import seed_initial_data_if_empty
from memetek.services.cache import cache
from memetek.bot.instance import create_bot, create_dispatcher, setup_bot_commands
from memetek.web.app import create_app

logger = logging.getLogger("memetek.main")


async def run_bot():
    """Start Telegram bot with polling."""
    logger.info("Initializing Telegram Bot...")
    if "FakeToken" in settings.TELEGRAM_BOT_TOKEN and not settings.TEST_MODE:
        logger.warning(
            "TELEGRAM_BOT_TOKEN is set to default placeholder! "
            "Please configure a valid token from @BotFather in your .env file."
        )

    bot = create_bot()
    dp = create_dispatcher()

    try:
        # Register public slash commands with Telegram
        if not settings.TEST_MODE and "FakeToken" not in settings.TELEGRAM_BOT_TOKEN:
            await setup_bot_commands(bot)

        # Delete any pending webhook if using polling
        if not settings.USE_WEBHOOK:
            await bot.delete_webhook(drop_pending_updates=False)
            logger.info("Starting Telegram Bot long-polling loop...")
            await dp.start_polling(bot)
        else:
            logger.info("Webhook mode enabled at %s", settings.WEBHOOK_URL)
            await bot.set_webhook(
                url=settings.WEBHOOK_URL,
                secret_token=settings.WEBHOOK_SECRET,
                drop_pending_updates=False,
            )
            # Keep alive
            while True:
                await asyncio.sleep(3600)

    except asyncio.CancelledError:
        logger.info("Telegram Bot loop cancelled. Cleaning up...")
    except Exception as e:
        logger.error("Telegram Bot encountered an unhandled exception: %s", e, exc_info=True)
    finally:
        await bot.session.close()
        logger.info("Telegram Bot session closed.")


async def run_web():
    """Start FastAPI Admin Dashboard & API Server."""
    logger.info(
        "Starting Web Dashboard server at http://%s:%d",
        settings.DASHBOARD_HOST,
        settings.DASHBOARD_PORT,
    )
    app = create_app()
    config = uvicorn.Config(
        app=app,
        host=settings.DASHBOARD_HOST,
        port=settings.DASHBOARD_PORT,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True,
    )
    server = uvicorn.Server(config)
    await server.serve()


async def run_all():
    """Run both Telegram Bot and FastAPI Dashboard concurrently."""
    logger.info("Booting MEMETEK Community Bot & Admin Dashboard...")
    await init_db()
    await cache.connect()

    async with async_session_factory() as session:
        await seed_initial_data_if_empty(session)

    # Concurrently run both tasks
    bot_task = asyncio.create_task(run_bot())
    web_task = asyncio.create_task(run_web())

    try:
        await asyncio.gather(bot_task, web_task)
    except asyncio.CancelledError:
        logger.info("Shutdown signal received. Terminating services...")
        bot_task.cancel()
        web_task.cancel()
        await asyncio.gather(bot_task, web_task, return_exceptions=True)
    finally:
        await cache.close()
        logger.info("All services shut down cleanly. Goodbye! 🫡")


def main():
    """CLI dispatcher."""
    setup_logging()
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "all"

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def shutdown_handler(sig, frame):
        logger.info("Received interrupt signal (%s). Initiating graceful shutdown...", sig)
        for task in asyncio.all_tasks(loop):
            task.cancel()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, shutdown_handler)
        except (ValueError, AttributeError):
            pass

    try:
        if mode == "bot":
            loop.run_until_complete(run_bot())
        elif mode == "web":
            loop.run_until_complete(run_web())
        else:
            loop.run_until_complete(run_all())
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Process interrupted by user.")
    finally:
        loop.close()


if __name__ == "__main__":
    main()

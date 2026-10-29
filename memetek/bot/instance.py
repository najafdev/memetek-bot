"""Telegram Bot and Dispatcher initialization and lifecycle configuration."""

import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeDefault

from memetek.config import settings
from memetek.bot.middlewares.db_session import DbSessionMiddleware
from memetek.bot.middlewares.user_tracker import UserTrackerMiddleware
from memetek.bot.middlewares.antispam_mw import AntiSpamMiddleware

from memetek.bot.handlers import general, fun, crypto, welcome, admin

logger = logging.getLogger(__name__)


def create_bot() -> Bot:
    """Create configured Bot instance."""
    return Bot(
        token=settings.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher() -> Dispatcher:
    """Create Dispatcher with middlewares and routers attached."""
    dp = Dispatcher()

    # 1. Attach Middlewares
    dp.update.outer_middleware(DbSessionMiddleware())
    dp.message.middleware(UserTrackerMiddleware())
    dp.message.middleware(AntiSpamMiddleware())

    # 2. Register Routers (order matters: specific before catch-all)
    dp.include_router(admin.router)
    dp.include_router(welcome.router)
    dp.include_router(crypto.router)
    dp.include_router(fun.router)
    dp.include_router(general.router)

    return dp


async def setup_bot_commands(bot: Bot) -> None:
    """Register public bot commands with Telegram BotFather UI."""
    commands = [
        BotCommand(command="start", description="Introduce the bot & quick guide"),
        BotCommand(command="help", description="Categorized command directory"),
        BotCommand(command="about", description="MEMETEK lore and description"),
        BotCommand(command="rules", description="Community rules and guidelines"),
        BotCommand(command="price", description="Real-time crypto price lookup"),
        BotCommand(command="watchlist", description="View personal token watchlist"),
        BotCommand(command="meme", description="Random meme from community vault"),
        BotCommand(command="topmemes", description="Top rated community memes"),
        BotCommand(command="submitmeme", description="Submit meme for review"),
        BotCommand(command="gm", description="Send vibrant GM greeting"),
        BotCommand(command="gn", description="Send relaxing GN greeting"),
        BotCommand(command="wagmi", description="Boost of positive community vibes"),
        BotCommand(command="ser", description="Funny degen-style crypto advice"),
        BotCommand(command="flip", description="Virtual coin flip for fun"),
        BotCommand(command="vibe", description="MEMETEK community vibe check"),
        BotCommand(command="stats", description="Community activity statistics"),
        BotCommand(command="id", description="Display chat & user Telegram IDs"),
        BotCommand(command="ping", description="Check bot status & latency"),
        BotCommand(command="admin", description="Admin moderation control panel"),
    ]
    try:
        await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
        logger.info("Bot commands successfully registered with Telegram.")
    except Exception as e:
        logger.warning("Failed to register bot commands with Telegram: %s", e)

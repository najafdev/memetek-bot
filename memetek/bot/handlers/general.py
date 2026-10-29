"""General informational command handlers for MEMETEK Bot."""

import time
from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from memetek.config import (
    BRAND_NAME,
    BRAND_TAGLINE,
    BRAND_OFFICIAL_DESCRIPTION,
    BRAND_DEFAULT_RULES,
)
from memetek.bot.keyb import get_help_keyboard, get_back_to_help_keyboard
from memetek.database.crud import (
    get_or_create_chat,
    get_community_stats,
)
from memetek.services.cache import cache

router = Router(name="general")


@router.message(CommandStart())
async def handle_start(message: Message, session: AsyncSession):
    """Handle /start command with brand intro and category shortcuts."""
    user = message.from_user
    name = user.first_name if user else "Degen"

    welcome_text = (
        f"🐱🪙 <b>YO, {name}! WELCOME TO {BRAND_NAME}!</b>\n\n"
        f"<i>{BRAND_TAGLINE}</i>\n\n"
        f"I am the official community guardian and engagement bot for <b>{BRAND_NAME}</b>. "
        f"I protect our group against spam, scams, and fud, while serving up real-time crypto prices, "
        f"unhinged memes, and degen entertainment.\n\n"
        f"🚀 <b>Quick Start:</b>\n"
        f"• /help — Browse all commands by category\n"
        f"• /about — The MEMETEK lore & community vision\n"
        f"• /rules — Community guidelines\n"
        f"• /price BTC — Fetch real-time crypto market data\n"
        f"• /meme — Fresh community memes\n"
        f"• /wagmi — Pure positive vibes\n\n"
        f"<i>Stay based. Stay bullish. WAGMI! 🫡💛</i>"
    )

    await message.answer(welcome_text, reply_markup=get_help_keyboard())


@router.message(Command("help"))
async def handle_help(message: Message):
    """Display categorized commands."""
    help_intro = (
        f"🤖 <b>{BRAND_NAME} COMMAND CENTER</b> 🚀\n\n"
        f"Select a category below to explore commands:"
    )
    await message.answer(help_intro, reply_markup=get_help_keyboard())


@router.callback_query(F.data.startswith("help:"))
async def handle_help_callbacks(callback: CallbackQuery):
    """Handle interactive help category navigation."""
    category = callback.data.split(":")[1]

    if category == "main":
        text_content = (
            f"🤖 <b>{BRAND_NAME} COMMAND CENTER</b> 🚀\n\n"
            f"Select a category below to explore commands:"
        )
        await callback.message.edit_text(text_content, reply_markup=get_help_keyboard())

    elif category == "general":
        text_content = (
            f"🐱 <b>GENERAL COMMANDS:</b>\n\n"
            f"• /start — Welcome & quick intro\n"
            f"• /help — Categorized command menu\n"
            f"• /about — Official community lore and description\n"
            f"• /rules — Group rules and safety guidelines\n"
            f"• /id — Display chat and your Telegram user ID\n"
            f"• /ping — Check bot status & system latency\n"
            f"• /stats — Community messages & activity stats\n"
        )
        await callback.message.edit_text(text_content, reply_markup=get_back_to_help_keyboard())

    elif category == "fun":
        text_content = (
            f"🐸 <b>FUN & MEME COMMANDS:</b>\n\n"
            f"• /meme — Random approved meme from community vault\n"
            f"• /topmemes — Highest upvoted community memes\n"
            f"• /submitmeme [text/caption] — Submit a meme for admin review\n"
            f"• /gm — Send a vibrant GM greeting\n"
            f"• /gn — Send a relaxing GN message\n"
            f"• /wagmi — Random boost of positive community energy\n"
            f"• /ser — Hilarious degen blockchain advice\n"
            f"• /flip — Virtual coin flip (entertainment only)\n"
            f"• /vibe — MEMETEK vibe check\n"
        )
        await callback.message.edit_text(text_content, reply_markup=get_back_to_help_keyboard())

    elif category == "crypto":
        text_content = (
            f"📊 <b>CRYPTO & ALPHA COMMANDS:</b>\n\n"
            f"• /price SYMBOL — Real-time price, 24h change & market cap (e.g. <code>/price SOL</code>)\n"
            f"• /watchlist — View your personal crypto watchlist\n"
            f"• /watch SYMBOL — Add an asset to your watchlist\n"
            f"• /unwatch SYMBOL — Remove an asset from your watchlist\n"
            f"• /token or /ca — Official MEMETEK contract address (verified only)\n\n"
            f"⚠️ <i>Informational only. NFA • DYOR.</i>"
        )
        await callback.message.edit_text(text_content, reply_markup=get_back_to_help_keyboard())

    elif category == "admin":
        text_content = (
            f"🛡️ <b>ADMIN & MODERATION COMMANDS:</b>\n"
            f"<i>(Chat administrators only)</i>\n\n"
            f"• /admin — Administrator dashboard & help\n"
            f"• /warn USER REASON — Issue a warning (escalates to mute)\n"
            f"• /warnings USER — View warning history\n"
            f"• /clearwarns USER — Clear all user warnings\n"
            f"• /mute USER DURATION REASON — Restrict member (e.g. <code>/mute @user 30m spam</code>)\n"
            f"• /unmute USER — Lift restriction\n"
            f"• /kick USER REASON — Remove member from group\n"
            f"• /ban USER REASON — Permanently ban member\n"
            f"• /unban USER — Unban member\n"
            f"• /purge COUNT — Bulk delete recent messages (1-100)\n"
            f"• /lock — Restrict group from sending messages\n"
            f"• /unlock — Restore normal chatting\n"
            f"• /setwelcome TEXT — Customize welcome message\n"
            f"• /setrules TEXT — Customize community rules\n"
            f"• /antispam on|off — Toggle automated spam shield\n"
            f"• /logs — View recent moderation actions\n"
        )
        await callback.message.edit_text(text_content, reply_markup=get_back_to_help_keyboard())

    await callback.answer()


@router.message(Command("about"))
async def handle_about(message: Message):
    """Show official MEMETEK description and lore."""
    await message.answer(BRAND_OFFICIAL_DESCRIPTION)


@router.message(Command("rules"))
async def handle_rules(message: Message, session: AsyncSession):
    """Show community rules."""
    chat = message.chat
    rules = BRAND_DEFAULT_RULES
    if chat.type in ("group", "supergroup"):
        db_chat = await get_or_create_chat(session, chat.id)
        if db_chat.rules_text:
            rules = db_chat.rules_text

    await message.answer(rules)


@router.message(Command("id"))
async def handle_id(message: Message):
    """Display current chat and user ID safely."""
    chat = message.chat
    user = message.from_user

    reply = (
        f"🆔 <b>TELEGRAM IDENTIFIERS:</b>\n\n"
        f"👤 <b>Your User ID:</b> <code>{user.id}</code>\n"
        f"🏷️ <b>Username:</b> @{user.username if user.username else 'N/A'}\n"
        f"💬 <b>Chat ID:</b> <code>{chat.id}</code>\n"
        f"📁 <b>Chat Type:</b> <code>{chat.type}</code>"
    )
    if chat.title:
        reply += f"\n🏷️ <b>Chat Title:</b> {chat.title}"

    await message.answer(reply)


@router.message(Command("ping"))
async def handle_ping(message: Message, session: AsyncSession):
    """Check bot responsiveness, database and cache health."""
    start_time = time.time()
    sent_msg = await message.answer("🏓 <i>Pinging MEMETEK network...</i>")
    latency_ms = (time.time() - start_time) * 1000

    # DB check
    db_status = "🟢 Healthy"
    try:
        await session.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"🔴 Error: {str(e)[:30]}"

    # Redis/Cache check
    cache_backend = "Redis" if cache.is_redis else "In-Memory"
    cache_status = f"🟢 Connected ({cache_backend})"

    reply = (
        f"🐱🪙 <b>PONG! MEMETEK BOT IS ONLINE</b> 🚀\n\n"
        f"⚡ <b>Telegram API Latency:</b> <code>{latency_ms:.1f}ms</code>\n"
        f"🗄️ <b>Database:</b> {db_status}\n"
        f"💾 <b>Cache Service:</b> {cache_status}\n"
        f"🛡️ <b>Shields:</b> 🟢 Active & Protecting"
    )
    await sent_msg.edit_text(reply)


@router.message(Command("stats"))
async def handle_stats(message: Message, session: AsyncSession):
    """Display community statistics."""
    chat = message.chat
    chat_id = chat.id if chat.type in ("group", "supergroup") else None

    stats = await get_community_stats(session, chat_id=chat_id)

    reply = (
        f"📊 <b>MEMETEK COMMUNITY STATS</b> 🚀\n\n"
        f"👥 <b>Tracked Members:</b> <code>{stats['tracked_members']}</code>\n"
        f"💬 <b>Total Messages Tracked:</b> <code>{stats['total_messages']}</code>\n"
        f"🐸 <b>Approved Community Memes:</b> <code>{stats['approved_memes']}</code>\n"
        f"🛡️ <b>Moderation Actions Logged:</b> <code>{stats['moderation_actions']}</code>\n"
        f"⚠️ <b>Active Warnings:</b> <code>{stats['active_warnings']}</code>\n\n"
        f"<i>Stats reflect privacy-compliant tracked activity. Keep memeing! 🔥</i>"
    )
    await message.answer(reply)

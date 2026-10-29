"""Crypto market and token command handlers for MEMETEK Bot."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from memetek.config import settings, BRAND_NAME
from memetek.services.market import market_service
from memetek.services.pumpfun import pumpfun_service
from memetek.bot.filters.admin import is_user_chat_admin
from memetek.database.crud import (
    get_or_create_chat,
    get_user_watchlist,
    add_to_watchlist,
    remove_from_watchlist,
)

router = Router(name="crypto")


@router.message(Command("price"))
async def handle_price(message: Message):
    """Fetch real-time asset market data."""
    parts = message.text.split() if message.text else []
    if len(parts) < 2:
        supported = ", ".join(settings.supported_symbols_list)
        await message.answer(
            f"ℹ️ <b>USAGE:</b> <code>/price SYMBOL</code>\n"
            f"Example: <code>/price BTC</code> or <code>/price SOL</code>\n\n"
            f"Supported symbols: {supported}"
        )
        return

    symbol = parts[1].strip().upper()
    result = await market_service.get_price(symbol)

    if not result.get("success"):
        error_msg = result.get("error", "Unable to retrieve price data.")
        await message.answer(f"❌ {error_msg}")
        return

    data = result["data"]
    formatted = market_service.format_price_message(data)
    await message.answer(formatted)


@router.message(Command("watchlist"))
async def handle_watchlist(message: Message, session: AsyncSession):
    """Display user's informational crypto watchlist."""
    user = message.from_user
    if not user:
        return

    symbols = await get_user_watchlist(session, user.id)
    if not symbols:
        await message.answer(
            "📋 <b>YOUR WATCHLIST IS EMPTY</b>\n\n"
            "Add tokens to your personal watchlist using:\n"
            "<code>/watch SYMBOL</code> (e.g. <code>/watch BTC</code>)\n\n"
            "<i>Keep track of your favorite meme and tech coins! 🚀</i>"
        )
        return

    text = f"📋 <b>YOUR {BRAND_NAME} WATCHLIST:</b>\n\n"
    for sym in symbols:
        price_res = await market_service.get_price(sym)
        if price_res.get("success"):
            p_data = price_res["data"]
            price_val = p_data["price"]
            change = p_data["change_24h"]
            ch_str = f"+{change:.1f}%" if change >= 0 else f"{change:.1f}%"
            text += f"• <b>${sym}</b>: <code>${price_val:,.4f}</code> ({ch_str})\n"
        else:
            text += f"• <b>${sym}</b>: <i>Data unavailable</i>\n"

    text += (
        "\n<i>Manage your watchlist with /watch and /unwatch.</i>\n"
        "⚠️ <i>Informational only. NFA • DYOR.</i>"
    )
    await message.answer(text)


@router.message(Command("watch"))
async def handle_watch(message: Message, session: AsyncSession):
    """Add a symbol to user's watchlist."""
    user = message.from_user
    if not user:
        return

    parts = message.text.split() if message.text else []
    if len(parts) < 2:
        await message.answer("ℹ️ <b>Usage:</b> <code>/watch SYMBOL</code> (e.g. <code>/watch SOL</code>)")
        return

    symbol = parts[1].strip().upper()
    coin_id = market_service.resolve_coin_id(symbol)
    if not coin_id:
        await message.answer(
            f"❌ <b>${symbol}</b> is not a supported market symbol.\n"
            f"Supported: {', '.join(settings.supported_symbols_list)}"
        )
        return

    added = await add_to_watchlist(session, user.id, symbol)
    if added:
        await message.answer(f"✅ Added <b>${symbol}</b> to your personal watchlist! View with <code>/watchlist</code>.")
    else:
        await message.answer(f"ℹ️ <b>${symbol}</b> is already in your watchlist.")


@router.message(Command("unwatch"))
async def handle_unwatch(message: Message, session: AsyncSession):
    """Remove a symbol from user's watchlist."""
    user = message.from_user
    if not user:
        return

    parts = message.text.split() if message.text else []
    if len(parts) < 2:
        await message.answer("ℹ️ <b>Usage:</b> <code>/unwatch SYMBOL</code> (e.g. <code>/unwatch SOL</code>)")
        return

    symbol = parts[1].strip().upper()
    removed = await remove_from_watchlist(session, user.id, symbol)
    if removed:
        await message.answer(f"🗑️ Removed <b>${symbol}</b> from your watchlist.")
    else:
        await message.answer(f"ℹ️ <b>${symbol}</b> was not in your watchlist.")


@router.message(Command("token", "ca"))
async def handle_token_info(message: Message, session: AsyncSession):
    """Display official MEMETEK contract address if configured, or safety warning."""
    chat = message.chat
    ca_address = None

    if chat.type in ("group", "supergroup"):
        db_chat = await get_or_create_chat(session, chat.id)
        ca_address = db_chat.official_contract_address

    if ca_address:
        reply = (
            f"🐱🪙 <b>OFFICIAL {BRAND_NAME} TOKEN CONTRACT</b> 💎\n\n"
            f"<b>Contract Address (CA):</b>\n"
            f"<code>{ca_address}</code>\n\n"
            f"⚠️ <b>SAFETY FIRST:</b> Always verify the contract address character-by-character "
            f"before interacting on decentralized exchanges (DEX). "
            f"Never trust random DMs offering tokens or claiming alternative contracts!"
        )
    else:
        reply = (
            f"🐱🪙 <b>OFFICIAL {BRAND_NAME} TOKEN INFORMATION</b>\n\n"
            f"🛡️ <b>STATUS:</b> <i>No official token contract has been announced yet.</i>\n\n"
            f"🚨 <b>SCAM ALERT:</b> Anyone sharing contract addresses, presale links, or airdrop claims "
            f"in DMs or unofficial channels is a SCAMMER trying to steal your funds.\n\n"
            f"📌 Official announcements will ONLY appear in our pinned messages and verified group links."
        )

    await message.answer(reply)


@router.message(Command("whales", "whale"))
async def handle_whales_info(message: Message):
    """Display tracked Pump.fun alpha whales and tracker status."""
    whales_list = "\n".join([f"  • <b>{w}</b>" for w in pumpfun_service.tracked_whales])
    text = (
        f"🐋 <b>PUMP.FUN WHALE TRACKER</b> 💊\n\n"
        f"The MEMETEK buy bot monitors on-chain Pump.fun buys and tags key alpha degens:\n\n"
        f"<b>Currently Tracked Whales:</b>\n"
        f"{whales_list}\n\n"
        f"🔔 <i>Whenever a tracked buy occurs, the bot broadcasts an alert here with token details, "
        f"green buy volume bars, and tags!</i>\n\n"
        f"💡 <i>Admins can test the alert using:</i> <code>/simulatebuy [SOL amount]</code>"
    )
    await message.answer(text, disable_web_page_preview=True)


@router.message(Command("simulatebuy", "testbuy"))
async def handle_simulate_buy(message: Message):
    """Admin command to simulate a live Pump.fun whale buy alert."""
    user = message.from_user
    if not user:
        return

    # Check permission
    is_admin = await is_user_chat_admin(message.bot, message.chat.id, user.id)
    if not is_admin:
        await message.answer("⚠️ <i>Only chat administrators can trigger buy simulation tests.</i>")
        return

    # Check optional SOL amount in argument
    parts = message.text.split() if message.text else []
    sol_amount = 3.5
    if len(parts) > 1:
        try:
            sol_amount = float(parts[1])
        except ValueError:
            pass

    alert_text = pumpfun_service.format_buy_alert(
        token_symbol="MEMETEK",
        token_name="MEMETEK Token",
        contract_address="8kG8M3M3T3KpumpFUNmoonCOINtokenCA123456789pump",
        sol_amount=sol_amount,
        usd_amount=sol_amount * 200.0,
        tokens_bought=sol_amount * 5200000,
        market_cap_usd=84200.0,
        buyer_handle="@slingoor",
        tx_hash="5xTestHashSolanaPumpfunTxPreview123456789",
    )

    await message.answer(alert_text, disable_web_page_preview=False)


@router.message(Command("trackwhale"))
async def handle_add_tracked_whale(message: Message):
    """Add a new whale handle to track (Admins only)."""
    user = message.from_user
    if not user:
        return

    is_admin = await is_user_chat_admin(message.bot, message.chat.id, user.id)
    if not is_admin:
        await message.answer("⚠️ <i>Only chat administrators can modify the whale watch list.</i>")
        return

    parts = message.text.split() if message.text else []
    if len(parts) < 2:
        await message.answer("ℹ️ <b>Usage:</b> <code>/trackwhale @username</code>")
        return

    handle = parts[1].strip()
    added = pumpfun_service.add_whale(handle)
    if added:
        await message.answer(f"✅ Added <b>{handle}</b> to the Pump.fun whale watch list! 🐋")
    else:
        await message.answer(f"ℹ️ <b>{handle}</b> is already in the whale watch list.")


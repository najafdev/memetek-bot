"""Pump.fun Whale Tracker and Buy Alert Service for MEMETEK."""

import html
import logging
from typing import List, Optional, Dict, Any
from aiogram import Bot

logger = logging.getLogger(__name__)

# Default tracked alpha whales
DEFAULT_TRACKED_WHALES: List[str] = [
    "@slingoor",
    "@The__Solstice",
    "@crackthecode",
]

DEFAULT_TOKEN_CA = "8kG8M3M3T3KpumpFUNmoonCOINtokenCA123456789pump"
DEFAULT_TOKEN_SYMBOL = "MEMETEK"
DEFAULT_TOKEN_NAME = "MEMETEK Token"


class PumpFunWhaleService:
    """Service for formatting and broadcasting Pump.fun whale buy alerts."""

    def __init__(self, tracked_whales: Optional[List[str]] = None):
        self.tracked_whales = tracked_whales or list(DEFAULT_TRACKED_WHALES)

    def add_whale(self, handle: str) -> bool:
        """Add a whale handle if not already present."""
        clean_handle = handle.strip()
        if not clean_handle.startswith("@"):
            clean_handle = f"@{clean_handle}"
        if clean_handle not in self.tracked_whales:
            self.tracked_whales.append(clean_handle)
            return True
        return False

    def remove_whale(self, handle: str) -> bool:
        """Remove a whale handle if present."""
        clean_handle = handle.strip()
        if not clean_handle.startswith("@"):
            clean_handle = f"@{clean_handle}"
        if clean_handle in self.tracked_whales:
            self.tracked_whales.remove(clean_handle)
            return True
        return False

    def format_buy_alert(
        self,
        token_symbol: str = DEFAULT_TOKEN_SYMBOL,
        token_name: str = DEFAULT_TOKEN_NAME,
        contract_address: str = DEFAULT_TOKEN_CA,
        sol_amount: float = 2.5,
        usd_amount: Optional[float] = None,
        tokens_bought: Optional[float] = None,
        market_cap_usd: Optional[float] = None,
        buyer_handle: Optional[str] = None,
        tx_hash: Optional[str] = None,
        extra_whales: Optional[List[str]] = None,
    ) -> str:
        """Format an internet-native, high-energy Pump.fun buy alert."""
        # Calculate dynamic green circles (proportional to SOL amount)
        green_count = max(4, min(int(sol_amount * 3), 36))
        green_bar = "🟢" * green_count

        # Approximate USD amount if not provided (assume ~$200/SOL)
        usd_val = usd_amount if usd_amount is not None else (sol_amount * 200.0)

        # Buyer tags
        whales_to_tag = list(self.tracked_whales)
        if extra_whales:
            for w in extra_whales:
                if w not in whales_to_tag:
                    whales_to_tag.append(w)

        whales_str = " ".join(whales_to_tag)

        # Buyer representation
        buyer_str = buyer_handle or whales_to_tag[0] if whales_to_tag else "Whale Degen"

        # Format tokens bought
        tokens_str = (
            f"{tokens_bought:,.0f}"
            if tokens_bought is not None
            else f"{sol_amount * 4500000:,.0f}"
        )

        # Format market cap
        mc_str = f"${market_cap_usd:,.0f}" if market_cap_usd else "$68,420"

        # Safe CA preview
        ca_short = (
            f"{contract_address[:6]}...{contract_address[-4:]}"
            if len(contract_address) > 12
            else contract_address
        )

        pump_url = f"https://pump.fun/coin/{contract_address}"
        tx_url = f"https://solscan.io/tx/{tx_hash}" if tx_hash else "https://solscan.io"

        message = (
            f"🚀🚀🚀 <b>PUMP.FUN WHALE BUY ALERT!</b> 💊\n\n"
            f"🔥 <b>Token:</b> {html.escape(token_name)} (<code>${html.escape(token_symbol)}</code>)\n"
            f"🛒 <b>Platform:</b> <a href=\"{pump_url}\">Pump.fun 💊</a>\n\n"
            f"💰 <b>Spent:</b> <b>{sol_amount:.2f} SOL</b> (~${usd_val:,.2f} USD)\n"
            f"🪙 <b>Acquired:</b> <code>{tokens_str}</code> ${html.escape(token_symbol)}\n"
            f"📊 <b>Market Cap:</b> <code>{mc_str}</code>\n"
            f"👤 <b>Buyer:</b> {html.escape(buyer_str)}\n\n"
            f"{green_bar}\n\n"
            f"🐋 <b>Whales on Watch:</b>\n"
            f"👉 {whales_str}\n\n"
            f"🔗 <a href=\"{pump_url}\"><b>Trade on Pump.fun</b></a> | "
            f"🔍 <a href=\"{tx_url}\"><b>Solscan Tx</b></a>\n"
            f"📋 <code>{html.escape(contract_address)}</code>\n\n"
            f"<i>⚠️ DYOR • Not Financial Advice • Where Memes Meet the Moon 🚀</i>"
        )
        return message

    async def broadcast_buy_alert(
        self,
        bot: Bot,
        chat_id: int,
        alert_text: str,
        media_url: Optional[str] = None,
    ) -> bool:
        """Send formatted buy alert to a designated Telegram chat."""
        try:
            if media_url:
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=media_url,
                    caption=alert_text,
                    parse_mode="HTML",
                )
            else:
                await bot.send_message(
                    chat_id=chat_id,
                    text=alert_text,
                    parse_mode="HTML",
                    disable_web_page_preview=False,
                )
            return True
        except Exception as e:
            logger.error("Failed to broadcast buy alert to chat %s: %s", chat_id, e)
            return False


# Singleton service instance
pumpfun_service = PumpFunWhaleService()

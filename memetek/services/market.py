"""Crypto market data service using CoinGecko public API with caching and attribution."""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Any
import httpx
from memetek.config import settings
from memetek.services.cache import cache

logger = logging.getLogger(__name__)

# Standard coin mapping: Symbol -> CoinGecko API ID
SYMBOL_MAP = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "BNB": "binancecoin",
    "DOGE": "dogecoin",
    "PEPE": "pepe",
    "SHIB": "shiba-inu",
    "BONK": "bonk",
    "WIF": "dogwifcoin",
    "FLOKI": "floki",
    "SUI": "sui",
    "AVAX": "avalanche-2",
    "ADA": "cardano",
    "XRP": "ripple",
    "NEAR": "near",
}


class MarketService:
    """Service to fetch real-time crypto market data with rate-limiting and caching."""

    BASE_URL = "https://api.coingecko.com/api/v3"

    def __init__(self, api_key: str = "", cache_ttl: int = 60):
        self.api_key = api_key
        self.cache_ttl = cache_ttl

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": "MEMETEK-Community-Bot/1.0",
        }
        if self.api_key:
            headers["x-cg-demo-api-key"] = self.api_key
        return headers

    def resolve_coin_id(self, symbol: str) -> Optional[str]:
        """Resolve a ticker symbol to its CoinGecko ID."""
        clean = symbol.strip().upper()
        return SYMBOL_MAP.get(clean)

    async def get_price(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch market data for symbol.
        Returns a dictionary with status, formatted text, and raw data.
        """
        clean_symbol = symbol.strip().upper()
        coin_id = self.resolve_coin_id(clean_symbol)

        if not coin_id:
            supported = ", ".join(settings.supported_symbols_list)
            return {
                "success": False,
                "error": f"Symbol <b>${clean_symbol}</b> is not in the supported list.\nSupported symbols: {supported}",
            }

        cache_key = f"market_price:{clean_symbol}"
        cached = await cache.get(cache_key)
        if cached:
            try:
                data = json.loads(cached) if isinstance(cached, str) else cached
                return {"success": True, "data": data, "from_cache": True}
            except Exception:
                pass

        # Make API request to CoinGecko
        url = f"{self.BASE_URL}/coins/markets"
        params = {
            "vs_currency": "usd",
            "ids": coin_id,
            "order": "market_cap_desc",
            "per_page": 1,
            "page": 1,
            "sparkline": "false",
            "price_change_percentage": "24h",
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.get(url, params=params, headers=self._get_headers())

            if response.status_code == 429:
                return {
                    "success": False,
                    "error": "Market data rate limit reached. Please wait a moment and try again. ⏳",
                }

            if response.status_code != 200:
                logger.error("CoinGecko API returned status %s: %s", response.status_code, response.text)
                return {
                    "success": False,
                    "error": f"Unable to fetch market data from CoinGecko (HTTP {response.status_code}).",
                }

            results = response.json()
            if not results or not isinstance(results, list):
                return {
                    "success": False,
                    "error": f"No market data found for {clean_symbol}.",
                }

            coin_data = results[0]
            current_price = coin_data.get("current_price", 0.0)
            price_change_24h = coin_data.get("price_change_percentage_24h") or 0.0
            market_cap = coin_data.get("market_cap") or 0
            volume_24h = coin_data.get("total_volume") or 0

            timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

            result_payload = {
                "symbol": clean_symbol,
                "name": coin_data.get("name", clean_symbol),
                "price": current_price,
                "change_24h": price_change_24h,
                "market_cap": market_cap,
                "volume_24h": volume_24h,
                "timestamp": timestamp_str,
                "source": "CoinGecko Public API",
            }

            # Cache the response
            await cache.set(cache_key, json.dumps(result_payload), ttl=self.cache_ttl)

            return {
                "success": True,
                "data": result_payload,
                "from_cache": False,
            }

        except httpx.TimeoutException:
            logger.warning("CoinGecko API request timed out for %s", clean_symbol)
            return {
                "success": False,
                "error": "Market data request timed out. Public API may be experiencing high latency.",
            }
        except Exception as e:
            logger.exception("Error querying market data for %s: %s", clean_symbol, e)
            return {
                "success": False,
                "error": f"Market data provider error: {str(e)}",
            }

    def format_price_message(self, data: Dict[str, Any]) -> str:
        """Format price dictionary into branded HTML Telegram message."""
        symbol = data["symbol"]
        name = data["name"]
        price = data["price"]
        change = data["change_24h"]
        market_cap = data["market_cap"]
        source = data["source"]
        timestamp = data["timestamp"]

        # Formatting price
        if price >= 1.0:
            price_str = f"${price:,.2f}"
        elif price >= 0.0001:
            price_str = f"${price:,.6f}"
        else:
            price_str = f"${price:,.10f}"

        # Direction emoji
        if change > 0:
            change_str = f"🟢 +{change:.2f}% (Bullish! 🚀)"
        elif change < 0:
            change_str = f"🔴 {change:.2f}% (DIP! 📉)"
        else:
            change_str = f"⚪ 0.00% (Crab 🦀)"

        mcap_str = f"${market_cap:,.0f}" if market_cap else "N/A"

        return (
            f"🐱🪙 <b>MEMETEK MARKET ALPHA: ${symbol}</b> ({name})\n\n"
            f"💵 <b>Price:</b> <code>{price_str}</code>\n"
            f"📊 <b>24h Change:</b> {change_str}\n"
            f"🏛️ <b>Market Cap:</b> <code>{mcap_str}</code>\n\n"
            f"🕒 <i>Timestamp: {timestamp}</i>\n"
            f"📡 <i>Source: {source}</i>\n\n"
            f"⚠️ <i>DYOR • NFA • Entertainment & informational purposes only.</i>"
        )


market_service = MarketService(
    api_key=settings.COINGECKO_API_KEY,
    cache_ttl=settings.MARKET_CACHE_TTL_SECONDS,
)

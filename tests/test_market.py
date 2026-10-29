"""Tests for Crypto Market Data Service."""

import pytest
from unittest.mock import AsyncMock, patch
import httpx

from memetek.services.market import MarketService


@pytest.mark.asyncio
async def test_symbol_resolution():
    """Check standard crypto tickers resolve to CoinGecko IDs."""
    service = MarketService()
    assert service.resolve_coin_id("BTC") == "bitcoin"
    assert service.resolve_coin_id("btc") == "bitcoin"
    assert service.resolve_coin_id("ETH") == "ethereum"
    assert service.resolve_coin_id("SOL") == "solana"
    assert service.resolve_coin_id("DOGE") == "dogecoin"
    assert service.resolve_coin_id("PEPE") == "pepe"
    assert service.resolve_coin_id("NONEXISTENTCOIN999") is None


@pytest.mark.asyncio
async def test_unsupported_symbol():
    """Verify informative error when asking for unknown symbol."""
    service = MarketService()
    res = await service.get_price("RANDOMFAKECOIN")
    assert res["success"] is False
    assert "not in the supported list" in res["error"]


@pytest.mark.asyncio
async def test_format_price_message():
    """Verify formatted Telegram HTML message contains required fields and disclaimers."""
    service = MarketService()
    mock_data = {
        "symbol": "BTC",
        "name": "Bitcoin",
        "price": 95123.45,
        "change_24h": 4.56,
        "market_cap": 1850000000000,
        "volume_24h": 45000000000,
        "timestamp": "2026-10-29 12:00:00 UTC",
        "source": "CoinGecko Public API",
    }
    formatted = service.format_price_message(mock_data)

    assert "$BTC" in formatted
    assert "Bitcoin" in formatted
    assert "$95,123.45" in formatted
    assert "+4.56%" in formatted
    assert "CoinGecko Public API" in formatted
    assert "DYOR • NFA" in formatted


@pytest.mark.asyncio
async def test_mocked_api_success():
    """Verify get_price parsing when API returns valid coin data."""
    service = MarketService()
    fake_coingecko_response = [
        {
            "id": "solana",
            "symbol": "sol",
            "name": "Solana",
            "current_price": 210.50,
            "market_cap": 98000000000,
            "total_volume": 4200000000,
            "price_change_percentage_24h": 7.82,
        }
    ]

    mock_resp = httpx.Response(
        status_code=200,
        json=fake_coingecko_response,
        request=httpx.Request("GET", "https://api.coingecko.com"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        res = await service.get_price("SOL")

        assert res["success"] is True
        assert res["data"]["symbol"] == "SOL"
        assert res["data"]["price"] == 210.50
        assert res["data"]["change_24h"] == 7.82


@pytest.mark.asyncio
async def test_api_rate_limit_handling():
    """Verify graceful handling when API rate limit is exceeded."""
    service = MarketService()
    mock_resp = httpx.Response(
        status_code=429,
        text="Rate limited",
        request=httpx.Request("GET", "https://api.coingecko.com"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        res = await service.get_price("BTC")

        assert res["success"] is False
        assert "rate limit" in res["error"].lower()


@pytest.mark.asyncio
async def test_api_timeout_handling():
    """Verify graceful fallback on network timeout."""
    service = MarketService()

    with patch("httpx.AsyncClient.get", side_effect=httpx.TimeoutException("Connection timed out")):
        res = await service.get_price("BTC")

        assert res["success"] is False
        assert "timed out" in res["error"].lower()

"""Unit and integration tests for Pump.fun Whale Buy Tracker."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from memetek.services.pumpfun import PumpFunWhaleService, DEFAULT_TRACKED_WHALES
from main import app
from memetek.bot.handlers.crypto import handle_whales_info, handle_simulate_buy, handle_add_tracked_whale


def test_pumpfun_format_buy_alert():
    """Verify buy alert message formatting and required tags."""
    service = PumpFunWhaleService()

    alert = service.format_buy_alert(
        token_symbol="MEMETEK",
        token_name="MEMETEK Moon Coin",
        contract_address="8kG8M3M3T3KpumpFUNmoonCOINtokenCA123456789pump",
        sol_amount=5.0,
        usd_amount=1000.0,
        tokens_bought=25000000,
        market_cap_usd=50000.0,
        buyer_handle="@slingoor",
    )

    # Assertions
    assert "PUMP.FUN WHALE BUY ALERT!" in alert
    assert "MEMETEK" in alert
    assert "5.00 SOL" in alert
    assert "$1,000.00 USD" in alert
    assert "🟢" in alert
    assert "@slingoor" in alert
    assert "@The__Solstice" in alert
    assert "@crackthecode" in alert
    assert "https://pump.fun/coin/8kG8M3M3T3KpumpFUNmoonCOINtokenCA123456789pump" in alert


def test_whale_service_add_remove():
    """Verify adding and removing whale handles."""
    service = PumpFunWhaleService(tracked_whales=["@slingoor", "@The__Solstice"])

    assert service.add_whale("@crackthecode") is True
    assert "@crackthecode" in service.tracked_whales
    # Duplicate addition should return False
    assert service.add_whale("@crackthecode") is False

    # Auto prefix with @
    assert service.add_whale("new_whale") is True
    assert "@new_whale" in service.tracked_whales

    # Removal
    assert service.remove_whale("@new_whale") is True
    assert "@new_whale" not in service.tracked_whales
    assert service.remove_whale("@nonexistent") is False


def test_tracked_whales_api_endpoint():
    """Verify /api/tracked-whales returns currently tracked whales."""
    with TestClient(app) as test_client:
        resp = test_client.get("/api/tracked-whales")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "@slingoor" in data["tracked_whales"]
        assert "@The__Solstice" in data["tracked_whales"]
        assert "@crackthecode" in data["tracked_whales"]


@pytest.mark.asyncio
async def test_handle_whales_info_handler():
    """Test /whales Telegram command handler outputs tracked whales."""
    message = AsyncMock()
    message.answer = AsyncMock()

    await handle_whales_info(message)

    message.answer.assert_called_once()
    called_text = message.answer.call_args[0][0]
    assert "PUMP.FUN WHALE TRACKER" in called_text
    assert "@slingoor" in called_text
    assert "@The__Solstice" in called_text
    assert "@crackthecode" in called_text


@pytest.mark.asyncio
async def test_simulate_buy_handler(mock_bot):
    """Test /simulatebuy admin command triggers formatted buy alert."""
    message = AsyncMock()
    message.bot = mock_bot
    message.chat.id = -100999
    message.from_user.id = 123456789  # Global superadmin
    message.text = "/simulatebuy 10.0"
    message.answer = AsyncMock()

    await handle_simulate_buy(message)

    message.answer.assert_called_once()
    called_text = message.answer.call_args[0][0]
    assert "PUMP.FUN WHALE BUY ALERT!" in called_text
    assert "10.00 SOL" in called_text
    assert "@slingoor" in called_text
    assert "@The__Solstice" in called_text
    assert "@crackthecode" in called_text


def test_whale_buy_webhook_endpoint():
    """Test POST /api/whale-buy invokes broadcast and returns success."""
    from unittest.mock import patch, AsyncMock
    from fastapi.testclient import TestClient
    from memetek.web.app import create_app

    app = create_app()
    with patch("memetek.services.pumpfun.PumpFunWhaleService.broadcast_buy_alert", new=AsyncMock(return_value=True)):
        with TestClient(app) as test_client:
            resp = test_client.post(
                "/api/whale-buy",
                json={
                    "token_symbol": "MEMETEK",
                    "sol_amount": 7.5,
                    "buyer": "@slingoor",
                    "chat_id": 1122866063,
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert data["token"] == "MEMETEK"
            assert "@slingoor" in data["tagged_whales"]



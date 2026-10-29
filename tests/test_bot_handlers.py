"""Tests for General, Fun, and Crypto Bot Handlers."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from memetek.bot.handlers.general import (
    handle_start,
    handle_help,
    handle_about,
    handle_rules,
    handle_id,
    handle_ping,
    handle_stats,
)
from memetek.bot.handlers.fun import (
    handle_gm,
    handle_gn,
    handle_wagmi,
    handle_ser,
    handle_flip,
    handle_vibe,
    handle_meme,
    handle_submit_meme,
)
from memetek.bot.handlers.crypto import (
    handle_price,
    handle_watchlist,
    handle_watch,
    handle_unwatch,
    handle_token_info,
)
from memetek.bot.handlers.welcome import handle_welcome_preview


@pytest.mark.asyncio
async def test_start_command(mock_message, db_session: AsyncSession):
    """Test /start introduction response."""
    await handle_start(mock_message, db_session)
    mock_message.answer.assert_called_once()
    reply = mock_message.answer.call_args[0][0]
    assert "WELCOME TO MEMETEK" in reply
    assert "Where Memes Meet the Moon" in reply


@pytest.mark.asyncio
async def test_help_command(mock_message):
    """Test /help command."""
    await handle_help(mock_message)
    mock_message.answer.assert_called_once()
    reply = mock_message.answer.call_args[0][0]
    assert "COMMAND CENTER" in reply


@pytest.mark.asyncio
async def test_about_command(mock_message):
    """Test /about command."""
    await handle_about(mock_message)
    mock_message.answer.assert_called_once()
    reply = mock_message.answer.call_args[0][0]
    assert "Not just a meme coin community" in reply
    assert "DYOR • NFA" in reply


@pytest.mark.asyncio
async def test_rules_command(mock_message, db_session: AsyncSession):
    """Test /rules command."""
    await handle_rules(mock_message, db_session)
    mock_message.answer.assert_called_once()
    reply = mock_message.answer.call_args[0][0]
    assert "MEMETEK COMMUNITY RULES" in reply
    assert "Respect the Fam" in reply


@pytest.mark.asyncio
async def test_id_command(mock_message):
    """Test /id command."""
    await handle_id(mock_message)
    mock_message.answer.assert_called_once()
    reply = mock_message.answer.call_args[0][0]
    assert str(mock_message.from_user.id) in reply
    assert str(mock_message.chat.id) in reply


@pytest.mark.asyncio
async def test_ping_command(mock_message, db_session: AsyncSession):
    """Test /ping command."""
    sent_msg = AsyncMock()
    mock_message.answer.return_value = sent_msg

    await handle_ping(mock_message, db_session)
    mock_message.answer.assert_called_once()
    sent_msg.edit_text.assert_called_once()
    edit_reply = sent_msg.edit_text.call_args[0][0]
    assert "PONG!" in edit_reply
    assert "🟢 Healthy" in edit_reply


@pytest.mark.asyncio
async def test_stats_command(mock_message, db_session: AsyncSession):
    """Test /stats command."""
    await handle_stats(mock_message, db_session)
    mock_message.answer.assert_called_once()
    reply = mock_message.answer.call_args[0][0]
    assert "MEMETEK COMMUNITY STATS" in reply
    assert "Tracked Members:" in reply


@pytest.mark.asyncio
async def test_fun_greetings(mock_message):
    """Test /gm, /gn, /wagmi, /ser, /flip, /vibe."""
    # GM
    await handle_gm(mock_message)
    assert "GM" in mock_message.answer.call_args[0][0]

    # GN
    await handle_gn(mock_message)
    assert "GN" in mock_message.answer.call_args[0][0]

    # WAGMI
    await handle_wagmi(mock_message)
    assert any(w in mock_message.answer.call_args[0][0] for w in ["WAGMI", "GONNA MAKE IT"])

    # SER
    await handle_ser(mock_message)
    assert "Ser" in mock_message.answer.call_args[0][0]

    # FLIP
    await handle_flip(mock_message)
    flip_reply = mock_message.answer.call_args[0][0]
    assert "VIRTUAL COIN FLIP" in flip_reply
    assert "DISCLAIMER" in flip_reply
    assert "NOT a trading signal" in flip_reply

    # VIBE
    await handle_vibe(mock_message)
    assert "VIBE" in mock_message.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_meme_and_submission(mock_message, db_session: AsyncSession):
    """Test /meme and /submitmeme."""
    # Seed memes and test /meme
    await handle_meme(mock_message, db_session)
    mock_message.answer.assert_called()
    assert "MEMETEK VAULT MEME" in mock_message.answer.call_args[0][0]

    # Submit meme
    mock_message.text = "/submitmeme When you hold through a 90% dip because of memes"
    await handle_submit_meme(mock_message, db_session)
    submit_reply = mock_message.answer.call_args[0][0]
    assert "MEME SUBMITTED!" in submit_reply
    assert "moderator approval queue" in submit_reply


@pytest.mark.asyncio
async def test_crypto_price_command(mock_message):
    """Test /price command handling."""
    # Usage prompt without args
    mock_message.text = "/price"
    await handle_price(mock_message)
    assert "USAGE:" in mock_message.answer.call_args[0][0]

    # Mocked price response
    mock_message.text = "/price BTC"
    with patch("memetek.services.market.market_service.get_price", new_callable=AsyncMock) as mock_get_price:
        mock_get_price.return_value = {
            "success": True,
            "data": {
                "symbol": "BTC",
                "name": "Bitcoin",
                "price": 95000.0,
                "change_24h": 3.5,
                "market_cap": 1800000000000,
                "volume_24h": 40000000000,
                "timestamp": "2026-10-29 12:00:00 UTC",
                "source": "CoinGecko Public API",
            },
        }
        await handle_price(mock_message)
        assert "$BTC" in mock_message.answer.call_args[0][0]
        assert "$95,000.00" in mock_message.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_crypto_watchlist_commands(mock_message, db_session: AsyncSession):
    """Test /watchlist, /watch, and /unwatch."""
    # Empty watchlist
    mock_message.text = "/watchlist"
    await handle_watchlist(mock_message, db_session)
    assert "YOUR WATCHLIST IS EMPTY" in mock_message.answer.call_args[0][0]

    # Add to watchlist
    mock_message.text = "/watch SOL"
    await handle_watch(mock_message, db_session)
    assert "Added <b>$SOL</b>" in mock_message.answer.call_args[0][0]

    # Remove from watchlist
    mock_message.text = "/unwatch SOL"
    await handle_unwatch(mock_message, db_session)
    assert "Removed <b>$SOL</b>" in mock_message.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_token_info_command(mock_message, db_session: AsyncSession):
    """Test /token or /ca command scam warning when unannounced."""
    mock_message.text = "/token"
    await handle_token_info(mock_message, db_session)
    reply = mock_message.answer.call_args[0][0]
    assert "No official token contract has been announced yet" in reply
    assert "SCAM ALERT" in reply


@pytest.mark.asyncio
async def test_welcome_preview(mock_message, db_session: AsyncSession):
    """Test /previewwelcome."""
    await handle_welcome_preview(mock_message, db_session)
    reply = mock_message.answer.call_args[0][0]
    assert "WELCOME MESSAGE PREVIEW" in reply
    assert "WELCOME TO MEMETEK" in reply

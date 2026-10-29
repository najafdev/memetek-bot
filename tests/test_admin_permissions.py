"""Tests for Administrator Permissions and Moderation Commands."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from aiogram.types import ChatMemberAdministrator, ChatMemberMember
from sqlalchemy.ext.asyncio import AsyncSession

from memetek.bot.filters.admin import IsChatAdmin, is_user_chat_admin
from memetek.bot.handlers.admin import (
    handle_admin_menu,
    handle_warn,
    handle_warnings,
    handle_clearwarns,
    handle_mute,
    handle_unmute,
    handle_kick,
    handle_ban,
    handle_unban,
    handle_purge,
    handle_lock,
    handle_unlock,
    handle_antispam_toggle,
    handle_setwelcome,
    handle_setrules,
    parse_duration,
)


@pytest.mark.asyncio
async def test_duration_parser():
    """Verify parse_duration helper."""
    assert parse_duration("30s").total_seconds() == 30
    assert parse_duration("15m").total_seconds() == 900
    assert parse_duration("2h").total_seconds() == 7200
    assert parse_duration("1d").total_seconds() == 86400
    assert parse_duration("invalid") is None


@pytest.mark.asyncio
async def test_admin_filter_rejection(mock_bot):
    """Test non-admin member is rejected by admin filter."""
    chat_id = -100123
    normal_user_id = 55555

    # Mock Telegram Bot API returning regular member
    mock_member = MagicMock(spec=ChatMemberMember)
    mock_member.status = "member"
    mock_bot.get_chat_member.return_value = mock_member

    is_admin = await is_user_chat_admin(mock_bot, chat_id, normal_user_id)
    assert is_admin is False


@pytest.mark.asyncio
async def test_admin_filter_acceptance(mock_bot):
    """Test Telegram chat administrator is accepted."""
    chat_id = -100123
    admin_user_id = 77777

    # Mock Telegram Bot API returning administrator
    mock_admin = MagicMock(spec=ChatMemberAdministrator)
    mock_admin.status = "administrator"
    mock_bot.get_chat_member.return_value = mock_admin

    is_admin = await is_user_chat_admin(mock_bot, chat_id, admin_user_id)
    assert is_admin is True


@pytest.mark.asyncio
async def test_superadmin_filter_acceptance(mock_bot):
    """Test global bot superadmin in settings.ADMIN_USER_IDS is always accepted."""
    chat_id = -100123
    superadmin_id = 123456789  # in settings.ADMIN_USER_IDS

    is_admin = await is_user_chat_admin(mock_bot, chat_id, superadmin_id)
    assert is_admin is True


@pytest.mark.asyncio
async def test_warn_and_escalation(mock_message, mock_bot, db_session: AsyncSession):
    """Test warning escalation: 3rd warning triggers automated mute."""
    mock_message.reply_to_message = MagicMock()
    mock_message.reply_to_message.from_user = MagicMock(id=88888, username="badactor")
    mock_message.text = "/warn scam shilling"

    # Warning 1
    await handle_warn(mock_message, mock_bot, db_session)
    reply1 = mock_message.answer.call_args[0][0]
    assert "1/3" in reply1
    mock_bot.restrict_chat_member.assert_not_called()

    # Warning 2
    await handle_warn(mock_message, mock_bot, db_session)
    reply2 = mock_message.answer.call_args[0][0]
    assert "2/3" in reply2
    mock_bot.restrict_chat_member.assert_not_called()

    # Warning 3 -> Threshold reached!
    await handle_warn(mock_message, mock_bot, db_session)
    reply3 = mock_message.answer.call_args[0][0]
    assert "3/3" in reply3
    assert "THRESHOLD REACHED!" in reply3
    mock_bot.restrict_chat_member.assert_called_once()


@pytest.mark.asyncio
async def test_warnings_and_clearwarns(mock_message, db_session: AsyncSession):
    """Test /warnings and /clearwarns commands."""
    mock_message.reply_to_message = MagicMock()
    mock_message.reply_to_message.from_user = MagicMock(id=77777)

    # Check warnings
    await handle_warnings(mock_message, db_session)
    assert "0 active warnings" in mock_message.answer.call_args[0][0]

    # Clear warnings
    await handle_clearwarns(mock_message, db_session)
    assert "Cleared" in mock_message.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_mute_and_unmute(mock_message, mock_bot, db_session: AsyncSession):
    """Test /mute and /unmute commands."""
    mock_message.reply_to_message = MagicMock()
    mock_message.reply_to_message.from_user = MagicMock(id=66666)
    mock_message.text = "/mute 45m spamming"

    await handle_mute(mock_message, mock_bot, db_session)
    mock_bot.restrict_chat_member.assert_called_once()
    assert "USER MUTED" in mock_message.answer.call_args[0][0]

    # Unmute
    await handle_unmute(mock_message, mock_bot, db_session)
    assert "unmuted" in mock_message.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_kick_and_ban(mock_message, mock_bot, db_session: AsyncSession):
    """Test /kick and /ban commands."""
    mock_message.reply_to_message = MagicMock()
    mock_message.reply_to_message.from_user = MagicMock(id=55555)
    mock_message.text = "/kick breaking rules"

    # Kick
    await handle_kick(mock_message, mock_bot, db_session)
    mock_bot.ban_chat_member.assert_called_once()
    mock_bot.unban_chat_member.assert_called_once()
    assert "kicked" in mock_message.answer.call_args[0][0]

    # Ban
    mock_message.text = "/ban malicious bot"
    await handle_ban(mock_message, mock_bot, db_session)
    assert "USER BANNED" in mock_message.answer.call_args[0][0]

    # Unban
    mock_message.text = "/unban 55555"
    await handle_unban(mock_message, mock_bot, db_session)
    assert "unbanned" in mock_message.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_purge_command(mock_message, mock_bot, db_session: AsyncSession):
    """Test /purge command."""
    mock_message.text = "/purge 5"
    mock_message.message_id = 50

    await handle_purge(mock_message, mock_bot, db_session)
    mock_bot.delete_message.assert_called()
    mock_bot.send_message.assert_called()


@pytest.mark.asyncio
async def test_lock_and_unlock(mock_message, mock_bot, db_session: AsyncSession):
    """Test /lock and /unlock commands."""
    # Lock
    await handle_lock(mock_message, mock_bot, db_session)
    mock_bot.set_chat_permissions.assert_called()
    assert "CHAT LOCKED" in mock_message.answer.call_args[0][0]

    # Unlock
    await handle_unlock(mock_message, mock_bot, db_session)
    assert "CHAT UNLOCKED" in mock_message.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_admin_settings_updates(mock_message, db_session: AsyncSession):
    """Test /antispam, /setwelcome, /setrules."""
    # Antispam toggle
    mock_message.text = "/antispam off"
    await handle_antispam_toggle(mock_message, db_session)
    assert "DISABLED" in mock_message.answer.call_args[0][0]

    # Setwelcome
    mock_message.text = "/setwelcome Welcome to the Moon, {name}!"
    await handle_setwelcome(mock_message, db_session)
    assert "Welcome message updated" in mock_message.answer.call_args[0][0]

    # Setrules
    mock_message.text = "/setrules 1. Be based. 2. Meme hard."
    await handle_setrules(mock_message, db_session)
    assert "Community rules updated" in mock_message.answer.call_args[0][0]

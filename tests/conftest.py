"""Pytest fixtures and configuration for MEMETEK test suite."""

import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from aiogram.types import User as TgUser, Chat as TgChat, Message as TgMessage, CallbackQuery as TgCallbackQuery

from memetek.database.models import Base
from memetek.config import settings

# Force test mode
settings.TEST_MODE = True
settings.DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
)
test_session_factory = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide fresh in-memory SQLite session per test."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with test_session_factory() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def mock_bot() -> AsyncMock:
    """Mock aiogram Bot instance."""
    bot = AsyncMock()
    bot.id = 999999999
    bot.send_message = AsyncMock(return_value=MagicMock(message_id=101))
    bot.delete_message = AsyncMock(return_value=True)
    bot.restrict_chat_member = AsyncMock(return_value=True)
    bot.ban_chat_member = AsyncMock(return_value=True)
    bot.unban_chat_member = AsyncMock(return_value=True)
    bot.set_chat_permissions = AsyncMock(return_value=True)
    return bot


@pytest.fixture
def mock_tg_user() -> TgUser:
    """Mock standard Telegram User."""
    return TgUser(
        id=12345,
        is_bot=False,
        first_name="TestDegen",
        last_name="Hodler",
        username="testdegen",
    )


@pytest.fixture
def mock_admin_user() -> TgUser:
    """Mock Admin Telegram User."""
    return TgUser(
        id=123456789,  # Configured in settings.ADMIN_USER_IDS
        is_bot=False,
        first_name="AdminChad",
        last_name="Memetek",
        username="adminchad",
    )


@pytest.fixture
def mock_group_chat() -> TgChat:
    """Mock Telegram Group Chat."""
    return TgChat(
        id=-100987654321,
        type="supergroup",
        title="MEMETEK Official Lounge",
        username="memetek_lounge",
    )


@pytest.fixture
def mock_message(mock_tg_user, mock_group_chat, mock_bot) -> TgMessage:
    """Create a mock Telegram message."""
    msg = MagicMock(spec=TgMessage)
    msg.message_id = 42
    msg.from_user = mock_tg_user
    msg.chat = mock_group_chat
    msg.text = "/start"
    msg.caption = None
    msg.document = None
    msg.photo = None
    msg.reply_to_message = None
    msg.answer = AsyncMock()
    msg.delete = AsyncMock()
    msg.bot = mock_bot
    return msg

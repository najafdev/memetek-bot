"""Database session middleware for aiogram 3."""

from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from memetek.database.session import async_session_factory


class DbSessionMiddleware(BaseMiddleware):
    """Provides an isolated AsyncSession per update."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        async with async_session_factory() as session:
            data["session"] = session
            try:
                return await handler(event, data)
            except Exception:
                await session.rollback()
                raise

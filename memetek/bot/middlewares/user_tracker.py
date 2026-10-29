"""User activity and privacy-conscious membership tracker."""

import logging
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message
from sqlalchemy.ext.asyncio import AsyncSession

from memetek.database.crud import (
    get_or_create_chat,
    get_or_create_user,
    record_chat_activity,
)

logger = logging.getLogger(__name__)


class UserTrackerMiddleware(BaseMiddleware):
    """Tracks message activity and ensures user/chat entities exist."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        session: AsyncSession = data.get("session")
        if not session:
            return await handler(event, data)

        if isinstance(event, Message):
            user = event.from_user
            chat = event.chat

            if user and not user.is_bot:
                db_user = await get_or_create_user(
                    session=session,
                    user_id=user.id,
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    is_bot=user.is_bot,
                )

                if chat.type in ("group", "supergroup"):
                    await get_or_create_chat(
                        session=session,
                        chat_id=chat.id,
                        title=chat.title,
                        username=chat.username,
                    )
                    # Respect privacy tracking opt-out
                    if not db_user.opt_out_tracking:
                        await record_chat_activity(
                            session=session,
                            chat_id=chat.id,
                            user_id=user.id,
                        )

        return await handler(event, data)

"""Telegram Chat Administrator and Superadmin Filters."""

import logging
from typing import Union
from aiogram import Bot
from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery, ChatMemberOwner, ChatMemberAdministrator

from memetek.config import settings

logger = logging.getLogger(__name__)


async def is_user_chat_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    """
    Verify whether a user is an actual administrator in the given Telegram chat,
    or a configured global bot superadmin.
    Never trusts user-supplied claims or usernames.
    """
    # 1. Global superadmins always have administrative privileges
    if user_id in settings.admin_id_set:
        return True

    # 2. Check actual chat permissions via Telegram Bot API
    try:
        member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        return isinstance(member, (ChatMemberOwner, ChatMemberAdministrator)) or member.status in (
            "creator",
            "administrator",
        )
    except Exception as e:
        logger.warning(
            "Failed to fetch chat member status for user %s in chat %s: %s",
            user_id,
            chat_id,
            e,
        )
        return False


class IsChatAdmin(BaseFilter):
    """
    Filter verifying that the sender is an actual Telegram chat administrator
    or configured bot superadmin.
    """

    async def __call__(
        self,
        event: Union[Message, CallbackQuery],
        bot: Bot,
    ) -> bool:
        user = event.from_user
        if not user:
            return False

        chat = event.chat if isinstance(event, Message) else (event.message.chat if event.message else None)
        if not chat:
            return user.id in settings.admin_id_set

        # In private chat, only global superadmins have access to admin actions
        if chat.type == "private":
            return user.id in settings.admin_id_set

        return await is_user_chat_admin(bot, chat.id, user.id)


class IsBotSuperAdmin(BaseFilter):
    """Filter verifying that the user is configured in ADMIN_USER_IDS."""

    async def __call__(
        self,
        event: Union[Message, CallbackQuery],
    ) -> bool:
        user = event.from_user
        if not user:
            return False
        return user.id in settings.admin_id_set

"""Anti-spam message inspection middleware."""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware, Bot
from aiogram.types import TelegramObject, Message, ChatPermissions
from sqlalchemy.ext.asyncio import AsyncSession

from memetek.config import settings
from memetek.services.antispam import antispam_service
from memetek.bot.filters.admin import is_user_chat_admin
from memetek.database.crud import (
    get_or_create_chat,
    get_allowed_domains,
    add_warning,
    record_moderation_action,
)

logger = logging.getLogger(__name__)


class AntiSpamMiddleware(BaseMiddleware):
    """Inspects incoming group messages for spam, scams, flooding, and phishing."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)

        message: Message = event
        chat = message.chat
        user = message.from_user

        # Only process group and supergroup messages
        if chat.type not in ("group", "supergroup") or not user or user.is_bot:
            return await handler(event, data)

        bot: Bot = data["bot"]
        session: AsyncSession = data.get("session")

        # Check if chat has anti-spam enabled
        db_chat = await get_or_create_chat(
            session=session,
            chat_id=chat.id,
            title=chat.title,
            username=chat.username,
        )
        if not db_chat.anti_spam_enabled:
            return await handler(event, data)

        # Check if user is an administrator (exempt from automated spam checks)
        is_admin = await is_user_chat_admin(bot, chat.id, user.id)
        if is_admin:
            return await handler(event, data)

        # Extract message content & attachment details
        text = message.text or message.caption or ""
        filename = message.document.file_name if message.document else None
        user_name = user.full_name

        # Retrieve allowed domains
        allowed_domains = await get_allowed_domains(session, chat.id)

        # Inspect message
        result = await antispam_service.inspect_message(
            chat_id=chat.id,
            user_id=user.id,
            text=text,
            user_name=user_name,
            filename=filename,
            allowed_domains=allowed_domains,
            is_chat_admin=False,
        )

        if not result.is_violation:
            return await handler(event, data)

        # Process violation
        logger.warning(
            "AntiSpam violation in chat %s by user %s (%s): %s [Action: %s]",
            chat.id,
            user.id,
            user.full_name,
            result.reason,
            result.action_type,
        )

        # Attempt to delete the offending message
        try:
            await message.delete()
        except Exception as e:
            logger.debug("Failed to delete spam message: %s", e)

        user_mention = user.mention_html(user.first_name)

        if result.action_type in ("delete", "warn"):
            # Issue a formal warning
            warn_count = await add_warning(
                session=session,
                chat_id=chat.id,
                user_id=user.id,
                reason=result.reason,
                moderator_user_id=None,  # Automated
            )
            await record_moderation_action(
                session=session,
                chat_id=chat.id,
                target_user_id=user.id,
                action_type="automated_warn",
                reason=result.reason,
                is_automated=True,
            )

            # Check threshold escalation
            if warn_count >= settings.MAX_WARNINGS_BEFORE_MUTE:
                until_date = datetime.now(timezone.utc) + timedelta(minutes=settings.MUTE_DURATION_MINUTES)
                try:
                    await bot.restrict_chat_member(
                        chat_id=chat.id,
                        user_id=user.id,
                        permissions=ChatPermissions(can_send_messages=False),
                        until_date=until_date,
                    )
                    await record_moderation_action(
                        session=session,
                        chat_id=chat.id,
                        target_user_id=user.id,
                        action_type="automated_mute",
                        reason=f"Reached warning limit ({warn_count}/{settings.MAX_WARNINGS_BEFORE_MUTE})",
                        duration_seconds=settings.MUTE_DURATION_MINUTES * 60,
                        is_automated=True,
                    )
                    escalation_msg = await chat.send_message(
                        f"🛡️ <b>AUTOMATED MODERATION</b> 🔨\n\n"
                        f"{user_mention} has reached <b>{warn_count} warnings</b> and is temporarily muted for "
                        f"<b>{settings.MUTE_DURATION_MINUTES} minutes</b>.\n"
                        f"Reason: <i>{result.reason}</i>\n\n"
                        f"📌 <i>Follow /rules to keep MEMETEK safe and based!</i>"
                    )
                    # Auto-delete notification after 60 seconds
                    asyncio.create_task(_delayed_delete(escalation_msg, 60))
                except Exception as e:
                    logger.warning("Failed to restrict user on warning limit: %s", e)
            else:
                warn_msg = await chat.send_message(
                    f"⚠️ <b>MEMETEK SECURITY ALERT</b>\n\n"
                    f"{user_mention}, your message was removed for violating community safety rules.\n"
                    f"<b>Reason:</b> <i>{result.reason}</i>\n"
                    f"<b>Active Warnings:</b> {warn_count}/{settings.MAX_WARNINGS_BEFORE_MUTE}\n\n"
                    f"ℹ️ <i>{result.safe_disclaimer}</i>"
                )
                asyncio.create_task(_delayed_delete(warn_msg, 45))

        elif result.action_type == "mute":
            until_date = datetime.now(timezone.utc) + timedelta(minutes=settings.MUTE_DURATION_MINUTES)
            try:
                await bot.restrict_chat_member(
                    chat_id=chat.id,
                    user_id=user.id,
                    permissions=ChatPermissions(can_send_messages=False),
                    until_date=until_date,
                )
                await record_moderation_action(
                    session=session,
                    chat_id=chat.id,
                    target_user_id=user.id,
                    action_type="automated_mute",
                    reason=result.reason,
                    duration_seconds=settings.MUTE_DURATION_MINUTES * 60,
                    is_automated=True,
                )
                mute_msg = await chat.send_message(
                    f"🔇 <b>MEMETEK FLOOD PROTECTION</b>\n\n"
                    f"{user_mention} was temporarily muted for {settings.MUTE_DURATION_MINUTES}m.\n"
                    f"Reason: <i>{result.reason}</i>"
                )
                asyncio.create_task(_delayed_delete(mute_msg, 30))
            except Exception as e:
                logger.warning("Failed to mute user on flood: %s", e)

        # Suppress further event processing for violating message
        return None


async def _delayed_delete(message: Message, delay_seconds: int) -> None:
    """Helper to auto-delete a warning notification after delay."""
    await asyncio.sleep(delay_seconds)
    try:
        await message.delete()
    except Exception:
        pass

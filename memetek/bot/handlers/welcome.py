"""Welcome system handlers for newly joined chat members."""

import asyncio
import html
import logging
from aiogram import Router, F, Bot
from aiogram.filters import Command, ChatMemberUpdatedFilter, JOIN_TRANSITION
from aiogram.types import Message, ChatMemberUpdated, User
from sqlalchemy.ext.asyncio import AsyncSession

from memetek.config import BRAND_DEFAULT_WELCOME
from memetek.database.crud import get_or_create_chat, get_or_create_user
from memetek.bot.filters.admin import IsChatAdmin

logger = logging.getLogger(__name__)

router = Router(name="welcome")


async def _schedule_message_deletion(message: Message, delay_seconds: int) -> None:
    """Delete a sent welcome message after the configured delay."""
    if delay_seconds <= 0:
        return
    await asyncio.sleep(delay_seconds)
    try:
        await message.delete()
    except Exception as e:
        logger.debug("Failed to delete welcome message after %ss: %s", delay_seconds, e)


async def send_welcome_for_user(
    bot: Bot,
    chat_id: int,
    user: User,
    session: AsyncSession,
) -> None:
    """Format and send the branded welcome message to a newly joined user."""
    db_chat = await get_or_create_chat(session, chat_id)
    if not db_chat.welcome_enabled:
        return

    # Track user
    await get_or_create_user(
        session=session,
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        is_bot=user.is_bot,
    )

    template = db_chat.welcome_text or BRAND_DEFAULT_WELCOME
    safe_name = user.mention_html(html.escape(user.first_name))
    safe_username = f"@{user.username}" if user.username else safe_name
    chat_title = html.escape(db_chat.title or "MEMETEK")

    formatted_text = template.replace("{name}", safe_name)
    formatted_text = formatted_text.replace("{username}", safe_username)
    formatted_text = formatted_text.replace("{chat_title}", chat_title)

    try:
        if db_chat.welcome_media_url:
            sent_msg = await bot.send_photo(
                chat_id=chat_id,
                photo=db_chat.welcome_media_url,
                caption=formatted_text,
            )
        else:
            sent_msg = await bot.send_message(
                chat_id=chat_id,
                text=formatted_text,
                disable_web_page_preview=True,
            )

        if db_chat.welcome_delete_seconds > 0:
            asyncio.create_task(
                _schedule_message_deletion(sent_msg, db_chat.welcome_delete_seconds)
            )

    except Exception as e:
        logger.error("Error sending welcome message in chat %s: %s", chat_id, e)


@router.chat_member(ChatMemberUpdatedFilter(JOIN_TRANSITION))
async def handle_new_chat_member_event(
    event: ChatMemberUpdated,
    bot: Bot,
    session: AsyncSession,
):
    """Event triggered when a user joins the group via link or invite."""
    new_user = event.new_chat_member.user
    if new_user.is_bot:
        return

    await send_welcome_for_user(
        bot=bot,
        chat_id=event.chat.id,
        user=new_user,
        session=session,
    )


@router.message(F.new_chat_members)
async def handle_new_chat_members_message(
    message: Message,
    bot: Bot,
    session: AsyncSession,
):
    """Fallback handler for service message 'User joined the group'."""
    if not message.new_chat_members:
        return

    for new_user in message.new_chat_members:
        if not new_user.is_bot:
            await send_welcome_for_user(
                bot=bot,
                chat_id=message.chat.id,
                user=new_user,
                session=session,
            )


@router.message(Command("previewwelcome"), IsChatAdmin())
async def handle_welcome_preview(message: Message, session: AsyncSession):
    """Preview the active welcome message format."""
    chat = message.chat
    user = message.from_user

    db_chat = await get_or_create_chat(session, chat.id)
    template = db_chat.welcome_text or BRAND_DEFAULT_WELCOME

    safe_name = user.mention_html(html.escape(user.first_name))
    safe_username = f"@{user.username}" if user.username else safe_name
    chat_title = html.escape(chat.title or "MEMETEK")

    preview = template.replace("{name}", safe_name)
    preview = preview.replace("{username}", safe_username)
    preview = preview.replace("{chat_title}", chat_title)

    header = "👁️ <b>WELCOME MESSAGE PREVIEW:</b>\n"
    header += f"<i>(Auto-delete is set to {db_chat.welcome_delete_seconds}s)</i>\n\n"

    await message.answer(header + preview)

"""Administrator and moderation command handlers for MEMETEK Bot."""

import asyncio
import html
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from aiogram import Router, Bot
from aiogram.filters import Command
from aiogram.types import Message, ChatPermissions
from sqlalchemy.ext.asyncio import AsyncSession

from memetek.config import settings, BRAND_NAME
from memetek.bot.filters.admin import IsChatAdmin
from memetek.database.crud import (
    get_or_create_chat,
    update_chat_settings,
    add_warning,
    get_active_warnings,
    clear_warnings,
    record_moderation_action,
    get_recent_moderation_actions,
)

logger = logging.getLogger(__name__)

router = Router(name="admin")
# Apply admin filter across this router
router.message.filter(IsChatAdmin())


def parse_duration(duration_str: str) -> Optional[timedelta]:
    """Parse string duration (e.g., '10m', '2h', '1d', '30s') into timedelta."""
    match = re.match(r"^(\d+)([smhd])$", duration_str.lower().strip())
    if not match:
        return None
    val, unit = int(match.group(1)), match.group(2)
    if unit == "s":
        return timedelta(seconds=val)
    elif unit == "m":
        return timedelta(minutes=val)
    elif unit == "h":
        return timedelta(hours=val)
    elif unit == "d":
        return timedelta(days=val)
    return None


def resolve_target_user(message: Message) -> Tuple[Optional[int], Optional[str]]:
    """
    Resolve target user_id and reason from reply or command arguments.
    Returns (target_user_id, reason).
    """
    args = message.text.split()[1:] if message.text else []

    # Case 1: Reply to a message
    if message.reply_to_message and message.reply_to_message.from_user:
        target_id = message.reply_to_message.from_user.id
        reason = " ".join(args) if args else "No reason specified"
        return target_id, reason

    # Case 2: User ID supplied as first argument
    if args and args[0].isdigit():
        target_id = int(args[0])
        reason = " ".join(args[1:]) if len(args) > 1 else "No reason specified"
        return target_id, reason

    return None, None


@router.message(Command("admin"))
async def handle_admin_menu(message: Message, session: AsyncSession):
    """Display administrative overview and current chat settings."""
    chat = message.chat
    db_chat = await get_or_create_chat(session, chat.id)

    status_antispam = "🟢 ENABLED" if db_chat.anti_spam_enabled else "🔴 DISABLED"
    status_welcome = "🟢 ENABLED" if db_chat.welcome_enabled else "🔴 DISABLED"
    status_locked = "🔴 LOCKED" if db_chat.is_locked else "🟢 UNLOCKED"

    reply = (
        f"🛡️ <b>{BRAND_NAME} ADMINISTRATOR COMMAND CENTER</b> 🛡️\n\n"
        f"<b>Chat:</b> {html.escape(chat.title or 'Unknown')} (<code>{chat.id}</code>)\n"
        f"• Anti-Spam Shield: {status_antispam}\n"
        f"• Welcome System: {status_welcome} (Auto-delete: {db_chat.welcome_delete_seconds}s)\n"
        f"• Group Chat State: {status_locked}\n"
        f"• Official CA: <code>{db_chat.official_contract_address or 'Not Configured'}</code>\n\n"
        f"<b>Moderation Tools:</b>\n"
        f"• <code>/warn USER REASON</code> — Issue warning\n"
        f"• <code>/warnings USER</code> — View warning history\n"
        f"• <code>/clearwarns USER</code> — Clear warnings\n"
        f"• <code>/mute USER DURATION REASON</code> — Restrict user (e.g. <code>30m</code>)\n"
        f"• <code>/unmute USER</code> — Lift mute\n"
        f"• <code>/kick USER REASON</code> — Kick user\n"
        f"• <code>/ban USER REASON</code> — Ban user\n"
        f"• <code>/unban USER</code> — Unban user\n"
        f"• <code>/purge COUNT</code> — Delete last 1-100 messages\n"
        f"• <code>/lock</code> & <code>/unlock</code> — Toggle group send permissions\n"
        f"• <code>/setwelcome TEXT</code> — Update welcome message\n"
        f"• <code>/setrules TEXT</code> — Update community rules\n"
        f"• <code>/antispam on|off</code> — Toggle automated spam shield\n"
        f"• <code>/logs</code> — Moderation audit trail"
    )
    await message.answer(reply)


@router.message(Command("warn"))
async def handle_warn(message: Message, bot: Bot, session: AsyncSession):
    """Issue a warning to a member."""
    chat = message.chat
    mod_user = message.from_user

    target_id, reason = resolve_target_user(message)
    if not target_id:
        await message.answer("ℹ️ <b>Usage:</b> Reply to user's message with <code>/warn REASON</code> or <code>/warn USER_ID REASON</code>")
        return

    # Don't warn the bot itself or self
    if target_id == mod_user.id or target_id == bot.id:
        await message.answer("❌ Invalid target user.")
        return

    await get_or_create_chat(session, chat.id)

    warn_count = await add_warning(
        session=session,
        chat_id=chat.id,
        user_id=target_id,
        reason=reason,
        moderator_user_id=mod_user.id,
    )
    await record_moderation_action(
        session=session,
        chat_id=chat.id,
        target_user_id=target_id,
        moderator_user_id=mod_user.id,
        action_type="warn",
        reason=reason,
    )

    reply = (
        f"⚠️ <b>WARNING ISSUED</b> ⚠️\n\n"
        f"<b>Target ID:</b> <code>{target_id}</code>\n"
        f"<b>Moderator:</b> @{mod_user.username or mod_user.first_name}\n"
        f"<b>Reason:</b> <i>{html.escape(reason)}</i>\n"
        f"<b>Active Warnings:</b> {warn_count}/{settings.MAX_WARNINGS_BEFORE_MUTE}"
    )

    # Automatic escalation if threshold met
    if warn_count >= settings.MAX_WARNINGS_BEFORE_MUTE:
        until_date = datetime.now(timezone.utc) + timedelta(minutes=settings.MUTE_DURATION_MINUTES)
        try:
            await bot.restrict_chat_member(
                chat_id=chat.id,
                user_id=target_id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until_date,
            )
            reply += (
                f"\n\n🚨 <b>THRESHOLD REACHED!</b> User has been automatically restricted for "
                f"<b>{settings.MUTE_DURATION_MINUTES} minutes</b>."
            )
        except Exception as e:
            logger.warning("Failed to auto-mute user on warn escalation: %s", e)

    await message.answer(reply)


@router.message(Command("warnings"))
async def handle_warnings(message: Message, session: AsyncSession):
    """View warning history for a user."""
    target_id, _ = resolve_target_user(message)
    if not target_id:
        await message.answer("ℹ️ <b>Usage:</b> Reply to a user with <code>/warnings</code> or <code>/warnings USER_ID</code>")
        return

    await get_or_create_chat(session, message.chat.id)
    active_warns = await get_active_warnings(session, message.chat.id, target_id)
    if not active_warns:
        await message.answer(f"✅ User <code>{target_id}</code> has 0 active warnings.")
        return

    reply = f"⚠️ <b>ACTIVE WARNINGS FOR USER</b> <code>{target_id}</code> ({len(active_warns)} total):\n\n"
    for i, w in enumerate(active_warns, 1):
        date_str = w.created_at.strftime("%Y-%m-%d %H:%M")
        reply += f"<b>{i}.</b> [{date_str}] <i>{html.escape(w.reason)}</i>\n"

    await message.answer(reply)


@router.message(Command("clearwarns"))
async def handle_clearwarns(message: Message, session: AsyncSession):
    """Clear all active warnings for a user."""
    target_id, _ = resolve_target_user(message)
    if not target_id:
        await message.answer("ℹ️ <b>Usage:</b> Reply to a user with <code>/clearwarns</code> or <code>/clearwarns USER_ID</code>")
        return

    await get_or_create_chat(session, message.chat.id)
    cleared = await clear_warnings(session, message.chat.id, target_id)
    await record_moderation_action(
        session=session,
        chat_id=message.chat.id,
        target_user_id=target_id,
        moderator_user_id=message.from_user.id,
        action_type="clearwarns",
        reason="Manual warning reset by administrator",
    )
    await message.answer(f"✅ Cleared <b>{cleared} active warnings</b> for user <code>{target_id}</code>.")


@router.message(Command("mute"))
async def handle_mute(message: Message, bot: Bot, session: AsyncSession):
    """Temporarily restrict a user."""
    chat = message.chat
    args = message.text.split()[1:] if message.text else []

    target_id = None
    duration = timedelta(minutes=60)
    reason = "Violating group rules"

    if message.reply_to_message and message.reply_to_message.from_user:
        target_id = message.reply_to_message.from_user.id
        if args:
            parsed_d = parse_duration(args[0])
            if parsed_d:
                duration = parsed_d
                reason = " ".join(args[1:]) if len(args) > 1 else reason
            else:
                reason = " ".join(args)
    elif args and args[0].isdigit():
        target_id = int(args[0])
        if len(args) > 1:
            parsed_d = parse_duration(args[1])
            if parsed_d:
                duration = parsed_d
                reason = " ".join(args[2:]) if len(args) > 2 else reason
            else:
                reason = " ".join(args[1:])

    if not target_id:
        await message.answer(
            "ℹ️ <b>Usage:</b> Reply with <code>/mute [duration] [reason]</code>\n"
            "Example: <code>/mute 30m excessive spamming</code>"
        )
        return

    until_date = datetime.now(timezone.utc) + duration
    duration_secs = int(duration.total_seconds())

    await get_or_create_chat(session, chat.id)

    try:
        await bot.restrict_chat_member(
            chat_id=chat.id,
            user_id=target_id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until_date,
        )
        await record_moderation_action(
            session=session,
            chat_id=chat.id,
            target_user_id=target_id,
            moderator_user_id=message.from_user.id,
            action_type="mute",
            reason=reason,
            duration_seconds=duration_secs,
        )
        await message.answer(
            f"🔇 <b>USER MUTED</b>\n\n"
            f"<b>Target ID:</b> <code>{target_id}</code>\n"
            f"<b>Duration:</b> {duration_secs // 60} minutes\n"
            f"<b>Reason:</b> <i>{html.escape(reason)}</i>"
        )
    except Exception as e:
        await message.answer(f"❌ Failed to mute member: {str(e)}")


@router.message(Command("unmute"))
async def handle_unmute(message: Message, bot: Bot, session: AsyncSession):
    """Remove a restriction from a member."""
    chat = message.chat
    target_id, _ = resolve_target_user(message)
    if not target_id:
        await message.answer("ℹ️ <b>Usage:</b> Reply with <code>/unmute</code> or <code>/unmute USER_ID</code>")
        return

    await get_or_create_chat(session, chat.id)

    try:
        await bot.restrict_chat_member(
            chat_id=chat.id,
            user_id=target_id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_photos=True,
                can_send_videos=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            ),
        )
        await record_moderation_action(
            session=session,
            chat_id=chat.id,
            target_user_id=target_id,
            moderator_user_id=message.from_user.id,
            action_type="unmute",
            reason="Unmuted by admin",
        )
        await message.answer(f"🔊 User <code>{target_id}</code> has been unmuted.")
    except Exception as e:
        await message.answer(f"❌ Failed to unmute member: {str(e)}")


@router.message(Command("kick"))
async def handle_kick(message: Message, bot: Bot, session: AsyncSession):
    """Remove a member from the group (unbans immediately so they can rejoin)."""
    chat = message.chat
    target_id, reason = resolve_target_user(message)
    if not target_id:
        await message.answer("ℹ️ <b>Usage:</b> Reply with <code>/kick [reason]</code> or <code>/kick USER_ID [reason]</code>")
        return

    await get_or_create_chat(session, chat.id)

    try:
        await bot.ban_chat_member(chat_id=chat.id, user_id=target_id)
        await bot.unban_chat_member(chat_id=chat.id, user_id=target_id)
        await record_moderation_action(
            session=session,
            chat_id=chat.id,
            target_user_id=target_id,
            moderator_user_id=message.from_user.id,
            action_type="kick",
            reason=reason,
        )
        await message.answer(f"👢 User <code>{target_id}</code> was kicked from the chat.\nReason: <i>{html.escape(reason)}</i>")
    except Exception as e:
        await message.answer(f"❌ Failed to kick member: {str(e)}")


@router.message(Command("ban"))
async def handle_ban(message: Message, bot: Bot, session: AsyncSession):
    """Permanently ban a member."""
    chat = message.chat
    target_id, reason = resolve_target_user(message)
    if not target_id:
        await message.answer("ℹ️ <b>Usage:</b> Reply with <code>/ban [reason]</code> or <code>/ban USER_ID [reason]</code>")
        return

    await get_or_create_chat(session, chat.id)

    try:
        await bot.ban_chat_member(chat_id=chat.id, user_id=target_id)
        await record_moderation_action(
            session=session,
            chat_id=chat.id,
            target_user_id=target_id,
            moderator_user_id=message.from_user.id,
            action_type="ban",
            reason=reason,
        )
        await message.answer(f"🔨 <b>USER BANNED</b>\n\nUser <code>{target_id}</code> has been banned from the chat.\nReason: <i>{html.escape(reason)}</i>")
    except Exception as e:
        await message.answer(f"❌ Failed to ban member: {str(e)}")


@router.message(Command("unban"))
async def handle_unban(message: Message, bot: Bot, session: AsyncSession):
    """Unban a member."""
    chat = message.chat
    target_id, _ = resolve_target_user(message)
    if not target_id:
        await message.answer("ℹ️ <b>Usage:</b> <code>/unban USER_ID</code>")
        return

    await get_or_create_chat(session, chat.id)

    try:
        await bot.unban_chat_member(chat_id=chat.id, user_id=target_id)
        await record_moderation_action(
            session=session,
            chat_id=chat.id,
            target_user_id=target_id,
            moderator_user_id=message.from_user.id,
            action_type="unban",
            reason="Unbanned by admin",
        )
        await message.answer(f"✅ User <code>{target_id}</code> has been unbanned.")
    except Exception as e:
        await message.answer(f"❌ Failed to unban member: {str(e)}")


@router.message(Command("purge"))
async def handle_purge(message: Message, bot: Bot, session: AsyncSession):
    """Bulk delete recent messages up to safe limit (1-100)."""
    parts = message.text.split() if message.text else []
    count = 10
    if len(parts) > 1 and parts[1].isdigit():
        count = min(max(int(parts[1]), 1), 100)

    chat_id = message.chat.id
    current_msg_id = message.message_id

    await get_or_create_chat(session, chat_id)

    # Gather message IDs backwards
    deleted_count = 0
    # Include the command message itself
    for msg_id in range(current_msg_id, current_msg_id - count - 1, -1):
        try:
            await bot.delete_message(chat_id=chat_id, message_id=msg_id)
            deleted_count += 1
        except Exception:
            pass

    await record_moderation_action(
        session=session,
        chat_id=chat_id,
        target_user_id=0,
        moderator_user_id=message.from_user.id,
        action_type="purge",
        reason=f"Purged {deleted_count} messages",
    )

    confirm_msg = await bot.send_message(
        chat_id=chat_id,
        text=f"🧹 Purged <b>{deleted_count} messages</b>.",
    )
    # Auto-delete confirmation after 5 seconds
    await asyncio.sleep(5)
    try:
        await confirm_msg.delete()
    except Exception:
        pass


@router.message(Command("lock"))
async def handle_lock(message: Message, bot: Bot, session: AsyncSession):
    """Restrict ordinary members from sending messages."""
    chat = message.chat
    await get_or_create_chat(session, chat.id)

    try:
        await bot.set_chat_permissions(
            chat_id=chat.id,
            permissions=ChatPermissions(can_send_messages=False),
        )
        await update_chat_settings(session, chat.id, is_locked=True)
        await record_moderation_action(
            session=session,
            chat_id=chat.id,
            target_user_id=0,
            moderator_user_id=message.from_user.id,
            action_type="lock",
            reason="Chat locked by moderator",
        )
        await message.answer("🔒 <b>CHAT LOCKED</b>: Sending messages is restricted to administrators.")
    except Exception as e:
        await message.answer(f"❌ Failed to lock chat: {str(e)}")


@router.message(Command("unlock"))
async def handle_unlock(message: Message, bot: Bot, session: AsyncSession):
    """Restore normal messaging permissions."""
    chat = message.chat
    await get_or_create_chat(session, chat.id)

    try:
        await bot.set_chat_permissions(
            chat_id=chat.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_photos=True,
                can_send_videos=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            ),
        )
        await update_chat_settings(session, chat.id, is_locked=False)
        await record_moderation_action(
            session=session,
            chat_id=chat.id,
            target_user_id=0,
            moderator_user_id=message.from_user.id,
            action_type="unlock",
            reason="Chat unlocked by moderator",
        )
        await message.answer("🔓 <b>CHAT UNLOCKED</b>: Normal chatting restored.")
    except Exception as e:
        await message.answer(f"❌ Failed to unlock chat: {str(e)}")


@router.message(Command("setwelcome"))
async def handle_setwelcome(message: Message, session: AsyncSession):
    """Update custom welcome text."""
    parts = message.text.split(maxsplit=1) if message.text else []
    if len(parts) < 2:
        await message.answer(
            "ℹ️ <b>Usage:</b> <code>/setwelcome YOUR_CUSTOM_MESSAGE</code>\n\n"
            "Supported template variables: <code>{name}</code>, <code>{username}</code>, <code>{chat_title}</code>"
        )
        return

    new_welcome = parts[1].strip()
    await update_chat_settings(session, message.chat.id, welcome_text=new_welcome)
    await message.answer("✅ <b>Welcome message updated!</b> Use <code>/previewwelcome</code> to inspect it.")


@router.message(Command("setrules"))
async def handle_setrules(message: Message, session: AsyncSession):
    """Update custom rules text."""
    parts = message.text.split(maxsplit=1) if message.text else []
    if len(parts) < 2:
        await message.answer("ℹ️ <b>Usage:</b> <code>/setrules YOUR_COMMUNITY_RULES</code>")
        return

    new_rules = parts[1].strip()
    await update_chat_settings(session, message.chat.id, rules_text=new_rules)
    await message.answer("✅ <b>Community rules updated!</b> Members can view them with <code>/rules</code>.")


@router.message(Command("antispam"))
async def handle_antispam_toggle(message: Message, session: AsyncSession):
    """Toggle automated anti-spam protection on/off."""
    parts = message.text.split() if message.text else []
    if len(parts) < 2 or parts[1].lower() not in ("on", "off"):
        await message.answer("ℹ️ <b>Usage:</b> <code>/antispam on</code> or <code>/antispam off</code>")
        return

    enable = parts[1].lower() == "on"
    await update_chat_settings(session, message.chat.id, anti_spam_enabled=enable)
    status_str = "🟢 <b>ENABLED</b>" if enable else "🔴 <b>DISABLED</b>"
    await message.answer(f"🛡️ Anti-spam automated protection is now {status_str}.")


@router.message(Command("logs"))
async def handle_logs(message: Message, session: AsyncSession):
    """Display recent moderation logs."""
    actions = await get_recent_moderation_actions(session, chat_id=message.chat.id, limit=10)
    if not actions:
        await message.answer("📋 <i>No recent moderation actions recorded for this chat.</i>")
        return

    reply = "📋 <b>RECENT MODERATION AUDIT LOGS:</b>\n\n"
    for a in actions:
        date_str = a.created_at.strftime("%m-%d %H:%M")
        actor = "🤖 AUTO" if a.is_automated else f"👤 Mod {a.moderator_user_id or 'Admin'}"
        reply += f"• <code>[{date_str}]</code> <b>{a.action_type.upper()}</b> on <code>{a.target_user_id}</code> by {actor}\n"
        if a.reason:
            reply += f"  ↳ <i>{html.escape(a.reason[:60])}</i>\n"

    await message.answer(reply)

"""Database operations and queries for MEMETEK Bot."""

import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy import select, update, delete, func, desc, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from memetek.database.models import (
    Chat,
    User,
    ChatMember,
    ModerationAction,
    Warning,
    AllowedDomain,
    Meme,
    MemeReaction,
    Watchlist,
    PriceAlert,
    ScheduledAnnouncement,
    AuditEvent,
    utc_now,
)
from memetek.config import (
    BRAND_DEFAULT_WELCOME,
    BRAND_DEFAULT_RULES,
)

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Chat CRUD
# -----------------------------------------------------------------------------
async def get_or_create_chat(
    session: AsyncSession,
    chat_id: int,
    title: Optional[str] = None,
    username: Optional[str] = None,
) -> Chat:
    """Get existing chat or create a new one with defaults."""
    stmt = select(Chat).where(Chat.chat_id == chat_id)
    result = await session.execute(stmt)
    chat = result.scalar_one_or_none()

    if not chat:
        chat = Chat(
            chat_id=chat_id,
            title=title,
            username=username,
            welcome_text=BRAND_DEFAULT_WELCOME,
            rules_text=BRAND_DEFAULT_RULES,
            anti_spam_enabled=True,
            welcome_enabled=True,
            welcome_delete_seconds=120,
        )
        session.add(chat)
        await session.commit()
        await session.refresh(chat)
    else:
        # Update title/username if changed
        updated = False
        if title and chat.title != title:
            chat.title = title
            updated = True
        if username and chat.username != username:
            chat.username = username
            updated = True
        if updated:
            await session.commit()

    return chat


async def update_chat_settings(
    session: AsyncSession,
    chat_id: int,
    **kwargs: Any,
) -> Optional[Chat]:
    """Update settings for a specific chat."""
    stmt = select(Chat).where(Chat.chat_id == chat_id)
    result = await session.execute(stmt)
    chat = result.scalar_one_or_none()
    if not chat:
        return None

    for key, value in kwargs.items():
        if hasattr(chat, key):
            setattr(chat, key, value)

    await session.commit()
    await session.refresh(chat)
    return chat


# -----------------------------------------------------------------------------
# User & Member CRUD
# -----------------------------------------------------------------------------
async def get_or_create_user(
    session: AsyncSession,
    user_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    is_bot: bool = False,
) -> User:
    """Get or create user record."""
    stmt = select(User).where(User.user_id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            user_id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            is_bot=is_bot,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    else:
        changed = False
        if username and user.username != username:
            user.username = username
            changed = True
        if first_name and user.first_name != first_name:
            user.first_name = first_name
            changed = True
        if last_name and user.last_name != last_name:
            user.last_name = last_name
            changed = True
        if changed:
            await session.commit()

    return user


async def record_chat_activity(
    session: AsyncSession,
    chat_id: int,
    user_id: int,
) -> None:
    """Record user activity and increment message count."""
    stmt = select(ChatMember).where(
        ChatMember.chat_id == chat_id,
        ChatMember.user_id == user_id,
    )
    result = await session.execute(stmt)
    member = result.scalar_one_or_none()

    now = utc_now()
    if not member:
        member = ChatMember(
            chat_id=chat_id,
            user_id=user_id,
            joined_at=now,
            message_count=1,
            reputation_points=1,
            last_active_at=now,
        )
        session.add(member)
    else:
        member.message_count += 1
        member.last_active_at = now

    await session.commit()


# -----------------------------------------------------------------------------
# Warnings & Moderation CRUD
# -----------------------------------------------------------------------------
async def add_warning(
    session: AsyncSession,
    chat_id: int,
    user_id: int,
    reason: str,
    moderator_user_id: Optional[int] = None,
) -> int:
    """Add a warning to a user and return total active warnings."""
    warning = Warning(
        chat_id=chat_id,
        user_id=user_id,
        moderator_user_id=moderator_user_id,
        reason=reason,
        is_active=True,
    )
    session.add(warning)
    await session.commit()

    # Count active warnings
    count_stmt = select(func.count(Warning.id)).where(
        Warning.chat_id == chat_id,
        Warning.user_id == user_id,
        Warning.is_active == True,
    )
    res = await session.execute(count_stmt)
    return res.scalar_one() or 0


async def get_active_warnings(
    session: AsyncSession,
    chat_id: int,
    user_id: int,
) -> List[Warning]:
    """Retrieve all active warnings for a user in a chat."""
    stmt = (
        select(Warning)
        .where(
            Warning.chat_id == chat_id,
            Warning.user_id == user_id,
            Warning.is_active == True,
        )
        .order_by(desc(Warning.created_at))
    )
    res = await session.execute(stmt)
    return list(res.scalars().all())


async def clear_warnings(
    session: AsyncSession,
    chat_id: int,
    user_id: int,
) -> int:
    """Mark all active warnings as inactive for a user in a chat."""
    stmt = (
        update(Warning)
        .where(
            Warning.chat_id == chat_id,
            Warning.user_id == user_id,
            Warning.is_active == True,
        )
        .values(is_active=False)
    )
    res = await session.execute(stmt)
    await session.commit()
    return res.rowcount or 0


async def record_moderation_action(
    session: AsyncSession,
    chat_id: int,
    target_user_id: int,
    action_type: str,
    reason: Optional[str] = None,
    moderator_user_id: Optional[int] = None,
    duration_seconds: Optional[int] = None,
    is_automated: bool = False,
) -> ModerationAction:
    """Log a moderation action to the audit trail."""
    action = ModerationAction(
        chat_id=chat_id,
        target_user_id=target_user_id,
        moderator_user_id=moderator_user_id,
        action_type=action_type,
        reason=reason,
        duration_seconds=duration_seconds,
        is_automated=is_automated,
    )
    session.add(action)
    await session.commit()
    await session.refresh(action)
    return action


async def get_recent_moderation_actions(
    session: AsyncSession,
    chat_id: Optional[int] = None,
    limit: int = 50,
) -> List[ModerationAction]:
    """Retrieve recent moderation actions."""
    stmt = select(ModerationAction)
    if chat_id is not None:
        stmt = stmt.where(ModerationAction.chat_id == chat_id)
    stmt = stmt.order_by(desc(ModerationAction.created_at)).limit(limit)
    res = await session.execute(stmt)
    return list(res.scalars().all())


# -----------------------------------------------------------------------------
# Domain Allowlist CRUD
# -----------------------------------------------------------------------------
async def get_allowed_domains(
    session: AsyncSession,
    chat_id: Optional[int] = None,
) -> List[str]:
    """Return combined global and chat-specific allowed domains."""
    conditions = [AllowedDomain.chat_id == None]
    if chat_id is not None:
        conditions.append(AllowedDomain.chat_id == chat_id)

    stmt = select(AllowedDomain.domain).where(or_(*conditions))
    res = await session.execute(stmt)
    return [d.lower() for d in res.scalars().all()]


async def add_allowed_domain(
    session: AsyncSession,
    domain: str,
    chat_id: Optional[int] = None,
    added_by_user_id: Optional[int] = None,
) -> bool:
    """Add a domain to the allowlist."""
    clean_domain = domain.strip().lower()
    stmt = select(AllowedDomain).where(
        AllowedDomain.chat_id == chat_id,
        AllowedDomain.domain == clean_domain,
    )
    res = await session.execute(stmt)
    if res.scalar_one_or_none():
        return False

    session.add(
        AllowedDomain(
            chat_id=chat_id,
            domain=clean_domain,
            added_by_user_id=added_by_user_id,
        )
    )
    await session.commit()
    return True


async def remove_allowed_domain(
    session: AsyncSession,
    domain: str,
    chat_id: Optional[int] = None,
) -> bool:
    """Remove a domain from the allowlist."""
    clean_domain = domain.strip().lower()
    stmt = delete(AllowedDomain).where(
        AllowedDomain.chat_id == chat_id,
        AllowedDomain.domain == clean_domain,
    )
    res = await session.execute(stmt)
    await session.commit()
    return (res.rowcount or 0) > 0


# -----------------------------------------------------------------------------
# Meme System CRUD
# -----------------------------------------------------------------------------
async def create_meme(
    session: AsyncSession,
    caption: str,
    media_type: str = "text",
    media_url: Optional[str] = None,
    file_id: Optional[str] = None,
    submitter_user_id: Optional[int] = None,
    chat_id: Optional[int] = None,
    status: str = "approved",
) -> Meme:
    """Create a new meme record."""
    meme = Meme(
        chat_id=chat_id,
        submitter_user_id=submitter_user_id,
        media_type=media_type,
        media_url=media_url,
        file_id=file_id,
        caption=caption,
        status=status,
    )
    session.add(meme)
    await session.commit()
    await session.refresh(meme)
    return meme


async def get_random_approved_meme(session: AsyncSession) -> Optional[Meme]:
    """Retrieve a random approved meme."""
    stmt = (
        select(Meme)
        .where(Meme.status == "approved")
        .order_by(func.random())
        .limit(1)
    )
    res = await session.execute(stmt)
    return res.scalar_one_or_none()


async def get_memes(
    session: AsyncSession,
    status: Optional[str] = None,
    limit: int = 50,
) -> List[Meme]:
    """Retrieve memes by status."""
    stmt = select(Meme)
    if status:
        stmt = stmt.where(Meme.status == status)
    stmt = stmt.order_by(desc(Meme.created_at)).limit(limit)
    res = await session.execute(stmt)
    return list(res.scalars().all())


async def review_meme(
    session: AsyncSession,
    meme_id: int,
    approve: bool,
) -> Optional[Meme]:
    """Approve or reject a submitted meme."""
    stmt = select(Meme).where(Meme.id == meme_id)
    res = await session.execute(stmt)
    meme = res.scalar_one_or_none()
    if not meme:
        return None

    meme.status = "approved" if approve else "rejected"
    await session.commit()
    await session.refresh(meme)
    return meme


async def add_meme_reaction(
    session: AsyncSession,
    meme_id: int,
    user_id: int,
    reaction_type: str,
) -> Tuple[bool, int]:
    """Add or update reaction to a meme. Returns (is_new, total_upvotes)."""
    stmt = select(MemeReaction).where(
        MemeReaction.meme_id == meme_id,
        MemeReaction.user_id == user_id,
    )
    res = await session.execute(stmt)
    reaction = res.scalar_one_or_none()

    meme_stmt = select(Meme).where(Meme.id == meme_id)
    m_res = await session.execute(meme_stmt)
    meme = m_res.scalar_one_or_none()
    if not meme:
        return False, 0

    is_new = False
    if not reaction:
        reaction = MemeReaction(
            meme_id=meme_id,
            user_id=user_id,
            reaction_type=reaction_type,
        )
        session.add(reaction)
        meme.upvotes += 1
        is_new = True
    else:
        reaction.reaction_type = reaction_type

    await session.commit()
    await session.refresh(meme)
    return is_new, meme.upvotes


async def get_top_memes(session: AsyncSession, limit: int = 10) -> List[Meme]:
    """Get highest upvoted memes."""
    stmt = (
        select(Meme)
        .where(Meme.status == "approved")
        .order_by(desc(Meme.upvotes), desc(Meme.created_at))
        .limit(limit)
    )
    res = await session.execute(stmt)
    return list(res.scalars().all())


# -----------------------------------------------------------------------------
# Watchlist CRUD
# -----------------------------------------------------------------------------
async def get_user_watchlist(session: AsyncSession, user_id: int) -> List[str]:
    """Get all token symbols watched by a user."""
    stmt = select(Watchlist.symbol).where(Watchlist.user_id == user_id)
    res = await session.execute(stmt)
    return list(res.scalars().all())


async def add_to_watchlist(session: AsyncSession, user_id: int, symbol: str) -> bool:
    """Add a token symbol to a user's watchlist."""
    clean_sym = symbol.strip().upper()
    stmt = select(Watchlist).where(
        Watchlist.user_id == user_id,
        Watchlist.symbol == clean_sym,
    )
    res = await session.execute(stmt)
    if res.scalar_one_or_none():
        return False

    session.add(Watchlist(user_id=user_id, symbol=clean_sym))
    await session.commit()
    return True


async def remove_from_watchlist(session: AsyncSession, user_id: int, symbol: str) -> bool:
    """Remove a token symbol from user's watchlist."""
    clean_sym = symbol.strip().upper()
    stmt = delete(Watchlist).where(
        Watchlist.user_id == user_id,
        Watchlist.symbol == clean_sym,
    )
    res = await session.execute(stmt)
    await session.commit()
    return (res.rowcount or 0) > 0


# -----------------------------------------------------------------------------
# Statistics & Audit CRUD
# -----------------------------------------------------------------------------
async def get_community_stats(
    session: AsyncSession,
    chat_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Aggregate statistics for dashboard and /stats."""
    # Member count
    m_stmt = select(func.count(ChatMember.id))
    if chat_id is not None:
        m_stmt = m_stmt.where(ChatMember.chat_id == chat_id)
    members_count = (await session.execute(m_stmt)).scalar_one() or 0

    # Total messages tracked
    msg_stmt = select(func.sum(ChatMember.message_count))
    if chat_id is not None:
        msg_stmt = msg_stmt.where(ChatMember.chat_id == chat_id)
    total_messages = (await session.execute(msg_stmt)).scalar_one() or 0

    # Moderation actions count
    mod_stmt = select(func.count(ModerationAction.id))
    if chat_id is not None:
        mod_stmt = mod_stmt.where(ModerationAction.chat_id == chat_id)
    mod_count = (await session.execute(mod_stmt)).scalar_one() or 0

    # Memes approved
    meme_stmt = select(func.count(Meme.id)).where(Meme.status == "approved")
    approved_memes = (await session.execute(meme_stmt)).scalar_one() or 0

    # Active warnings
    warn_stmt = select(func.count(Warning.id)).where(Warning.is_active == True)
    if chat_id is not None:
        warn_stmt = warn_stmt.where(Warning.chat_id == chat_id)
    active_warnings = (await session.execute(warn_stmt)).scalar_one() or 0

    return {
        "tracked_members": members_count,
        "total_messages": int(total_messages),
        "moderation_actions": mod_count,
        "approved_memes": approved_memes,
        "active_warnings": active_warnings,
    }


async def record_audit_event(
    session: AsyncSession,
    admin_user_id: str,
    action: str,
    details: str,
    ip_address: Optional[str] = None,
) -> AuditEvent:
    """Record an audit trail event for administrative operations."""
    event = AuditEvent(
        admin_user_id=str(admin_user_id),
        action=action,
        details=details,
        ip_address=ip_address,
    )
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return event


async def get_audit_events(
    session: AsyncSession,
    limit: int = 50,
) -> List[AuditEvent]:
    """Retrieve recent audit events."""
    stmt = select(AuditEvent).order_by(desc(AuditEvent.created_at)).limit(limit)
    res = await session.execute(stmt)
    return list(res.scalars().all())


# -----------------------------------------------------------------------------
# Seeding initial data
# -----------------------------------------------------------------------------
async def seed_initial_data_if_empty(session: AsyncSession) -> None:
    """Seed initial approved MEMETEK memes and default trusted domains."""
    # Check if memes exist
    res = await session.execute(select(func.count(Meme.id)))
    count = res.scalar_one() or 0
    if count == 0:
        seed_memes = [
            ("When you buy the top of a meme coin but you're in it for the tech. 💀🚀", "text"),
            ("Ser, we don't do red candles here. Only moon missions and unhinged vibes. 🌕🐸", "text"),
            ("Me explaining to my family why MEMETEK is a sophisticated hedge against fiat: 🧠📈", "text"),
            ("Rule #1 of crypto: Never fade the memes. Rule #2: WAGMI. 🫡🪙", "text"),
            ("Bull market: Degen. Bear market: Degen. Crab market: Extreme degen. 🦀🔥", "text"),
            ("They said 'take profits'. I said 'MEMETEK to the moon'. 🚀💛", "text"),
            ("Just a humble meme coin enthusiast turning caffeine into blockchain alpha. ☕✨", "text"),
            ("Sleep is temporary. The MEMETEK community is forever. GM kings! 👑☀️", "text"),
        ]
        for caption, mtype in seed_memes:
            session.add(Meme(caption=caption, media_type=mtype, status="approved", upvotes=5))

    # Check trusted domains
    dom_res = await session.execute(select(func.count(AllowedDomain.id)))
    dom_count = dom_res.scalar_one() or 0
    if dom_count == 0:
        default_domains = [
            "t.me",
            "telegram.org",
            "coingecko.com",
            "coinmarketcap.com",
            "dexscreener.com",
            "dextools.io",
            "etherscan.io",
            "solscan.io",
            "x.com",
            "twitter.com",
            "github.com",
        ]
        for dom in default_domains:
            session.add(AllowedDomain(domain=dom, chat_id=None))

    await session.commit()

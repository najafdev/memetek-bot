"""Tests for Database Operations and CRUD functions."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from memetek.database.crud import (
    get_or_create_chat,
    update_chat_settings,
    get_or_create_user,
    record_chat_activity,
    add_warning,
    get_active_warnings,
    clear_warnings,
    record_moderation_action,
    get_recent_moderation_actions,
    create_meme,
    review_meme,
    add_meme_reaction,
    get_top_memes,
    add_to_watchlist,
    get_user_watchlist,
    remove_from_watchlist,
    add_allowed_domain,
    get_allowed_domains,
    remove_allowed_domain,
    record_audit_event,
    get_audit_events,
    get_community_stats,
    seed_initial_data_if_empty,
)


@pytest.mark.asyncio
async def test_chat_lifecycle(db_session: AsyncSession):
    """Test chat registration and settings updates."""
    chat_id = -100123456789
    chat = await get_or_create_chat(db_session, chat_id=chat_id, title="Test Group")

    assert chat.chat_id == chat_id
    assert chat.title == "Test Group"
    assert chat.anti_spam_enabled is True
    assert chat.welcome_enabled is True

    # Update settings
    updated = await update_chat_settings(
        db_session,
        chat_id=chat_id,
        anti_spam_enabled=False,
        official_contract_address="0x1234567890abcdef",
    )
    assert updated.anti_spam_enabled is False
    assert updated.official_contract_address == "0x1234567890abcdef"


@pytest.mark.asyncio
async def test_user_and_activity_tracking(db_session: AsyncSession):
    """Test user registration and activity incrementing."""
    user_id = 998877
    user = await get_or_create_user(
        db_session,
        user_id=user_id,
        username="cryptodegen",
        first_name="Crypto",
    )
    assert user.user_id == user_id
    assert user.username == "cryptodegen"

    # Activity tracking
    chat_id = -100555
    await get_or_create_chat(db_session, chat_id=chat_id)
    await record_chat_activity(db_session, chat_id=chat_id, user_id=user_id)
    await record_chat_activity(db_session, chat_id=chat_id, user_id=user_id)

    stats = await get_community_stats(db_session, chat_id=chat_id)
    assert stats["tracked_members"] == 1
    assert stats["total_messages"] == 2


@pytest.mark.asyncio
async def test_warnings_and_clearing(db_session: AsyncSession):
    """Test warning counter and clearance."""
    chat_id = -100111
    user_id = 44444
    await get_or_create_chat(db_session, chat_id=chat_id)

    count1 = await add_warning(db_session, chat_id, user_id, "Rule violation 1", 999)
    assert count1 == 1

    count2 = await add_warning(db_session, chat_id, user_id, "Rule violation 2", 999)
    assert count2 == 2

    active = await get_active_warnings(db_session, chat_id, user_id)
    assert len(active) == 2

    cleared = await clear_warnings(db_session, chat_id, user_id)
    assert cleared == 2

    active_after = await get_active_warnings(db_session, chat_id, user_id)
    assert len(active_after) == 0


@pytest.mark.asyncio
async def test_moderation_actions_logging(db_session: AsyncSession):
    """Test logging and retrieval of moderation actions."""
    chat_id = -100222
    await get_or_create_chat(db_session, chat_id=chat_id)

    action = await record_moderation_action(
        db_session,
        chat_id=chat_id,
        target_user_id=55555,
        moderator_user_id=999,
        action_type="mute",
        reason="Flood spam",
        duration_seconds=1800,
        is_automated=False,
    )
    assert action.id is not None
    assert action.action_type == "mute"

    recent = await get_recent_moderation_actions(db_session, chat_id=chat_id)
    assert len(recent) == 1
    assert recent[0].action_type == "mute"


@pytest.mark.asyncio
async def test_meme_workflow(db_session: AsyncSession):
    """Test submitting, reviewing, reacting, and ranking memes."""
    meme = await create_meme(
        db_session,
        caption="When the green candle hits just right 🚀",
        submitter_user_id=123,
        status="pending",
    )
    assert meme.status == "pending"

    # Approve meme
    approved = await review_meme(db_session, meme.id, approve=True)
    assert approved.status == "approved"

    # Reactions
    is_new, upvotes = await add_meme_reaction(db_session, meme.id, user_id=101, reaction_type="fire")
    assert is_new is True
    assert upvotes == 1

    # Same user changing reaction doesn't increment score twice
    is_new2, upvotes2 = await add_meme_reaction(db_session, meme.id, user_id=101, reaction_type="moon")
    assert is_new2 is False
    assert upvotes2 == 1

    top = await get_top_memes(db_session)
    assert len(top) >= 1
    assert top[0].id == meme.id


@pytest.mark.asyncio
async def test_watchlist_management(db_session: AsyncSession):
    """Test adding and removing tokens from personal watchlist."""
    user_id = 88888
    await get_or_create_user(db_session, user_id=user_id)

    # Add symbols
    assert await add_to_watchlist(db_session, user_id, "SOL") is True
    assert await add_to_watchlist(db_session, user_id, "BTC") is True
    # Duplicate add
    assert await add_to_watchlist(db_session, user_id, "SOL") is False

    wl = await get_user_watchlist(db_session, user_id)
    assert "SOL" in wl
    assert "BTC" in wl

    # Remove symbol
    assert await remove_from_watchlist(db_session, user_id, "SOL") is True
    wl_after = await get_user_watchlist(db_session, user_id)
    assert "SOL" not in wl_after
    assert "BTC" in wl_after


@pytest.mark.asyncio
async def test_domain_allowlist(db_session: AsyncSession):
    """Test domain allowlist management."""
    assert await add_allowed_domain(db_session, "custommoon.io") is True
    assert await add_allowed_domain(db_session, "custommoon.io") is False

    domains = await get_allowed_domains(db_session)
    assert "custommoon.io" in domains

    assert await remove_allowed_domain(db_session, "custommoon.io") is True
    domains_after = await get_allowed_domains(db_session)
    assert "custommoon.io" not in domains_after


@pytest.mark.asyncio
async def test_audit_event_logging(db_session: AsyncSession):
    """Test admin audit trail."""
    await record_audit_event(
        db_session,
        admin_user_id="admin_chad",
        action="update_settings",
        details="Changed anti-spam parameters",
        ip_address="192.168.1.1",
    )
    events = await get_audit_events(db_session)
    assert len(events) >= 1
    assert events[0].action == "update_settings"
    assert events[0].admin_user_id == "admin_chad"

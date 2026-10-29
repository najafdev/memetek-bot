"""SQLAlchemy 2.0 ORM models for MEMETEK community bot."""

from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class Chat(Base):
    """Telegram Chat configuration and status."""
    __tablename__ = "chats"

    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Community Features
    anti_spam_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    welcome_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    welcome_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    welcome_media_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    welcome_delete_seconds: Mapped[int] = mapped_column(Integer, default=120, nullable=False)
    rules_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Token & CA configuration
    official_contract_address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    # Relationships
    members: Mapped[List["ChatMember"]] = relationship(
        "ChatMember", back_populates="chat", cascade="all, delete-orphan"
    )
    moderation_actions: Mapped[List["ModerationAction"]] = relationship(
        "ModerationAction", back_populates="chat", cascade="all, delete-orphan"
    )
    warnings: Mapped[List["Warning"]] = relationship(
        "Warning", back_populates="chat", cascade="all, delete-orphan"
    )


class User(Base):
    """Telegram User profile and privacy preferences."""
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_bot: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    opt_out_tracking: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    # Relationships
    memberships: Mapped[List["ChatMember"]] = relationship(
        "ChatMember", back_populates="user", cascade="all, delete-orphan"
    )
    watchlists: Mapped[List["Watchlist"]] = relationship(
        "Watchlist", back_populates="user", cascade="all, delete-orphan"
    )


class ChatMember(Base):
    """Membership mapping with activity and reputation."""
    __tablename__ = "chat_members"
    __table_args__ = (
        UniqueConstraint("chat_id", "user_id", name="uq_chat_user"),
        Index("ix_chat_members_chat_user", "chat_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("chats.chat_id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)

    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reputation_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_active_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    chat: Mapped["Chat"] = relationship("Chat", back_populates="members")
    user: Mapped["User"] = relationship("User", back_populates="memberships")


class ModerationAction(Base):
    """Audit log of moderation actions taken (automated or manual)."""
    __tablename__ = "moderation_actions"
    __table_args__ = (
        Index("ix_mod_actions_chat_target", "chat_id", "target_user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("chats.chat_id", ondelete="CASCADE"), nullable=False)
    target_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    moderator_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)  # warn, mute, unmute, kick, ban, unban, purge, spam_block, lock, unlock
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_automated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)

    chat: Mapped["Chat"] = relationship("Chat", back_populates="moderation_actions")


class Warning(Base):
    """User warning tracking for threshold escalation."""
    __tablename__ = "warnings"
    __table_args__ = (
        Index("ix_warnings_chat_user", "chat_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("chats.chat_id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    moderator_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    chat: Mapped["Chat"] = relationship("Chat", back_populates="warnings")


class AllowedDomain(Base):
    """Domain allowlist for safe community links."""
    __tablename__ = "allowed_domains"
    __table_args__ = (
        UniqueConstraint("chat_id", "domain", name="uq_chat_domain"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)  # Null = Global
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    added_by_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Meme(Base):
    """Curated and community-submitted memes."""
    __tablename__ = "memes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    submitter_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    media_type: Mapped[str] = mapped_column(String(20), default="text")  # text, photo, animation, video
    media_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    caption: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="approved", index=True)  # approved, pending, rejected
    upvotes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    reactions: Mapped[List["MemeReaction"]] = relationship(
        "MemeReaction", back_populates="meme", cascade="all, delete-orphan"
    )


class MemeReaction(Base):
    """User reactions to memes."""
    __tablename__ = "meme_reactions"
    __table_args__ = (
        UniqueConstraint("meme_id", "user_id", name="uq_meme_user_reaction"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    meme_id: Mapped[int] = mapped_column(Integer, ForeignKey("memes.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reaction_type: Mapped[str] = mapped_column(String(20), nullable=False)  # fire, moon, dead, based
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    meme: Mapped["Meme"] = relationship("Meme", back_populates="reactions")


class Watchlist(Base):
    """User crypto asset watchlist."""
    __tablename__ = "watchlists"
    __table_args__ = (
        UniqueConstraint("user_id", "symbol", name="uq_user_symbol"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    user: Mapped["User"] = relationship("User", back_populates="watchlists")


class PriceAlert(Base):
    """Opt-in user price alerts."""
    __tablename__ = "price_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    chat_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    target_price: Mapped[float] = mapped_column(Float, nullable=False)
    condition: Mapped[str] = mapped_column(String(10), nullable=False)  # above, below
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    triggered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ScheduledAnnouncement(Base):
    """Scheduled community prompts and announcements."""
    __tablename__ = "scheduled_announcements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    cron_expression: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    next_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AuditEvent(Base):
    """Admin dashboard and security audit event log."""
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admin_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[str] = mapped_column(Text, nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

"""Initial schema migration

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-10-29 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. chats
    op.create_table(
        'chats',
        sa.Column('chat_id', sa.BigInteger(), primary_key=True, nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('username', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('anti_spam_enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('welcome_enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('welcome_text', sa.Text(), nullable=True),
        sa.Column('welcome_media_url', sa.String(length=1024), nullable=True),
        sa.Column('welcome_delete_seconds', sa.Integer(), nullable=False, server_default='120'),
        sa.Column('rules_text', sa.Text(), nullable=True),
        sa.Column('official_contract_address', sa.String(length=255), nullable=True),
        sa.Column('is_locked', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 2. users
    op.create_table(
        'users',
        sa.Column('user_id', sa.BigInteger(), primary_key=True, nullable=False),
        sa.Column('username', sa.String(length=255), nullable=True),
        sa.Column('first_name', sa.String(length=255), nullable=True),
        sa.Column('last_name', sa.String(length=255), nullable=True),
        sa.Column('is_bot', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('opt_out_tracking', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_users_username', 'users', ['username'])

    # 3. chat_members
    op.create_table(
        'chat_members',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('chat_id', sa.BigInteger(), sa.ForeignKey('chats.chat_id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False),
        sa.Column('joined_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('message_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('reputation_points', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_active_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('chat_id', 'user_id', name='uq_chat_user'),
    )
    op.create_index('ix_chat_members_chat_user', 'chat_members', ['chat_id', 'user_id'])

    # 4. moderation_actions
    op.create_table(
        'moderation_actions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('chat_id', sa.BigInteger(), sa.ForeignKey('chats.chat_id', ondelete='CASCADE'), nullable=False),
        sa.Column('target_user_id', sa.BigInteger(), nullable=False),
        sa.Column('moderator_user_id', sa.BigInteger(), nullable=True),
        sa.Column('action_type', sa.String(length=50), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('is_automated', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_mod_actions_chat_target', 'moderation_actions', ['chat_id', 'target_user_id'])
    op.create_index('ix_moderation_actions_created_at', 'moderation_actions', ['created_at'])

    # 5. warnings
    op.create_table(
        'warnings',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('chat_id', sa.BigInteger(), sa.ForeignKey('chats.chat_id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('moderator_user_id', sa.BigInteger(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_warnings_chat_user', 'warnings', ['chat_id', 'user_id'])

    # 6. allowed_domains
    op.create_table(
        'allowed_domains',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('chat_id', sa.BigInteger(), nullable=True),
        sa.Column('domain', sa.String(length=255), nullable=False),
        sa.Column('added_by_user_id', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('chat_id', 'domain', name='uq_chat_domain'),
    )

    # 7. memes
    op.create_table(
        'memes',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('chat_id', sa.BigInteger(), nullable=True),
        sa.Column('submitter_user_id', sa.BigInteger(), nullable=True),
        sa.Column('media_type', sa.String(length=20), nullable=False, server_default='text'),
        sa.Column('media_url', sa.String(length=1024), nullable=True),
        sa.Column('file_id', sa.String(length=255), nullable=True),
        sa.Column('caption', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='approved'),
        sa.Column('upvotes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_memes_status', 'memes', ['status'])

    # 8. meme_reactions
    op.create_table(
        'meme_reactions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('meme_id', sa.Integer(), sa.ForeignKey('memes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('reaction_type', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('meme_id', 'user_id', name='uq_meme_user_reaction'),
    )

    # 9. watchlists
    op.create_table(
        'watchlists',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('user_id', 'symbol', name='uq_user_symbol'),
    )

    # 10. price_alerts
    op.create_table(
        'price_alerts',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('chat_id', sa.BigInteger(), nullable=True),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('target_price', sa.Float(), nullable=False),
        sa.Column('condition', sa.String(length=10), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('triggered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 11. scheduled_announcements
    op.create_table(
        'scheduled_announcements',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('chat_id', sa.BigInteger(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message_text', sa.Text(), nullable=False),
        sa.Column('cron_expression', sa.String(length=50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('next_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 12. audit_events
    op.create_table(
        'audit_events',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('admin_user_id', sa.String(length=255), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('details', sa.Text(), nullable=False),
        sa.Column('ip_address', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('audit_events')
    op.drop_table('scheduled_announcements')
    op.drop_table('price_alerts')
    op.drop_table('watchlists')
    op.drop_table('meme_reactions')
    op.drop_table('memes')
    op.drop_table('allowed_domains')
    op.drop_table('warnings')
    op.drop_table('moderation_actions')
    op.drop_table('chat_members')
    op.drop_table('users')
    op.drop_table('chats')

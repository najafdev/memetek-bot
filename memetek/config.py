"""Configuration settings for MEMETEK Telegram Bot."""

import logging
from typing import List, Set
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 1. Telegram
    TELEGRAM_BOT_TOKEN: str = Field(
        default="123456789:AAFakeTokenForLocalTestingOnlyXYZ12345",
        description="Telegram bot token obtained from @BotFather",
    )
    USE_WEBHOOK: bool = False
    WEBHOOK_URL: str = ""
    WEBHOOK_SECRET: str = "memetek_webhook_secret_key"

    # 2. Database & Cache
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./memetek.db",
        description="Async database connection string (PostgreSQL asyncpg or SQLite aiosqlite)",
    )
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for caching and rate limiting",
    )

    # 3. Access Control
    ADMIN_USER_IDS: str = Field(
        default="",
        description="Comma-separated Telegram user IDs of super administrators",
    )
    ALLOWED_CHAT_IDS: str = Field(
        default="",
        description="Comma-separated Telegram chat IDs allowed to use the bot",
    )

    # 4. Web Dashboard
    DASHBOARD_ENABLED: bool = True
    DASHBOARD_HOST: str = "0.0.0.0"
    DASHBOARD_PORT: int = 8080
    DASHBOARD_USERNAME: str = "admin"
    DASHBOARD_PASSWORD: str = "AdminDegenPassword2026!"
    DASHBOARD_SECRET_KEY: str = "memetek_super_secret_jwt_key_degens_moon_2026_salt"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        """Normalize database connection string for Railway, Render, Supabase, and Heroku."""
        import os
        if not v:
            v = os.getenv("POSTGRES_URL") or os.getenv("DATABASE_PUBLIC_URL") or "sqlite+aiosqlite:///./memetek.db"
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        if v.startswith("postgresql://") and "+asyncpg" not in v:
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        if v.startswith("sqlite://") and "+aiosqlite" not in v:
            return v.replace("sqlite://", "sqlite+aiosqlite://", 1)
        return v

    @field_validator("DASHBOARD_PORT", mode="before")
    @classmethod
    def detect_railway_port(cls, v):
        """Use Railway-assigned $PORT if present."""
        import os
        port_env = os.getenv("PORT")
        if port_env and str(port_env).isdigit():
            return int(port_env)
        return v

    @field_validator("REDIS_URL", mode="before")
    @classmethod
    def detect_railway_redis(cls, v: str) -> str:
        """Use Railway-injected REDIS_PRIVATE_URL or REDIS_URL if present."""
        import os
        return os.getenv("REDIS_PRIVATE_URL") or os.getenv("REDIS_URL") or v

    # 5. External APIs / Market
    COINGECKO_API_KEY: str = ""
    SUPPORTED_SYMBOLS: str = "BTC,ETH,SOL,DOGE,PEPE,SHIB,BONK,WIF,FLOKI"
    MARKET_CACHE_TTL_SECONDS: int = 60

    # 6. Community & Anti-Spam
    DEFAULT_WELCOME_AUTO_DELETE_SECONDS: int = 120
    FLOOD_MAX_MESSAGES: int = 5
    FLOOD_WINDOW_SECONDS: int = 5
    MAX_WARNINGS_BEFORE_MUTE: int = 3
    MUTE_DURATION_MINUTES: int = 120

    # 7. Runtime
    LOG_LEVEL: str = "INFO"
    TIMEZONE: str = "UTC"
    APP_ENV: str = "production"
    TEST_MODE: bool = False

    @property
    def admin_id_set(self) -> Set[int]:
        """Parsed set of admin user IDs."""
        if not self.ADMIN_USER_IDS.strip():
            return set()
        ids = set()
        for item in self.ADMIN_USER_IDS.split(","):
            item = item.strip()
            if item.isdigit() or (item.startswith("-") and item[1:].isdigit()):
                ids.add(int(item))
        return ids

    @property
    def allowed_chat_id_set(self) -> Set[int]:
        """Parsed set of allowed chat IDs."""
        if not self.ALLOWED_CHAT_IDS.strip():
            return set()
        ids = set()
        for item in self.ALLOWED_CHAT_IDS.split(","):
            item = item.strip()
            if item.isdigit() or (item.startswith("-") and item[1:].isdigit()):
                ids.add(int(item))
        return ids

    @property
    def supported_symbols_list(self) -> List[str]:
        """Parsed list of supported crypto symbols uppercase."""
        return [s.strip().upper() for s in self.SUPPORTED_SYMBOLS.split(",") if s.strip()]


# Brand Constants
BRAND_NAME = "MEMETEK"
BRAND_TAGLINE = "Where Memes Meet the Moon 🚀"
BRAND_OFFICIAL_DESCRIPTION = """🐱🪙 <b>Welcome to MEMETEK — Where Memes Meet the Moon 🚀</b>

Not just a meme coin community, bro… it's a whole vibe. 💀🔥

💎 <b>Built on memes, powered by the community</b>
🐸 <b>Unhinged memes & degen energy</b>
🚀 <b>Big dreams, moon missions</b>
🫂 <b>No gatekeeping, just vibes</b>
👑 <b>We meme different. We move different.</b>

Less talking. More memeing. WAGMI. 🫡

⚡ <i>Stay based. Stay bullish. Stay MEMETEK.</i>

DYOR • NFA • Never fade the memes. 🖤💛"""

BRAND_DEFAULT_WELCOME = """🐱 <b>YO, WELCOME TO MEMETEK, {name}!</b> 🪙

Where memes meet the moon. 🚀

💎 Bring the memes.
🐸 Bring the degen energy.
🫂 Respect the community.
🛡️ Watch out for fake admins and scam links.

📌 Read the group rules (/rules) and check pinned messages.

<i>Less talking. More memeing. WAGMI!</i> 🔥"""

BRAND_DEFAULT_RULES = """📜 <b>MEMETEK COMMUNITY RULES</b> 📜

1. <b>Respect the Fam</b>: No harassment, hate speech, or toxic abuse. Keep it degen, keep it friendly.
2. <b>No Phishing or Malicious Links</b>: Zero tolerance for scam links, fake mints, draining sites, or sketchy files.
3. <b>No Impersonation</b>: Admins will NEVER DM you first offering technical support or asking for private keys.
4. <b>No Unsolicited Shilling / Referral Spam</b>: Share memes and tech discussions, not random coin spam or telegram invite links.
5. <b>DYOR & NFA</b>: Everything shared here is for entertainment and culture. Not financial advice.
6. <b>Meme Hard or Go Home</b>: High-tier memes get respect. Spam gets the hammer.

<i>Break the rules and face the MEMETEK banhammer! 🔨</i>"""

settings = Settings()


def setup_logging():
    """Configure structured logging based on settings."""
    numeric_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

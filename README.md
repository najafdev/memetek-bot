# MEMETEK — Telegram Community & Engagement Bot

<p align="center">
  <img src="https://img.shields.io/badge/MEMETEK-Where%20Memes%20Meet%20The%20Moon%20%F0%9F%9A%80-F3BA2F?style=for-the-badge" alt="MEMETEK Banner">
  <br>
  <img src="https://img.shields.io/badge/Python-3.12+-blue.svg" alt="Python 3.12+">
  <img src="https://img.shields.io/badge/aiogram-3.x-2CA5E0.svg" alt="aiogram 3.x">
  <img src="https://img.shields.io/badge/FastAPI-0.115+-009688.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/SQLAlchemy-2.0-red.svg" alt="SQLAlchemy 2.0">
  <img src="https://img.shields.io/badge/Redis-7-DC382D.svg" alt="Redis">
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED.svg" alt="Docker">
  <img src="https://img.shields.io/badge/Tests-51%20Passed-00FF66.svg" alt="Tests">
</p>

---

## 🐱 Brand Identity & Lore

- **Name:** MEMETEK
- **Tagline:** *Where Memes Meet the Moon 🚀*
- **Personality:** Funny, degen, chaotic, bullish, welcoming, community-first
- **Visual Identity:** Obsidian black (`#0B0E14`), Yellow/Gold (`#F3BA2F`), Neon Green (`#00FF66`), Cyan (`#00F0FF`)
- **Tone:** Internet-native, meme culture, crypto slang, friendly but not spammy

> 🐱🪙 **Welcome to MEMETEK — Where Memes Meet the Moon 🚀**  
> *Not just a meme coin community, bro… it's a whole vibe. 💀🔥*  
>   
> 💎 Built on memes, powered by the community  
> 🐸 Unhinged memes & degen energy  
> 🚀 Big dreams, moon missions  
> 🫂 No gatekeeping, just vibes  
> 👑 We meme different. We move different.  
>   
> Less talking. More memeing. WAGMI. 🫡  
> ⚡ Stay based. Stay bullish. Stay MEMETEK.  
> DYOR • NFA • Never fade the memes. 🖤💛  

---

## 🚀 Core Features

### 1. Branded Welcome System
- Welcomes new members automatically with personalized safe mentions (`user.mention_html()`).
- Supports dynamic placeholders: `{name}`, `{username}`, `{chat_title}`.
- Configurable welcome message auto-deletion timer to keep group chat clean.
- In-chat preview command (`/previewwelcome`) and web editor.

### 2. High-Grade Anti-Spam & Phishing Shield
- **Flood Control:** Rate limits rapid-fire message spam (sliding window).
- **Copy-Paste Deduplication:** Detects and removes repeated identical messages.
- **Malicious Link & Phishing Detector:** Inspects URLs against trusted domain allowlists; flags phishing lures (`claim-airdrop`, `wallet-connect`, `drainer`, suspicious TLDs).
- **Executable Filter:** Blocks dangerous files (`.exe`, `.bat`, `.apk`, `.vbs`, `.js`, `.scr`).
- **Impersonation Prevention:** Protects against fake admin accounts using deceptive names.
- **Warning Escalation:** Configurable automated escalation (e.g., 3 warnings = 2h temporary mute).
- **Safe Heuristic Disclaimers:** Clearly notes that automated checks are heuristics and not absolute guarantees of safety.

### 3. Crypto Alpha & Market Information
- Real-time price, 24h % change, and market cap via CoinGecko Public API.
- Request caching (60s TTL) to prevent rate limits.
- Personal token watchlists (`/watch`, `/unwatch`, `/watchlist`).
- Official contract address verification (`/token`, `/ca`): Displays official CA only when configured; warns against counterfeit tokens and DM scammers.
- Purely informational — strictly non-custodial with no trading or wallet interaction.

### 4. Meme Vault & Engagement Hub
- Community meme library with reaction buttons (🔥 Degen, 🚀 Moon, 💀 Dead, 👑 Based).
- User meme submissions (`/submitmeme`) placed into a moderator approval queue.
- Hall of Fame ranking (`/topmemes`).
- Degen commands: `/gm`, `/gn`, `/wagmi`, `/ser`, `/flip` (virtual coin with entertainment disclaimer), and `/vibe`.

### 5. Administrator Control Center
- Strict Telegram Bot API permission verification (`get_chat_member`).
- Comprehensive moderation toolkit: `/warn`, `/warnings`, `/clearwarns`, `/mute`, `/unmute`, `/kick`, `/ban`, `/unban`, `/purge`, `/lock`, `/unlock`, `/antispam`, `/logs`.

### 6. Responsive Dark Admin Dashboard (FastAPI)
- Obsidian black, yellow/gold, and neon green design system.
- Secure session authentication with JWT and HTTP-only cookies.
- Overview metrics: Tracked members, messages, approved memes, active warnings.
- Real-time Moderation Queue and Audit Trail.
- Meme Approval Queue (one-click Approve / Reject).
- Welcome message and community rules live editor.
- Trusted domain allowlist manager.
- Healthcheck endpoint (`/health`, `/healthz`, `/api/health`).

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Runtime** | Python 3.12+ | Clean, asynchronous runtime |
| **Telegram API** | aiogram 3.31+ | High-performance Telegram Bot framework |
| **Web & API** | FastAPI 0.115+ | Responsive admin dashboard & health check |
| **Database** | PostgreSQL 16 / asyncpg | Persistent relational storage & transactions |
| **ORM & Migrations** | SQLAlchemy 2.0 & Alembic | Schema definitions & versioned migrations |
| **Cache & Flood Control**| Redis 7 & In-Memory fallback | Rate limits, deduplication & market cache |
| **Template Engine** | Jinja2 | Modern server-rendered dark UI |
| **Testing** | pytest & pytest-asyncio | 51 comprehensive automated unit/integration tests |
| **Deployment** | Docker & Docker Compose | Multi-container production deployment |

---

## 📁 Project Architecture

```
memetek/
├── bot/
│   ├── filters/admin.py          # Real-time Telegram admin verification
│   ├── handlers/
│   │   ├── admin.py              # Moderation tools (/warn, /mute, /purge, /lock...)
│   │   ├── crypto.py             # Market alpha (/price, /watchlist, /ca...)
│   │   ├── fun.py                # Memes, greetings & degen fun (/meme, /wagmi...)
│   │   ├── general.py            # Info commands (/start, /help, /rules, /stats...)
│   │   └── welcome.py            # New member welcome logic & auto-deletion
│   ├── middlewares/
│   │   ├── antispam_mw.py        # Message scanner & flood protection
│   │   ├── db_session.py         # AsyncSession injector
│   │   └── user_tracker.py       # Privacy-conscious membership tracking
│   ├── instance.py               # Bot & Dispatcher setup
│   └── keyb.py                   # Inline reaction & navigation keyboards
├── database/
│   ├── models.py                 # SQLAlchemy 2.0 ORM models
│   ├── crud.py                   # Async database operations & queries
│   └── session.py                # Async engine & sessionmaker
├── services/
│   ├── antispam.py               # Phishing, file & flood detection engine
│   ├── cache.py                  # Dual Redis / In-Memory cache provider
│   ├── market.py                 # CoinGecko market client with rate limiting
│   └── meme_service.py           # Meme vault & engagement generators
├── web/
│   ├── routes/
│   │   ├── api.py                # REST API & health checks
│   │   └── pages.py              # Admin dashboard HTML pages
│   ├── static/css/style.css      # Dark MEMETEK brand CSS
│   ├── templates/                # Jinja2 dashboard templates
│   ├── app.py                    # FastAPI application factory
│   └── auth.py                   # Secure JWT & session management
├── alembic/                      # Database migrations
├── config.py                     # Pydantic Settings & brand definitions
└── main.py                       # CLI entrypoint (all, bot, web)
```

---

## ⚡ Quickstart Guide

### Option A: Local Development (Python)

1. **Clone repository:**
   ```bash
   git clone https://github.com/your-org/memetek-bot.git
   cd memetek-bot
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your TELEGRAM_BOT_TOKEN and ADMIN_USER_IDS
   ```

4. **Run migrations:**
   ```bash
   alembic upgrade head
   ```

5. **Start application:**
   ```bash
   python -m memetek.main all
   ```
   - Bot long-polling starts immediately.
   - Web Dashboard will be accessible at: `http://localhost:8080` (Default credentials: `admin` / `ChangeMeInProductionDegen123!`).

---

### Option B: Production Deployment (Docker Compose)

```bash
cp .env.example .env
docker compose up -d --build
```

Verify service health:
```bash
docker compose ps
curl http://localhost:8080/health
```

---

## 🤖 Full Command Directory

### 🐱 General Commands
| Command | Description |
|---|---|
| `/start` | Introduces the bot, brand lore, and quick-start menu |
| `/help` | Interactive categorized command center |
| `/about` | Official MEMETEK story and community vision |
| `/rules` | Community rules and safety guidelines |
| `/id` | Displays current chat ID and your Telegram user ID |
| `/ping` | Checks bot latency, database status, and cache connection |
| `/stats` | Community messages, members, and approved meme stats |

### 🐸 Fun & Meme Commands
| Command | Description |
|---|---|
| `/meme` | Random approved meme with interactive reaction buttons |
| `/topmemes` | Top-rated community memes in the Hall of Fame |
| `/submitmeme [caption]` | Submits a meme or photo for moderator review |
| `/gm` | Sends a vibrant MEMETEK GM greeting |
| `/gn` | Sends a relaxing GN greeting |
| `/wagmi` | Positive community energy boost |
| `/ser` | Hilarious degen crypto advice |
| `/flip` | Virtual coin flip (entertainment only, labeled NFA) |
| `/vibe` | MEMETEK community vibe check |

### 📊 Crypto & Alpha Commands
| Command | Description |
|---|---|
| `/price SYMBOL` | Real-time price, 24h change & market cap (e.g. `/price SOL`) |
| `/watchlist` | View your personal watched assets |
| `/watch SYMBOL` | Add asset to your watchlist |
| `/unwatch SYMBOL` | Remove asset from your watchlist |
| `/token` or `/ca` | Official verified MEMETEK contract address (or scam warning) |

### 🛡️ Administrator Commands (Chat Admins Only)
| Command | Description |
|---|---|
| `/admin` | Displays administrator dashboard & chat settings |
| `/warn USER REASON` | Issues a warning (automatically mutes at 3 warnings) |
| `/warnings USER` | Displays warning history for a user |
| `/clearwarns USER` | Clears all active warnings for a user |
| `/mute USER DURATION REASON` | Temporarily restricts a member (e.g. `/mute 30m spam`) |
| `/unmute USER` | Lifts a restriction |
| `/kick USER REASON` | Removes member from group (can rejoin) |
| `/ban USER REASON` | Permanently bans a member |
| `/unban USER` | Unbans a member |
| `/purge COUNT` | Bulk deletes recent messages (1-100 safe limit) |
| `/lock` | Locks the chat (restricts non-admins from sending messages) |
| `/unlock` | Restores normal chatting permissions |
| `/setwelcome TEXT` | Updates the group welcome message |
| `/setrules TEXT` | Updates community rules |
| `/antispam on\|off` | Toggles automated anti-spam protection |
| `/logs` | Displays recent moderation audit trail |

---

## 🧪 Automated Testing

The project includes 51 automated tests covering handlers, permissions, spam filters, market services, database CRUD, and web APIs.

Run tests:
```bash
pytest -v
```

Test coverage:
- ✅ **Anti-Spam & Phishing:** Message flooding, duplicate spam, phishing keyword URLs, prohibited file extensions, mass mentions, impersonation names.
- ✅ **Permissions & Safety:** Verification that ordinary members cannot execute admin commands, chat admin verification, superadmin bypass, warning escalation.
- ✅ **Market Data:** Symbol resolution, price formatting, CoinGecko API mocks, 429 rate limit handling, network timeouts.
- ✅ **Bot Handlers:** All general, fun, crypto, and welcome handlers.
- ✅ **Database Operations:** Chats, users, warnings, moderation logs, meme reactions, watchlists, allowlists, and audit logs.
- ✅ **Web Dashboard & API:** Health checks, login authentication, session cookies, unauthorized redirects, REST stats, and meme review endpoints.

---

## 🔒 Security & Compliance

- **No Financial Advice (NFA):** Market commands and virtual coin flips include prominent disclaimers that they are for entertainment and informational purposes only.
- **Non-Custodial:** The bot never requests or stores private keys, seed phrases, or exchange credentials.
- **Privacy Conscious:** Tracks minimal activity necessary for community management; members can opt out of engagement tracking.
- **Secure by Default:** Database and Redis services are isolated inside an internal bridge network with zero public host exposure.

---

## 📜 Documentation References

- [Railway Deployment Guide](RAILWAY_DEPLOYMENT.md) — 1-click persistent 24/7 cloud hosting with PostgreSQL & Redis.
- [Telegram Setup Guide](TELEGRAM_SETUP.md) — Step-by-step BotFather, privacy mode, and permissions guide.
- [Production Deployment Guide](DEPLOYMENT.md) — Docker Compose, PostgreSQL & Redis security, backup & restore procedures.

---

*Stay based. Stay bullish. Stay MEMETEK. WAGMI! 🐱🪙🚀*

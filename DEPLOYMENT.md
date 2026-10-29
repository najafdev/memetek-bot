# MEMETEK Telegram Bot — Production Deployment Guide

This guide details how to deploy the production-ready **MEMETEK Community Bot & Web Dashboard** using Docker Compose, PostgreSQL, and Redis.

---

## 1. System Architecture

The deployment topology consists of three isolated services communicating over an internal Docker bridge network:

```
[ Telegram API ] ─────────► [ Webhook / Long Polling ]
                                  │
                                  ▼
┌────────────────────────────────────────────────────────┐
│ memetek-bot (Python 3.12, aiogram 3.x, FastAPI)        │
│ ├── Telegram Dispatcher & Anti-Spam Middleware         │
│ └── Admin Dashboard & Healthcheck API (:8080)          │
└───────────────┬────────────────────────┬───────────────┘
                │                        │
       (PostgreSQL asyncpg)        (Redis async)
                ▼                        ▼
┌────────────────────────┐      ┌────────────────────────┐
│ memetek-postgres       │      │ memetek-redis          │
│ (PostgreSQL 16 Alpine) │      │ (Redis 7 Alpine)       │
│ Persistent Volume      │      │ Rate Limits & Cache    │
└────────────────────────┘      └────────────────────────┘
```

> [!SECURITY]
> Database (`memetek-postgres`) and Cache (`memetek-redis`) ports are **NOT** published to the public host. They are strictly accessible only to the `memetek-bot` container through the private internal bridge network (`memetek-network`).

---

## 2. Prerequisites

- Linux Server (Ubuntu 22.04 LTS / Debian 12 recommended)
- Docker Engine 24.0+ & Docker Compose v2.20+
- Reverse Proxy (Nginx, Caddy, or Cloudflare Tunnel) with SSL/TLS certificate for Webhook / Dashboard access.

---

## 3. Production Deployment with Docker Compose

### Step 1: Clone and Configure Environment

```bash
git clone https://github.com/your-org/memetek-bot.git /opt/memetek
cd /opt/memetek
cp .env.example .env
```

Edit `.env` and fill in your production values:

```ini
# Production Bot Token
TELEGRAM_BOT_TOKEN=123456789:AAProductionTokenFromBotFather

# Superadministrator Telegram IDs (comma-separated)
ADMIN_USER_IDS=123456789,987654321

# PostgreSQL Database Credentials
POSTGRES_USER=memetek_user
POSTGRES_PASSWORD=UseAStrongRandomPassword123!
POSTGRES_DB=memetek_db

# Redis URL (internal container name)
REDIS_URL=redis://redis:6379/0

# Dashboard Security
DASHBOARD_ENABLED=true
DASHBOARD_USERNAME=admin
DASHBOARD_PASSWORD=AnotherStrongRandomPassword456!
DASHBOARD_SECRET_KEY=generate_a_random_32_byte_hex_string_here

# Runtime Settings
LOG_LEVEL=INFO
APP_ENV=production
TEST_MODE=false
```

### Step 2: Build and Start Containers

```bash
docker compose up -d --build
```

### Step 3: Verify Status and Health

Check running containers:

```bash
docker compose ps
```

Expected output:
```
NAME               IMAGE               STATUS                    PORTS
memetek-bot        memetek-bot:latest  Up (healthy)              0.0.0.0:8080->8080/tcp
memetek-postgres   postgres:16-alpine  Up (healthy)              5432/tcp
memetek-redis      redis:7-alpine      Up (healthy)              6379/tcp
```

Test health endpoint:

```bash
curl -f http://localhost:8080/health
```

Expected JSON response:
```json
{
  "status": "ok",
  "version": "1.0.0",
  "database": "connected",
  "cache": "redis"
}
```

---

## 4. Database Migrations with Alembic

The bot automatically creates tables on startup, but you can manage formal database schema migrations using Alembic inside the container:

```bash
# Check current migration revision
docker compose exec bot alembic current

# Upgrade database to the latest revision
docker compose exec bot alembic upgrade head

# Generate a new migration revision
docker compose exec bot alembic revision -m "add_new_feature_table"
```

---

## 5. Webhook Configuration (Optional for High-Traffic Groups)

By default, the bot runs in **long polling mode**, which works without exposing any incoming ports or managing SSL certificates.

For high-throughput environments where Telegram webhooks are preferred:

1. Obtain a public domain with valid HTTPS certificate (e.g., `https://bot.memetek.io`).
2. Update `.env`:
   ```ini
   USE_WEBHOOK=true
   WEBHOOK_URL=https://bot.memetek.io/telegram/webhook
   WEBHOOK_SECRET=your_super_secret_webhook_token_here
   ```
3. Configure Nginx reverse proxy:
   ```nginx
   server {
       server_name bot.memetek.io;
       listen 443 ssl http2;
       ssl_certificate /etc/letsencrypt/live/bot.memetek.io/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/bot.memetek.io/privkey.pem;

       location / {
           proxy_pass http://127.0.0.1:8080;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```
4. Restart the bot container:
   ```bash
   docker compose restart bot
   ```

---

## 6. Backup & Restore Procedures

### Automated Database Backup

Create a periodic backup script (e.g. daily cron job):

```bash
#!/usr/bin/env bash
BACKUP_DIR="/opt/memetek/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
mkdir -p "$BACKUP_DIR"

# Run pg_dump within the postgres container
docker compose exec -T postgres pg_dump -U memetek_user memetek_db | gzip > "$BACKUP_DIR/memetek_backup_$TIMESTAMP.sql.gz"

# Keep last 14 days of backups
find "$BACKUP_DIR" -type f -name "*.sql.gz" -mtime +14 -delete
```

### Restoring Database from Backup

```bash
gunzip -c /opt/memetek/backups/memetek_backup_20261029.sql.gz | \
  docker compose exec -T postgres psql -U memetek_user -d memetek_db
```

---

## 7. Graceful Shutdown & Container Updates

To update code without dropping messages:

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart cleanly
docker compose up -d --build --remove-orphans
```

The application registers `SIGTERM` and `SIGINT` signal handlers, closing the Telegram session and database pools gracefully before terminating.

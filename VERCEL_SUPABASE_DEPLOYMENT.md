# MEMETEK Bot — Vercel + Supabase Deployment Guide

This guide walks you through deploying **MEMETEK** for **100% free** using **Vercel** (for Serverless Hosting) and **Supabase** (for Managed PostgreSQL).

---

## 🏗️ Architecture on Vercel + Supabase

```
[ Telegram Users & Groups ]
              │
              │ (Webhook HTTP POST)
              ▼
┌────────────────────────────────────────────────────────┐
│ Vercel Serverless Function (api/index.py)              │
│ ├── Telegram Webhook Processor (/api/webhook)          │
│ └── FastAPI Admin Mission Control Dashboard (/)        │
└───────────────┬────────────────────────────────────────┘
                │
                │ (PostgreSQL Connection via asyncpg / NullPool)
                ▼
┌────────────────────────────────────────────────────────┐
│ Supabase Managed PostgreSQL (Port 6543 / 5432)        │
│ ├── Chats, Warnings, Moderation Audit Trail            │
│ └── Meme Vault, Watchlists & Allowed Domains          │
└────────────────────────────────────────────────────────┘
```

---

## 📋 Step 1: Create Free Supabase Database (2 Minutes)

1. Go to **[supabase.com](https://supabase.com)** and sign in / sign up (free).
2. Click **"New Project"**.
3. Fill in:
   - **Name:** `memetek-bot`
   - **Database Password:** *Choose a strong password and save it!*
   - **Region:** Choose a region close to you or US East.
4. Click **"Create new project"** (takes ~1 minute to provision).

### Your Supabase Project Information
- **Project Reference:** `ehgyfquubiububzqqoqd`
- **Project URL:** `https://ehgyfquubiububzqqoqd.supabase.co`
- **Database Settings Direct Link:** [https://supabase.com/dashboard/project/ehgyfquubiububzqqoqd/settings/database](https://supabase.com/dashboard/project/ehgyfquubiububzqqoqd/settings/database)

### Get the Database Connection String:
1. In your Supabase dashboard, navigate to:
   [**Project Settings → Database**](https://supabase.com/dashboard/project/ehgyfquubiububzqqoqd/settings/database).
2. Scroll to **"Connection string"** and select the **"URI"** tab.
3. Select **Mode:** **Transaction** (Port `6543`):
   ```
   postgresql://postgres.ehgyfquubiububzqqoqd:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
   ```
4. Replace `[YOUR-PASSWORD]` with the database password you chose when creating the project.

> [!NOTE]
> All 12 tables and initial seed data (allowed domains & approved memes) have already been created and verified in this Supabase database.
> MEMETEK includes a built-in normalizer that automatically translates `postgresql://` to `postgresql+asyncpg://` and configures `NullPool` with `statement_cache_size=0` for Supabase's transaction pooler. You can paste the URI directly from Supabase into Vercel!

---

## 📋 Step 2: Deploy to Vercel (2 Minutes)

1. Go to **[vercel.com](https://vercel.com)** and log in with your GitHub account.
2. Click **"Add New..."** → **"Project"**.
3. Find your **`najafdev/memetek-bot`** repository and click **"Import"**.
4. In the project configuration:
   - **Framework Preset:** Leave as *Other* (or *FastAPI*).
   - **Root Directory:** `./`
5. Expand **"Environment Variables"** and add:

| Variable Name | Value | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | `123456789:ABC...` | Your token from [@BotFather](https://t.me/BotFather) |
| `DATABASE_URL` | `postgresql://postgres.[REF]:[PASS]@...:6543/postgres` | Your Supabase connection string from Step 1 |
| `ADMIN_USER_IDS` | `123456789` | Your numeric Telegram User ID (get via `/id`) |
| `WEBHOOK_SECRET` | `memetek_secret_key_random32chars` | Random string to authenticate Telegram requests |
| `DASHBOARD_PASSWORD` | `YourAdminPassword123!` | Password for Web Mission Control |
| `DASHBOARD_SECRET_KEY` | `random_session_key_32chars` | Secret key for JWT sessions |
| `APP_ENV` | `serverless` | Optimizes database pool for serverless execution |

6. Click **"Deploy"**.
7. Vercel will build the project and assign you a live domain (e.g., `https://memetek-bot.vercel.app`).

---

## 📋 Step 3: Register Webhook with Telegram (1 Minute)

Now tell Telegram to deliver all updates directly to your Vercel serverless webhook.

Open your browser or run this command in your terminal:

```bash
curl -F "url=https://<your-vercel-domain>.vercel.app/api/webhook" \
     -F "secret_token=memetek_secret_key_random32chars" \
     https://api.telegram.org/bot<YOUR_TELEGRAM_BOT_TOKEN>/setWebhook
```

*(Replace `<your-vercel-domain>`, `memetek_secret_key_random32chars`, and `<YOUR_TELEGRAM_BOT_TOKEN>` with your real values).*

You will get a confirmation JSON response:
```json
{"ok": true, "result": true, "description": "Webhook was set"}
```

---

## 📋 Step 4: Verify Deployment

1. **Telegram Chat:**
   - Open your bot in Telegram and send `/ping`.
   - Send `/start` or `/price SOL`.
   - The bot will process the update serverlessly on Vercel and query your Supabase database!

2. **Admin Mission Control:**
   - Open `https://<your-vercel-domain>.vercel.app` in your browser.
   - Log in with `admin` and your configured `DASHBOARD_PASSWORD`.
   - You can review memes, update welcome rules, view active warnings, and inspect audit logs!

---

## 🔍 Troubleshooting Tips

- **Database Connection Error (`password authentication failed`):**
  Check that you replaced `[YOUR-PASSWORD]` in your Supabase connection string with your actual password (and that special characters like `@` or `#` in the password are URL-encoded).
- **Telegram Webhook Status Check:**
  To see if Telegram is encountering any errors sending updates to your Vercel app:
  ```bash
  https://api.telegram.org/bot<YOUR_TELEGRAM_BOT_TOKEN>/getWebhookInfo
  ```
- **Vercel Function Logs:**
  In Vercel, go to your project dashboard → **Logs** to view live runtime logs for any incoming webhook or dashboard request.

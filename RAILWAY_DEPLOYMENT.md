# MEMETEK Telegram Bot — Railway Deployment Guide

**[Railway.app](https://railway.app)** is one of the best platforms to run MEMETEK. Unlike serverless platforms like Vercel, Railway runs persistent 24/7 background worker processes, supports native Docker, has 1-click managed PostgreSQL and Redis plugins, and preserves background tasks (such as welcome message auto-deletion timers).

---

## 🚀 Why Railway for Telegram Bots?

- **Persistent 24/7 Long Polling:** Runs without needing webhooks or public domains.
- **1-Click PostgreSQL & Redis:** Instant managed databases in the same private network.
- **Auto-Environment Linking:** Railway automatically populates `DATABASE_URL` and `REDIS_URL`.
- **Automatic Health Checks:** Monitors `/health` to restart containers if unhealthy.
- **Affordable / Generous:** $5 free monthly credit with pay-as-you-go pricing.

---

## 📋 Step-by-Step Deployment Walkthrough

### Step 1: Push Code to GitHub

Make sure your MEMETEK bot code is pushed to your GitHub repository:
```bash
git add .
git commit -m "feat: railway deployment configuration"
git push origin main
```

---

### Step 2: Create a New Project on Railway

1. Go to [railway.app](https://railway.app) and log in (with GitHub).
2. Click **"New Project"**.
3. Select **"Deploy from GitHub repo"** → select your `memetek-bot` repository.
4. Railway will automatically detect the [`railway.json`](railway.json) and [`Dockerfile`](Dockerfile).

---

### Step 3: Add Managed PostgreSQL & Redis in 1 Click

1. Inside your Railway project canvas, click the **"+ Create"** button (or press `Ctrl+K` / `Cmd+K`).
2. Select **"Database"** → **"Add PostgreSQL"**.
   - Railway will provision a private PostgreSQL 16 database.
3. Click **"+ Create"** again.
4. Select **"Database"** → **"Add Redis"**.
   - Railway will provision a private Redis instance.

---

### Step 4: Configure Environment Variables

Click on your **bot service** card in Railway → open the **"Variables"** tab:

1. **Telegram Credentials:**
   - `TELEGRAM_BOT_TOKEN`: Your token from [@BotFather](https://t.me/BotFather) (e.g. `123456789:AA...`).
   - `ADMIN_USER_IDS`: Your numeric Telegram User ID (e.g. `123456789`). Send `/id` to the bot to get it.

2. **Connect Database & Redis:**
   - Click **"Add Reference"** (or **"Variable Reference"**):
     - Select `Postgres` → `DATABASE_URL`.
     - Select `Redis` → `REDIS_URL`.
   *(MEMETEK automatically translates `postgresql://` to `postgresql+asyncpg://` for async SQLAlchemy compatibility).*

3. **Dashboard Security (Optional):**
   - `DASHBOARD_ENABLED`: `true`
   - `DASHBOARD_USERNAME`: `admin`
   - `DASHBOARD_PASSWORD`: `YourSecretPassword123!`
   - `DASHBOARD_SECRET_KEY`: `random_32_character_secret_key`

---

### Step 5: Generate a Public Domain (For Admin Dashboard)

If you want to access the Web Mission Control Dashboard:
1. In your bot service, go to **Settings** → **Networking**.
2. Click **"Generate Domain"** (e.g. `memetek-production.up.railway.app`).
3. Railway automatically routes traffic to port `8080`.

---

### Step 6: Deploy & Verify

1. Railway will automatically trigger a build using the [`Dockerfile`](Dockerfile).
2. Open the **"Deployments"** → **"View Logs"** tab:
   You should see:
   ```
   [INFO] Initializing database schema...
   [INFO] Connected to Redis successfully.
   [INFO] Starting Telegram Bot long-polling loop...
   [INFO] Starting Web Dashboard server at http://0.0.0.0:8080
   ```
3. Test your bot in Telegram by sending `/ping` in your community group!

---

## 🛠️ Upgrades & Maintenance on Railway

- **Continuous Deployment:** Every time you `git push` to `main`, Railway automatically rebuilds and redeploys your bot with zero manual effort.
- **Database Backups:** Railway provides automated daily backups of your PostgreSQL database under the Postgres service's **"Backups"** tab.

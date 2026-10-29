# MEMETEK Bot — Render Deployment Guide 🚀

Deploy **MEMETEK** for free on **[Render.com](https://render.com)** with persistent hosting, automatic SSL, and Supabase PostgreSQL.

---

## ⚡ Option A: Instant Deploy via Blueprint (Fastest — 1 Click)

1. Go to **[dashboard.render.com](https://dashboard.render.com)**.
2. Click **New +** → **Blueprint**.
3. Select your repository: **`najafdev/memetek-bot`**.
4. Render will read [`render.yaml`](file:///root/bot/render.yaml) automatically.
5. In the prompts, enter your 2 secret values:
   - **`TELEGRAM_BOT_TOKEN`**: `9190040330:AAEhTUkkpi1SeHRUcgWODzm8Rxr2z1eM7iA`
   - **`DATABASE_URL`**: `postgresql://postgres.ehgyfquubiububzqqoqd:%40Ethicalhacker07@aws-0-eu-west-1.pooler.supabase.com:6543/postgres`
6. Click **Apply**. Render will build and deploy your live bot!

---

## 🛠️ Option B: Manual Web Service Setup

If you prefer to configure manually:

1. Click **New +** → **Web Service**.
2. Connect your repository: **`najafdev/memetek-bot`**.
3. Set the service settings:
   - **Name:** `memetek-bot`
   - **Language:** `Python 3`
   - **Branch:** `main`
   - **Build Command:** `pip install --upgrade pip && pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type:** `Free`
4. Under **Environment Variables**, add:

| Key | Value |
|---|---|
| `TELEGRAM_BOT_TOKEN` | `9190040330:AAEhTUkkpi1SeHRUcgWODzm8Rxr2z1eM7iA` |
| `DATABASE_URL` | `postgresql://postgres.ehgyfquubiububzqqoqd:%40Ethicalhacker07@aws-0-eu-west-1.pooler.supabase.com:6543/postgres` |
| `ADMIN_USER_IDS` | `1122866063` |
| `WEBHOOK_SECRET` | `memetek_secret_key_2026_xyz` |
| `DASHBOARD_USERNAME` | `admin` |
| `DASHBOARD_PASSWORD` | `AdminDegenPassword2026!` |
| `DASHBOARD_SECRET_KEY` | `memetek_super_secret_jwt_key_degens_moon_2026` |
| `PYTHON_VERSION` | `3.12.0` |

5. Click **Deploy Web Service**.

---

## 🔗 Connect Webhook to Render

Once Render is live (e.g. `https://memetek-bot.onrender.com`):

```bash
curl -F "url=https://<YOUR-RENDER-APP>.onrender.com/api/webhook" \
     -F "secret_token=memetek_secret_key_2026_xyz" \
     https://api.telegram.org/bot9190040330:AAEhTUkkpi1SeHRUcgWODzm8Rxr2z1eM7iA/setWebhook
```

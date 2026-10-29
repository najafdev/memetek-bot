# MEMETEK Telegram Bot — Setup & Configuration Guide

Welcome to the official setup guide for **MEMETEK** (*Where Memes Meet the Moon 🚀*). Follow this step-by-step walkthrough to create, configure, and connect your Telegram community bot.

---

## 1. Creating the Bot via @BotFather

1. Open Telegram and search for the official **[@BotFather](https://t.me/BotFather)** (look for the verified blue checkmark).
2. Start a conversation and send the command:
   ```
   /newbot
   ```
3. Choose a display name for your bot, e.g.:
   ```
   MEMETEK Community Bot
   ```
4. Choose a unique username ending in `bot`, e.g.:
   ```
   memetek_community_bot
   ```
5. BotFather will generate an API access token in the format:
   ```
   123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
   ```

---

## 2. Storing the Bot Token Securely

Never commit your bot token to Git or publish it in public repositories.
Copy `.env.example` to `.env` in the bot root directory:

```bash
cp .env.example .env
```

Open `.env` and set `TELEGRAM_BOT_TOKEN`:

```ini
TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
```

---

## 3. Configuring Telegram Group Privacy Mode

By default, Telegram bots have **Privacy Mode** enabled, meaning they only receive messages that explicitly mention them (e.g., `@memetek_community_bot`) or start with a slash `/`.

For MEMETEK's **Anti-Spam, Phishing, and Flood Protection Shields** to monitor group text for malicious links and spam, Privacy Mode must be adjusted:

1. In **@BotFather**, send:
   ```
   /setprivacy
   ```
2. Select your bot `@memetek_community_bot`.
3. Choose **`Disable`**.
4. BotFather will confirm: *"Privacy mode is now disabled for [bot name]."*.

> [!NOTE]
> If you keep Privacy Mode enabled, the bot can still respond to commands (e.g. `/price`, `/meme`, `/warn`), but it will **not** be able to passively inspect regular member messages for malicious phishing links, scam token ads, or flooding.

---

## 4. Configuring Public Bot Commands in BotFather

Register the official MEMETEK command menu in Telegram's quick-select UI:

1. In **@BotFather**, send:
   ```
   /setcommands
   ```
2. Select your bot `@memetek_community_bot`.
3. Paste the following block:
   ```
   start - Introduce the bot and quick guide
   help - Categorized command directory
   about - MEMETEK lore and community vision
   rules - Group rules and guidelines
   price - Real-time crypto market alpha (/price SOL)
   watchlist - View your personal crypto watchlist
   watch - Add token to personal watchlist
   unwatch - Remove token from watchlist
   meme - Random approved meme from community vault
   topmemes - Highest upvoted community memes
   submitmeme - Submit a meme for moderator review
   gm - Send vibrant GM greeting
   gn - Send relaxing GN greeting
   wagmi - Positive community energy boost
   ser - Hilarious degen crypto wisdom
   flip - Virtual coin flip (entertainment only)
   vibe - MEMETEK vibe check
   token - Official verified contract address (CA)
   id - Display current chat & user Telegram ID
   ping - Check bot latency and health
   admin - Administrator command control center
   ```

---

## 5. Adding the Bot to Your Telegram Group

1. Open your Telegram group (e.g., **MEMETEK Community Lounge**).
2. Go to **Group Info** → **Members** / **Administrators** → **Add Member**.
3. Search for your bot username (`@memetek_community_bot`) and add it.

---

## 6. Granting Administrator Permissions

For the bot to protect members, welcome newcomers, and enforce moderation actions, promote it to an **Administrator** with the following permissions:

| Permission | Required? | Purpose |
|---|---|---|
| **Delete Messages** | **Yes** | Removes phishing links, scam shilling, and auto-deletes welcome notices |
| **Ban / Restrict Users** | **Yes** | Mutes floody spammers and bans phishing accounts |
| **Pin Messages** | **Recommended** | Pins important community announcements |
| **Invite Users via Link** | **Optional** | Generates temporary join links if configured |
| **Remain Anonymous** | **No** | Keep disabled so bot identity is clear |
| **Add New Admins** | **No** | Do **not** grant admin creation rights |

---

## 7. Configuring Administrator IDs Securely

To prevent unauthorized access to bot-wide administrative functions, configure numeric Telegram User IDs in `.env`:

1. Send `/id` to the bot in a direct message or in the group to get your numeric ID (e.g. `123456789`).
2. Add your ID to `.env`:
   ```ini
   ADMIN_USER_IDS=123456789,987654321
   ```

> [!IMPORTANT]
> The bot verifies administrative status in real-time via Telegram's Bot API (`get_chat_member`), verifying whether a user is an actual group administrator or creator before executing commands like `/mute`, `/ban`, `/warn`, or `/purge`. It **never** relies on self-reported usernames or input parameters.

---

## 8. Starting the Bot

Start the bot locally or via Docker:

```bash
# Direct Python:
python3 -m memetek.main all

# Or with Docker Compose:
docker compose up -d
```

---

## 9. Verification Checklist

Test that all systems are operational:

1. **Ping Test**: Send `/ping` in the group. The bot should reply with latency (`~Xms`), Database status `🟢 Healthy`, and Cache status `🟢 Connected`.
2. **Help Navigation**: Send `/help` and click the category buttons (`🐱 General`, `🐸 Fun & Memes`, `📊 Crypto & Alpha`, `🛡️ Moderation`).
3. **Price Lookup**: Send `/price BTC` or `/price SOL`. The bot should return live market data attributed to CoinGecko.
4. **Welcome Test**: Have a new user join or run `/previewwelcome` as an admin.
5. **Anti-Spam Verification**: Have a non-admin post a prohibited test string (e.g. `t.me/+joinchat` or a link to `claim-airdrop.xyz`). The bot will instantly delete the message and log a warning.
6. **Admin Restrict Test**: Reply to a message with `/mute 5m testing mute` as an administrator.

---

## 10. Troubleshooting Common Telegram Errors

| Error | Cause | Fix |
|---|---|---|
| `401 Unauthorized` | Invalid `TELEGRAM_BOT_TOKEN` | Double-check token in `.env` without extra quotes or spaces. |
| `403 Forbidden: bot was blocked by the user` | User has not started DM with the bot | User must click Start in private chat with the bot. |
| `400 Bad Request: not enough rights to restrict member` | Bot lacks administrator rights in group | Grant bot "Ban Users" and "Delete Messages" permissions in Telegram Group Settings. |
| `Conflict: terminated by other getUpdates request` | Multiple bot instances running simultaneously | Kill running duplicate bot processes before starting a new instance. |
| `400 Bad Request: message to delete not found` | Message already deleted or too old (> 48h) | Telegram does not allow deleting messages older than 48 hours. |
| `429 Too Many Requests` | Telegram API rate limit exceeded | The bot incorporates built-in backoff and caching to prevent spamming Telegram servers. |

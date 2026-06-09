# Render Deployment Guide (Aiven PostgreSQL)

This covers hosting everything on [Render](https://render.com): the bot + API as one Web Service, and the dashboard as a Static Site, using **Aiven** for the database.

---

## Before You Start

You'll need:
- A [Render](https://render.com) account
- Your code pushed to a GitHub or GitLab repo
- A [Discord Application](https://discord.com/developers/applications) with a bot token and OAuth2 credentials
- Your Aiven PostgreSQL service (already running)

---

## Step 1 — Aiven Database Setup

### Get your connection string
1. Go to [console.aiven.io](https://console.aiven.io) → your PostgreSQL service
2. On the **Overview** tab, find the **Connection information** section
3. Copy the **Service URI** — it looks like:
   ```
   postgres://avnadmin:PASSWORD@HOST.aivencloud.com:PORT/defaultdb?sslmode=require
   ```
   This is your `DATABASE_URL`.

### Apply the schema
In the Aiven console, go to **Databases → Query Editor**, or use a client like [TablePlus](https://tableplus.com) or [DBeaver](https://dbeaver.io), and run the contents of `bot/database.sql`.

Or from a terminal (with psql installed):
```bash
psql "YOUR_SERVICE_URI" -f bot/database.sql
```

> Aiven enforces SSL on all connections. The `?sslmode=require` at the end of the URI is already there — the code handles it automatically when `DB_SSL=true` is set.

---

## Step 2 — Discord Application Setup

1. Go to [discord.com/developers/applications](https://discord.com/developers/applications) → your app
2. **Bot** tab → copy the **Token** → this is `DISCORD_TOKEN`
3. **OAuth2 → General** tab → copy the **Client ID** and **Client Secret**
4. Under **Redirects**, add:
   ```
   https://YOUR-API-SERVICE.onrender.com/api/auth/callback
   ```
   *(Come back and add this after Step 3 once you know the URL)*

---

## Step 3 — Bot + API Web Service

One Render Web Service runs both the Python bot and the Node.js API server.

### Create the service
1. Render → **New → Web Service**
2. Connect your GitHub/GitLab repo
3. Configure:

| Field | Value |
|---|---|
| **Name** | `nightpigeon-api` |
| **Branch** | `main` |
| **Root Directory** | *(leave blank)* |
| **Runtime** | **Node** |
| **Build Command** | `npm install -g pnpm && pnpm install && pip install -r bot/requirements.txt` |
| **Start Command** | `bash start.sh` |
| **Instance Type** | Free (or Starter for always-on) |

### Environment variables

Add all of these under **Environment → Environment Variables**:

| Key | Value |
|---|---|
| `DISCORD_TOKEN` | Your bot token |
| `DATABASE_URL` | Your Aiven Service URI (with `?sslmode=require`) |
| `DB_SSL` | `true` |
| `BOT_OWNER_ID` | Your Discord user ID (right-click yourself → Copy ID) |
| `DISCORD_CLIENT_ID` | OAuth2 Client ID |
| `DISCORD_CLIENT_SECRET` | OAuth2 Client Secret |
| `DISCORD_REDIRECT_URI` | `https://YOUR-API-SERVICE.onrender.com/api/auth/callback` |
| `SESSION_SECRET` | A long random string — run `openssl rand -hex 32` to generate one |
| `DASHBOARD_URL` | `https://YOUR-DASHBOARD.onrender.com` *(fill in after Step 4)* |
| `NODE_ENV` | `production` |
| `PORT` | `10000` |

> After the service deploys, copy its URL and go back to the Discord Developer Portal to add the redirect URI, then also set `DASHBOARD_URL` once you have the dashboard URL.

---

## Step 4 — Dashboard Static Site

### Create the static site
1. Render → **New → Static Site**
2. Connect the same repo
3. Configure:

| Field | Value |
|---|---|
| **Name** | `nightpigeon-dashboard` |
| **Branch** | `main` |
| **Root Directory** | *(leave blank)* |
| **Build Command** | `npm install -g pnpm && pnpm install && cd artifacts/dashboard && PORT=3000 BASE_PATH=/ NODE_ENV=production pnpm build` |
| **Publish Directory** | `artifacts/dashboard/dist/public` |

### Build environment variables

| Key | Value |
|---|---|
| `VITE_API_URL` | `https://YOUR-API-SERVICE.onrender.com/api` |

> `VITE_API_URL` is baked into the frontend at build time. If your API URL ever changes, redeploy the dashboard.

---

## Step 5 — Whitelist Your First Server

The bot leaves any server it is not whitelisted for. After inviting it:

1. Invite the bot via the OAuth2 URL from the Discord Developer Portal  
   *(Scopes: `bot` · Permissions: `Administrator`)*
2. In any channel the bot can read, run:
   ```
   !whitelist YOUR_SERVER_ID
   ```
   Get the server ID by right-clicking the server icon → **Copy Server ID** (requires Developer Mode in Discord settings)

---

## Step 6 — Access the Dashboard

1. Go to `https://YOUR-DASHBOARD.onrender.com`
2. Click **Dashboard** → **Sign in with Discord**
3. Authorize → you'll land back on the dashboard
4. Your whitelisted server appears in the sidebar
5. Select it → edit the YAML → **Save Config**

### Who can see a server on the dashboard?
- The **bot owner** (`BOT_OWNER_ID`)
- The **guild owner** (whoever ran `!whitelist`)
- Anyone added to the `config_access` database table

---

## Aiven SSL — What Was Changed

To support Aiven's mandatory SSL, two files were updated. You don't need to do anything manually — just set `DB_SSL=true` and the code handles it:

- **Node.js API** (`lib/db/src/index.ts`) — passes `ssl: { rejectUnauthorized: false }` to the pg pool when `DB_SSL=true`
- **Python bot** (`bot/main.py`) — creates an SSL context with certificate verification disabled when `DB_SSL=true` (Aiven uses self-signed certs internally, so this is expected)

---

## Common Issues

| Problem | Fix |
|---|---|
| Bot not connecting to DB | Check `DATABASE_URL` includes `?sslmode=require` and `DB_SSL=true` is set |
| `SSL connection required` error | Make sure `DB_SSL=true` is in the Web Service env vars |
| OAuth login redirects to wrong URL | `DISCORD_REDIRECT_URI` on the API service must exactly match what's in the Discord Developer Portal |
| Dashboard login loop | `DASHBOARD_URL` must be set on the API service so cross-origin cookies work |
| "No whitelisted servers" | Run `!whitelist SERVER_ID` in your server first |
| Service sleeps on free tier | Use [UptimeRobot](https://uptimerobot.com) to ping the API every 5 min, or upgrade to Starter |

---

## Quick Reference

| What | Where |
|---|---|
| Bot + API URL | `https://nightpigeon-api.onrender.com` |
| Dashboard URL | `https://nightpigeon-dashboard.onrender.com` |
| Aiven connection string | Aiven Console → Service → Overview → Service URI |
| Discord app settings | [discord.com/developers/applications](https://discord.com/developers/applications) |

# Render Deployment Guide

This covers hosting everything on [Render](https://render.com): the bot + API together as one Web Service, and the dashboard as a Static Site.

---

## Before You Start

You'll need:
- A [Render](https://render.com) account
- Your code pushed to a GitHub or GitLab repo
- A [Discord Application](https://discord.com/developers/applications) with a bot token and OAuth2 credentials
- A PostgreSQL database (Render provides one, or use [Neon](https://neon.tech) for free)

---

## Step 1 — Create the Database

### Option A: Render PostgreSQL
1. In the Render dashboard → **New → PostgreSQL**
2. Give it a name (e.g. `nightpigeon-db`)
3. Choose the free tier → **Create Database**
4. Copy the **Internal Database URL** (use this for services on Render) or **External Database URL** (for local use)

### Option B: Neon (free, recommended)
1. Sign up at [neon.tech](https://neon.tech)
2. Create a project → copy the connection string

### Apply the schema
Run this once with any PostgreSQL client (e.g. [psql](https://www.postgresql.org/docs/current/app-psql.html), [TablePlus](https://tableplus.com), or Neon's SQL editor):

```sql
-- paste the full contents of bot/database.sql here
```

Or from a terminal:
```bash
psql YOUR_DATABASE_URL < bot/database.sql
```

---

## Step 2 — Discord Application Setup

1. Go to [discord.com/developers/applications](https://discord.com/developers/applications) → your app
2. **Bot tab** → copy the **Token** (this is `DISCORD_TOKEN`)
3. **OAuth2 → General tab** → copy the **Client ID** and **Client Secret**
4. Under **Redirects**, add:
   ```
   https://YOUR-API-SERVICE.onrender.com/api/auth/callback
   ```
   (You'll know this URL after Step 3. Come back and add it then.)

---

## Step 3 — Bot + API Web Service

This single Render Web Service runs the Python bot and the Node.js API server together.

### Create the service
1. Render dashboard → **New → Web Service**
2. Connect your GitHub repo
3. Fill in:

| Field | Value |
|---|---|
| **Name** | `nightpigeon-api` (or whatever you like) |
| **Region** | Closest to you |
| **Branch** | `main` |
| **Root Directory** | *(leave blank)* |
| **Runtime** | **Node** |
| **Build Command** | `npm install -g pnpm && pnpm install && pip install -r bot/requirements.txt` |
| **Start Command** | `bash start.sh` |
| **Instance Type** | Free (or Starter for always-on) |

### Environment variables
Add these in the **Environment** tab:

| Key | Value |
|---|---|
| `DISCORD_TOKEN` | Your bot token |
| `DATABASE_URL` | Your PostgreSQL connection string |
| `BOT_OWNER_ID` | Your Discord user ID (right-click yourself → Copy ID) |
| `DISCORD_CLIENT_ID` | OAuth2 Client ID |
| `DISCORD_CLIENT_SECRET` | OAuth2 Client Secret |
| `DISCORD_REDIRECT_URI` | `https://YOUR-API-SERVICE.onrender.com/api/auth/callback` |
| `SESSION_SECRET` | A long random string (e.g. run `openssl rand -hex 32`) |
| `DASHBOARD_URL` | `https://YOUR-DASHBOARD.onrender.com` (fill in after Step 4) |
| `NODE_ENV` | `production` |
| `PORT` | `10000` |

> **After deploying**, copy the service URL (e.g. `https://nightpigeon-api.onrender.com`) and go back to the Discord Developer Portal to add the redirect URI.

---

## Step 4 — Dashboard Static Site

The dashboard is a React app built with Vite and served as a static site.

### Create the static site
1. Render dashboard → **New → Static Site**
2. Connect the same GitHub repo
3. Fill in:

| Field | Value |
|---|---|
| **Name** | `nightpigeon-dashboard` |
| **Branch** | `main` |
| **Root Directory** | *(leave blank)* |
| **Build Command** | `npm install -g pnpm && pnpm install && cd artifacts/dashboard && PORT=3000 BASE_PATH=/ NODE_ENV=production pnpm build` |
| **Publish Directory** | `artifacts/dashboard/dist/public` |

### Environment variables (build-time)
| Key | Value |
|---|---|
| `VITE_API_URL` | `https://YOUR-API-SERVICE.onrender.com/api` |

> The `VITE_API_URL` is baked into the frontend at build time. Every time you change the API URL, you'll need to redeploy the dashboard.

---

## Step 5 — Whitelist Your First Server

The bot only stays in servers that are explicitly whitelisted. Use the `!deveval` command (owner only) to whitelist your server:

1. Invite the bot to your server using the OAuth2 URL from the Discord Developer Portal (scopes: `bot`, permissions: `Administrator`)
2. In any channel the bot can see, run:
   ```
   !whitelist YOUR_SERVER_ID
   ```
   Replace `YOUR_SERVER_ID` with your Discord server's ID (right-click the server icon → Copy Server ID)

---

## Step 6 — Access the Dashboard

1. Go to `https://YOUR-DASHBOARD.onrender.com`
2. Click **Dashboard** → **Sign in with Discord**
3. Authorize the app — you'll be redirected back to the dashboard
4. If your server is whitelisted and you have access, it will appear in the sidebar
5. Select a server → edit its YAML configuration → **Save Config**

### Who can access the dashboard?
A user can see a server in the dashboard if they are:
- The **bot owner** (`BOT_OWNER_ID`)
- The **guild owner** (the person who whitelisted the server)
- Granted access via the `config_access` database table

---

## Common Issues

**Bot isn't responding**
- Check the Web Service logs in Render for Python errors
- Make sure `DISCORD_TOKEN` is correct and the bot is invited to the server

**"OAuth not configured" on login**
- Check `DISCORD_CLIENT_ID` and `DISCORD_CLIENT_SECRET` are set on the Web Service
- Make sure the redirect URI in the Discord Developer Portal exactly matches `DISCORD_REDIRECT_URI`

**Dashboard shows "no whitelisted servers"**
- The server must be added to `whitelisted_guilds` via `!whitelist` first
- Your Discord account must be the guild owner or have `config_access`

**Cookies not working / login loop**
- Make sure `DASHBOARD_URL` is set on the API service (enables cross-origin cookie support)
- The API service must be running on HTTPS (`NODE_ENV=production`)

**Free tier sleeps after 15 minutes of inactivity**
- Upgrade to a paid Render plan, or use [UptimeRobot](https://uptimerobot.com) to ping your service every 5 minutes to keep it awake

---

## Summary of Services

| Service | Type | URL |
|---|---|---|
| Bot + API | Web Service (Node) | `https://nightpigeon-api.onrender.com` |
| Dashboard | Static Site | `https://nightpigeon-dashboard.onrender.com` |
| Database | PostgreSQL | Internal URL used by the Web Service |

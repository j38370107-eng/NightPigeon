import { Router, Request, Response } from "express";
import { db } from "@workspace/db";

const router = Router();

const DISCORD_CLIENT_ID = process.env.DISCORD_CLIENT_ID || "";
const DISCORD_CLIENT_SECRET = process.env.DISCORD_CLIENT_SECRET || "";
const REDIRECT_URI = process.env.DISCORD_REDIRECT_URI || `${process.env.REPLIT_DEV_DOMAIN ? `https://${process.env.REPLIT_DEV_DOMAIN}` : "http://localhost"}/api/auth/callback`;

declare module "express-session" {
  interface SessionData {
    user?: {
      id: string;
      username: string;
      avatar: string | null;
      discriminator: string;
      accessToken: string;
    };
  }
}

router.get("/discord", (_req: Request, res: Response) => {
  if (!DISCORD_CLIENT_ID) {
    res.status(500).json({ error: "Discord OAuth not configured. Set DISCORD_CLIENT_ID and DISCORD_CLIENT_SECRET." });
    return;
  }
  const params = new URLSearchParams({
    client_id: DISCORD_CLIENT_ID,
    redirect_uri: REDIRECT_URI,
    response_type: "code",
    scope: "identify guilds",
  });
  res.redirect(`https://discord.com/oauth2/authorize?${params}`);
});

router.get("/callback", async (req: Request, res: Response) => {
  const { code } = req.query;
  if (!code || typeof code !== "string") {
    res.redirect("/?error=no_code");
    return;
  }

  if (!DISCORD_CLIENT_ID || !DISCORD_CLIENT_SECRET) {
    res.redirect("/?error=oauth_not_configured");
    return;
  }

  try {
    const tokenRes = await fetch("https://discord.com/api/oauth2/token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        client_id: DISCORD_CLIENT_ID,
        client_secret: DISCORD_CLIENT_SECRET,
        grant_type: "authorization_code",
        code,
        redirect_uri: REDIRECT_URI,
      }),
    });

    if (!tokenRes.ok) {
      res.redirect("/?error=token_failed");
      return;
    }

    const tokenData = await tokenRes.json() as { access_token: string; token_type: string };

    const userRes = await fetch("https://discord.com/api/users/@me", {
      headers: { Authorization: `Bearer ${tokenData.access_token}` },
    });

    if (!userRes.ok) {
      res.redirect("/?error=user_fetch_failed");
      return;
    }

    const user = await userRes.json() as { id: string; username: string; avatar: string | null; discriminator: string };

    (req.session as any).user = {
      id: user.id,
      username: user.username,
      avatar: user.avatar,
      discriminator: user.discriminator,
      accessToken: tokenData.access_token,
    };

    res.redirect("/dashboard");
  } catch (err) {
    console.error("OAuth callback error:", err);
    res.redirect("/?error=oauth_error");
  }
});

router.get("/me", (req: Request, res: Response) => {
  const user = (req.session as any).user;
  if (!user) {
    res.status(401).json({ error: "Not authenticated" });
    return;
  }
  const { accessToken: _at, ...publicUser } = user;
  res.json(publicUser);
});

router.post("/logout", (req: Request, res: Response) => {
  req.session.destroy(() => {
    res.json({ success: true });
  });
});

export default router;

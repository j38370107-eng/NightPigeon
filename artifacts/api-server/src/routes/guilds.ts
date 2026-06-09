import { Router, Request, Response } from "express";
import { pool } from "@workspace/db";

const router = Router();

function requireAuth(req: Request, res: Response): any | null {
  const user = (req.session as any).user;
  if (!user) {
    res.status(401).json({ error: "Not authenticated" });
    return null;
  }
  return user;
}

async function getUserGuilds(accessToken: string): Promise<any[]> {
  const res = await fetch("https://discord.com/api/users/@me/guilds", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!res.ok) return [];
  return res.json() as Promise<any[]>;
}

async function canAccessGuild(userId: string, guildId: string): Promise<boolean> {
  const client = await pool.connect();
  try {
    // Check if guild is whitelisted
    const whitelistRow = await client.query(
      "SELECT guild_owner_id FROM whitelisted_guilds WHERE guild_id = $1",
      [BigInt(guildId)]
    );
    if (whitelistRow.rows.length === 0) return false;

    // Bot owner bypass
    const ownerIdEnv = process.env.BOT_OWNER_ID;
    if (ownerIdEnv && userId === ownerIdEnv) return true;

    // Guild owner check
    if (whitelistRow.rows[0].guild_owner_id?.toString() === userId) return true;

    // Config access check
    const accessRow = await client.query(
      "SELECT 1 FROM config_access WHERE guild_id = $1 AND user_id = $2",
      [BigInt(guildId), BigInt(userId)]
    );
    return accessRow.rows.length > 0;
  } finally {
    client.release();
  }
}

// GET /api/guilds
router.get("/", async (req: Request, res: Response) => {
  const user = requireAuth(req, res);
  if (!user) return;

  try {
    const discordGuilds = await getUserGuilds(user.accessToken);

    const client = await pool.connect();
    try {
      const { rows: whitelisted } = await client.query("SELECT guild_id, guild_name FROM whitelisted_guilds");
      const whitelistedIds = new Set(whitelisted.map((r: any) => r.guild_id.toString()));

      const { rows: configs } = await client.query("SELECT guild_id FROM guild_configs");
      const configIds = new Set(configs.map((r: any) => r.guild_id.toString()));

      const ownerId = process.env.BOT_OWNER_ID;

      // Filter to guilds user can access
      const accessible = [];
      for (const g of discordGuilds) {
        if (!whitelistedIds.has(g.id)) continue;

        // Check access
        const isOwner = ownerId && user.id === ownerId;
        const isAdmin = (g.permissions & 0x8) === 0x8;

        const { rows: accessRows } = await client.query(
          "SELECT 1 FROM config_access WHERE guild_id = $1 AND user_id = $2",
          [BigInt(g.id), BigInt(user.id)]
        );

        const { rows: ownerRows } = await client.query(
          "SELECT 1 FROM whitelisted_guilds WHERE guild_id = $1 AND guild_owner_id = $2",
          [BigInt(g.id), BigInt(user.id)]
        );

        if (isOwner || accessRows.length > 0 || ownerRows.length > 0 || isAdmin) {
          accessible.push({
            id: g.id,
            name: g.name,
            icon: g.icon,
            memberCount: null,
            hasConfig: configIds.has(g.id),
          });
        }
      }

      res.json(accessible);
    } finally {
      client.release();
    }
  } catch (err) {
    console.error("Get guilds error:", err);
    res.status(500).json({ error: "Internal server error" });
  }
});

// GET /api/guilds/:guildId/config
router.get("/:guildId/config", async (req: Request, res: Response) => {
  const user = requireAuth(req, res);
  if (!user) return;

  const { guildId } = req.params;

  if (!(await canAccessGuild(user.id, guildId))) {
    res.status(403).json({ error: "Not authorized" });
    return;
  }

  const client = await pool.connect();
  try {
    const { rows } = await client.query(
      "SELECT config FROM guild_configs WHERE guild_id = $1",
      [BigInt(guildId)]
    );

    const yaml = rows[0]?.config || getDefaultYaml();
    res.json({ guildId, yaml, updatedAt: null });
  } finally {
    client.release();
  }
});

// PUT /api/guilds/:guildId/config
router.put("/:guildId/config", async (req: Request, res: Response) => {
  const user = requireAuth(req, res);
  if (!user) return;

  const { guildId } = req.params;
  const { yaml } = req.body as { yaml: string };

  if (!yaml || typeof yaml !== "string") {
    res.status(400).json({ error: "yaml is required" });
    return;
  }

  if (!(await canAccessGuild(user.id, guildId))) {
    res.status(403).json({ error: "Not authorized" });
    return;
  }

  const client = await pool.connect();
  try {
    await client.query(
      "INSERT INTO guild_configs (guild_id, config) VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET config = $2",
      [BigInt(guildId), yaml]
    );
    res.json({ guildId, yaml, updatedAt: new Date().toISOString() });
  } finally {
    client.release();
  }
});

// DELETE /api/guilds/:guildId/config
router.delete("/:guildId/config", async (req: Request, res: Response) => {
  const user = requireAuth(req, res);
  if (!user) return;

  const { guildId } = req.params;

  if (!(await canAccessGuild(user.id, guildId))) {
    res.status(403).json({ error: "Not authorized" });
    return;
  }

  const client = await pool.connect();
  try {
    await client.query("DELETE FROM guild_configs WHERE guild_id = $1", [BigInt(guildId)]);
    res.json({ success: true });
  } finally {
    client.release();
  }
});

function getDefaultYaml(): string {
  return `# Bot Configuration
# Edit this YAML to configure your server

levels:
  users: {}
  roles: {}
  commands: {}

tags: {}

plugins:
  moderation:
    enabled: true
    mute_role: null
    dm_on_action: true
    mute_remove_roles: false
    ban_delete_message_days: 1

  logging:
    enabled: false
    channel: null

  automod:
    enabled: false

  welcome:
    enabled: true
    welcome:
      enabled: false
      channel: null
      message: "Welcome to {server}, {user.mention}!"
    goodbye:
      enabled: false
      channel: null
      message: "{user} has left {server}."

  command_aliases:
    config:
      aliases:
        b: ban
        k: kick
        m: mute
        w: warn
        p: purge

  preset_reasons:
    config:
      presets:
        spam: "Spamming in chat"
        ads: "Advertising without permission"
        toxic: "Toxic behavior"
`;
}

export default router;

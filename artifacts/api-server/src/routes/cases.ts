import { Router, Request, Response } from "express";
import { pool } from "@workspace/db";

const router = Router({ mergeParams: true });

function requireAuth(req: Request, res: Response): any | null {
  const user = (req.session as any).user;
  if (!user) {
    res.status(401).json({ error: "Not authenticated" });
    return null;
  }
  return user;
}

async function canAccessGuild(userId: string, guildId: string): Promise<boolean> {
  const client = await pool.connect();
  try {
    const whitelistRow = await client.query(
      "SELECT guild_owner_id FROM whitelisted_guilds WHERE guild_id = $1",
      [BigInt(guildId)]
    );
    if (whitelistRow.rows.length === 0) return false;

    const ownerIdEnv = process.env.BOT_OWNER_ID;
    if (ownerIdEnv && userId === ownerIdEnv) return true;

    if (whitelistRow.rows[0].guild_owner_id?.toString() === userId) return true;

    const accessRow = await client.query(
      "SELECT 1 FROM config_access WHERE guild_id = $1 AND user_id = $2",
      [BigInt(guildId), BigInt(userId)]
    );
    return accessRow.rows.length > 0;
  } finally {
    client.release();
  }
}

// GET /api/guilds/:guildId/cases
// Query params: limit, offset, action, user_id
router.get("/", async (req: Request, res: Response) => {
  const user = requireAuth(req, res);
  if (!user) return;

  const { guildId } = req.params;

  if (!(await canAccessGuild(user.id, guildId))) {
    res.status(403).json({ error: "Not authorized" });
    return;
  }

  const limit = Math.min(Math.max(parseInt(req.query.limit as string) || 50, 1), 100);
  const offset = Math.max(parseInt(req.query.offset as string) || 0, 0);
  const actionFilter = (req.query.action as string) || null;
  const userIdFilter = (req.query.user_id as string) || null;

  const client = await pool.connect();
  try {
    const conditions: string[] = ["guild_id = $1"];
    const params: any[] = [BigInt(guildId)];
    let idx = 2;

    if (actionFilter && actionFilter !== "all") {
      conditions.push(`action = $${idx++}`);
      params.push(actionFilter);
    }

    if (userIdFilter) {
      try {
        conditions.push(`user_id = $${idx++}`);
        params.push(BigInt(userIdFilter));
      } catch {
        // Invalid user ID, ignore
      }
    }

    const where = conditions.join(" AND ");

    const countResult = await client.query(
      `SELECT COUNT(*) FROM cases WHERE ${where}`,
      params
    );
    const total = parseInt(countResult.rows[0].count, 10);

    const rows = await client.query(
      `SELECT id, user_id, moderator_id, action, reason, duration, expires_at, created_at
       FROM cases WHERE ${where}
       ORDER BY id DESC
       LIMIT $${idx++} OFFSET $${idx++}`,
      [...params, limit, offset]
    );

    const cases = rows.rows.map((r) => ({
      id: r.id,
      userId: r.user_id.toString(),
      moderatorId: r.moderator_id.toString(),
      action: r.action,
      reason: r.reason ?? null,
      duration: r.duration ?? null,
      expiresAt: r.expires_at ?? null,
      createdAt: r.created_at,
    }));

    res.json({ cases, total, limit, offset });
  } finally {
    client.release();
  }
});

export default router;

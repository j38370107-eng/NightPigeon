from datetime import datetime, timezone, timedelta

import discord
from discord.ext import commands
from discord.ext import tasks

from message_formatter import format_template, send_dm


class DurationRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._check_duration_roles.start()
        self._check_warnings.start()

    def cog_unload(self):
        self._check_duration_roles.cancel()
        self._check_warnings.cancel()

    def _cfg(self, config):
        return config.get("plugins", {}).get("duration_roles", {})

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        added = set(after.roles) - set(before.roles)
        if not added:
            return

        config = await self.bot.config_loader.get_config(after.guild.id)
        cfg = self._cfg(config)
        if not cfg.get("enabled"):
            return

        for role in added:
            for dr in cfg.get("roles", []):
                if dr.get("role") and int(dr["role"]) == role.id:
                    duration_days = dr.get("duration_days", 30)
                    expires = datetime.now(timezone.utc) + timedelta(days=duration_days)
                    async with self.bot.pool.acquire() as conn:
                        await conn.execute(
                            "INSERT INTO duration_role_assignments (guild_id, user_id, role_id, expires_at) VALUES ($1,$2,$3,$4) ON CONFLICT DO NOTHING",
                            after.guild.id, after.id, role.id, expires
                        )

    @tasks.loop(minutes=1)
    async def _check_duration_roles(self):
        await self.bot.wait_until_ready()
        now = datetime.now(timezone.utc)
        async with self.bot.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM duration_role_assignments WHERE expires_at <= $1", now)
            for row in rows:
                guild = self.bot.get_guild(row["guild_id"])
                if not guild:
                    continue
                member = guild.get_member(row["user_id"])
                role = guild.get_role(row["role_id"])
                if not member or not role:
                    continue
                config = await self.bot.config_loader.get_config(guild.id)
                cfg = self._cfg(config)
                msgs = cfg.get("messages", {})
                dr_config = next((dr for dr in cfg.get("roles", []) if dr.get("role") and int(dr["role"]) == role.id), {})
                on_expiry = dr_config.get("on_expiry", "remove")
                replace_with_id = dr_config.get("replace_with")

                try:
                    await member.remove_roles(role, reason="Duration role expired")
                    if on_expiry == "replace" and replace_with_id:
                        replace_role = guild.get_role(int(replace_with_id))
                        if replace_role:
                            await member.add_roles(replace_role, reason="Duration role replacement")
                            if dr_config.get("dm_on_removal"):
                                await send_dm(member, msgs.get("role_replaced_dm", "Your {trigger} role in {server} has been replaced with {reason}"),
                                              user=member, server=guild, trigger=role.name, reason=replace_role.name)
                    elif dr_config.get("dm_on_removal"):
                        await send_dm(member, msgs.get("role_expired_dm", "Your {trigger} role in {server} has expired"),
                                      user=member, server=guild, trigger=role.name)
                except Exception:
                    pass

            if rows:
                ids = [(r["guild_id"], r["user_id"], r["role_id"]) for r in rows]
                await conn.executemany("DELETE FROM duration_role_assignments WHERE guild_id=$1 AND user_id=$2 AND role_id=$3", ids)

    @tasks.loop(hours=12)
    async def _check_warnings(self):
        await self.bot.wait_until_ready()
        now = datetime.now(timezone.utc)
        async with self.bot.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM duration_role_assignments WHERE expires_at > $1", now)
        for row in rows:
            guild = self.bot.get_guild(row["guild_id"])
            if not guild:
                continue
            member = guild.get_member(row["user_id"])
            role = guild.get_role(row["role_id"])
            if not member or not role:
                continue
            config = await self.bot.config_loader.get_config(guild.id)
            cfg = self._cfg(config)
            dr_config = next((dr for dr in cfg.get("roles", []) if dr.get("role") and int(dr["role"]) == role.id), {})
            warn_days = dr_config.get("dm_warning_days", 3)
            days_left = (row["expires_at"].replace(tzinfo=timezone.utc) - now).days
            if days_left == warn_days:
                msgs = cfg.get("messages", {})
                await send_dm(member, msgs.get("role_expiry_warning_dm", "Your {trigger} role in {server} expires in {count} days"),
                              user=member, server=guild, trigger=role.name, count=str(days_left))


async def setup(bot):
    await bot.add_cog(DurationRoles(bot))

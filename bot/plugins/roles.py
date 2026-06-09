from datetime import datetime, timezone

import discord
from discord.ext import commands
from discord.ext import tasks

from duration_parser import parse_duration
from message_formatter import format_template, send_dm


class Roles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._expire_temproles.start()

    def cog_unload(self):
        self._expire_temproles.cancel()

    def _cfg(self, config):
        return config.get("plugins", {}).get("roles", {})

    def _check(self, config, member, cmd):
        lvl = self.bot.get_cog("Levels")
        return (not lvl) or lvl.has_level(config, member, cmd)

    @commands.command(name="addrole")
    async def addrole_cmd(self, ctx, member: discord.Member, role: discord.Role, *, reason: str = None):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "addrole"):
            return
        cfg = self._cfg(config)
        msgs = cfg.get("messages", {})
        if role >= ctx.guild.me.top_role:
            await ctx.send(msgs.get("error_role_hierarchy", "That role is above my highest role"))
            return
        await member.add_roles(role, reason=reason or "No reason")
        await ctx.send(format_template(msgs.get("addrole_success", "{user} has been given {trigger} | Reason: {reason}"),
                                       user=member, trigger=role.name, reason=reason or "No reason"))

    @commands.command(name="removerole")
    async def removerole_cmd(self, ctx, member: discord.Member, role: discord.Role, *, reason: str = None):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "removerole"):
            return
        cfg = self._cfg(config)
        msgs = cfg.get("messages", {})
        await member.remove_roles(role, reason=reason or "No reason")
        await ctx.send(format_template(msgs.get("removerole_success", "{trigger} has been removed from {user} | Reason: {reason}"),
                                       user=member, trigger=role.name, reason=reason or "No reason"))

    @commands.command(name="temprole")
    async def temprole_cmd(self, ctx, member: discord.Member, role: discord.Role, duration: str = "1d", *, reason: str = None):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "temprole"):
            return
        cfg = self._cfg(config)
        msgs = cfg.get("messages", {})
        td, dur_str, _ = parse_duration(duration)
        if not td:
            await ctx.send("Invalid duration")
            return
        expires = datetime.now(timezone.utc) + td
        await member.add_roles(role, reason=reason or "Temp role")
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO temp_roles (guild_id, user_id, role_id, expires_at) VALUES ($1,$2,$3,$4) ON CONFLICT DO NOTHING",
                ctx.guild.id, member.id, role.id, expires
            )
        await ctx.send(format_template(msgs.get("temprole_success", "{user} has been given {trigger} | Duration: {duration} | Expires: {expires_at}"),
                                       user=member, trigger=role.name, duration=dur_str, expires_at=str(expires.strftime("%Y-%m-%d %H:%M UTC"))))
        if cfg.get("dm_on_action"):
            await send_dm(member, msgs.get("temprole_dm", "You have been given {trigger} in {server} for: {reason} | Duration: {duration}"),
                          user=member, server=ctx.guild, trigger=role.name, reason=reason or "No reason", duration=dur_str)

    @commands.command(name="temproles")
    async def temproles_cmd(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        async with self.bot.pool.acquire() as conn:
            rows = await conn.fetch("SELECT role_id, expires_at FROM temp_roles WHERE guild_id=$1 AND user_id=$2", ctx.guild.id, target.id)
        if not rows:
            config = await self.bot.config_loader.get_config(ctx.guild.id)
            await ctx.send(config.get("plugins", {}).get("roles", {}).get("messages", {}).get("temprole_list_empty", "No active temp roles"))
            return
        lines = [f"<@&{r['role_id']}> — expires <t:{int(r['expires_at'].timestamp())}:R>" for r in rows]
        await ctx.send(f"**Temp roles for {target}:**\n" + "\n".join(lines))

    @tasks.loop(seconds=30)
    async def _expire_temproles(self):
        await self.bot.wait_until_ready()
        now = datetime.now(timezone.utc)
        async with self.bot.pool.acquire() as conn:
            rows = await conn.fetch("SELECT guild_id, user_id, role_id FROM temp_roles WHERE expires_at <= $1", now)
            for row in rows:
                guild = self.bot.get_guild(row["guild_id"])
                if not guild:
                    continue
                member = guild.get_member(row["user_id"])
                role = guild.get_role(row["role_id"])
                if member and role:
                    try:
                        await member.remove_roles(role, reason="Temp role expired")
                    except Exception:
                        pass
            if rows:
                ids = [(r["guild_id"], r["user_id"], r["role_id"]) for r in rows]
                await conn.executemany("DELETE FROM temp_roles WHERE guild_id=$1 AND user_id=$2 AND role_id=$3", ids)


async def setup(bot):
    await bot.add_cog(Roles(bot))

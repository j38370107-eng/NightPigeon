from collections import defaultdict
from datetime import datetime, timezone

import discord
from discord.ext import commands

from message_formatter import format_template


class AntiNuke(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # {guild_id: {user_id: {action_type: [timestamps]}}}
        self._counts: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    def _cfg(self, config):
        return config.get("plugins", {}).get("antinuke", {})

    def _is_whitelisted(self, cfg, member):
        if member.id == self.bot.owner_id:
            return True
        wl_roles = [int(r) for r in cfg.get("whitelist_roles", [])]
        wl_users = [int(u) for u in cfg.get("whitelist_users", [])]
        if member.id in wl_users:
            return True
        if any(r.id in wl_roles for r in getattr(member, "roles", [])):
            return True
        return False

    async def _check(self, guild: discord.Guild, executor_id: int, action: str):
        config = await self.bot.config_loader.get_config(guild.id)
        cfg = self._cfg(config)
        if not cfg.get("enabled"):
            return

        executor = guild.get_member(executor_id)
        if not executor:
            return
        if self._is_whitelisted(cfg, executor):
            return

        interval = cfg.get("interval_seconds", 10)
        threshold = cfg.get("thresholds", {}).get(action, 3)
        now = datetime.now(timezone.utc)

        bucket = self._counts[guild.id][executor_id][action]
        bucket[:] = [t for t in bucket if (now - t).total_seconds() < interval]
        bucket.append(now)

        if len(bucket) >= threshold:
            bucket.clear()
            act = cfg.get("action", "ban")
            quarantine_id = cfg.get("quarantine_role")
            reason = f"Anti-nuke: {action} threshold exceeded"

            if act == "ban":
                try:
                    await guild.ban(executor, reason=reason)
                except Exception:
                    pass
            elif act == "kick":
                try:
                    await executor.kick(reason=reason)
                except Exception:
                    pass
            elif act == "quarantine" and quarantine_id:
                role = guild.get_role(int(quarantine_id))
                if role:
                    try:
                        await executor.add_roles(role, reason=reason)
                    except Exception:
                        pass

            cases = self.bot.get_cog("Cases")
            case_id = await cases.create_case(guild.id, executor_id, self.bot.user.id, act, reason) if cases else 0

            lg = self.bot.get_cog("Logging")
            if lg:
                msg = cfg.get("messages", {}).get("triggered", "{user} exceeded the {rule} threshold and was {action}d | Case: {case_id}")
                chan = await lg._get_log_channel(guild, "antinuke")
                if chan:
                    try:
                        await chan.send(format_template(msg, user=executor, rule=action, action=act, case_id=str(case_id)))
                    except Exception:
                        pass

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
            await self._check(channel.guild, entry.user.id, "channel_delete")

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_create):
            await self._check(channel.guild, entry.user.id, "channel_create")

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
            await self._check(role.guild, entry.user.id, "role_delete")

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_create):
            await self._check(role.guild, entry.user.id, "role_create")

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
            await self._check(guild, entry.user.id, "ban")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        async for entry in member.guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
            if entry.target.id == member.id:
                await self._check(member.guild, entry.user.id, "kick")


async def setup(bot):
    await bot.add_cog(AntiNuke(bot))

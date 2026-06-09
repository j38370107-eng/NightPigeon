import asyncio
from collections import deque
from datetime import datetime, timezone, timedelta

import discord
from discord.ext import commands

from message_formatter import format_template


class AntiRaid(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # {guild_id: deque of join timestamps}
        self._joins: dict = {}
        # {guild_id: bool}
        self._raid_mode: dict = {}

    def _cfg(self, config):
        return config.get("plugins", {}).get("antiraid", {})

    @commands.command(name="raidmode")
    async def raidmode_cmd(self, ctx, mode: str):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        lvl = self.bot.get_cog("Levels")
        if lvl and not lvl.has_level(config, ctx.author, "raidmode"):
            return
        cfg = self._cfg(config)
        msgs = cfg.get("messages", {})
        if mode.lower() == "on":
            self._raid_mode[ctx.guild.id] = True
            await ctx.send("Raid mode enabled")
        elif mode.lower() == "off":
            self._raid_mode[ctx.guild.id] = False
            await ctx.send(msgs.get("raid_ended", "Raid mode ended"))

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        config = await self.bot.config_loader.get_config(member.guild.id)
        cfg = self._cfg(config)
        if not cfg.get("enabled"):
            return

        gid = member.guild.id
        if gid not in self._joins:
            self._joins[gid] = deque()

        now = datetime.now(timezone.utc)
        interval = cfg.get("join_interval_seconds", 10)
        self._joins[gid] = deque(t for t in self._joins[gid] if (now - t).total_seconds() < interval)
        self._joins[gid].append(now)

        # Check account age
        min_age = cfg.get("account_age_min_days", 7)
        age = (now - member.created_at).days
        if age < min_age:
            msgs = cfg.get("messages", {})
            lg = self.bot.get_cog("Logging")
            if lg:
                chan = await lg._get_log_channel(member.guild, "antiraid")
                if chan:
                    try:
                        await chan.send(format_template(msgs.get("new_account_flagged", "New account | {user} | Age: {trigger} days"),
                                                        user=member, trigger=str(age)))
                    except Exception:
                        pass

        # Check raid threshold
        threshold = cfg.get("join_threshold", 10)
        if len(self._joins[gid]) >= threshold and not self._raid_mode.get(gid):
            self._raid_mode[gid] = True
            await self._handle_raid(member.guild, config, list(self._joins[gid]))

    async def _handle_raid(self, guild: discord.Guild, config: dict, join_times: list):
        cfg = self._cfg(config)
        msgs = cfg.get("messages", {})
        action = cfg.get("action", "kick")
        lockdown_channels = [int(c) for c in cfg.get("lockdown_channels", [])]

        recent_members = []
        now = datetime.now(timezone.utc)
        interval = cfg.get("join_interval_seconds", 10)
        for member in guild.members:
            if member.joined_at and (now - member.joined_at.replace(tzinfo=timezone.utc)).total_seconds() < interval:
                recent_members.append(member)

        ok = 0
        for member in recent_members:
            try:
                if action == "kick":
                    await member.kick(reason="Anti-raid")
                elif action == "ban":
                    await guild.ban(member, reason="Anti-raid")
                ok += 1
            except Exception:
                pass

        # Lock channels
        for cid in lockdown_channels:
            chan = guild.get_channel(cid)
            if chan:
                overwrite = chan.overwrites_for(guild.default_role)
                overwrite.send_messages = False
                try:
                    await chan.set_permissions(guild.default_role, overwrite=overwrite)
                except Exception:
                    pass

        # Log
        lg = self.bot.get_cog("Logging")
        if lg:
            log_chan = await lg._get_log_channel(guild, "antiraid")
            if log_chan:
                try:
                    await log_chan.send(format_template(
                        msgs.get("raid_detected", "Raid detected | {count} joins | Action: {action} | Affected: {success_count}"),
                        count=str(len(join_times)), action=action,
                        success_count=str(ok), duration=f"{cfg.get('join_interval_seconds', 10)}s"
                    ))
                except Exception:
                    pass

        # Auto-unlock
        auto_unlock = cfg.get("auto_unlock_minutes", 10)
        if auto_unlock and lockdown_channels:
            await asyncio.sleep(auto_unlock * 60)
            for cid in lockdown_channels:
                chan = guild.get_channel(cid)
                if chan:
                    overwrite = chan.overwrites_for(guild.default_role)
                    overwrite.send_messages = None
                    try:
                        await chan.set_permissions(guild.default_role, overwrite=overwrite)
                    except Exception:
                        pass
            self._raid_mode[guild.id] = False
            if lg:
                log_chan = await lg._get_log_channel(guild, "antiraid")
                if log_chan:
                    try:
                        await log_chan.send(msgs.get("raid_ended", "Raid mode ended"))
                    except Exception:
                        pass


async def setup(bot):
    await bot.add_cog(AntiRaid(bot))

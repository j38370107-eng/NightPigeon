import json
from datetime import datetime, timezone

import discord
from discord.ext import commands

from message_formatter import format_template


class Lockdown(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _cfg(self, config):
        return config.get("plugins", {}).get("lockdown", {})

    def _check(self, config, member, cmd):
        lvl = self.bot.get_cog("Levels")
        return (not lvl) or lvl.has_level(config, member, cmd)

    async def _lock_channel(self, channel: discord.TextChannel, mod, reason: str, remove_send=True, remove_reactions=False, remove_threads=False):
        overwrite = channel.overwrites_for(channel.guild.default_role)
        original = {
            "send_messages": overwrite.send_messages,
            "add_reactions": overwrite.add_reactions,
            "create_public_threads": overwrite.create_public_threads,
        }
        if remove_send:
            overwrite.send_messages = False
        if remove_reactions:
            overwrite.add_reactions = False
        if remove_threads:
            overwrite.create_public_threads = False
        await channel.set_permissions(channel.guild.default_role, overwrite=overwrite)

        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO locked_channels (guild_id, channel_id, locked_by, reason, original_permissions, locked_at) VALUES ($1,$2,$3,$4,$5,$6) ON CONFLICT DO NOTHING",
                channel.guild.id, channel.id, mod.id, reason, json.dumps(original), datetime.now(timezone.utc)
            )

    async def _unlock_channel(self, channel: discord.TextChannel, mod, reason: str):
        async with self.bot.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT original_permissions FROM locked_channels WHERE guild_id=$1 AND channel_id=$2",
                                      channel.guild.id, channel.id)
            await conn.execute("DELETE FROM locked_channels WHERE guild_id=$1 AND channel_id=$2", channel.guild.id, channel.id)

        overwrite = channel.overwrites_for(channel.guild.default_role)
        if row and row["original_permissions"]:
            original = json.loads(row["original_permissions"])
            overwrite.send_messages = original.get("send_messages")
            overwrite.add_reactions = original.get("add_reactions")
            overwrite.create_public_threads = original.get("create_public_threads")
        else:
            overwrite.send_messages = None
        await channel.set_permissions(channel.guild.default_role, overwrite=overwrite)

    @commands.group(name="lockdown", invoke_without_command=True)
    async def lockdown_cmd(self, ctx, target=None, *, reason: str = None):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "lockdown"):
            return
        cfg = self._cfg(config)
        msgs = cfg.get("messages", {})
        reason = reason or "No reason provided"

        if target == "-server":
            channels_to_lock = [int(c) for c in cfg.get("server_lockdown_channels", [])] or [ch.id for ch in ctx.guild.text_channels]
            locked = 0
            for cid in channels_to_lock:
                ch = ctx.guild.get_channel(cid)
                if ch:
                    await self._lock_channel(ch, ctx.author, reason)
                    locked += 1
            await ctx.send(format_template(msgs.get("lockdown_server_start", "Server lockdown activated | {count} channels locked"),
                                           count=str(locked), reason=reason, mod=ctx.author))
            return

        # Check if it's a preset
        presets = cfg.get("presets", {})
        if target and target in presets:
            preset = presets[target]
            channels_to_lock = [int(c) for c in preset.get("channels", [])]
            locked = 0
            for cid in channels_to_lock:
                ch = ctx.guild.get_channel(cid)
                if ch:
                    await self._lock_channel(ch, ctx.author, preset.get("reason", reason),
                                             remove_send=preset.get("remove_send", True),
                                             remove_reactions=preset.get("remove_reactions", False),
                                             remove_threads=preset.get("remove_threads", False))
                    locked += 1
            await ctx.send(f"Preset **{target}** applied: {locked} channels locked")
            return

        # Lock specific channel or current
        channel = ctx.channel
        if target:
            try:
                channel = await commands.TextChannelConverter().convert(ctx, target)
            except Exception:
                channel = ctx.channel

        async with self.bot.pool.acquire() as conn:
            existing = await conn.fetchrow("SELECT 1 FROM locked_channels WHERE guild_id=$1 AND channel_id=$2", ctx.guild.id, channel.id)
        if existing:
            await ctx.send(format_template(msgs.get("already_locked", "{channel.mention} is already locked"), channel=channel))
            return

        await self._lock_channel(channel, ctx.author, reason)
        await ctx.send(format_template(msgs.get("lockdown_start", "{channel.mention} has been locked | Reason: {reason}"),
                                       channel=channel, reason=reason, mod=ctx.author))
        notice = msgs.get("lockdown_channel_notice")
        if notice:
            try:
                await channel.send(format_template(notice, channel=channel, reason=reason, mod=ctx.author))
            except Exception:
                pass

    @lockdown_cmd.command(name="list")
    async def lockdown_list(self, ctx):
        async with self.bot.pool.acquire() as conn:
            rows = await conn.fetch("SELECT channel_id, locked_at FROM locked_channels WHERE guild_id=$1", ctx.guild.id)
        if not rows:
            await ctx.send("No locked channels")
            return
        lines = [f"<#{r['channel_id']}> — locked {r['locked_at'].strftime('%Y-%m-%d %H:%M UTC')}" for r in rows]
        await ctx.send("**Locked Channels:**\n" + "\n".join(lines))

    @commands.command(name="unlock")
    async def unlock_cmd(self, ctx, target=None, *, reason: str = None):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "unlock"):
            return
        cfg = self._cfg(config)
        msgs = cfg.get("messages", {})
        reason = reason or "No reason provided"

        if target == "-server":
            async with self.bot.pool.acquire() as conn:
                rows = await conn.fetch("SELECT channel_id FROM locked_channels WHERE guild_id=$1", ctx.guild.id)
            unlocked = 0
            for row in rows:
                ch = ctx.guild.get_channel(row["channel_id"])
                if ch:
                    await self._unlock_channel(ch, ctx.author, reason)
                    unlocked += 1
            await ctx.send(format_template(msgs.get("lockdown_server_end", "Server lockdown lifted | {count} channels unlocked"), count=str(unlocked)))
            return

        channel = ctx.channel
        if target:
            try:
                channel = await commands.TextChannelConverter().convert(ctx, target)
            except Exception:
                channel = ctx.channel

        await self._unlock_channel(channel, ctx.author, reason)
        await ctx.send(format_template(msgs.get("lockdown_end", "{channel.mention} has been unlocked"), channel=channel))
        notice = msgs.get("unlock_channel_notice")
        if notice:
            try:
                await channel.send(format_template(notice, channel=channel, mod=ctx.author))
            except Exception:
                pass


async def setup(bot):
    await bot.add_cog(Lockdown(bot))

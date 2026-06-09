import asyncio
from datetime import datetime, timezone, timedelta

import discord
from discord.ext import commands
from discord.ext import tasks


class AutoClean(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._autoclean_loop.start()

    def cog_unload(self):
        self._autoclean_loop.cancel()

    def _cfg(self, config):
        return config.get("plugins", {}).get("autoclean", {})

    async def _run_clean(self, guild: discord.Guild, channel: discord.TextChannel, rule: dict):
        mode = rule.get("mode", "interval")
        ignore_pinned = rule.get("ignore_pinned", True)
        ignore_bots = rule.get("ignore_bots", False)
        ignore_roles = [int(r) for r in (rule.get("ignore_roles") or [])]
        delay = rule.get("delay_seconds", 0)

        def should_delete(msg: discord.Message):
            if ignore_pinned and msg.pinned:
                return False
            if ignore_bots and msg.author.bot:
                return False
            if hasattr(msg.author, "roles") and any(r.id in ignore_roles for r in msg.author.roles):
                return False
            return True

        deleted = 0
        now = datetime.now(timezone.utc)

        try:
            if mode == "keepx":
                keep = rule.get("keep_count", 10)
                msgs = [m async for m in channel.history(limit=keep + 200) if should_delete(m)]
                to_delete = msgs[keep:]
            elif mode == "maxage":
                max_age = rule.get("max_age_seconds", 3600)
                cutoff = now - timedelta(seconds=max_age)
                to_delete = [m async for m in channel.history(limit=200) if should_delete(m) and m.created_at.replace(tzinfo=timezone.utc) < cutoff]
            else:  # interval
                to_delete = [m async for m in channel.history(limit=200) if should_delete(m)]

            # Bulk delete for messages under 14 days
            recent = [m for m in to_delete if (now - m.created_at.replace(tzinfo=timezone.utc)).days < 14]
            old = [m for m in to_delete if (now - m.created_at.replace(tzinfo=timezone.utc)).days >= 14]

            if recent:
                for chunk in [recent[i:i+100] for i in range(0, len(recent), 100)]:
                    if delay:
                        await asyncio.sleep(delay)
                    try:
                        await channel.delete_messages(chunk)
                        deleted += len(chunk)
                    except Exception:
                        pass

            for msg in old:
                if delay:
                    await asyncio.sleep(delay)
                try:
                    await msg.delete()
                    deleted += 1
                except Exception:
                    pass

        except Exception:
            pass

        return deleted

    @tasks.loop(minutes=1)
    async def _autoclean_loop(self):
        await self.bot.wait_until_ready()
        now = datetime.now(timezone.utc)

        async with self.bot.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM autoclean_channels WHERE enabled=true AND (last_run IS NULL OR last_run + INTERVAL '1 second' * interval_seconds <= $1)", now)
            for row in rows:
                guild = self.bot.get_guild(row["guild_id"])
                if not guild:
                    continue
                channel = guild.get_channel(row["channel_id"])
                if not channel:
                    continue
                rule = dict(row)
                await self._run_clean(guild, channel, rule)
                await conn.execute("UPDATE autoclean_channels SET last_run=$1 WHERE id=$2", now, row["id"])

        # Also run YAML rules
        for guild in self.bot.guilds:
            try:
                config = await self.bot.config_loader.get_config(guild.id)
                cfg = self._cfg(config)
                if not cfg.get("enabled"):
                    continue
                for rule in cfg.get("channels", []):
                    if not rule.get("enabled", True) or not rule.get("channel"):
                        continue
                    channel = guild.get_channel(int(rule["channel"]))
                    if not channel:
                        continue
                    interval = rule.get("interval_seconds", 3600)
                    key = f"autoclean_{guild.id}_{channel.id}"
                    last = getattr(self, f"_last_{key}", None)
                    if last and (now - last).total_seconds() < interval:
                        continue
                    setattr(self, f"_last_{key}", now)
                    await self._run_clean(guild, channel, rule)
            except Exception:
                pass

    @commands.group(name="autoclean", invoke_without_command=True)
    async def autoclean_group(self, ctx):
        await ctx.send("Usage: `!autoclean add/remove/list/enable/disable/now`")

    @autoclean_group.command(name="add")
    async def ac_add(self, ctx, channel: discord.TextChannel, mode: str, value: str):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        lvl = self.bot.get_cog("Levels")
        if lvl and not lvl.has_level(config, ctx.author, "autoclean"):
            return
        kwargs = {"guild_id": ctx.guild.id, "channel_id": channel.id, "mode": mode}
        if mode == "interval":
            kwargs["interval_seconds"] = int(value)
        elif mode == "keepx":
            kwargs["keep_count"] = int(value)
        elif mode == "maxage":
            kwargs["max_age_seconds"] = int(value)
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO autoclean_channels (guild_id, channel_id, mode, interval_seconds, keep_count, max_age_seconds) VALUES ($1,$2,$3,$4,$5,$6) ON CONFLICT DO NOTHING",
                ctx.guild.id, channel.id, mode,
                kwargs.get("interval_seconds", 3600), kwargs.get("keep_count", 10), kwargs.get("max_age_seconds", 86400)
            )
        msgs = self._cfg(config).get("messages", {})
        await ctx.send(msgs.get("autoclean_added", "Autoclean added for {channel.mention} | Mode: {trigger}").replace("{channel.mention}", channel.mention).replace("{trigger}", mode))

    @autoclean_group.command(name="remove")
    async def ac_remove(self, ctx, channel: discord.TextChannel):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        lvl = self.bot.get_cog("Levels")
        if lvl and not lvl.has_level(config, ctx.author, "autoclean"):
            return
        async with self.bot.pool.acquire() as conn:
            await conn.execute("DELETE FROM autoclean_channels WHERE guild_id=$1 AND channel_id=$2", ctx.guild.id, channel.id)
        msgs = self._cfg(config).get("messages", {})
        await ctx.send(msgs.get("autoclean_removed", "Autoclean removed").replace("{channel.mention}", channel.mention))

    @autoclean_group.command(name="list")
    async def ac_list(self, ctx):
        async with self.bot.pool.acquire() as conn:
            rows = await conn.fetch("SELECT channel_id, mode, enabled FROM autoclean_channels WHERE guild_id=$1", ctx.guild.id)
        if not rows:
            await ctx.send("No autoclean rules")
            return
        lines = [f"<#{r['channel_id']}> — {r['mode']} {'✓' if r['enabled'] else '✗'}" for r in rows]
        await ctx.send("**Autoclean Rules:**\n" + "\n".join(lines))

    @autoclean_group.command(name="now")
    async def ac_now(self, ctx, channel: discord.TextChannel):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        lvl = self.bot.get_cog("Levels")
        if lvl and not lvl.has_level(config, ctx.author, "autoclean"):
            return
        deleted = await self._run_clean(ctx.guild, channel, {"mode": "interval"})
        msgs = self._cfg(config).get("messages", {})
        await ctx.send(msgs.get("autoclean_ran", "Autoclean ran | Deleted: {count} messages").replace("{count}", str(deleted)).replace("{channel.mention}", channel.mention))


async def setup(bot):
    await bot.add_cog(AutoClean(bot))

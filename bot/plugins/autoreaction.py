import re
from datetime import datetime, timezone

import discord
from discord.ext import commands


class AutoReaction(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._cooldowns: dict = {}

    def _cfg(self, config):
        return config.get("plugins", {}).get("autoreaction", {})

    def _matches(self, content: str, trigger: str, trigger_type: str, match_case: bool) -> bool:
        if not match_case:
            content = content.lower()
            trigger = trigger.lower()
        if trigger_type == "exact":
            return content == trigger
        elif trigger_type == "startswith":
            return content.startswith(trigger)
        elif trigger_type == "endswith":
            return content.endswith(trigger)
        elif trigger_type == "regex":
            try:
                return bool(re.search(trigger, content))
            except Exception:
                return False
        else:
            return trigger in content

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        config = await self.bot.config_loader.get_config(message.guild.id)
        cfg = self._cfg(config)
        if not cfg.get("enabled"):
            return

        all_rules = list(cfg.get("reactions", []))
        async with self.bot.pool.acquire() as conn:
            db_rows = await conn.fetch("SELECT * FROM auto_reactions WHERE guild_id=$1 AND enabled=true", message.guild.id)
        for row in db_rows:
            all_rules.append(dict(row))

        for rule in all_rules:
            trigger = rule.get("trigger", "")
            if not trigger:
                continue
            if not self._matches(message.content, trigger, rule.get("trigger_type", "contains"), rule.get("match_case", False)):
                continue

            ignore_channels = [int(c) for c in (rule.get("ignore_channels") or [])]
            if message.channel.id in ignore_channels:
                continue

            rule_id = rule.get("id") or trigger
            key = (message.guild.id, rule_id)
            cooldown = rule.get("cooldown_seconds", 0)
            if cooldown and key in self._cooldowns:
                elapsed = (datetime.now(timezone.utc) - self._cooldowns[key]).total_seconds()
                if elapsed < cooldown:
                    continue
            self._cooldowns[key] = datetime.now(timezone.utc)

            emojis = rule.get("emojis") or []
            for emoji in emojis:
                try:
                    await message.add_reaction(emoji)
                except Exception:
                    pass

    @commands.group(name="autoreaction", invoke_without_command=True)
    async def autoreaction_group(self, ctx):
        await ctx.send("Usage: `!autoreaction add/remove/list/enable/disable`")

    @autoreaction_group.command(name="add")
    async def ar_add(self, ctx, trigger_type: str, trigger: str, *emojis):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        lvl = self.bot.get_cog("Levels")
        if lvl and not lvl.has_level(config, ctx.author, "autoreaction"):
            return
        async with self.bot.pool.acquire() as conn:
            row = await conn.fetchrow(
                "INSERT INTO auto_reactions (guild_id, trigger, emojis, trigger_type) VALUES ($1,$2,$3,$4) RETURNING id",
                ctx.guild.id, trigger, list(emojis), trigger_type
            )
        await ctx.send(f"Auto reaction #{row['id']} added")

    @autoreaction_group.command(name="remove")
    async def ar_remove(self, ctx, rule_id: int):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        lvl = self.bot.get_cog("Levels")
        if lvl and not lvl.has_level(config, ctx.author, "autoreaction"):
            return
        async with self.bot.pool.acquire() as conn:
            await conn.execute("DELETE FROM auto_reactions WHERE id=$1 AND guild_id=$2", rule_id, ctx.guild.id)
        await ctx.send(f"Auto reaction #{rule_id} removed")

    @autoreaction_group.command(name="list")
    async def ar_list(self, ctx):
        async with self.bot.pool.acquire() as conn:
            rows = await conn.fetch("SELECT id, trigger, emojis, enabled FROM auto_reactions WHERE guild_id=$1 ORDER BY id", ctx.guild.id)
        if not rows:
            await ctx.send("No auto reactions set up")
            return
        lines = [f"`{r['id']}` {'✓' if r['enabled'] else '✗'} — `{r['trigger']}` → {' '.join(r['emojis'] or [])}" for r in rows]
        await ctx.send("**Auto Reactions:**\n" + "\n".join(lines[:20]))


async def setup(bot):
    await bot.add_cog(AutoReaction(bot))

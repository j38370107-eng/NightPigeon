import re
import asyncio
from datetime import datetime, timezone

import discord
from discord.ext import commands


class AutoReply(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._cooldowns: dict = {}  # {(guild_id, rule_id): datetime}

    def _cfg(self, config):
        return config.get("plugins", {}).get("autoreply", {})

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
        else:  # contains
            return trigger in content

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        config = await self.bot.config_loader.get_config(message.guild.id)
        cfg = self._cfg(config)
        if not cfg.get("enabled"):
            return

        all_rules = list(cfg.get("replies", []))

        # DB rules
        async with self.bot.pool.acquire() as conn:
            db_rows = await conn.fetch("SELECT * FROM auto_replies WHERE guild_id=$1 AND enabled=true", message.guild.id)
        for row in db_rows:
            all_rules.append(dict(row))

        for rule in all_rules:
            trigger = rule.get("trigger", "")
            if not trigger:
                continue
            trigger_type = rule.get("trigger_type", "contains")
            match_case = rule.get("match_case", False)
            if not self._matches(message.content, trigger, trigger_type, match_case):
                continue

            # Check ignore/only
            ignore_roles = [int(r) for r in (rule.get("ignore_roles") or [])]
            ignore_channels = [int(c) for c in (rule.get("ignore_channels") or [])]
            only_channels = [int(c) for c in (rule.get("only_channels") or [])]
            only_roles = [int(r) for r in (rule.get("only_roles") or [])]

            if message.channel.id in ignore_channels:
                continue
            if any(r.id in ignore_roles for r in message.author.roles):
                continue
            if only_channels and message.channel.id not in only_channels:
                continue
            if only_roles and not any(r.id in only_roles for r in message.author.roles):
                continue

            # Cooldown
            rule_id = rule.get("id") or trigger
            key = (message.guild.id, rule_id)
            cooldown = rule.get("cooldown_seconds", 0)
            if cooldown and key in self._cooldowns:
                elapsed = (datetime.now(timezone.utc) - self._cooldowns[key]).total_seconds()
                if elapsed < cooldown:
                    continue
            self._cooldowns[key] = datetime.now(timezone.utc)

            response = rule.get("response", "")
            reply_type = rule.get("reply_type", "message")
            delete_trigger = rule.get("delete_trigger", False)
            delete_after = rule.get("delete_after")

            if delete_trigger:
                try:
                    await message.delete()
                except Exception:
                    pass

            try:
                if reply_type == "reply":
                    sent = await message.reply(response)
                elif reply_type == "dm":
                    try:
                        await message.author.send(response)
                    except Exception:
                        pass
                    sent = None
                else:
                    sent = await message.channel.send(response)

                if delete_after and sent:
                    await asyncio.sleep(int(delete_after))
                    try:
                        await sent.delete()
                    except Exception:
                        pass
            except Exception:
                pass
            break  # Only first matching rule

    @commands.group(name="autoreply", invoke_without_command=True)
    async def autoreply_group(self, ctx):
        await ctx.send("Usage: `!autoreply add/remove/list/enable/disable/edit`")

    @autoreply_group.command(name="add")
    async def ar_add(self, ctx, trigger_type: str, trigger: str, *, response: str):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        lvl = self.bot.get_cog("Levels")
        if lvl and not lvl.has_level(config, ctx.author, "autoreply"):
            return
        async with self.bot.pool.acquire() as conn:
            row = await conn.fetchrow(
                "INSERT INTO auto_replies (guild_id, trigger, response, trigger_type) VALUES ($1,$2,$3,$4) RETURNING id",
                ctx.guild.id, trigger, response, trigger_type
            )
        msgs = self._cfg(config).get("messages", {})
        await ctx.send(msgs.get("autoreply_added", "Auto reply added").replace("{trigger}", str(row["id"])))

    @autoreply_group.command(name="remove")
    async def ar_remove(self, ctx, rule_id: int):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        lvl = self.bot.get_cog("Levels")
        if lvl and not lvl.has_level(config, ctx.author, "autoreply"):
            return
        async with self.bot.pool.acquire() as conn:
            await conn.execute("DELETE FROM auto_replies WHERE id=$1 AND guild_id=$2", rule_id, ctx.guild.id)
        msgs = self._cfg(config).get("messages", {})
        await ctx.send(msgs.get("autoreply_removed", "Auto reply removed"))

    @autoreply_group.command(name="list")
    async def ar_list(self, ctx):
        async with self.bot.pool.acquire() as conn:
            rows = await conn.fetch("SELECT id, trigger, trigger_type, enabled FROM auto_replies WHERE guild_id=$1 ORDER BY id", ctx.guild.id)
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        yaml_rules = self._cfg(config).get("replies", [])
        if not rows and not yaml_rules:
            msgs = self._cfg(config).get("messages", {})
            await ctx.send(msgs.get("autoreply_list_empty", "No auto replies set up"))
            return
        lines = []
        for r in yaml_rules:
            lines.append(f"[YAML] `{r.get('id', '?')}` — {r.get('trigger_type', 'contains')}: `{r.get('trigger', '')}` → {r.get('response', '')[:40]}")
        for r in rows:
            status = "✓" if r["enabled"] else "✗"
            lines.append(f"[DB] `{r['id']}` {status} — {r['trigger_type']}: `{r['trigger']}`")
        await ctx.send("**Auto Replies:**\n" + "\n".join(lines[:20]))

    @autoreply_group.command(name="enable")
    async def ar_enable(self, ctx, rule_id: int):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        lvl = self.bot.get_cog("Levels")
        if lvl and not lvl.has_level(config, ctx.author, "autoreply"):
            return
        async with self.bot.pool.acquire() as conn:
            await conn.execute("UPDATE auto_replies SET enabled=true WHERE id=$1 AND guild_id=$2", rule_id, ctx.guild.id)
        await ctx.send(f"Auto reply #{rule_id} enabled")

    @autoreply_group.command(name="disable")
    async def ar_disable(self, ctx, rule_id: int):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        lvl = self.bot.get_cog("Levels")
        if lvl and not lvl.has_level(config, ctx.author, "autoreply"):
            return
        async with self.bot.pool.acquire() as conn:
            await conn.execute("UPDATE auto_replies SET enabled=false WHERE id=$1 AND guild_id=$2", rule_id, ctx.guild.id)
        await ctx.send(f"Auto reply #{rule_id} disabled")


async def setup(bot):
    await bot.add_cog(AutoReply(bot))

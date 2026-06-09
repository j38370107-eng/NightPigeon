import asyncio
from collections import defaultdict
from datetime import datetime, timezone

import discord
from discord.ext import commands
from discord.ext import tasks

from message_formatter import format_template


class SlowmodeAuto(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # {channel_id: [timestamps]}
        self._buckets: dict = defaultdict(list)
        # {channel_id: asyncio.Task}
        self._remove_tasks: dict = {}

    def _cfg(self, config):
        return config.get("plugins", {}).get("slowmode_auto", {})

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        config = await self.bot.config_loader.get_config(message.guild.id)
        cfg = self._cfg(config)
        if not cfg.get("enabled"):
            return

        ignore_channels = [int(c) for c in cfg.get("ignore_channels", [])]
        ignore_roles = [int(r) for r in cfg.get("ignore_roles", [])]
        if message.channel.id in ignore_channels:
            return
        if any(r.id in ignore_roles for r in message.author.roles):
            return

        cid = message.channel.id
        now = datetime.now(timezone.utc)

        for rule in cfg.get("rules", []):
            channel_id = rule.get("channel")
            if channel_id and int(channel_id) != cid:
                continue

            window = rule.get("window_seconds", 5)
            self._buckets[cid] = [t for t in self._buckets[cid] if (now - t).total_seconds() < window]
            self._buckets[cid].append(now)

            if len(self._buckets[cid]) >= rule.get("messages_per_seconds", 10):
                apply = rule.get("apply_slowmode", 3)
                apply = max(rule.get("min_slowmode", 1), min(apply, rule.get("max_slowmode", 120)))

                if message.channel.slowmode_delay < apply:
                    try:
                        await message.channel.edit(slowmode_delay=apply)
                        lg = self.bot.get_cog("Logging")
                        if lg:
                            log_chan = await lg._get_log_channel(message.guild, None)
                            msgs = cfg.get("messages", {})
                            if log_chan:
                                await log_chan.send(format_template(msgs.get("slowmode_applied", "Slowmode of {count}s applied in {channel.mention}"),
                                                                    count=str(apply), channel=message.channel))
                    except Exception:
                        pass

                remove_after = rule.get("remove_after_seconds", 30)
                if cid in self._remove_tasks and not self._remove_tasks[cid].done():
                    self._remove_tasks[cid].cancel()
                self._remove_tasks[cid] = asyncio.get_event_loop().create_task(
                    self._remove_slowmode(message.channel, config, remove_after)
                )

    async def _remove_slowmode(self, channel: discord.TextChannel, config: dict, delay: int):
        await asyncio.sleep(delay)
        try:
            await channel.edit(slowmode_delay=0)
            lg = self.bot.get_cog("Logging")
            cfg = self._cfg(config)
            if lg:
                log_chan = await lg._get_log_channel(channel.guild, None)
                msgs = cfg.get("messages", {})
                if log_chan:
                    await log_chan.send(format_template(msgs.get("slowmode_removed", "Slowmode removed in {channel.mention}"), channel=channel))
        except Exception:
            pass


async def setup(bot):
    await bot.add_cog(SlowmodeAuto(bot))

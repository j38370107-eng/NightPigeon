import asyncio
from datetime import datetime, timezone

import discord
from discord.ext import commands
from discord.ext import tasks

from duration_parser import parse_duration
from message_formatter import format_template


class Reminders(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._check_reminders.start()

    def cog_unload(self):
        self._check_reminders.cancel()

    @commands.command(name="remind")
    async def remind_cmd(self, ctx, duration: str, *, message: str):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        cfg = config.get("plugins", {}).get("reminders", {})
        msgs = cfg.get("messages", {})

        td, dur_str, _ = parse_duration(duration)
        if not td:
            await ctx.send("Invalid duration. Use: 10m, 1h, 1d, 1w")
            return

        remind_at = datetime.now(timezone.utc) + td
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO reminders (guild_id, user_id, channel_id, message, remind_at) VALUES ($1,$2,$3,$4,$5)",
                ctx.guild.id, ctx.author.id, ctx.channel.id, message, remind_at
            )
        await ctx.send(format_template(msgs.get("reminder_set", "Reminder set for {duration} | Message: {reminder_message}"),
                                       duration=dur_str, reminder_message=message))

    @commands.command(name="reminders")
    async def reminders_list(self, ctx):
        async with self.bot.pool.acquire() as conn:
            rows = await conn.fetch("SELECT id, message, remind_at FROM reminders WHERE user_id=$1 AND guild_id=$2 ORDER BY remind_at",
                                    ctx.author.id, ctx.guild.id)
        if not rows:
            config = await self.bot.config_loader.get_config(ctx.guild.id)
            msgs = config.get("plugins", {}).get("reminders", {}).get("messages", {})
            await ctx.send(msgs.get("reminder_list_empty", "You have no active reminders"))
            return
        lines = [f"**#{r['id']}** — {r['message'][:60]} — <t:{int(r['remind_at'].timestamp())}:R>" for r in rows]
        await ctx.send("**Your Reminders:**\n" + "\n".join(lines))

    @commands.command(name="delreminder")
    async def delreminder_cmd(self, ctx, reminder_id: int):
        async with self.bot.pool.acquire() as conn:
            r = await conn.execute("DELETE FROM reminders WHERE id=$1 AND user_id=$2", reminder_id, ctx.author.id)
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        msgs = config.get("plugins", {}).get("reminders", {}).get("messages", {})
        if r == "DELETE 0":
            await ctx.send(msgs.get("reminder_not_found", "Reminder not found"))
        else:
            await ctx.send(msgs.get("reminder_deleted", "Reminder deleted"))

    @tasks.loop(seconds=30)
    async def _check_reminders(self):
        await self.bot.wait_until_ready()
        now = datetime.now(timezone.utc)
        async with self.bot.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM reminders WHERE remind_at <= $1", now)
            for row in rows:
                guild = self.bot.get_guild(row["guild_id"])
                if not guild:
                    continue
                channel = guild.get_channel(row["channel_id"])
                user = guild.get_member(row["user_id"])
                if not channel or not user:
                    continue
                config = await self.bot.config_loader.get_config(guild.id)
                msgs = config.get("plugins", {}).get("reminders", {}).get("messages", {})
                msg = msgs.get("reminder_fired", "{user.mention} Reminder: {reminder_message} | Set: {reminder_set_at}")
                try:
                    await channel.send(format_template(msg, user=user, reminder_message=row["message"],
                                                       reminder_set_at=row["created_at"].strftime("%Y-%m-%d %H:%M UTC")))
                except Exception:
                    pass
            if rows:
                ids = [r["id"] for r in rows]
                await conn.execute(f"DELETE FROM reminders WHERE id = ANY($1::int[])", ids)


async def setup(bot):
    await bot.add_cog(Reminders(bot))

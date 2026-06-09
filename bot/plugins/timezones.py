from datetime import datetime

import discord
from discord.ext import commands
import pytz

from message_formatter import format_template


class Timezones(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _cfg(self, config):
        return config.get("plugins", {}).get("timezones", {})

    @commands.group(name="timezone", invoke_without_command=True)
    async def timezone_cmd(self, ctx):
        await ctx.send("Usage: `!timezone set <tz>` | `!timezone get` | `!timezone list` | `!timezone clear`")

    @timezone_cmd.command(name="set")
    async def tz_set(self, ctx, tz: str):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        msgs = self._cfg(config).get("messages", {})
        if tz not in pytz.all_timezones:
            await ctx.send(msgs.get("timezone_invalid", "Invalid timezone. Use a valid tz identifier e.g. America/New_York"))
            return
        async with self.bot.pool.acquire() as conn:
            await conn.execute("INSERT INTO user_timezones (user_id, timezone) VALUES ($1,$2) ON CONFLICT (user_id) DO UPDATE SET timezone=$2",
                               ctx.author.id, tz)
        await ctx.send(format_template(msgs.get("timezone_set", "Your timezone has been set to {trigger}"), trigger=tz))

    @timezone_cmd.command(name="get")
    async def tz_get(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        msgs = self._cfg(config).get("messages", {})
        async with self.bot.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT timezone FROM user_timezones WHERE user_id=$1", target.id)
        if not row:
            await ctx.send(format_template(msgs.get("timezone_not_set", "{user} has not set a timezone"), user=target))
            return
        await ctx.send(format_template(msgs.get("timezone_get", "{user}'s timezone is {trigger}"), user=target, trigger=row["timezone"]))

    @timezone_cmd.command(name="clear")
    async def tz_clear(self, ctx):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        msgs = self._cfg(config).get("messages", {})
        async with self.bot.pool.acquire() as conn:
            await conn.execute("DELETE FROM user_timezones WHERE user_id=$1", ctx.author.id)
        await ctx.send(msgs.get("timezone_cleared", "Your timezone has been cleared"))

    @timezone_cmd.command(name="list")
    async def tz_list(self, ctx):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        msgs = self._cfg(config).get("messages", {})
        async with self.bot.pool.acquire() as conn:
            rows = await conn.fetch("SELECT user_id, timezone FROM user_timezones")
        member_tzs = [(ctx.guild.get_member(r["user_id"]), r["timezone"]) for r in rows]
        member_tzs = [(m, tz) for m, tz in member_tzs if m]
        if not member_tzs:
            await ctx.send(msgs.get("timezone_list_empty", "No members have set a timezone yet"))
            return
        lines = [f"**{m.display_name}**: {tz}" for m, tz in member_tzs[:20]]
        await ctx.send("**Member Timezones:**\n" + "\n".join(lines))

    @commands.command(name="time")
    async def time_cmd(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        msgs = self._cfg(config).get("messages", {})
        async with self.bot.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT timezone FROM user_timezones WHERE user_id=$1", target.id)
        if not row:
            await ctx.send(format_template(msgs.get("timezone_not_set", "{user} has not set a timezone"), user=target))
            return
        tz = pytz.timezone(row["timezone"])
        now = datetime.now(tz)
        await ctx.send(format_template(msgs.get("time_result", "Current time for {user}: {trigger}"),
                                       user=target, trigger=now.strftime("%H:%M %Z (%Y-%m-%d)")))

    @commands.command(name="timefor")
    async def timefor_cmd(self, ctx, tz_name: str):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        msgs = self._cfg(config).get("messages", {})
        if tz_name not in pytz.all_timezones:
            await ctx.send(msgs.get("timezone_invalid", "Invalid timezone"))
            return
        tz = pytz.timezone(tz_name)
        now = datetime.now(tz)
        await ctx.send(format_template(msgs.get("timefor_result", "Current time in {trigger}: {reason}"),
                                       trigger=tz_name, reason=now.strftime("%H:%M %Z (%Y-%m-%d)")))

    @commands.command(name="timeconvert")
    async def timeconvert_cmd(self, ctx, time_str: str, from_tz: str, to_tz: str):
        if from_tz not in pytz.all_timezones or to_tz not in pytz.all_timezones:
            await ctx.send("Invalid timezone(s)")
            return
        try:
            from_zone = pytz.timezone(from_tz)
            to_zone = pytz.timezone(to_tz)
            naive = datetime.strptime(time_str, "%H:%M")
            localized = from_zone.localize(naive.replace(year=datetime.now().year, month=datetime.now().month, day=datetime.now().day))
            converted = localized.astimezone(to_zone)
            await ctx.send(f"**{time_str} {from_tz}** = **{converted.strftime('%H:%M')} {to_tz}**")
        except Exception as e:
            await ctx.send(f"Error: {e}")


async def setup(bot):
    await bot.add_cog(Timezones(bot))

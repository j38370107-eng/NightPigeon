import discord
from discord.ext import commands

from message_formatter import format_template


class History(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def add_history_event(self, guild_id: int, user_id: int, event_type: str, description: str, mod_id: int = None):
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO history_events (guild_id, user_id, event_type, description, moderator_id) VALUES ($1,$2,$3,$4,$5)",
                guild_id, user_id, event_type, description, mod_id
            )

    @commands.group(name="history", invoke_without_command=True)
    async def history_cmd(self, ctx, member: discord.Member = None, filter_type: str = None):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        lvl = self.bot.get_cog("Levels")
        if lvl and not lvl.has_level(config, ctx.author, "history"):
            return

        target = member or ctx.author
        msgs = config.get("plugins", {}).get("history", {}).get("messages", {})

        async with self.bot.pool.acquire() as conn:
            if filter_type == "cases":
                rows = await conn.fetch("SELECT action as event_type, reason as description, created_at FROM cases WHERE guild_id=$1 AND user_id=$2 ORDER BY created_at DESC LIMIT 20",
                                        ctx.guild.id, target.id)
            elif filter_type == "notes":
                rows = await conn.fetch("SELECT action as event_type, reason as description, created_at FROM cases WHERE guild_id=$1 AND user_id=$2 AND action='note' ORDER BY created_at DESC LIMIT 20",
                                        ctx.guild.id, target.id)
            elif filter_type in ("joins", "roles"):
                rows = await conn.fetch("SELECT event_type, description, created_at FROM history_events WHERE guild_id=$1 AND user_id=$2 AND event_type=$3 ORDER BY created_at DESC LIMIT 20",
                                        ctx.guild.id, target.id, filter_type.rstrip("s"))
            else:
                rows = await conn.fetch("""
                    SELECT event_type, description, created_at FROM (
                        SELECT action as event_type, reason as description, created_at FROM cases WHERE guild_id=$1 AND user_id=$2
                        UNION ALL
                        SELECT event_type, description, created_at FROM history_events WHERE guild_id=$1 AND user_id=$2
                    ) combined ORDER BY created_at DESC LIMIT 25
                """, ctx.guild.id, target.id)

        if not rows:
            await ctx.send(format_template(msgs.get("history_empty", "No history found for {user}"), user=target))
            return

        lines = [f"**[{r['event_type'].upper()}]** {r['description'] or ''} — {r['created_at'].strftime('%Y-%m-%d %H:%M UTC')}" for r in rows]
        text = f"**History for {target.display_name}:**\n" + "\n".join(lines)
        for chunk in [text[i:i+1900] for i in range(0, len(text), 1900)]:
            await ctx.send(chunk)

    @history_cmd.command(name="clear")
    async def history_clear(self, ctx, member: discord.Member):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        lvl = self.bot.get_cog("Levels")
        if lvl and not lvl.has_level(config, ctx.author, "history"):
            return
        async with self.bot.pool.acquire() as conn:
            await conn.execute("DELETE FROM history_events WHERE guild_id=$1 AND user_id=$2", ctx.guild.id, member.id)
        msgs = config.get("plugins", {}).get("history", {}).get("messages", {})
        await ctx.send(format_template(msgs.get("history_cleared", "History cleared for {user}"), user=member))

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await self.add_history_event(member.guild.id, member.id, "join", f"Joined the server")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        await self.add_history_event(member.guild.id, member.id, "leave", f"Left the server")

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.nick != after.nick:
            await self.add_history_event(before.guild.id, after.id, "nick",
                                          f"Nickname changed: {before.nick or before.name} → {after.nick or after.name}")
        added = set(after.roles) - set(before.roles)
        for role in added:
            await self.add_history_event(before.guild.id, after.id, "role", f"Role added: {role.name}")
        removed = set(before.roles) - set(after.roles)
        for role in removed:
            await self.add_history_event(before.guild.id, after.id, "role", f"Role removed: {role.name}")


async def setup(bot):
    await bot.add_cog(History(bot))

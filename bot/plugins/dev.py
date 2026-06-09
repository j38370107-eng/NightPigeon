import traceback

import discord
from discord.ext import commands


class Dev(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _is_owner(self, user):
        return user.id == self.bot.owner_id

    @commands.command(name="whitelist")
    async def whitelist_cmd(self, ctx, server_id: int, owner_id: int, *, notes: str = None):
        if not self._is_owner(ctx.author):
            return
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO whitelisted_guilds (guild_id, guild_owner_id, whitelisted_by, guild_name, notes) VALUES ($1,$2,$3,$4,$5) ON CONFLICT (guild_id) DO UPDATE SET guild_owner_id=$2, notes=$5",
                server_id, owner_id, ctx.author.id, "Unknown", notes
            )
        await ctx.send(f"Server `{server_id}` whitelisted (owner: `{owner_id}`)")

    @commands.command(name="unwhitelist")
    async def unwhitelist_cmd(self, ctx, server_id: int, *, reason: str = None):
        if not self._is_owner(ctx.author):
            return
        async with self.bot.pool.acquire() as conn:
            await conn.execute("DELETE FROM whitelisted_guilds WHERE guild_id=$1", server_id)
        guild = self.bot.get_guild(server_id)
        if guild:
            await guild.leave()
        await ctx.send(f"Server `{server_id}` removed from whitelist")

    @commands.command(name="whitelistlist")
    async def whitelistlist_cmd(self, ctx):
        if not self._is_owner(ctx.author):
            return
        async with self.bot.pool.acquire() as conn:
            rows = await conn.fetch("SELECT guild_id, guild_name, guild_owner_id FROM whitelisted_guilds ORDER BY whitelisted_at DESC")
        if not rows:
            await ctx.send("No whitelisted servers")
            return
        lines = [f"`{r['guild_id']}` — {r['guild_name']} (owner: `{r['guild_owner_id']}`)" for r in rows]
        await ctx.send("**Whitelisted Servers:**\n" + "\n".join(lines[:30]))

    @commands.command(name="whitelistinfo")
    async def whitelistinfo_cmd(self, ctx, server_id: int):
        if not self._is_owner(ctx.author):
            return
        async with self.bot.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM whitelisted_guilds WHERE guild_id=$1", server_id)
        if not row:
            await ctx.send(f"Server `{server_id}` is not whitelisted")
            return
        await ctx.send(f"**Whitelist Info**\nID: `{row['guild_id']}`\nName: {row['guild_name']}\nOwner: `{row['guild_owner_id']}`\nWhitelisted by: `{row['whitelisted_by']}`\nAt: {row['whitelisted_at']}\nNotes: {row['notes'] or 'None'}")

    @commands.command(name="whitelistnotes")
    async def whitelistnotes_cmd(self, ctx, server_id: int, *, notes: str):
        if not self._is_owner(ctx.author):
            return
        async with self.bot.pool.acquire() as conn:
            await conn.execute("UPDATE whitelisted_guilds SET notes=$1 WHERE guild_id=$2", notes, server_id)
        await ctx.send(f"Notes updated for `{server_id}`")

    @commands.command(name="transferowner")
    async def transferowner_cmd(self, ctx, server_id: int, new_owner_id: int):
        if not self._is_owner(ctx.author):
            return
        async with self.bot.pool.acquire() as conn:
            await conn.execute("UPDATE whitelisted_guilds SET guild_owner_id=$1 WHERE guild_id=$2", new_owner_id, server_id)
        await ctx.send(f"Owner of `{server_id}` updated to `{new_owner_id}`")

    @commands.command(name="devleave")
    async def devleave_cmd(self, ctx, server_id: int):
        if not self._is_owner(ctx.author):
            return
        guild = self.bot.get_guild(server_id)
        if guild:
            await guild.leave()
            await ctx.send(f"Left `{server_id}`")
        else:
            await ctx.send(f"Not in `{server_id}`")

    @commands.command(name="devservers")
    async def devservers_cmd(self, ctx):
        if not self._is_owner(ctx.author):
            return
        lines = [f"`{g.id}` — {g.name} ({g.member_count} members)" for g in self.bot.guilds]
        text = "\n".join(lines) or "No servers"
        for chunk in [text[i:i+1900] for i in range(0, len(text), 1900)]:
            await ctx.send(chunk)

    @commands.command(name="deveval")
    async def deveval_cmd(self, ctx, *, code: str):
        if not self._is_owner(ctx.author):
            return
        code = code.strip('`').lstrip('python').lstrip('py').strip()
        try:
            import io, contextlib
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exec(f"async def _eval():\n" + "\n".join(f"    {line}" for line in code.split("\n")), {"bot": self.bot, "ctx": ctx, "discord": discord})
                import asyncio
                await eval("_eval()")
            result = output.getvalue() or "No output"
        except Exception:
            result = traceback.format_exc()
        for chunk in [result[i:i+1990] for i in range(0, len(result), 1990)]:
            await ctx.send(f"```\n{chunk}\n```")

    @commands.command(name="devreload")
    async def devreload_cmd(self, ctx, plugin: str):
        if not self._is_owner(ctx.author):
            return
        try:
            await self.bot.reload_extension(f"plugins.{plugin}")
            await ctx.send(f"Reloaded `{plugin}`")
        except Exception as e:
            await ctx.send(f"Failed: {e}")

    @commands.command(name="devreloadall")
    async def devreloadall_cmd(self, ctx):
        if not self._is_owner(ctx.author):
            return
        ok, fail = [], []
        for ext in list(self.bot.extensions.keys()):
            try:
                await self.bot.reload_extension(ext)
                ok.append(ext)
            except Exception as e:
                fail.append(f"{ext}: {e}")
        lines = [f"✓ {e}" for e in ok] + [f"✗ {e}" for e in fail]
        await ctx.send("\n".join(lines) or "Nothing reloaded")

    @commands.command(name="devstats")
    async def devstats_cmd(self, ctx):
        if not self._is_owner(ctx.author):
            return
        import platform, sys
        latency = round(self.bot.latency * 1000, 2)
        await ctx.send(f"**Bot Stats**\nServers: {len(self.bot.guilds)}\nUsers: {sum(g.member_count for g in self.bot.guilds)}\nLatency: {latency}ms\nPython: {sys.version[:20]}\nDiscord.py: {discord.__version__}")


async def setup(bot):
    await bot.add_cog(Dev(bot))

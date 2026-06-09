from datetime import datetime, timezone

import discord
from discord.ext import commands


class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="userinfo")
    async def userinfo_cmd(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        embed = discord.Embed(title=str(target), color=target.color)
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="ID", value=str(target.id))
        embed.add_field(name="Created", value=target.created_at.strftime("%Y-%m-%d"))
        embed.add_field(name="Joined", value=target.joined_at.strftime("%Y-%m-%d") if target.joined_at else "N/A")
        embed.add_field(name="Roles", value=str(len(target.roles) - 1))
        embed.add_field(name="Bot", value=str(target.bot))
        await ctx.send(embed=embed)

    @commands.command(name="avatar")
    async def avatar_cmd(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        embed = discord.Embed(title=f"{target.display_name}'s Avatar", color=0x5865F2)
        embed.set_image(url=target.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name="banner")
    async def banner_cmd(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        msgs = config.get("plugins", {}).get("utility", {}).get("messages", {})
        user = await self.bot.fetch_user(target.id)
        if not user.banner:
            await ctx.send(msgs.get("banner_none", "{user} has no banner set").replace("{user}", str(target)))
            return
        embed = discord.Embed(title=f"{target.display_name}'s Banner")
        embed.set_image(url=user.banner.url)
        await ctx.send(embed=embed)

    @commands.command(name="serverinfo")
    async def serverinfo_cmd(self, ctx):
        g = ctx.guild
        embed = discord.Embed(title=g.name, color=0x5865F2)
        if g.icon:
            embed.set_thumbnail(url=g.icon.url)
        embed.add_field(name="ID", value=str(g.id))
        embed.add_field(name="Owner", value=str(g.owner))
        embed.add_field(name="Members", value=str(g.member_count))
        embed.add_field(name="Channels", value=str(len(g.channels)))
        embed.add_field(name="Roles", value=str(len(g.roles)))
        embed.add_field(name="Created", value=g.created_at.strftime("%Y-%m-%d"))
        await ctx.send(embed=embed)

    @commands.command(name="roleinfo")
    async def roleinfo_cmd(self, ctx, role: discord.Role):
        embed = discord.Embed(title=role.name, color=role.color)
        embed.add_field(name="ID", value=str(role.id))
        embed.add_field(name="Members", value=str(len(role.members)))
        embed.add_field(name="Mentionable", value=str(role.mentionable))
        embed.add_field(name="Hoisted", value=str(role.hoist))
        embed.add_field(name="Created", value=role.created_at.strftime("%Y-%m-%d"))
        await ctx.send(embed=embed)

    @commands.command(name="channelinfo")
    async def channelinfo_cmd(self, ctx, channel: discord.TextChannel = None):
        target = channel or ctx.channel
        embed = discord.Embed(title=f"#{target.name}", color=0x5865F2)
        embed.add_field(name="ID", value=str(target.id))
        embed.add_field(name="Category", value=str(target.category) if target.category else "None")
        embed.add_field(name="Topic", value=target.topic or "None")
        embed.add_field(name="Slowmode", value=f"{target.slowmode_delay}s")
        embed.add_field(name="NSFW", value=str(target.nsfw))
        await ctx.send(embed=embed)

    @commands.command(name="membercount")
    async def membercount_cmd(self, ctx):
        await ctx.send(f"**{ctx.guild.name}** has **{ctx.guild.member_count}** members")

    @commands.command(name="roles")
    async def roles_cmd(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        roles = [r.mention for r in reversed(target.roles) if r != ctx.guild.default_role]
        if not roles:
            await ctx.send(f"{target.display_name} has no roles")
            return
        await ctx.send(f"**{target.display_name}'s roles:** {', '.join(roles[:30])}")

    @commands.command(name="joined")
    async def joined_cmd(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        if not target.joined_at:
            await ctx.send("Join date unknown")
            return
        await ctx.send(f"**{target.display_name}** joined on {target.joined_at.strftime('%B %d, %Y at %H:%M UTC')}")

    @commands.command(name="snowflake")
    async def snowflake_cmd(self, ctx, snowflake: int):
        ts = discord.utils.snowflake_time(snowflake)
        await ctx.send(f"**Snowflake `{snowflake}`**\nCreated: {ts.strftime('%Y-%m-%d %H:%M:%S UTC')}")

    @commands.command(name="permissions")
    async def permissions_cmd(self, ctx, member: discord.Member = None, channel: discord.TextChannel = None):
        target = member or ctx.author
        target_chan = channel or ctx.channel
        perms = target_chan.permissions_for(target)
        allowed = [p for p, v in perms if v]
        denied = [p for p, v in perms if not v]
        embed = discord.Embed(title=f"Permissions for {target.display_name}", color=0x5865F2)
        embed.add_field(name="Allowed", value=", ".join(allowed[:20]) or "None", inline=False)
        embed.add_field(name="Denied", value=", ".join(denied[:20]) or "None", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="inrole")
    async def inrole_cmd(self, ctx, role: discord.Role):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        msgs = config.get("plugins", {}).get("utility", {}).get("messages", {})
        members = role.members
        if not members:
            await ctx.send(msgs.get("inrole_empty", "No members have that role"))
            return
        lines = [str(m) for m in members[:30]]
        await ctx.send(f"**Members with {role.name} ({len(members)}):**\n" + "\n".join(lines))

    @commands.command(name="charcount")
    async def charcount_cmd(self, ctx, *, text: str):
        await ctx.send(f"**Characters:** {len(text)} | **Words:** {len(text.split())} | **Lines:** {text.count(chr(10)) + 1}")

    @commands.command(name="warncount")
    async def warncount_cmd(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        async with self.bot.pool.acquire() as conn:
            count = await conn.fetchval("SELECT COUNT(*) FROM cases WHERE guild_id=$1 AND user_id=$2 AND action='warn'", ctx.guild.id, target.id)
        await ctx.send(f"**{target.display_name}** has **{count}** warnings")

    @commands.command(name="modstats")
    async def modstats_cmd(self, ctx, mod: discord.Member = None):
        target = mod or ctx.author
        async with self.bot.pool.acquire() as conn:
            rows = await conn.fetch("SELECT action, COUNT(*) as cnt FROM cases WHERE guild_id=$1 AND moderator_id=$2 GROUP BY action",
                                    ctx.guild.id, target.id)
        if not rows:
            await ctx.send(f"No mod stats for {target.display_name}")
            return
        lines = [f"**{r['action']}**: {r['cnt']}" for r in rows]
        await ctx.send(f"**Mod stats for {target.display_name}:**\n" + "\n".join(lines))

    @commands.command(name="botstats")
    async def botstats_cmd(self, ctx):
        import sys
        await ctx.send(f"**Bot Stats**\nServers: {len(self.bot.guilds)}\nLatency: {round(self.bot.latency * 1000, 2)}ms\nDiscord.py: {discord.__version__}\nPython: {sys.version[:20]}")

    @commands.command(name="bansearch")
    async def bansearch_cmd(self, ctx, user_id: int):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        msgs = config.get("plugins", {}).get("utility", {}).get("messages", {})
        lvl = self.bot.get_cog("Levels")
        if lvl and not lvl.has_level(config, ctx.author, "bansearch"):
            return
        try:
            entry = await ctx.guild.fetch_ban(discord.Object(id=user_id))
            await ctx.send(f"**{entry.user}** (`{entry.user.id}`) is banned\nReason: {entry.reason or 'None'}")
        except discord.NotFound:
            await ctx.send(msgs.get("bansearch_not_found", "{trigger} is not banned").replace("{trigger}", str(user_id)))

    @commands.command(name="casesearch")
    async def casesearch_cmd(self, ctx, *, keyword: str):
        async with self.bot.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM cases WHERE guild_id=$1 AND reason ILIKE $2 ORDER BY id DESC LIMIT 10",
                                    ctx.guild.id, f"%{keyword}%")
        if not rows:
            await ctx.send(f"No cases matching `{keyword}`")
            return
        cases_cog = self.bot.get_cog("Cases")
        text = "\n\n".join(cases_cog._fmt_case(dict(r)) for r in rows) if cases_cog else str(rows)
        for chunk in [text[i:i+1900] for i in range(0, len(text), 1900)]:
            await ctx.send(chunk)

    @commands.command(name="embed")
    async def embed_cmd(self, ctx, *, json_str: str):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        lvl = self.bot.get_cog("Levels")
        if lvl and not lvl.has_level(config, ctx.author, "embed"):
            return
        import json
        try:
            data = json.loads(json_str)
            embed = discord.Embed.from_dict(data)
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"Invalid embed JSON: {e}")

    @commands.command(name="help")
    async def help_cmd(self, ctx, command: str = None):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        cfg = config.get("plugins", {}).get("utility", {})
        msgs = cfg.get("messages", {})
        lvl_cog = self.bot.get_cog("Levels")
        user_level = lvl_cog.get_user_level(config, ctx.author) if lvl_cog else 0

        if command:
            cmd = self.bot.get_command(command)
            if not cmd:
                await ctx.send(msgs.get("help_not_found", "Command {trigger} not found").replace("{trigger}", command))
                return
            req = lvl_cog.get_command_level(config, cmd.name) if lvl_cog else 0
            lock = " 🔒" if user_level < req else ""
            await ctx.send(f"**!{cmd.name}**{lock}\n{cmd.help or 'No description'}\nRequired Level: {req}")
            return

        # Build help by category
        categories = {
            "Moderation": ["ban", "forceban", "unban", "kick", "mute", "unmute", "warn", "purge", "slowmode", "lock", "unlock", "hide", "unhide"],
            "Cases": ["case", "cases", "servercases", "deletecase", "reason", "editcase", "addcase", "note", "viewnotes", "casecount"],
            "Utility": ["userinfo", "avatar", "banner", "serverinfo", "roleinfo", "roles", "joined", "membercount", "snowflake", "permissions", "inrole", "charcount", "warncount", "modstats"],
            "Tags": ["tag"],
            "Reminders": ["remind", "reminders", "delreminder"],
            "Roles": ["addrole", "removerole", "temprole", "temproles"],
            "Config": ["setconfig", "getconfig", "resetconfig"],
            "Other": ["level", "history", "watch", "unwatch", "watchlist", "immune", "unimmune", "timezone", "time", "starboard"],
        }

        lines = [f"**{ctx.guild.name} Bot Help** | Prefix: `!`\nYour level: **{user_level}**\n"]
        for cat, cmds in categories.items():
            cat_lines = []
            for name in cmds:
                req = lvl_cog.get_command_level(config, name) if lvl_cog else 0
                if user_level >= req:
                    cat_lines.append(f"`!{name}`")
                else:
                    cat_lines.append(f"`!{name}`🔒")
            lines.append(f"**{cat}:** " + " ".join(cat_lines))

        custom = cfg.get("custom_help_entries", [])
        if custom:
            lines.append("**Custom:** " + " ".join(f"`{e}`" for e in custom))

        await ctx.send("\n".join(lines))


async def setup(bot):
    await bot.add_cog(Utility(bot))

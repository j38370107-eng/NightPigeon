import discord
from discord.ext import commands
from datetime import datetime
from message_formatter import format_template, send_msg


class Cases(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def create_case(self, guild_id: int, user_id: int, mod_id: int,
                          action: str, reason: str = None,
                          duration: str = None, expires_at: datetime = None) -> int:
        async with self.bot.pool.acquire() as conn:
            row = await conn.fetchrow(
                "INSERT INTO cases (guild_id, user_id, moderator_id, action, reason, duration, expires_at) "
                "VALUES ($1,$2,$3,$4,$5,$6,$7) RETURNING id",
                guild_id, user_id, mod_id, action, reason, duration, expires_at
            )
        return row["id"]

    def _fmt_case(self, row: dict) -> str:
        exp = f" | Expires: {row['expires_at']}" if row.get('expires_at') else ""
        dur = f" | Duration: {row['duration']}" if row.get('duration') else ""
        return (f"**Case #{row['id']}** | **{row['action'].upper()}**\n"
                f"User: <@{row['user_id']}> | Mod: <@{row['moderator_id']}>\n"
                f"Reason: {row['reason'] or 'None'}{dur}{exp}\n"
                f"Date: {row['created_at'].strftime('%Y-%m-%d %H:%M UTC')}")

    @commands.command(name="case")
    async def case_cmd(self, ctx, case_id: int):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        levels = self.bot.get_cog("Levels")
        if levels and not levels.has_level(config, ctx.author, "case"):
            return
        async with self.bot.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM cases WHERE id=$1 AND guild_id=$2", case_id, ctx.guild.id)
        if not row:
            msgs = config.get("plugins", {}).get("cases", {}).get("messages", {})
            t = msgs.get("case_not_found", "Case {trigger} not found")
            await ctx.send(format_template(t, trigger=str(case_id)))
            return
        await ctx.send(self._fmt_case(dict(row)))

    @commands.command(name="cases")
    async def cases_cmd(self, ctx, member: discord.Member = None):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        levels = self.bot.get_cog("Levels")
        if levels and not levels.has_level(config, ctx.author, "cases"):
            return
        target = member or ctx.author
        async with self.bot.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM cases WHERE guild_id=$1 AND user_id=$2 ORDER BY id DESC LIMIT 10", ctx.guild.id, target.id)
        if not rows:
            msgs = config.get("plugins", {}).get("cases", {}).get("messages", {})
            t = msgs.get("no_cases", "No cases found for {user}")
            await ctx.send(format_template(t, user=target))
            return
        text = "\n\n".join(self._fmt_case(dict(r)) for r in rows)
        for chunk in [text[i:i+1900] for i in range(0, len(text), 1900)]:
            await ctx.send(chunk)

    @commands.command(name="servercases")
    async def servercases_cmd(self, ctx):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        levels = self.bot.get_cog("Levels")
        if levels and not levels.has_level(config, ctx.author, "servercases"):
            return
        async with self.bot.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM cases WHERE guild_id=$1 ORDER BY id DESC LIMIT 15", ctx.guild.id)
        if not rows:
            msgs = config.get("plugins", {}).get("cases", {}).get("messages", {})
            await ctx.send(msgs.get("no_server_cases", "No cases issued yet"))
            return
        text = "\n\n".join(self._fmt_case(dict(r)) for r in rows)
        for chunk in [text[i:i+1900] for i in range(0, len(text), 1900)]:
            await ctx.send(chunk)

    @commands.command(name="deletecase")
    async def deletecase_cmd(self, ctx, case_id: int):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        levels = self.bot.get_cog("Levels")
        if levels and not levels.has_level(config, ctx.author, "deletecase"):
            return
        async with self.bot.pool.acquire() as conn:
            r = await conn.execute("DELETE FROM cases WHERE id=$1 AND guild_id=$2", case_id, ctx.guild.id)
        msgs = config.get("plugins", {}).get("cases", {}).get("messages", {})
        if r == "DELETE 0":
            await ctx.send(format_template(msgs.get("case_not_found", "Case {trigger} not found"), trigger=str(case_id)))
        else:
            await ctx.send(format_template(msgs.get("case_deleted", "Case {trigger} deleted"), trigger=str(case_id)))

    @commands.command(name="reason")
    async def reason_cmd(self, ctx, case_id: int, *, new_reason: str):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        levels = self.bot.get_cog("Levels")
        if levels and not levels.has_level(config, ctx.author, "reason"):
            return
        async with self.bot.pool.acquire() as conn:
            r = await conn.execute("UPDATE cases SET reason=$1 WHERE id=$2 AND guild_id=$3", new_reason, case_id, ctx.guild.id)
        msgs = config.get("plugins", {}).get("cases", {}).get("messages", {})
        if r == "UPDATE 0":
            await ctx.send(format_template(msgs.get("case_not_found", "Case {trigger} not found"), trigger=str(case_id)))
        else:
            await ctx.send(format_template(msgs.get("case_edited", "Case {case_id} updated"), case_id=str(case_id)))

    @commands.command(name="editcase")
    async def editcase_cmd(self, ctx, case_id: int, field: str, *, value: str):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        levels = self.bot.get_cog("Levels")
        if levels and not levels.has_level(config, ctx.author, "editcase"):
            return
        field = field.lower()
        if field not in ("reason", "duration"):
            await ctx.send("Field must be `reason` or `duration`")
            return
        async with self.bot.pool.acquire() as conn:
            if field == "reason":
                await conn.execute("UPDATE cases SET reason=$1 WHERE id=$2 AND guild_id=$3", value, case_id, ctx.guild.id)
            else:
                await conn.execute("UPDATE cases SET duration=$1 WHERE id=$2 AND guild_id=$3", value, case_id, ctx.guild.id)
        msgs = config.get("plugins", {}).get("cases", {}).get("messages", {})
        await ctx.send(format_template(msgs.get("case_edited", "Case {case_id} updated"), case_id=str(case_id)))

    @commands.command(name="addcase")
    async def addcase_cmd(self, ctx, member: discord.Member, case_type: str, *, reason: str = None):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        levels = self.bot.get_cog("Levels")
        if levels and not levels.has_level(config, ctx.author, "addcase"):
            return
        case_id = await self.create_case(ctx.guild.id, member.id, ctx.author.id, case_type, reason)
        msgs = config.get("plugins", {}).get("cases", {}).get("messages", {})
        await ctx.send(format_template(msgs.get("addcase_success", "{case_type} case added for {user} | Case: {case_id}"),
                                       user=member, case_type=case_type, case_id=str(case_id)))

    @commands.command(name="forceaddcase")
    async def forceaddcase_cmd(self, ctx, user_id: int, case_type: str, *, reason: str = None):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        levels = self.bot.get_cog("Levels")
        if levels and not levels.has_level(config, ctx.author, "addcase"):
            return
        case_id = await self.create_case(ctx.guild.id, user_id, ctx.author.id, case_type, reason)
        await ctx.send(f"{case_type} case added for `{user_id}` | Case: {case_id}")

    @commands.command(name="casecount")
    async def casecount_cmd(self, ctx, member: discord.Member = None):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        target = member or ctx.author
        async with self.bot.pool.acquire() as conn:
            count = await conn.fetchval("SELECT COUNT(*) FROM cases WHERE guild_id=$1 AND user_id=$2", ctx.guild.id, target.id)
        msgs = config.get("plugins", {}).get("cases", {}).get("messages", {})
        await ctx.send(format_template(msgs.get("casecount", "{user} has {count} total cases"), user=target, count=str(count)))

    @commands.command(name="note")
    async def note_cmd(self, ctx, member: discord.Member, *, text: str):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        levels = self.bot.get_cog("Levels")
        if levels and not levels.has_level(config, ctx.author, "note"):
            return
        case_id = await self.create_case(ctx.guild.id, member.id, ctx.author.id, "note", text)
        msgs = config.get("plugins", {}).get("cases", {}).get("messages", {})
        await ctx.send(format_template(msgs.get("note_success", "Note added for {user} | Case: {case_id}"),
                                       user=member, case_id=str(case_id)))

    @commands.command(name="forcenote")
    async def forcenote_cmd(self, ctx, user_id: int, *, text: str):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        levels = self.bot.get_cog("Levels")
        if levels and not levels.has_level(config, ctx.author, "note"):
            return
        case_id = await self.create_case(ctx.guild.id, user_id, ctx.author.id, "note", text)
        await ctx.send(f"Note added for `{user_id}` | Case: {case_id}")

    @commands.command(name="viewnote")
    async def viewnote_cmd(self, ctx, case_id: int):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        async with self.bot.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM cases WHERE id=$1 AND guild_id=$2 AND action='note'", case_id, ctx.guild.id)
        if not row:
            await ctx.send(f"Note {case_id} not found")
            return
        await ctx.send(self._fmt_case(dict(row)))

    @commands.command(name="viewnotes")
    async def viewnotes_cmd(self, ctx, member: discord.Member):
        async with self.bot.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM cases WHERE guild_id=$1 AND user_id=$2 AND action='note' ORDER BY id DESC", ctx.guild.id, member.id)
        if not rows:
            await ctx.send(f"No notes for {member}")
            return
        text = "\n\n".join(self._fmt_case(dict(r)) for r in rows)
        for chunk in [text[i:i+1900] for i in range(0, len(text), 1900)]:
            await ctx.send(chunk)

    @commands.command(name="deletenote")
    async def deletenote_cmd(self, ctx, case_id: int):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        levels = self.bot.get_cog("Levels")
        if levels and not levels.has_level(config, ctx.author, "deletenote"):
            return
        async with self.bot.pool.acquire() as conn:
            r = await conn.execute("DELETE FROM cases WHERE id=$1 AND guild_id=$2 AND action='note'", case_id, ctx.guild.id)
        msgs = config.get("plugins", {}).get("cases", {}).get("messages", {})
        if r == "DELETE 0":
            await ctx.send(msgs.get("note_not_found", f"Note {case_id} not found"))
        else:
            await ctx.send(format_template(msgs.get("note_deleted", "Note {case_id} deleted"), case_id=str(case_id)))

    @commands.command(name="notesearch")
    async def notesearch_cmd(self, ctx, *, keyword: str):
        async with self.bot.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM cases WHERE guild_id=$1 AND action='note' AND reason ILIKE $2 ORDER BY id DESC LIMIT 10",
                                    ctx.guild.id, f"%{keyword}%")
        if not rows:
            await ctx.send(f"No notes matching `{keyword}`")
            return
        text = "\n\n".join(self._fmt_case(dict(r)) for r in rows)
        for chunk in [text[i:i+1900] for i in range(0, len(text), 1900)]:
            await ctx.send(chunk)

    @commands.command(name="editnote")
    async def editnote_cmd(self, ctx, case_id: int, *, new_text: str):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        levels = self.bot.get_cog("Levels")
        if levels and not levels.has_level(config, ctx.author, "editnote"):
            return
        async with self.bot.pool.acquire() as conn:
            r = await conn.execute("UPDATE cases SET reason=$1 WHERE id=$2 AND guild_id=$3 AND action='note'", new_text, case_id, ctx.guild.id)
        if r == "UPDATE 0":
            await ctx.send(f"Note {case_id} not found")
        else:
            await ctx.send(f"Note {case_id} updated")


async def setup(bot):
    await bot.add_cog(Cases(bot))

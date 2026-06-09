import asyncio
from datetime import datetime, timezone

import discord
from discord.ext import commands, tasks

from duration_parser import parse_duration
from message_formatter import format_template, send_msg, send_dm


def _get_msg(config: dict, key: str) -> str:
    return config.get("plugins", {}).get("moderation", {}).get("messages", {}).get(key, "")


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._expire_loop.start()

    def cog_unload(self):
        self._expire_loop.cancel()

    def _cfg(self, config: dict) -> dict:
        return config.get("plugins", {}).get("moderation", {})

    def _check(self, config, member, cmd):
        lvl = self.bot.get_cog("Levels")
        return (not lvl) or lvl.has_level(config, member, cmd)

    def _resolve_reason(self, config, reason):
        return self.bot.config_loader.resolve_preset(config, reason) or "No reason provided"

    async def _log(self, guild, **kwargs):
        lg = self.bot.get_cog("Logging")
        if lg:
            await lg.log_action(guild, "mod_action", "moderation", **kwargs)

    async def _check_escalation(self, ctx, config, target, action):
        esc = self.bot.get_cog("Escalation")
        if esc:
            await esc.check_manual(ctx, config, target, action)

    # ── BAN ────────────────────────────────────────────────────────
    @commands.command(name="ban")
    async def ban_cmd(self, ctx, member: discord.Member, duration: str = None, *, reason: str = None):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "ban"):
            return
        reason = self._resolve_reason(config, reason)
        cfg = self._cfg(config)

        if member.top_role >= ctx.author.top_role and ctx.author.id != self.bot.owner_id:
            await ctx.send(format_template(_get_msg(config, "error_hierarchy"), action="ban"))
            return

        td, dur_str, capped = (None, "permanent", False)
        expires = None
        if duration and duration.lower() not in ("perm", "permanent"):
            td, dur_str, capped = parse_duration(duration)
            if td is None and dur_str is None:
                reason_full = reason
                duration = None
                dur_str = "permanent"
            elif td:
                expires = datetime.now(timezone.utc) + td

        if cfg.get("dm_on_action"):
            await send_dm(member, _get_msg(config, "ban_dm"),
                          user=member, server=ctx.guild, reason=reason, duration=dur_str)

        delete_days = cfg.get("ban_delete_message_days", 1)
        try:
            await ctx.guild.ban(member, reason=reason, delete_message_days=delete_days)
        except discord.Forbidden:
            await ctx.send("I don't have permission to ban that user.")
            return

        cases = self.bot.get_cog("Cases")
        case_id = 0
        if cases:
            case_id = await cases.create_case(ctx.guild.id, member.id, ctx.author.id, "ban", reason, dur_str, expires)

        if expires:
            async with self.bot.pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO temp_bans (guild_id, user_id, expires_at) VALUES ($1,$2,$3) ON CONFLICT (guild_id,user_id) DO UPDATE SET expires_at=$3",
                    ctx.guild.id, member.id, expires
                )

        msg = _get_msg(config, "ban_success") or "{user} has been banned | Case: {case_id}"
        await ctx.send(format_template(msg, user=member, case_id=str(case_id), reason=reason, duration=dur_str))
        if capped:
            await ctx.send("Note: Duration capped at 180 days")
        await self._log(ctx.guild, mod=ctx.author, user=member, action="ban", reason=reason, duration=dur_str, case_id=str(case_id))
        await self._check_escalation(ctx, config, member, "ban")

    @commands.command(name="forceban")
    async def forceban_cmd(self, ctx, user_id: int, *, reason: str = None):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "forceban"):
            return
        reason = self._resolve_reason(config, reason)
        try:
            await ctx.guild.ban(discord.Object(id=user_id), reason=reason)
        except Exception as e:
            await ctx.send(f"Failed: {e}")
            return
        cases = self.bot.get_cog("Cases")
        case_id = await cases.create_case(ctx.guild.id, user_id, ctx.author.id, "ban", reason) if cases else 0
        msg = _get_msg(config, "forceban_success") or "{user.id} has been banned | Case: {case_id}"
        await ctx.send(format_template(msg, user=discord.Object(id=user_id), case_id=str(case_id), reason=reason, duration="permanent"))

    @commands.command(name="unban")
    async def unban_cmd(self, ctx, user_id: int, *, reason: str = None):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "unban"):
            return
        reason = self._resolve_reason(config, reason)
        try:
            await ctx.guild.unban(discord.Object(id=user_id), reason=reason)
        except discord.NotFound:
            await ctx.send(format_template(_get_msg(config, "error_not_banned") or "{user} is not banned", user=discord.Object(id=user_id)))
            return
        async with self.bot.pool.acquire() as conn:
            await conn.execute("DELETE FROM temp_bans WHERE guild_id=$1 AND user_id=$2", ctx.guild.id, user_id)
        cases = self.bot.get_cog("Cases")
        case_id = await cases.create_case(ctx.guild.id, user_id, ctx.author.id, "unban", reason) if cases else 0
        await ctx.send(format_template(_get_msg(config, "unban_success") or "{user.id} has been unbanned | Case: {case_id}",
                                       user=discord.Object(id=user_id), case_id=str(case_id)))

    @commands.command(name="softban")
    async def softban_cmd(self, ctx, member: discord.Member, *, reason: str = None):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "ban"):
            return
        reason = self._resolve_reason(config, reason)
        if member.top_role >= ctx.author.top_role and ctx.author.id != self.bot.owner_id:
            await ctx.send(format_template(_get_msg(config, "error_hierarchy"), action="softban"))
            return
        if self._cfg(config).get("dm_on_action"):
            await send_dm(member, _get_msg(config, "softban_dm"), user=member, server=ctx.guild, reason=reason)
        await ctx.guild.ban(member, reason=reason, delete_message_days=7)
        await ctx.guild.unban(member, reason="Softban unban")
        cases = self.bot.get_cog("Cases")
        case_id = await cases.create_case(ctx.guild.id, member.id, ctx.author.id, "softban", reason) if cases else 0
        await ctx.send(format_template(_get_msg(config, "softban_success") or "{user} has been softbanned | Case: {case_id}",
                                       user=member, case_id=str(case_id)))

    @commands.command(name="tempban")
    async def tempban_cmd(self, ctx, member: discord.Member, duration: str = "1d", *, reason: str = None):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "ban"):
            return
        reason = self._resolve_reason(config, reason)
        td, dur_str, capped = parse_duration(duration)
        if not td:
            await ctx.send(_get_msg(config, "error_invalid_duration") or "Invalid duration")
            return
        expires = datetime.now(timezone.utc) + td
        if self._cfg(config).get("dm_on_action"):
            await send_dm(member, _get_msg(config, "ban_dm"), user=member, server=ctx.guild, reason=reason, duration=dur_str)
        await ctx.guild.ban(member, reason=reason, delete_message_days=1)
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO temp_bans (guild_id, user_id, expires_at) VALUES ($1,$2,$3) ON CONFLICT (guild_id,user_id) DO UPDATE SET expires_at=$3",
                ctx.guild.id, member.id, expires
            )
        cases = self.bot.get_cog("Cases")
        case_id = await cases.create_case(ctx.guild.id, member.id, ctx.author.id, "tempban", reason, dur_str, expires) if cases else 0
        await ctx.send(format_template(_get_msg(config, "tempban_success") or "{user} has been temp banned | Duration: {duration} | Case: {case_id}",
                                       user=member, case_id=str(case_id), duration=dur_str))
        if capped:
            await ctx.send("Note: Duration capped at 180 days")

    @commands.command(name="banlist")
    async def banlist_cmd(self, ctx):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "ban"):
            return
        bans = [entry async for entry in ctx.guild.bans(limit=20)]
        if not bans:
            await ctx.send(_get_msg(config, "banlist_empty") or "No bans found")
            return
        lines = [f"`{entry.user.id}` — {entry.user} | {entry.reason or 'No reason'}" for entry in bans]
        await ctx.send("**Recent Bans:**\n" + "\n".join(lines[:20]))

    @commands.command(name="baninfo")
    async def baninfo_cmd(self, ctx, user_id: int):
        try:
            entry = await ctx.guild.fetch_ban(discord.Object(id=user_id))
            await ctx.send(f"**Ban Info**\nUser: {entry.user} (`{entry.user.id}`)\nReason: {entry.reason or 'None'}")
        except discord.NotFound:
            await ctx.send("That user is not banned")

    # ── KICK ───────────────────────────────────────────────────────
    @commands.command(name="kick")
    async def kick_cmd(self, ctx, member: discord.Member, *, reason: str = None):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "kick"):
            return
        reason = self._resolve_reason(config, reason)
        if member.top_role >= ctx.author.top_role and ctx.author.id != self.bot.owner_id:
            await ctx.send(format_template(_get_msg(config, "error_hierarchy"), action="kick"))
            return
        if self._cfg(config).get("dm_on_action"):
            await send_dm(member, _get_msg(config, "kick_dm"), user=member, server=ctx.guild, reason=reason)
        await member.kick(reason=reason)
        cases = self.bot.get_cog("Cases")
        case_id = await cases.create_case(ctx.guild.id, member.id, ctx.author.id, "kick", reason) if cases else 0
        await ctx.send(format_template(_get_msg(config, "kick_success") or "{user} has been kicked | Case: {case_id}",
                                       user=member, case_id=str(case_id)))
        await self._log(ctx.guild, mod=ctx.author, user=member, action="kick", reason=reason, case_id=str(case_id))
        await self._check_escalation(ctx, config, member, "kick")

    # ── MUTE ───────────────────────────────────────────────────────
    @commands.command(name="mute")
    async def mute_cmd(self, ctx, member: discord.Member, duration: str = None, *, reason: str = None):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "mute"):
            return
        reason = self._resolve_reason(config, reason)
        cfg = self._cfg(config)
        mute_role_id = cfg.get("mute_role")
        if not mute_role_id:
            await ctx.send("No mute role configured. Set `plugins.moderation.mute_role` in config.")
            return
        mute_role = ctx.guild.get_role(int(mute_role_id))
        if not mute_role:
            await ctx.send("Mute role not found")
            return

        async with self.bot.pool.acquire() as conn:
            existing = await conn.fetchrow("SELECT 1 FROM mutes WHERE guild_id=$1 AND user_id=$2", ctx.guild.id, member.id)
        if existing:
            await ctx.send(format_template(_get_msg(config, "error_already_muted") or "{user} is already muted", user=member))
            return

        td, dur_str, capped = (None, "permanent", False)
        expires = None
        if duration:
            td, dur_str, capped = parse_duration(duration)
            if td:
                expires = datetime.now(timezone.utc) + td
            elif dur_str is None:
                reason_parts = [duration]
                if reason:
                    reason_parts.append(reason)
                reason = " ".join(reason_parts)
                dur_str = "permanent"
                td = None

        removed_roles = []
        if cfg.get("mute_remove_roles"):
            removed_roles = [r.id for r in member.roles if not r.managed and r != ctx.guild.default_role]
            try:
                await member.edit(roles=[mute_role])
            except Exception:
                await member.add_roles(mute_role)
        else:
            await member.add_roles(mute_role, reason=reason)

        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO mutes (guild_id, user_id, expires_at, removed_roles) VALUES ($1,$2,$3,$4) ON CONFLICT (guild_id,user_id) DO UPDATE SET expires_at=$3, removed_roles=$4",
                ctx.guild.id, member.id, expires, removed_roles
            )

        if cfg.get("dm_on_action"):
            await send_dm(member, _get_msg(config, "mute_dm"), user=member, server=ctx.guild, reason=reason, duration=dur_str)

        cases = self.bot.get_cog("Cases")
        case_id = await cases.create_case(ctx.guild.id, member.id, ctx.author.id, "mute", reason, dur_str, expires) if cases else 0
        await ctx.send(format_template(_get_msg(config, "mute_success") or "{user} has been muted | Duration: {duration} | Case: {case_id}",
                                       user=member, case_id=str(case_id), duration=dur_str))
        if capped:
            await ctx.send("Note: Duration capped at 180 days")
        await self._log(ctx.guild, mod=ctx.author, user=member, action="mute", reason=reason, duration=dur_str, case_id=str(case_id))
        await self._check_escalation(ctx, config, member, "mute")

    @commands.command(name="forcemute")
    async def forcemute_cmd(self, ctx, user_id: int, duration: str = None, *, reason: str = None):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "forcemute"):
            return
        member = ctx.guild.get_member(user_id)
        if not member:
            await ctx.send(_get_msg(config, "error_user_not_found") or "User not found")
            return
        await self.mute_cmd(ctx, member, duration, reason=reason)

    @commands.command(name="unmute")
    async def unmute_cmd(self, ctx, member: discord.Member, *, reason: str = None):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "unmute"):
            return
        reason = self._resolve_reason(config, reason)
        cfg = self._cfg(config)
        mute_role_id = cfg.get("mute_role")
        if mute_role_id:
            mute_role = ctx.guild.get_role(int(mute_role_id))
            if mute_role and mute_role in member.roles:
                await member.remove_roles(mute_role, reason=reason)

        async with self.bot.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT removed_roles FROM mutes WHERE guild_id=$1 AND user_id=$2", ctx.guild.id, member.id)
            await conn.execute("DELETE FROM mutes WHERE guild_id=$1 AND user_id=$2", ctx.guild.id, member.id)

        if row and cfg.get("mute_remove_roles") and row["removed_roles"]:
            roles = [ctx.guild.get_role(rid) for rid in row["removed_roles"] if ctx.guild.get_role(rid)]
            if roles:
                try:
                    await member.edit(roles=roles)
                except Exception:
                    pass

        if cfg.get("dm_on_action"):
            await send_dm(member, _get_msg(config, "unmute_dm"), user=member, server=ctx.guild)

        cases = self.bot.get_cog("Cases")
        case_id = await cases.create_case(ctx.guild.id, member.id, ctx.author.id, "unmute", reason) if cases else 0
        await ctx.send(format_template(_get_msg(config, "unmute_success") or "{user} has been unmuted | Case: {case_id}",
                                       user=member, case_id=str(case_id)))

    @commands.command(name="forceunmute")
    async def forceunmute_cmd(self, ctx, user_id: int, *, reason: str = None):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "forceunmute"):
            return
        member = ctx.guild.get_member(user_id)
        if not member:
            await ctx.send(_get_msg(config, "error_user_not_found") or "User not found")
            return
        await self.unmute_cmd(ctx, member, reason=reason)

    @commands.command(name="mutelist")
    async def mutelist_cmd(self, ctx):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        async with self.bot.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM mutes WHERE guild_id=$1", ctx.guild.id)
        if not rows:
            await ctx.send(_get_msg(config, "mutelist_empty") or "No users currently muted")
            return
        lines = []
        for r in rows:
            exp = f" (expires {r['expires_at'].strftime('%Y-%m-%d %H:%M UTC')})" if r["expires_at"] else " (permanent)"
            lines.append(f"<@{r['user_id']}>{exp}")
        await ctx.send("**Muted Users:**\n" + "\n".join(lines))

    # ── WARN ───────────────────────────────────────────────────────
    @commands.command(name="warn")
    async def warn_cmd(self, ctx, member: discord.Member, *, reason: str = None):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "warn"):
            return
        reason = self._resolve_reason(config, reason)
        if self._cfg(config).get("dm_on_action"):
            await send_dm(member, _get_msg(config, "warn_dm"), user=member, server=ctx.guild, reason=reason)
        cases = self.bot.get_cog("Cases")
        case_id = await cases.create_case(ctx.guild.id, member.id, ctx.author.id, "warn", reason) if cases else 0
        await ctx.send(format_template(_get_msg(config, "warn_success") or "{user} has been warned | Case: {case_id}",
                                       user=member, case_id=str(case_id), reason=reason))
        await self._log(ctx.guild, mod=ctx.author, user=member, action="warn", reason=reason, case_id=str(case_id))
        await self._check_escalation(ctx, config, member, "warn")

    @commands.command(name="forcewarn")
    async def forcewarn_cmd(self, ctx, user_id: int, *, reason: str = None):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "forcewarn"):
            return
        reason = self._resolve_reason(config, reason)
        cases = self.bot.get_cog("Cases")
        case_id = await cases.create_case(ctx.guild.id, user_id, ctx.author.id, "warn", reason) if cases else 0
        await ctx.send(format_template(_get_msg(config, "forcewarn_success") or "{user.id} has been warned | Case: {case_id}",
                                       user=discord.Object(id=user_id), case_id=str(case_id), reason=reason))

    # ── PURGE ──────────────────────────────────────────────────────
    @commands.group(name="purge", invoke_without_command=True)
    async def purge_cmd(self, ctx, amount: int = 10):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "purge"):
            return
        deleted = await ctx.channel.purge(limit=amount + 1)
        m = await ctx.send(format_template(_get_msg(config, "purge_success") or "{count} messages deleted", count=str(len(deleted) - 1)))
        await asyncio.sleep(3)
        try:
            await m.delete()
        except Exception:
            pass

    @purge_cmd.command(name="bots")
    async def purge_bots(self, ctx, amount: int = 10):
        deleted = await ctx.channel.purge(limit=amount, check=lambda m: m.author.bot)
        await ctx.send(f"Deleted {len(deleted)} bot messages", delete_after=3)

    @purge_cmd.command(name="user")
    async def purge_user(self, ctx, member: discord.Member, amount: int = 10):
        deleted = await ctx.channel.purge(limit=100, check=lambda m: m.author == member)
        await ctx.send(f"Deleted {len(deleted)} messages from {member}", delete_after=3)

    @purge_cmd.command(name="contains")
    async def purge_contains(self, ctx, text: str, amount: int = 10):
        deleted = await ctx.channel.purge(limit=100, check=lambda m: text.lower() in m.content.lower())
        await ctx.send(f"Deleted {len(deleted)} messages", delete_after=3)

    @purge_cmd.command(name="embeds")
    async def purge_embeds(self, ctx, amount: int = 10):
        deleted = await ctx.channel.purge(limit=amount, check=lambda m: bool(m.embeds))
        await ctx.send(f"Deleted {len(deleted)} messages", delete_after=3)

    @purge_cmd.command(name="images")
    async def purge_images(self, ctx, amount: int = 10):
        deleted = await ctx.channel.purge(limit=amount, check=lambda m: bool(m.attachments))
        await ctx.send(f"Deleted {len(deleted)} messages", delete_after=3)

    @purge_cmd.command(name="links")
    async def purge_links(self, ctx, amount: int = 10):
        deleted = await ctx.channel.purge(limit=amount, check=lambda m: "http" in m.content)
        await ctx.send(f"Deleted {len(deleted)} messages", delete_after=3)

    # ── SLOWMODE ───────────────────────────────────────────────────
    @commands.command(name="slowmode")
    async def slowmode_cmd(self, ctx, seconds: str, channel: discord.TextChannel = None):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "slowmode"):
            return
        target = channel or ctx.channel
        if seconds.lower() == "off":
            await target.edit(slowmode_delay=0)
            await ctx.send(format_template(_get_msg(config, "slowmode_off") or "Slowmode removed in {channel.mention}", channel=target))
        else:
            try:
                secs = int(seconds)
            except ValueError:
                await ctx.send("Invalid slowmode value")
                return
            await target.edit(slowmode_delay=min(secs, 21600))
            await ctx.send(format_template(_get_msg(config, "slowmode_success") or "Slowmode set to {count}s in {channel.mention}",
                                           count=str(secs), channel=target))

    # ── NICK ───────────────────────────────────────────────────────
    @commands.command(name="nick")
    async def nick_cmd(self, ctx, member: discord.Member, *, nickname: str):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "nick"):
            return
        await member.edit(nick=nickname)
        await ctx.send(format_template(_get_msg(config, "nick_success") or "{user}'s nickname updated",
                                       user=member, trigger=nickname))

    @commands.command(name="forcenick")
    async def forcenick_cmd(self, ctx, user_id: int, *, nickname: str):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "forcenick"):
            return
        member = ctx.guild.get_member(user_id)
        if not member:
            await ctx.send("User not in server")
            return
        await member.edit(nick=nickname)
        await ctx.send(f"Nickname set for `{user_id}`")

    @commands.command(name="resetnick")
    async def resetnick_cmd(self, ctx, member: discord.Member):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "resetnick"):
            return
        await member.edit(nick=None)
        await ctx.send(format_template(_get_msg(config, "resetnick_success") or "{user}'s nickname has been reset", user=member))

    @commands.command(name="locknick")
    async def locknick_cmd(self, ctx, member: discord.Member):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "locknick"):
            return
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO nick_locks (guild_id, user_id, locked_nick, locked_by) VALUES ($1,$2,$3,$4) ON CONFLICT (guild_id,user_id) DO UPDATE SET locked_nick=$3",
                ctx.guild.id, member.id, member.display_name, ctx.author.id
            )
        await ctx.send(format_template(_get_msg(config, "locknick_success") or "{user}'s nickname has been locked", user=member))

    @commands.command(name="unlocknick")
    async def unlocknick_cmd(self, ctx, member: discord.Member):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "unlocknick"):
            return
        async with self.bot.pool.acquire() as conn:
            await conn.execute("DELETE FROM nick_locks WHERE guild_id=$1 AND user_id=$2", ctx.guild.id, member.id)
        await ctx.send(format_template(_get_msg(config, "unlocknick_success") or "{user}'s nickname lock removed", user=member))

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.nick == after.nick:
            return
        async with self.bot.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT locked_nick FROM nick_locks WHERE guild_id=$1 AND user_id=$2", before.guild.id, after.id)
        if row and after.nick != row["locked_nick"]:
            try:
                await after.edit(nick=row["locked_nick"])
            except Exception:
                pass

    # ── CHANNEL ────────────────────────────────────────────────────
    @commands.command(name="lock")
    async def lock_cmd(self, ctx, channel: discord.TextChannel = None, *, reason: str = None):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "lock"):
            return
        target = channel or ctx.channel
        reason = self._resolve_reason(config, reason)
        overwrite = target.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = False
        await target.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.send(format_template(_get_msg(config, "lock_success") or "{channel.mention} has been locked | Reason: {reason}",
                                       channel=target, reason=reason, mod=ctx.author))

    @commands.command(name="unlock")
    async def unlock_cmd(self, ctx, channel: discord.TextChannel = None, *, reason: str = None):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "unlock"):
            return
        target = channel or ctx.channel
        overwrite = target.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = None
        await target.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.send(format_template(_get_msg(config, "unlock_success") or "{channel.mention} has been unlocked",
                                       channel=target, mod=ctx.author))

    @commands.command(name="hide")
    async def hide_cmd(self, ctx, channel: discord.TextChannel = None, *, reason: str = None):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "lock"):
            return
        target = channel or ctx.channel
        overwrite = target.overwrites_for(ctx.guild.default_role)
        overwrite.view_channel = False
        await target.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.send(f"{target.mention} has been hidden")

    @commands.command(name="unhide")
    async def unhide_cmd(self, ctx, channel: discord.TextChannel = None):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "unlock"):
            return
        target = channel or ctx.channel
        overwrite = target.overwrites_for(ctx.guild.default_role)
        overwrite.view_channel = None
        await target.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.send(f"{target.mention} is now visible")

    # ── WATCHLIST ──────────────────────────────────────────────────
    @commands.command(name="watch")
    async def watch_cmd(self, ctx, member: discord.Member, *, reason: str = None):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "watch"):
            return
        reason = self._resolve_reason(config, reason)
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO watchlist (guild_id, user_id, reason, added_by) VALUES ($1,$2,$3,$4) ON CONFLICT DO NOTHING",
                ctx.guild.id, member.id, reason, ctx.author.id
            )
        await ctx.send(format_template(_get_msg(config, "watch_success") or "{user} added to watchlist", user=member))

    @commands.command(name="unwatch")
    async def unwatch_cmd(self, ctx, member: discord.Member):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "unwatch"):
            return
        async with self.bot.pool.acquire() as conn:
            await conn.execute("DELETE FROM watchlist WHERE guild_id=$1 AND user_id=$2", ctx.guild.id, member.id)
        await ctx.send(format_template(_get_msg(config, "unwatch_success") or "{user} removed from watchlist", user=member))

    @commands.command(name="watchlist")
    async def watchlist_cmd(self, ctx):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "watchlist"):
            return
        async with self.bot.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM watchlist WHERE guild_id=$1", ctx.guild.id)
        if not rows:
            await ctx.send(_get_msg(config, "watchlist_empty") or "No users on watchlist")
            return
        lines = [f"<@{r['user_id']}> — {r['reason'] or 'No reason'}" for r in rows]
        await ctx.send("**Watchlist:**\n" + "\n".join(lines))

    # ── IMMUNE ─────────────────────────────────────────────────────
    @commands.command(name="immune")
    async def immune_cmd(self, ctx, member: discord.Member):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "immune"):
            return
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO automod_immune (guild_id, user_id, added_by) VALUES ($1,$2,$3) ON CONFLICT DO NOTHING",
                ctx.guild.id, member.id, ctx.author.id
            )
        await ctx.send(format_template(_get_msg(config, "immune_success") or "{user} is now immune to automod", user=member))

    @commands.command(name="unimmune")
    async def unimmune_cmd(self, ctx, member: discord.Member):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "unimmune"):
            return
        async with self.bot.pool.acquire() as conn:
            await conn.execute("DELETE FROM automod_immune WHERE guild_id=$1 AND user_id=$2", ctx.guild.id, member.id)
        await ctx.send(format_template(_get_msg(config, "unimmune_success") or "{user}'s automod immunity removed", user=member))

    @commands.command(name="immunelist")
    async def immunelist_cmd(self, ctx):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "immunelist"):
            return
        async with self.bot.pool.acquire() as conn:
            rows = await conn.fetch("SELECT user_id FROM automod_immune WHERE guild_id=$1", ctx.guild.id)
        if not rows:
            await ctx.send(_get_msg(config, "immunelist_empty") or "No automod immune users")
            return
        lines = [f"<@{r['user_id']}>" for r in rows]
        await ctx.send("**Automod Immune:**\n" + "\n".join(lines))

    # ── ROLE BANS ──────────────────────────────────────────────────
    @commands.command(name="roleban")
    async def roleban_cmd(self, ctx, member: discord.Member, role: discord.Role, *, reason: str = None):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "roleban"):
            return
        reason = self._resolve_reason(config, reason)
        if role in member.roles:
            await member.remove_roles(role)
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO role_bans (guild_id, user_id, role_id, reason, moderator_id) VALUES ($1,$2,$3,$4,$5) ON CONFLICT DO NOTHING",
                ctx.guild.id, member.id, role.id, reason, ctx.author.id
            )
        await ctx.send(format_template(_get_msg(config, "roleban_success") or "{user} banned from {trigger}", user=member, trigger=role.name))

    @commands.command(name="unroleban")
    async def unroleban_cmd(self, ctx, member: discord.Member, role: discord.Role):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "unroleban"):
            return
        async with self.bot.pool.acquire() as conn:
            await conn.execute("DELETE FROM role_bans WHERE guild_id=$1 AND user_id=$2 AND role_id=$3", ctx.guild.id, member.id, role.id)
        await ctx.send(format_template(_get_msg(config, "unroleban_success") or "{user}'s role ban for {trigger} removed", user=member, trigger=role.name))

    @commands.command(name="rolebanned")
    async def rolebanned_cmd(self, ctx, member: discord.Member):
        async with self.bot.pool.acquire() as conn:
            rows = await conn.fetch("SELECT role_id, reason FROM role_bans WHERE guild_id=$1 AND user_id=$2", ctx.guild.id, member.id)
        if not rows:
            await ctx.send(f"{member} has no role bans")
            return
        lines = [f"<@&{r['role_id']}> — {r['reason'] or 'No reason'}" for r in rows]
        await ctx.send(f"**Role bans for {member}:**\n" + "\n".join(lines))

    @commands.Cog.listener()
    async def on_member_update_roleban(self, before: discord.Member, after: discord.Member):
        added_roles = set(after.roles) - set(before.roles)
        if not added_roles:
            return
        async with self.bot.pool.acquire() as conn:
            for role in added_roles:
                row = await conn.fetchrow("SELECT 1 FROM role_bans WHERE guild_id=$1 AND user_id=$2 AND role_id=$3",
                                          before.guild.id, after.id, role.id)
                if row:
                    try:
                        await after.remove_roles(role, reason="Role ban active")
                    except Exception:
                        pass

    # ── SEEN ───────────────────────────────────────────────────────
    @commands.command(name="seen")
    async def seen_cmd(self, ctx, member: discord.Member):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "seen"):
            return
        async with self.bot.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT last_seen, last_channel_id FROM seen WHERE guild_id=$1 AND user_id=$2", ctx.guild.id, member.id)
        if not row or not row["last_seen"]:
            await ctx.send(format_template(_get_msg(config, "seen_never") or "{user} has never been seen", user=member))
            return
        channel = ctx.guild.get_channel(row["last_channel_id"]) if row["last_channel_id"] else None
        when = row["last_seen"].strftime("%Y-%m-%d %H:%M UTC")
        await ctx.send(format_template(_get_msg(config, "seen_result") or "{user} was last seen {trigger} in {channel}",
                                       user=member, trigger=when, channel=channel))

    @commands.Cog.listener()
    async def on_message_seen(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO seen (guild_id, user_id, last_seen, last_channel_id) VALUES ($1,$2,$3,$4) ON CONFLICT (guild_id,user_id) DO UPDATE SET last_seen=$3, last_channel_id=$4",
                message.guild.id, message.author.id, datetime.now(timezone.utc), message.channel.id
            )

    # ── CLEANUP ────────────────────────────────────────────────────
    @commands.command(name="cleanup")
    async def cleanup_cmd(self, ctx, amount: int = 10):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "cleanup"):
            return
        deleted = await ctx.channel.purge(limit=amount + 1, check=lambda m: m.author == self.bot.user)
        await ctx.send(format_template(_get_msg(config, "cleanup_success") or "Deleted {count} bot messages",
                                       count=str(len(deleted))), delete_after=3)

    # ── BACKGROUND ─────────────────────────────────────────────────
    @tasks.loop(seconds=30)
    async def _expire_loop(self):
        await self.bot.wait_until_ready()
        now = datetime.now(timezone.utc)

        # Expire temp bans
        async with self.bot.pool.acquire() as conn:
            expired_bans = await conn.fetch("SELECT guild_id, user_id FROM temp_bans WHERE expires_at <= $1", now)
            for row in expired_bans:
                guild = self.bot.get_guild(row["guild_id"])
                if guild:
                    try:
                        await guild.unban(discord.Object(id=row["user_id"]), reason="Temp ban expired")
                    except Exception:
                        pass
            if expired_bans:
                ids = [(r["guild_id"], r["user_id"]) for r in expired_bans]
                await conn.executemany("DELETE FROM temp_bans WHERE guild_id=$1 AND user_id=$2", ids)

        # Expire mutes
        async with self.bot.pool.acquire() as conn:
            expired_mutes = await conn.fetch("SELECT guild_id, user_id, removed_roles FROM mutes WHERE expires_at IS NOT NULL AND expires_at <= $1", now)
            for row in expired_mutes:
                guild = self.bot.get_guild(row["guild_id"])
                if not guild:
                    continue
                member = guild.get_member(row["user_id"])
                if not member:
                    continue
                try:
                    config = await self.bot.config_loader.get_config(guild.id)
                    cfg = self._cfg(config)
                    mute_role_id = cfg.get("mute_role")
                    if mute_role_id:
                        mute_role = guild.get_role(int(mute_role_id))
                        if mute_role and mute_role in member.roles:
                            await member.remove_roles(mute_role, reason="Mute expired")
                    if cfg.get("mute_remove_roles") and row["removed_roles"]:
                        roles = [guild.get_role(rid) for rid in row["removed_roles"] if guild.get_role(rid)]
                        if roles:
                            await member.edit(roles=roles)
                except Exception:
                    pass
            if expired_mutes:
                ids = [(r["guild_id"], r["user_id"]) for r in expired_mutes]
                await conn.executemany("DELETE FROM mutes WHERE guild_id=$1 AND user_id=$2", ids)


async def setup(bot):
    await bot.add_cog(Moderation(bot))

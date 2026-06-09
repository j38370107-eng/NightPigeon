import discord
from discord.ext import commands
from message_formatter import format_template


class MassActions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _check(self, config, member, cmd):
        lvl = self.bot.get_cog("Levels")
        return (not lvl) or lvl.has_level(config, member, cmd)

    def _resolve_reason(self, config, reason):
        return self.bot.config_loader.resolve_preset(config, reason) or "No reason provided"

    def _get_msg(self, config, key):
        return config.get("plugins", {}).get("mass_actions", {}).get("messages", {}).get(key, "")

    def _parse_targets_reason(self, args: str):
        if "|" in args:
            targets_part, reason = args.split("|", 1)
            return targets_part.strip(), reason.strip()
        return args.strip(), None

    def _extract_ids(self, text: str):
        import re
        return [int(m) for m in re.findall(r"\d{17,20}", text)]

    @commands.command(name="masswarn")
    async def masswarn(self, ctx, *, args: str):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "masswarn"):
            return
        targets_str, reason = self._parse_targets_reason(args)
        reason = self._resolve_reason(config, reason)
        ids = self._extract_ids(targets_str)
        max_t = config.get("plugins", {}).get("mass_actions", {}).get("max_targets", 20)
        if not ids:
            await ctx.send(self._get_msg(config, "error_no_targets") or "No valid targets provided")
            return
        if len(ids) > max_t:
            await ctx.send(format_template(self._get_msg(config, "error_too_many_targets") or "Max {count} users", count=str(max_t)))
            return
        ok, fail = 0, 0
        cases = self.bot.get_cog("Cases")
        mod = self.bot.get_cog("Moderation")
        for uid in ids:
            member = ctx.guild.get_member(uid)
            if not member:
                fail += 1
                continue
            try:
                if cases:
                    await cases.create_case(ctx.guild.id, uid, ctx.author.id, "warn", reason)
                if mod and config.get("plugins", {}).get("moderation", {}).get("dm_on_action"):
                    from message_formatter import send_dm
                    await send_dm(member, "You have been warned in {server} for the following reason: {reason}",
                                  user=member, server=ctx.guild, reason=reason)
                ok += 1
            except Exception:
                fail += 1
        await ctx.send(format_template(self._get_msg(config, "masswarn_success") or "{success_count}/{total} users warned | Failed: {fail_count}",
                                       success_count=str(ok), total=str(len(ids)), fail_count=str(fail)))

    @commands.command(name="massmute")
    async def massmute(self, ctx, *, args: str):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "massmute"):
            return
        targets_str, reason = self._parse_targets_reason(args)
        reason = self._resolve_reason(config, reason)
        ids = self._extract_ids(targets_str)
        max_t = config.get("plugins", {}).get("mass_actions", {}).get("max_targets", 20)
        if not ids:
            await ctx.send(self._get_msg(config, "error_no_targets") or "No valid targets provided")
            return
        if len(ids) > max_t:
            await ctx.send(f"Max {max_t} targets")
            return
        mute_role_id = config.get("plugins", {}).get("moderation", {}).get("mute_role")
        mute_role = ctx.guild.get_role(int(mute_role_id)) if mute_role_id else None
        ok, fail = 0, 0
        for uid in ids:
            member = ctx.guild.get_member(uid)
            if not member or not mute_role:
                fail += 1
                continue
            try:
                await member.add_roles(mute_role, reason=reason)
                ok += 1
            except Exception:
                fail += 1
        await ctx.send(format_template(self._get_msg(config, "massmute_success") or "{success_count}/{total} users muted | Failed: {fail_count}",
                                       success_count=str(ok), total=str(len(ids)), fail_count=str(fail)))

    @commands.command(name="masskick")
    async def masskick(self, ctx, *, args: str):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "masskick"):
            return
        targets_str, reason = self._parse_targets_reason(args)
        reason = self._resolve_reason(config, reason)
        ids = self._extract_ids(targets_str)
        max_t = config.get("plugins", {}).get("mass_actions", {}).get("max_targets", 20)
        if not ids:
            await ctx.send(self._get_msg(config, "error_no_targets") or "No valid targets provided")
            return
        if len(ids) > max_t:
            await ctx.send(f"Max {max_t} targets")
            return
        ok, fail = 0, 0
        for uid in ids:
            member = ctx.guild.get_member(uid)
            if not member:
                fail += 1
                continue
            try:
                await member.kick(reason=reason)
                ok += 1
            except Exception:
                fail += 1
        await ctx.send(format_template(self._get_msg(config, "masskick_success") or "{success_count}/{total} users kicked | Failed: {fail_count}",
                                       success_count=str(ok), total=str(len(ids)), fail_count=str(fail)))

    @commands.command(name="massban")
    async def massban(self, ctx, *, args: str):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "massban"):
            return
        targets_str, reason = self._parse_targets_reason(args)
        reason = self._resolve_reason(config, reason)
        ids = self._extract_ids(targets_str)
        max_t = config.get("plugins", {}).get("mass_actions", {}).get("max_targets", 20)
        if not ids:
            await ctx.send(self._get_msg(config, "error_no_targets") or "No valid targets provided")
            return
        if len(ids) > max_t:
            await ctx.send(f"Max {max_t} targets")
            return
        ok, fail = 0, 0
        for uid in ids:
            try:
                await ctx.guild.ban(discord.Object(id=uid), reason=reason)
                ok += 1
            except Exception:
                fail += 1
        await ctx.send(format_template(self._get_msg(config, "massban_success") or "{success_count}/{total} users banned | Failed: {fail_count}",
                                       success_count=str(ok), total=str(len(ids)), fail_count=str(fail)))

    @commands.command(name="massunban")
    async def massunban(self, ctx, *, args: str):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "massunban"):
            return
        targets_str, reason = self._parse_targets_reason(args)
        ids = self._extract_ids(targets_str)
        if not ids:
            await ctx.send(self._get_msg(config, "error_no_targets") or "No valid targets provided")
            return
        ok, fail = 0, 0
        for uid in ids:
            try:
                await ctx.guild.unban(discord.Object(id=uid))
                ok += 1
            except Exception:
                fail += 1
        await ctx.send(format_template(self._get_msg(config, "massunban_success") or "{success_count}/{total} users unbanned | Failed: {fail_count}",
                                       success_count=str(ok), total=str(len(ids)), fail_count=str(fail)))

    @commands.command(name="massunmute")
    async def massunmute(self, ctx, *, args: str):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "massunban"):
            return
        targets_str, reason = self._parse_targets_reason(args)
        ids = self._extract_ids(targets_str)
        mute_role_id = config.get("plugins", {}).get("moderation", {}).get("mute_role")
        mute_role = ctx.guild.get_role(int(mute_role_id)) if mute_role_id else None
        if not mute_role:
            await ctx.send("No mute role configured")
            return
        ok, fail = 0, 0
        for uid in ids:
            member = ctx.guild.get_member(uid)
            if not member:
                fail += 1
                continue
            try:
                if mute_role in member.roles:
                    await member.remove_roles(mute_role)
                ok += 1
            except Exception:
                fail += 1
        await ctx.send(format_template(self._get_msg(config, "massunmute_success") or "{success_count}/{total} users unmuted | Failed: {fail_count}",
                                       success_count=str(ok), total=str(len(ids)), fail_count=str(fail)))

    @commands.command(name="massforcewarn")
    async def massforcewarn(self, ctx, *, args: str):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "massforcewarn"):
            return
        await self.masswarn(ctx, args=args)

    @commands.command(name="massforcemute")
    async def massforcemute(self, ctx, *, args: str):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "massforcemute"):
            return
        await self.massmute(ctx, args=args)

    @commands.command(name="massforcekick")
    async def massforcekick(self, ctx, *, args: str):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "massforcekick"):
            return
        await self.masskick(ctx, args=args)

    @commands.command(name="massforceban")
    async def massforceban(self, ctx, *, args: str):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self._check(config, ctx.author, "massforceban"):
            return
        await self.massban(ctx, args=args)


async def setup(bot):
    await bot.add_cog(MassActions(bot))

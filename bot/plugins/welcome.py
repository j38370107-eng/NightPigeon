import asyncio
from datetime import datetime, timezone

import discord
from discord.ext import commands

from message_formatter import format_template, send_msg, send_dm


class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # {guild_id: {user_id: [role_ids]}} for rejoin restore
        self._saved_roles: dict = {}

    def _cfg(self, config):
        return config.get("plugins", {}).get("welcome", {})

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        config = await self.bot.config_loader.get_config(member.guild.id)
        cfg = self._cfg(config)
        if not cfg.get("enabled"):
            return

        # Account age gate
        age_gate = cfg.get("account_age_gate", {})
        if age_gate.get("enabled"):
            min_age = age_gate.get("min_age_days", 7)
            age = (datetime.now(timezone.utc) - member.created_at).days
            if age < min_age:
                days_left = min_age - age
                msg = age_gate.get("message", "Your account is too new.")
                await send_dm(member, msg, user=member, server=member.guild, trigger=str(days_left))
                if age_gate.get("kick", True):
                    try:
                        await member.kick(reason=f"Account too new ({age} days)")
                    except Exception:
                        pass
                return

        # Rejoin restore roles
        rejoin = cfg.get("rejoin_restore_roles", {})
        if rejoin.get("enabled"):
            saved = self._saved_roles.get(member.guild.id, {}).get(member.id, [])
            ignore = [int(r) for r in rejoin.get("ignore_roles", [])]
            roles = [member.guild.get_role(rid) for rid in saved if rid not in ignore and member.guild.get_role(rid)]
            if roles:
                try:
                    await member.add_roles(*roles, reason="Rejoin restore")
                except Exception:
                    pass
        else:
            # Welcome role
            wr = cfg.get("welcome_role", {})
            if wr.get("enabled") and wr.get("role"):
                role = member.guild.get_role(int(wr["role"]))
                if role:
                    try:
                        await member.add_roles(role, reason="Welcome role")
                    except Exception:
                        pass

        # Join DM
        join_dm = cfg.get("join_dm", {})
        if join_dm.get("enabled") and join_dm.get("message"):
            await send_dm(member, join_dm["message"], user=member, server=member.guild)

        # Welcome message
        welcome = cfg.get("welcome", {})
        if welcome.get("enabled") and welcome.get("channel") and welcome.get("message"):
            chan = member.guild.get_channel(int(welcome["channel"]))
            if chan:
                content = format_template(welcome["message"], user=member, server=member.guild)
                if welcome.get("ping"):
                    content = f"{member.mention} {content}"
                delete_after = welcome.get("delete_after")
                try:
                    m = await chan.send(content)
                    if delete_after:
                        await asyncio.sleep(int(delete_after))
                        await m.delete()
                except Exception:
                    pass

        # Update member count channel
        await self._update_member_count(member.guild, config)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        config = await self.bot.config_loader.get_config(member.guild.id)
        cfg = self._cfg(config)
        if not cfg.get("enabled"):
            return

        # Save roles for rejoin restore
        rejoin = cfg.get("rejoin_restore_roles", {})
        if rejoin.get("enabled"):
            ignore = [int(r) for r in rejoin.get("ignore_roles", [])]
            role_ids = [r.id for r in member.roles if not r.managed and r != member.guild.default_role and r.id not in ignore]
            if member.guild.id not in self._saved_roles:
                self._saved_roles[member.guild.id] = {}
            self._saved_roles[member.guild.id][member.id] = role_ids

        # Goodbye message
        goodbye = cfg.get("goodbye", {})
        if goodbye.get("enabled") and goodbye.get("channel") and goodbye.get("message"):
            chan = member.guild.get_channel(int(goodbye["channel"]))
            if chan:
                content = format_template(goodbye["message"], user=member, server=member.guild)
                delete_after = goodbye.get("delete_after")
                try:
                    m = await chan.send(content)
                    if delete_after:
                        await asyncio.sleep(int(delete_after))
                        await m.delete()
                except Exception:
                    pass

        await self._update_member_count(member.guild, config)

    async def _update_member_count(self, guild: discord.Guild, config: dict):
        cfg = self._cfg(config)
        mcc = cfg.get("member_count_channel", {})
        if not mcc.get("enabled") or not mcc.get("channel"):
            return
        chan = guild.get_channel(int(mcc["channel"]))
        if not chan:
            return
        name = format_template(mcc.get("format", "Members: {server.member_count}"), server=guild)
        try:
            await chan.edit(name=name)
        except Exception:
            pass

    @commands.command(name="welcome_test")
    async def welcome_test(self, ctx):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        lvl = self.bot.get_cog("Levels")
        if lvl and not lvl.has_level(config, ctx.author, "welcome_test"):
            return
        await self.on_member_join(ctx.author)
        await ctx.send("Welcome message test triggered")


async def setup(bot):
    await bot.add_cog(Welcome(bot))

import re
import random

import discord
from discord.ext import commands

from message_formatter import format_template, send_dm

ZALGO_RE = re.compile(r'[\u0300-\u036f\u0489\u1dc0-\u1dff]')
UNREADABLE_RE = re.compile(r'^[^\w\s]{3,}')
HOIST_RE = re.compile(r'^[^a-zA-Z0-9\s]')


class ModNick(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _cfg(self, config):
        return config.get("plugins", {}).get("modnick", {})

    def _get_replacement(self, cfg: dict) -> str:
        random_names = cfg.get("random_names", [])
        if random_names:
            return random.choice(random_names)
        return cfg.get("default_name", "Moderated Nickname")

    def _check_nick(self, nick: str, cfg: dict) -> tuple[bool, str]:
        rules = cfg.get("rules", {})
        if not nick:
            if rules.get("blank"):
                return True, "blank"
            return False, None
        if rules.get("hoist") and HOIST_RE.match(nick):
            return True, "hoist"
        if rules.get("zalgo") and ZALGO_RE.search(nick):
            return True, "zalgo"
        if rules.get("unreadable") and UNREADABLE_RE.match(nick):
            return True, "unreadable"
        if rules.get("bad_words"):
            bad = self.bot.config_loader  # Can't easily access without guild
            pass
        for pattern in rules.get("custom_patterns", []):
            try:
                if re.search(pattern, nick, re.IGNORECASE):
                    return True, f"custom pattern: {pattern}"
            except Exception:
                pass
        return False, None

    @commands.command(name="modnick")
    async def modnick_cmd(self, ctx, member: discord.Member):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        cfg = self._cfg(config)
        lvl = self.bot.get_cog("Levels")
        if lvl and not lvl.has_level(config, ctx.author, "modnick"):
            return
        new_nick = self._get_replacement(cfg)
        await member.edit(nick=new_nick)
        msgs = cfg.get("messages", {})
        await ctx.send(format_template(msgs.get("nickname_changed", "{user}'s nickname was changed to {trigger}"),
                                       user=member, trigger=new_nick, reason="manual modnick"))

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.nick == after.nick and before.name == after.name:
            return
        config = await self.bot.config_loader.get_config(after.guild.id)
        cfg = self._cfg(config)
        if not cfg.get("enabled"):
            return

        nick = after.nick or after.name
        violated, rule = self._check_nick(nick, cfg)
        if not violated:
            return

        new_nick = self._get_replacement(cfg)
        msgs = cfg.get("messages", {})
        try:
            await after.edit(nick=new_nick)
        except Exception:
            return

        await send_dm(after, msgs.get("nickname_changed_dm", "Your nickname in {server} has been changed to {trigger}"),
                      user=after, server=after.guild, trigger=new_nick)

        cases = self.bot.get_cog("Cases")
        if cases:
            await cases.create_case(after.guild.id, after.id, self.bot.user.id, "note",
                                    f"Nickname moderated: {nick} → {new_nick} (rule: {rule})")

        if cfg.get("log_changes"):
            lg = self.bot.get_cog("Logging")
            if lg:
                chan = await lg._get_log_channel(after.guild, "members")
                if chan:
                    try:
                        await chan.send(format_template(msgs.get("nickname_changed", "{user}'s nickname was changed to {trigger} | Rule: {reason}"),
                                                        user=after, trigger=new_nick, reason=rule))
                    except Exception:
                        pass

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        config = await self.bot.config_loader.get_config(member.guild.id)
        cfg = self._cfg(config)
        if not cfg.get("enabled"):
            return
        nick = member.nick or member.name
        violated, rule = self._check_nick(nick, cfg)
        if violated:
            new_nick = self._get_replacement(cfg)
            try:
                await member.edit(nick=new_nick)
            except Exception:
                pass


async def setup(bot):
    await bot.add_cog(ModNick(bot))

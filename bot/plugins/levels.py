import discord
from discord.ext import commands

DEFAULT_LEVELS = {
    "ban": 50, "forceban": 75, "unban": 50, "tempban": 50, "softban": 50,
    "kick": 25, "mute": 25, "forcemute": 75, "unmute": 25, "forceunmute": 75,
    "tempmute": 25, "warn": 25, "forcewarn": 25, "purge": 25, "slowmode": 25,
    "addcase": 25, "forceaddcase": 25, "editcase": 50, "deletecase": 75,
    "reason": 50, "case": 25, "cases": 25, "servercases": 25, "casecount": 25,
    "exportcases": 25, "note": 25, "forcenote": 25, "viewnote": 25,
    "viewnotes": 25, "deletenote": 50, "notesearch": 25, "editnote": 50,
    "masswarn": 75, "massmute": 75, "masskick": 75, "massban": 100,
    "massunban": 75, "massunmute": 75, "massforcewarn": 75, "massforcemute": 75,
    "massforcekick": 75, "massforceban": 100, "raidmode": 100,
    "lockdown": 50, "unlock": 50, "lock": 50, "hide": 50, "unhide": 50,
    "modnick": 25, "history": 25, "watch": 50, "unwatch": 50,
    "watchlist": 25, "immune": 75, "unimmune": 75, "immunelist": 25,
    "roleban": 75, "unroleban": 75, "rolebanned": 25, "nick": 50,
    "forcenick": 75, "resetnick": 50, "forceresetnick": 75, "locknick": 75,
    "unlocknick": 75, "seen": 25, "cleanup": 50, "rr": 100, "ticket": 0,
    "ticket_close": 0, "ticket_claim": 25, "ticket_delete": 75,
    "ticket_adduser": 25, "ticket_removeuser": 25, "ticket_blacklist": 50,
    "ticket_unblacklist": 50, "ticket_panel": 100, "starboard": 0,
    "timezone": 0, "time": 0, "timefor": 0, "timeconvert": 0,
    "autoreply": 50, "autoreaction": 50, "autoclean": 100, "slowmode_auto": 100,
    "welcome_test": 100, "configaccess": 100, "level": 0, "levels": 100,
    "levelset": 100, "userinfo": 0, "avatar": 0, "banner": 0, "roles": 0,
    "joined": 0, "firstmsg": 25, "bansearch": 25, "casesearch": 25,
    "warncount": 25, "modstats": 25, "serverinfo": 0, "channelinfo": 0,
    "roleinfo": 0, "membercount": 0, "botstats": 0, "botinfo": 0,
    "inviteinfo": 25, "snowflake": 0, "permissions": 0, "inrole": 25,
    "charcount": 0, "embed": 50, "help": 0, "tag": 0, "remind": 0,
    "reminders": 0, "delreminder": 0, "addrole": 50, "removerole": 50,
    "temprole": 50, "temproles": 25, "setconfig": 100, "getconfig": 100,
    "resetconfig": 100,
}


class Levels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_user_level(self, config: dict, member) -> int:
        if not member:
            return 0
        if member.id == self.bot.owner_id:
            return 1000
        levels = config.get("levels", {})
        best = 0
        users = levels.get("users", {})
        if str(member.id) in users:
            best = max(best, int(users[str(member.id)]))
        roles = levels.get("roles", {})
        if hasattr(member, "roles"):
            for role in member.roles:
                if str(role.id) in roles:
                    best = max(best, int(roles[str(role.id)]))
        return best

    def get_command_level(self, config: dict, cmd: str) -> int:
        yaml_override = config.get("levels", {}).get("commands", {})
        if cmd in yaml_override:
            return int(yaml_override[cmd])
        return DEFAULT_LEVELS.get(cmd, 50)

    def has_level(self, config: dict, member, cmd: str) -> bool:
        return self.get_user_level(config, member) >= self.get_command_level(config, cmd)

    @commands.command(name="level")
    async def level_cmd(self, ctx, member: discord.Member = None):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        target = member or ctx.author
        lvl = self.get_user_level(config, target)
        await ctx.send(f"**{target.display_name}** has level **{lvl}**")

    @commands.command(name="levels")
    async def levels_cmd(self, ctx):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self.has_level(config, ctx.author, "levels"):
            return
        lc = config.get("levels", {})
        lines = []
        for uid, lvl in lc.get("users", {}).items():
            lines.append(f"  <@{uid}> → **{lvl}**")
        for rid, lvl in lc.get("roles", {}).items():
            lines.append(f"  <@&{rid}> → **{lvl}**")
        if not lines:
            await ctx.send("No level assignments configured.")
        else:
            await ctx.send("**Level Assignments:**\n" + "\n".join(lines))

    @commands.command(name="levelset")
    async def levelset_cmd(self, ctx, member: discord.Member = None):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        if not self.has_level(config, ctx.author, "levelset"):
            return
        target = member or ctx.author
        lvl = self.get_user_level(config, target)
        await ctx.send(f"**{target.display_name}** would have level **{lvl}**")


async def setup(bot):
    await bot.add_cog(Levels(bot))

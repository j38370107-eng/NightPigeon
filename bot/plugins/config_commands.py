import discord
from discord.ext import commands

DEFAULT_YAML = """# Bot Configuration
# Full docs at your dashboard

levels:
  users: {}
  roles: {}
  commands: {}

tags: {}

plugins:
  moderation:
    enabled: true
    mute_role: null
    dm_on_action: true
    mute_remove_roles: false
    ban_delete_message_days: 1

  logging:
    enabled: false
    channel: null

  automod:
    enabled: false

  welcome:
    enabled: true
    welcome:
      enabled: false
      channel: null
      message: "Welcome to {server}, {user.mention}!"
    goodbye:
      enabled: false
      channel: null
      message: "{user} has left {server}."

  command_aliases:
    config:
      aliases:
        b: ban
        k: kick
        m: mute
        w: warn
        p: purge

  preset_reasons:
    config:
      presets:
        spam: "Spamming in chat"
        ads: "Advertising without permission"
        toxic: "Toxic behavior"
"""


class ConfigCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _can_manage_config(self, ctx):
        if ctx.author.id == self.bot.owner_id:
            return True
        return False

    async def _is_guild_owner(self, ctx):
        async with self.bot.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT guild_owner_id FROM whitelisted_guilds WHERE guild_id=$1", ctx.guild.id)
        if row and row["guild_owner_id"] == ctx.author.id:
            return True
        return False

    async def _has_config_access(self, ctx):
        if ctx.author.id == self.bot.owner_id:
            return True
        if await self._is_guild_owner(ctx):
            return True
        async with self.bot.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT 1 FROM config_access WHERE guild_id=$1 AND user_id=$2", ctx.guild.id, ctx.author.id)
        return row is not None

    @commands.command(name="setconfig")
    async def setconfig_cmd(self, ctx):
        if not await self._has_config_access(ctx):
            return
        if not ctx.message.content.strip().split(None, 1)[1:]:
            await ctx.send("Usage: `!setconfig` followed by your YAML on the next lines in a code block")
            return

        # Extract YAML from code block or raw
        content = ctx.message.content.split(None, 1)
        if len(content) < 2:
            await ctx.send("Provide YAML after the command")
            return

        yaml_str = content[1].strip()
        if yaml_str.startswith("```"):
            lines = yaml_str.split("\n")
            yaml_str = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            yaml_str = yaml_str.strip("`").strip()

        success = await self.bot.config_loader.set_config(ctx.guild.id, yaml_str)
        if success:
            await ctx.send("Config saved successfully")
        else:
            await ctx.send("Invalid YAML. Please check your config and try again.")

    @commands.command(name="getconfig")
    async def getconfig_cmd(self, ctx):
        if not await self._has_config_access(ctx):
            return
        raw = await self.bot.config_loader.get_raw(ctx.guild.id)
        if not raw:
            raw = DEFAULT_YAML
        try:
            dm = await ctx.author.create_dm()
            chunks = [raw[i:i+1900] for i in range(0, len(raw), 1900)]
            for i, chunk in enumerate(chunks):
                if i == 0:
                    await dm.send(f"**Config for {ctx.guild.name}:**\n```yaml\n{chunk}\n```")
                else:
                    await dm.send(f"```yaml\n{chunk}\n```")
            await ctx.send("Config DM'd to you")
        except Exception:
            await ctx.send("Couldn't DM you. Please enable DMs.")

    @commands.command(name="resetconfig")
    async def resetconfig_cmd(self, ctx):
        if not await self._has_config_access(ctx):
            return
        await self.bot.config_loader.reset_config(ctx.guild.id)
        await ctx.send("Config reset to defaults")

    @commands.group(name="configaccess", invoke_without_command=True)
    async def configaccess_cmd(self, ctx):
        pass

    @configaccess_cmd.command(name="add")
    async def configaccess_add(self, ctx, member: discord.Member):
        if not (ctx.author.id == self.bot.owner_id or await self._is_guild_owner(ctx)):
            return
        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO config_access (guild_id, user_id, granted_by) VALUES ($1,$2,$3) ON CONFLICT DO NOTHING",
                ctx.guild.id, member.id, ctx.author.id
            )
        await ctx.send(f"{member.mention} can now manage config")

    @configaccess_cmd.command(name="remove")
    async def configaccess_remove(self, ctx, member: discord.Member):
        if not (ctx.author.id == self.bot.owner_id or await self._is_guild_owner(ctx)):
            return
        async with self.bot.pool.acquire() as conn:
            await conn.execute("DELETE FROM config_access WHERE guild_id=$1 AND user_id=$2", ctx.guild.id, member.id)
        await ctx.send(f"{member.mention}'s config access removed")

    @configaccess_cmd.command(name="list")
    async def configaccess_list(self, ctx):
        if not (ctx.author.id == self.bot.owner_id or await self._is_guild_owner(ctx)):
            return
        async with self.bot.pool.acquire() as conn:
            rows = await conn.fetch("SELECT user_id FROM config_access WHERE guild_id=$1", ctx.guild.id)
        if not rows:
            await ctx.send("No config access users")
            return
        lines = [f"<@{r['user_id']}>" for r in rows]
        await ctx.send("**Config Access:**\n" + "\n".join(lines))


async def setup(bot):
    await bot.add_cog(ConfigCommands(bot))

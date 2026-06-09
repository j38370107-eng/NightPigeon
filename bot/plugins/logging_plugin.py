import discord
from discord.ext import commands
from message_formatter import format_template


class Logging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _get_log_channel(self, guild: discord.Guild, category: str = None) -> discord.TextChannel:
        config = await self.bot.config_loader.get_config(guild.id)
        lc = config.get("plugins", {}).get("logging", {})
        if not lc.get("enabled"):
            return None
        chan_id = None
        if category:
            chan_id = lc.get("channels", {}).get(category)
        if not chan_id:
            chan_id = lc.get("channel")
        if not chan_id:
            return None
        return guild.get_channel(int(chan_id))

    async def log_action(self, guild: discord.Guild, event: str, category: str = None, **kwargs):
        chan = await self._get_log_channel(guild, category)
        if not chan:
            return
        config = await self.bot.config_loader.get_config(guild.id)
        msgs = config.get("plugins", {}).get("logging", {}).get("messages", {})
        template = msgs.get(event)
        if not template:
            return
        text = format_template(template, server=guild, **kwargs)
        try:
            await chan.send(text)
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return
        await self.log_action(message.guild, "message_delete", "messages",
                              user=message.author, channel=message.channel,
                              trigger=message.content[:500] or "[no content]")

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if not before.guild or before.author.bot or before.content == after.content:
            return
        await self.log_action(before.guild, "message_edit", "messages",
                              user=before.author, channel=before.channel,
                              trigger=before.content[:300], reason=after.content[:300])

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages):
        if not messages:
            return
        guild = messages[0].guild
        if not guild:
            return
        await self.log_action(guild, "message_bulk_delete", "messages",
                              channel=messages[0].channel, count=len(messages))

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await self.log_action(member.guild, "member_join", "members",
                              user=member, server=member.guild)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        await self.log_action(member.guild, "member_leave", "members",
                              user=member, server=member.guild)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user):
        await self.log_action(guild, "member_ban", "members", user=user)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user):
        await self.log_action(guild, "member_unban", "members", user=user)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.nick != after.nick:
            await self.log_action(before.guild, "nickname_change", "members",
                                  user=after, trigger=before.nick or before.name,
                                  reason=after.nick or after.name)
        added = set(after.roles) - set(before.roles)
        removed = set(before.roles) - set(after.roles)
        for role in added:
            await self.log_action(before.guild, "role_added", "members",
                                  user=after, trigger=role.name)
        for role in removed:
            await self.log_action(before.guild, "role_removed", "members",
                                  user=after, trigger=role.name)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before, after):
        if before.channel is None and after.channel:
            await self.log_action(member.guild, "voice_join", "voice",
                                  user=member, channel=after.channel)
        elif before.channel and after.channel is None:
            await self.log_action(member.guild, "voice_leave", "voice",
                                  user=member, channel=before.channel)
        elif before.channel and after.channel and before.channel != after.channel:
            await self.log_action(member.guild, "voice_move", "voice",
                                  user=member, trigger=before.channel.name,
                                  reason=after.channel.name)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        await self.log_action(channel.guild, "channel_create", "server", channel=channel)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        await self.log_action(channel.guild, "channel_delete", "server", trigger=channel.name)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        await self.log_action(role.guild, "role_create", "server", trigger=role.name)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        await self.log_action(role.guild, "role_delete", "server", trigger=role.name)

    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        await self.log_action(after, "server_update", "server", server=after)


async def setup(bot):
    await bot.add_cog(Logging(bot))

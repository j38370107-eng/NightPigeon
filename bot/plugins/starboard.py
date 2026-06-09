import discord
from discord.ext import commands
from datetime import datetime, timezone, timedelta

from message_formatter import format_template, build_embed


class Starboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _cfg(self, config):
        return config.get("plugins", {}).get("starboard", {})

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        config = await self.bot.config_loader.get_config(guild.id)
        cfg = self._cfg(config)
        if not cfg.get("enabled") or not cfg.get("channel"):
            return

        emoji = cfg.get("emoji", "⭐")
        if str(payload.emoji) != emoji:
            return

        channel = guild.get_channel(payload.channel_id)
        if not channel:
            return

        ignore_channels = [int(c) for c in cfg.get("ignore_channels", [])]
        if channel.id in ignore_channels:
            return

        try:
            message = await channel.fetch_message(payload.message_id)
        except Exception:
            return

        if not cfg.get("bots_allowed") and message.author.bot:
            return
        if not cfg.get("nsfw_allowed") and channel.nsfw:
            return

        max_age = cfg.get("max_age_days", 7)
        if (datetime.now(timezone.utc) - message.created_at).days > max_age:
            return

        # Count stars
        reaction = discord.utils.get(message.reactions, emoji=emoji)
        if not reaction:
            return
        count = reaction.count

        threshold = cfg.get("threshold", 3)
        if count < threshold:
            return

        sb_channel = guild.get_channel(int(cfg["channel"]))
        if not sb_channel:
            return

        async with self.bot.pool.acquire() as conn:
            existing = await conn.fetchrow("SELECT starboard_message_id FROM starboard_messages WHERE guild_id=$1 AND message_id=$2",
                                           guild.id, message.id)

        fmt = cfg.get("format", {})
        header_template = fmt.get("header", "{emoji} **{star_count}** {channel.mention}")
        header = format_template(header_template, emoji=emoji, star_count=str(count), channel=channel)

        embed_cfg = fmt.get("embed", {})
        content = message.content or ""
        image_url = message.attachments[0].url if message.attachments else ""
        msg_link = f"https://discord.com/channels/{guild.id}/{channel.id}/{message.id}"

        embed = build_embed(embed_cfg,
                            user=message.author, content=content, image=image_url,
                            message_link=msg_link, star_count=str(count), channel=channel)
        if not embed.color:
            embed.color = 0xFFD700

        if existing and existing["starboard_message_id"]:
            try:
                sb_msg = await sb_channel.fetch_message(existing["starboard_message_id"])
                await sb_msg.edit(content=header, embed=embed)
            except Exception:
                pass
        else:
            try:
                sb_msg = await sb_channel.send(content=header, embed=embed)
                async with self.bot.pool.acquire() as conn:
                    await conn.execute(
                        "INSERT INTO starboard_messages (guild_id, message_id, starboard_message_id, channel_id, author_id, star_count) VALUES ($1,$2,$3,$4,$5,$6) ON CONFLICT DO NOTHING",
                        guild.id, message.id, sb_msg.id, channel.id, message.author.id, count
                    )
            except Exception:
                pass

    @commands.group(name="starboard", invoke_without_command=True)
    async def starboard_cmd(self, ctx):
        await ctx.send("Usage: `!starboard top [count]` | `!starboard stats [@user]` | `!starboard clear @user`")

    @starboard_cmd.command(name="top")
    async def sb_top(self, ctx, count: int = 10):
        async with self.bot.pool.acquire() as conn:
            rows = await conn.fetch("SELECT message_id, channel_id, author_id, star_count FROM starboard_messages WHERE guild_id=$1 ORDER BY star_count DESC LIMIT $2",
                                    ctx.guild.id, count)
        if not rows:
            config = await self.bot.config_loader.get_config(ctx.guild.id)
            msgs = self._cfg(config).get("messages", {})
            await ctx.send(msgs.get("starboard_empty", "No starred messages found"))
            return
        lines = [f"**{r['star_count']}⭐** — <@{r['author_id']}> in <#{r['channel_id']}> [[jump](https://discord.com/channels/{ctx.guild.id}/{r['channel_id']}/{r['message_id']})]" for r in rows]
        await ctx.send("**Top Starred Messages:**\n" + "\n".join(lines))

    @starboard_cmd.command(name="stats")
    async def sb_stats(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        async with self.bot.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT SUM(star_count) as total, COUNT(*) as msgs FROM starboard_messages WHERE guild_id=$1 AND author_id=$2",
                                      ctx.guild.id, target.id)
        if not row or not row["total"]:
            await ctx.send(f"No star data for {target.display_name}")
            return
        await ctx.send(f"**{target.display_name}** — **{row['total']}** total stars across **{row['msgs']}** messages")

    @starboard_cmd.command(name="clear")
    async def sb_clear(self, ctx, member: discord.Member):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        lvl = self.bot.get_cog("Levels")
        if lvl and not lvl.has_level(config, ctx.author, "starboard"):
            return
        async with self.bot.pool.acquire() as conn:
            await conn.execute("DELETE FROM starboard_messages WHERE guild_id=$1 AND author_id=$2", ctx.guild.id, member.id)
        await ctx.send(f"Starboard entries cleared for {member.display_name}")


async def setup(bot):
    await bot.add_cog(Starboard(bot))

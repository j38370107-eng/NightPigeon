import discord
from discord.ext import commands
from message_formatter import format_template


class Tags(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="tag")
    async def tag_cmd(self, ctx, *, name: str = None):
        config = await self.bot.config_loader.get_config(ctx.guild.id)
        cfg = config.get("plugins", {}).get("tags", {})
        if not cfg.get("enabled", True):
            return
        msgs = cfg.get("messages", {})
        tags = config.get("tags", {})

        if not name or name.strip().lower() == "list":
            if not tags:
                await ctx.send(msgs.get("tag_list_empty", "No tags created yet"))
                return
            lines = [f"`{k}` — {str(v)[:60]}" for k, v in list(tags.items())[:30]]
            await ctx.send("**Tags:**\n" + "\n".join(lines))
            return

        name = name.strip().lower()
        if name not in tags:
            await ctx.send(format_template(msgs.get("tag_not_found", "Tag {trigger} not found"), trigger=name))
            return

        await ctx.send(str(tags[name]))


async def setup(bot):
    await bot.add_cog(Tags(bot))

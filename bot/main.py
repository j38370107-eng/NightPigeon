import asyncio
import logging
import os
import ssl as ssl_lib
from pathlib import Path

import asyncpg
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

from config_loader import ConfigLoader

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("bot")

PLUGIN_DIR = Path(__file__).parent / "plugins"


class ZepBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents, case_insensitive=True, help_command=None)
        self.pool: asyncpg.Pool = None
        self.config_loader: ConfigLoader = None
        self.owner_id = int(os.getenv("BOT_OWNER_ID", 0))

    async def setup_hook(self):
        ssl_ctx = None
        if os.getenv("DB_SSL") == "true":
            ssl_ctx = ssl_lib.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl_lib.CERT_NONE
        self.pool = await asyncpg.create_pool(os.getenv("DATABASE_URL"), min_size=2, max_size=10, ssl=ssl_ctx)
        self.config_loader = ConfigLoader(self.pool)

        for plugin_file in sorted(PLUGIN_DIR.glob("*.py")):
            if plugin_file.name.startswith("_"):
                continue
            mod = f"plugins.{plugin_file.stem}"
            try:
                await self.load_extension(mod)
                logger.info(f"Loaded: {mod}")
            except Exception as e:
                logger.error(f"Failed to load {mod}: {e}", exc_info=True)

    async def on_ready(self):
        logger.info(f"Ready: {self.user} ({self.user.id})")
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT guild_id FROM whitelisted_guilds")
        whitelist = {r["guild_id"] for r in rows}
        for guild in list(self.guilds):
            if guild.id not in whitelist:
                logger.info(f"Leaving non-whitelisted guild: {guild.name}")
                await guild.leave()

    async def on_guild_join(self, guild: discord.Guild):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT 1 FROM whitelisted_guilds WHERE guild_id = $1", guild.id)
        if not row:
            try:
                owner = guild.owner or await self.fetch_user(guild.owner_id)
                await owner.send(f"Sorry, **{guild.name}** is not whitelisted to use this bot.")
            except Exception:
                pass
            try:
                bot_owner = await self.fetch_user(self.owner_id)
                await bot_owner.send(f"Tried to join non-whitelisted guild: **{guild.name}** ({guild.id}) — left.")
            except Exception:
                pass
            await guild.leave()

    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if not message.guild:
            if message.author.id == self.owner_id:
                await self.process_commands(message)
            return

        # Resolve aliases from YAML config before dispatch
        if message.content.startswith("!"):
            try:
                config = await self.config_loader.get_config(message.guild.id)
                aliases = config.get("plugins", {}).get("command_aliases", {}).get("config", {}).get("aliases", {})
                parts = message.content[1:].split(None, 1)
                if parts:
                    cmd = parts[0].lower()
                    if cmd in aliases:
                        rest = f" {parts[1]}" if len(parts) > 1 else ""
                        message.content = f"!{aliases[cmd]}{rest}"
            except Exception:
                pass

        await self.process_commands(message)

    async def on_command_error(self, ctx, error):
        if isinstance(error, (commands.CommandNotFound, commands.CheckFailure, commands.MissingRequiredArgument)):
            return
        logger.error(f"Command error in {ctx.command}: {error}", exc_info=error)

    async def is_whitelisted(self, guild_id: int) -> bool:
        async with self.pool.acquire() as conn:
            return bool(await conn.fetchrow("SELECT 1 FROM whitelisted_guilds WHERE guild_id = $1", guild_id))


bot = ZepBot()


@bot.check
async def global_whitelist_check(ctx: commands.Context):
    if ctx.author.id == bot.owner_id:
        return True
    if not ctx.guild:
        return False
    return await bot.is_whitelisted(ctx.guild.id)


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise ValueError("DISCORD_TOKEN not set")
    bot.run(token)

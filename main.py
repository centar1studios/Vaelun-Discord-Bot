import asyncio
import logging
import os
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv

from utils.database import Database


load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")
SYNC_COMMANDS = os.getenv("SYNC_COMMANDS", "false").lower() == "true"

if not TOKEN:
    raise RuntimeError("Missing DISCORD_TOKEN in your .env file.")


LOG_DIR = Path("data")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "bot.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger("centari")


EXTENSIONS = [
    "cogs.admin",
    "cogs.automod",
    "cogs.autoroles",
    "cogs.community",
    "cogs.confessions",
    "cogs.counting",
    "cogs.custom_embeds",
    "cogs.fonts",
    "cogs.help",
    "cogs.moderation",
    "cogs.persona",
    "cogs.reaction_roles",
    "cogs.status",
    "cogs.starboard",
    "cogs.sticky",
    "cogs.tickets",
    "cogs.welcome",
]


class CentariBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = True
        intents.messages = True
        intents.message_content = True
        intents.reactions = True

        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,
        )

        self.db = Database("data/database.json")

    async def setup_hook(self):
        logger.info("----------------------------------------")
        logger.info("Starting setup_hook...")
        logger.info("----------------------------------------")

        for extension in EXTENSIONS:
            try:
                await self.load_extension(extension)
                logger.info("Loaded %s", extension)
            except Exception:
                logger.exception("Failed to load %s", extension)

        if not SYNC_COMMANDS:
            logger.info("----------------------------------------")
            logger.info("Skipping slash command sync on startup.")
            logger.info("Set SYNC_COMMANDS=true in .env when you change slash commands.")
            logger.info("----------------------------------------")
            return

        try:
            if GUILD_ID:
                guild = discord.Object(id=int(GUILD_ID))
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                logger.info("Synced %s command(s) to guild %s", len(synced), GUILD_ID)
            else:
                synced = await self.tree.sync()
                logger.info("Synced %s global command(s)", len(synced))
        except Exception:
            logger.exception("Slash command sync failed.")
            raise

    async def on_ready(self):
        logger.info("----------------------------------------")
        logger.info("DEI IS ONLINE")
        logger.info("Logged in as: %s", self.user)
        logger.info("Bot ID: %s", self.user.id if self.user else "Unknown")
        logger.info("Connected guilds: %s", len(self.guilds))
        logger.info("----------------------------------------")

        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="over Centari Studios",
            )
        )


async def main():
    bot = CentariBot()

    async with bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())

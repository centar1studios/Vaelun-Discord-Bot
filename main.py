import asyncio
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from utils.database import Database


load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")

if not TOKEN:
    raise RuntimeError("Missing DISCORD_TOKEN in your .env file.")


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
            help_command=None
        )

        self.db = Database("data/database.json")

    async def setup_hook(self):
        extensions = [
            "cogs.admin",
            "cogs.automod",
            "cogs.community",
            "cogs.help",
            "cogs.moderation",
            "cogs.persona",
            "cogs.tickets",
            "cogs.welcome",
        ]

        for extension in extensions:
            await self.load_extension(extension)
            print(f"Loaded {extension}")

        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            print(f"Synced {len(synced)} command(s) to guild {GUILD_ID}")
        else:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} global command(s)")

    async def on_ready(self):
        print(f"Logged in as {self.user} | ID: {self.user.id}")

        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="over Centari Studios"
            )
        )


async def main():
    bot = CentariBot()

    async with bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())

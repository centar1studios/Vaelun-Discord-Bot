import os

import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import success_embed, error_embed, info_embed


DEFAULT_STATUS = {
    "activity_type": "watching",
    "text": "over Centari Studios",
    "discord_status": "online",
}


ACTIVITY_TYPES = {
    "playing": discord.ActivityType.playing,
    "watching": discord.ActivityType.watching,
    "listening": discord.ActivityType.listening,
    "competing": discord.ActivityType.competing,
}

DISCORD_STATUSES = {
    "online": discord.Status.online,
    "idle": discord.Status.idle,
    "dnd": discord.Status.dnd,
}


class StatusGroup(app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__(name="status", description="Manage the bot status.")
        self.bot = bot
        self.owner_id = os.getenv("OWNER_ID")

    def is_allowed(self, interaction: discord.Interaction) -> bool:
        if self.owner_id:
            return str(interaction.user.id) == str(self.owner_id)

        if interaction.user.guild_permissions.administrator:
            return True

        return False

    def get_status_config(self) -> dict:
        data = self.bot.db.load()
        status_config = data.get("bot_status")

        if not isinstance(status_config, dict):
            status_config = DEFAULT_STATUS.copy()
            data["bot_status"] = status_config
            self.bot.db.save(data)

        for key, value in DEFAULT_STATUS.items():
            if key not in status_config:
                status_config[key] = value

        data["bot_status"] = status_config
        self.bot.db.save(data)

        return status_config

    def save_status_config(self, status_config: dict):
        data = self.bot.db.load()
        data["bot_status"] = status_config
        self.bot.db.save(data)

    async def apply_status(self, status_config: dict):
        activity_type_name = status_config.get("activity_type", DEFAULT_STATUS["activity_type"])
        text = status_config.get("text", DEFAULT_STATUS["text"])
        discord_status_name = status_config.get("discord_status", DEFAULT_STATUS["discord_status"])

        activity_type = ACTIVITY_TYPES.get(activity_type_name, discord.ActivityType.watching)
        discord_status = DISCORD_STATUSES.get(discord_status_name, discord.Status.online)

        activity = discord.Activity(
            type=activity_type,
            name=text,
        )

        await self.bot.change_presence(
            status=discord_status,
            activity=activity,
        )

    @app_commands.command(name="view", description="View the current saved bot status.")
    async def view(self, interaction: discord.Interaction):
        status_config = self.get_status_config()

        description = (
            f"**Activity Type:** `{status_config.get('activity_type')}`\n"
            f"**Text:** `{status_config.get('text')}`\n"
            f"**Discord Status:** `{status_config.get('discord_status')}`"
        )

        await interaction.response.send_message(
            embed=info_embed("Bot Status", description),
            ephemeral=True,
        )

    @app_commands.command(name="set", description="Set the bot status.")
    @app_commands.choices(
        activity_type=[
            app_commands.Choice(name="Playing", value="playing"),
            app_commands.Choice(name="Watching", value="watching"),
            app_commands.Choice(name="Listening", value="listening"),
            app_commands.Choice(name="Competing", value="competing"),
        ],
        discord_status=[
            app_commands.Choice(name="Online", value="online"),
            app_commands.Choice(name="Idle", value="idle"),
            app_commands.Choice(name="Do Not Disturb", value="dnd"),
        ],
    )
    async def set_status(
        self,
        interaction: discord.Interaction,
        activity_type: app_commands.Choice[str],
        text: str,
        discord_status: app_commands.Choice[str] | None = None,
    ):
        if not self.is_allowed(interaction):
            await interaction.response.send_message(
                embed=error_embed("Only the bot owner can change the global bot status."),
                ephemeral=True,
            )
            return

        text = text.strip()

        if not text:
            await interaction.response.send_message(
                embed=error_embed("Status text cannot be empty."),
                ephemeral=True,
            )
            return

        if len(text) > 128:
            await interaction.response.send_message(
                embed=error_embed("Status text must be 128 characters or less."),
                ephemeral=True,
            )
            return

        status_config = {
            "activity_type": activity_type.value,
            "text": text,
            "discord_status": discord_status.value if discord_status else "online",
            "updated_by": interaction.user.id,
        }

        self.save_status_config(status_config)
        await self.apply_status(status_config)

        await interaction.response.send_message(
            embed=success_embed(
                f"Bot status updated to `{activity_type.value} {text}`."
            ),
            ephemeral=True,
        )

    @app_commands.command(name="reset", description="Reset the bot status back to default.")
    async def reset(self, interaction: discord.Interaction):
        if not self.is_allowed(interaction):
            await interaction.response.send_message(
                embed=error_embed("Only the bot owner can reset the global bot status."),
                ephemeral=True,
            )
            return

        status_config = DEFAULT_STATUS.copy()

        self.save_status_config(status_config)
        await self.apply_status(status_config)

        await interaction.response.send_message(
            embed=success_embed("Bot status reset to default."),
            ephemeral=True,
        )


class Status(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.group = StatusGroup(bot)
        self.bot.tree.add_command(self.group)

    @commands.Cog.listener()
    async def on_ready(self):
        status_config = self.group.get_status_config()
        await self.group.apply_status(status_config)


async def setup(bot: commands.Bot):
    await bot.add_cog(Status(bot))

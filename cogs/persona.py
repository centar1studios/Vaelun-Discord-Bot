import re

import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import persona_embed, success_embed, error_embed


HEX_RE = re.compile(r"^#?[0-9A-Fa-f]{6}$")


class PersonaGroup(app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__(name="persona", description="Customize this server's Persona.")
        self.bot = bot

    @app_commands.command(name="view", description="View this server's Persona.")
    async def view(self, interaction: discord.Interaction):
        persona = self.bot.db.get_persona(interaction.guild.id)

        description = f"""
**Name:** {persona["name"]}
**Bio:** {persona["bio"]}
**Color:** {persona["color"]}
**Footer:** {persona["footer"]}
**Avatar URL:** {persona["avatar_url"] or "None"}
"""

        await interaction.response.send_message(
            embed=persona_embed(persona, "Server Persona", description)
        )

    @app_commands.command(name="name", description="Set Persona name.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_name(self, interaction: discord.Interaction, name: str):
        self.bot.db.update_persona(interaction.guild.id, "name", name)
        await interaction.response.send_message(
            embed=success_embed("Persona name updated."),
            ephemeral=True,
        )

    @app_commands.command(name="bio", description="Set Persona bio.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def bio(self, interaction: discord.Interaction, bio: str):
        if len(bio) > 500:
            await interaction.response.send_message(
                embed=error_embed("Bio must be 500 characters or less."),
                ephemeral=True,
            )
            return

        self.bot.db.update_persona(interaction.guild.id, "bio", bio)
        await interaction.response.send_message(
            embed=success_embed("Persona bio updated."),
            ephemeral=True,
        )

    @app_commands.command(name="avatar", description="Set Persona avatar URL used in embeds.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def avatar(self, interaction: discord.Interaction, avatar_url: str):
        if not avatar_url.startswith("http://") and not avatar_url.startswith("https://"):
            await interaction.response.send_message(
                embed=error_embed("Use a valid image URL."),
                ephemeral=True,
            )
            return

        self.bot.db.update_persona(interaction.guild.id, "avatar_url", avatar_url)
        await interaction.response.send_message(
            embed=success_embed("Persona avatar updated."),
            ephemeral=True,
        )

    @app_commands.command(name="color", description="Set Persona color. Example: #9B7BFF")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def color(self, interaction: discord.Interaction, color: str):
        if not HEX_RE.match(color):
            await interaction.response.send_message(
                embed=error_embed("Use a valid hex color like #9B7BFF."),
                ephemeral=True,
            )
            return

        if not color.startswith("#"):
            color = f"#{color}"

        self.bot.db.update_persona(interaction.guild.id, "color", color)
        await interaction.response.send_message(
            embed=success_embed("Persona color updated."),
            ephemeral=True,
        )

    @app_commands.command(name="footer", description="Set Persona footer.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def footer(self, interaction: discord.Interaction, footer: str):
        self.bot.db.update_persona(interaction.guild.id, "footer", footer)
        await interaction.response.send_message(
            embed=success_embed("Persona footer updated."),
            ephemeral=True,
        )

    @app_commands.command(name="nickname", description="Set bot nickname in this server.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def nickname(self, interaction: discord.Interaction, nickname: str):
        try:
            await interaction.guild.me.edit(nick=nickname)
            await interaction.response.send_message(
                embed=success_embed("Bot nickname updated."),
                ephemeral=True,
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=error_embed("I need permission to change my nickname."),
                ephemeral=True,
            )

    @app_commands.command(name="reset", description="Reset this server's Persona.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def reset(self, interaction: discord.Interaction):
        guild_data = self.bot.db.get_guild(interaction.guild.id)

        guild_data["persona"] = {
            "name": "Centari Studios",
            "bio": (
                "A free all-in-one Discord bot for moderation, tickets, safety, "
                "community tools, and creative server management."
            ),
            "avatar_url": None,
            "color": "#9B7BFF",
            "footer": "Powered by Centari Studios",
        }

        self.bot.db.update_guild(interaction.guild.id, guild_data)
        await interaction.response.send_message(
            embed=success_embed("Persona reset."),
            ephemeral=True,
        )


class Persona(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.tree.add_command(PersonaGroup(bot))


async def setup(bot: commands.Bot):
    await bot.add_cog(Persona(bot))

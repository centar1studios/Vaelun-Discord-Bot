import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import success_embed, error_embed, info_embed


class AutoRoleGroup(app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__(name="autorole", description="Automatic role tools.")
        self.bot = bot

    @app_commands.command(name="set", description="Set the role new members receive when they join.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_autorole(
        self,
        interaction: discord.Interaction,
        role: discord.Role,
    ):
        me = interaction.guild.me

        if role.is_default():
            await interaction.response.send_message(
                embed=error_embed("You cannot use `@everyone` as the autorole."),
                ephemeral=True,
            )
            return

        if role.managed:
            await interaction.response.send_message(
                embed=error_embed("That role is managed by an integration or bot, so I cannot assign it."),
                ephemeral=True,
            )
            return

        if interaction.guild.owner_id != interaction.user.id and role >= interaction.user.top_role:
            await interaction.response.send_message(
                embed=error_embed("You cannot set an autorole equal to or higher than your highest role."),
                ephemeral=True,
            )
            return

        if me and role >= me.top_role:
            await interaction.response.send_message(
                embed=error_embed("I cannot assign that role because it is equal to or higher than my highest role."),
                ephemeral=True,
            )
            return

        self.bot.db.update_setting(interaction.guild.id, "autorole_id", role.id)

        await interaction.response.send_message(
            embed=success_embed(f"Autorole set to {role.mention}. New members will receive this role when they join."),
            ephemeral=True,
        )

    @app_commands.command(name="clear", description="Clear the current autorole.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def clear_autorole(self, interaction: discord.Interaction):
        self.bot.db.update_setting(interaction.guild.id, "autorole_id", None)

        await interaction.response.send_message(
            embed=success_embed("Autorole cleared. New members will no longer receive an automatic role."),
            ephemeral=True,
        )

    @app_commands.command(name="show", description="Show the current autorole.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def show_autorole(self, interaction: discord.Interaction):
        role_id = self.bot.db.get_setting(interaction.guild.id, "autorole_id")

        if not role_id:
            await interaction.response.send_message(
                embed=info_embed("Autorole", "No autorole is currently configured."),
                ephemeral=True,
            )
            return

        try:
            role = interaction.guild.get_role(int(role_id))
        except (ValueError, TypeError):
            role = None

        if not role:
            await interaction.response.send_message(
                embed=info_embed(
                    "Autorole",
                    f"An autorole is saved, but the role no longer exists.\nSaved role ID: `{role_id}`",
                ),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=info_embed("Autorole", f"New members currently receive {role.mention}."),
            ephemeral=True,
        )


class TestAutoRoleGroup(app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__(name="test-autorole", description="Test autorole tools.")
        self.bot = bot

    @app_commands.command(name="check", description="Check if the bot can assign the current autorole.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def check(self, interaction: discord.Interaction):
        role_id = self.bot.db.get_setting(interaction.guild.id, "autorole_id")

        if not role_id:
            await interaction.response.send_message(
                embed=error_embed("No autorole is configured."),
                ephemeral=True,
            )
            return

        try:
            role = interaction.guild.get_role(int(role_id))
        except (ValueError, TypeError):
            role = None

        if not role:
            await interaction.response.send_message(
                embed=error_embed(f"The configured autorole no longer exists. Saved role ID: `{role_id}`"),
                ephemeral=True,
            )
            return

        me = interaction.guild.me

        if role.is_default():
            await interaction.response.send_message(
                embed=error_embed("The configured autorole is `@everyone`, which cannot be assigned."),
                ephemeral=True,
            )
            return

        if role.managed:
            await interaction.response.send_message(
                embed=error_embed("The configured autorole is managed by an integration or bot, so I cannot assign it."),
                ephemeral=True,
            )
            return

        if me and role >= me.top_role:
            await interaction.response.send_message(
                embed=error_embed(
                    f"I cannot assign {role.mention} because it is equal to or higher than my highest role."
                ),
                ephemeral=True,
            )
            return

        if not interaction.guild.me.guild_permissions.manage_roles:
            await interaction.response.send_message(
                embed=error_embed("I do not have the `Manage Roles` permission."),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=success_embed(
                f"Autorole check passed. I should be able to assign {role.mention} to new members."
            ),
            ephemeral=True,
        )


class AutoRoles(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.tree.add_command(AutoRoleGroup(bot))
        self.bot.tree.add_command(TestAutoRoleGroup(bot))


async def setup(bot: commands.Bot):
    await bot.add_cog(AutoRoles(bot))

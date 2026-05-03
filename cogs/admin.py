import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import success_embed, error_embed, info_embed


class ConfigGroup(app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__(name="config", description="Configure Centari Studios.")
        self.bot = bot

    @app_commands.command(name="set-log-channel", description="Set the main logging channel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_log_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        self.bot.db.update_setting(interaction.guild.id, "log_channel_id", channel.id)
        await interaction.response.send_message(embed=success_embed(f"Log channel set to {channel.mention}."), ephemeral=True)

    @app_commands.command(name="set-staff-role", description="Set the staff role.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_staff_role(self, interaction: discord.Interaction, role: discord.Role):
        self.bot.db.update_setting(interaction.guild.id, "staff_role_id", role.id)
        await interaction.response.send_message(embed=success_embed(f"Staff role set to {role.mention}."), ephemeral=True)

    @app_commands.command(name="set-welcome-channel", description="Set the welcome channel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_welcome_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        self.bot.db.update_setting(interaction.guild.id, "welcome_channel_id", channel.id)
        await interaction.response.send_message(embed=success_embed(f"Welcome channel set to {channel.mention}."), ephemeral=True)

    @app_commands.command(name="set-leave-channel", description="Set the leave channel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_leave_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        self.bot.db.update_setting(interaction.guild.id, "leave_channel_id", channel.id)
        await interaction.response.send_message(embed=success_embed(f"Leave channel set to {channel.mention}."), ephemeral=True)

    @app_commands.command(name="set-verified-role", description="Set the verification role.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_verified_role(self, interaction: discord.Interaction, role: discord.Role):
        self.bot.db.update_setting(interaction.guild.id, "verified_role_id", role.id)
        await interaction.response.send_message(embed=success_embed(f"Verified role set to {role.mention}."), ephemeral=True)

    @app_commands.command(name="view", description="View server configuration.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def view(self, interaction: discord.Interaction):
        settings = self.bot.db.get_guild(interaction.guild.id)["settings"]

        description = "\n".join([
            f"**Staff Role:** {settings.get('staff_role_id')}",
            f"**Log Channel:** {settings.get('log_channel_id')}",
            f"**Ticket Category:** {settings.get('ticket_category_id')}",
            f"**Transcript Channel:** {settings.get('transcript_channel_id')}",
            f"**Welcome Channel:** {settings.get('welcome_channel_id')}",
            f"**Leave Channel:** {settings.get('leave_channel_id')}",
            f"**Verified Role:** {settings.get('verified_role_id')}",
        ])

        await interaction.response.send_message(embed=info_embed("Centari Config", description), ephemeral=True)


class AdminTools(app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__(name="admin", description="Admin utilities, health, backups, and role restore.")
        self.bot = bot

    @app_commands.command(name="health", description="View a basic server health report.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def health(self, interaction: discord.Interaction):
        guild = interaction.guild

        open_tickets = 0
        data = self.bot.db.load()

        for ticket in data["tickets"].values():
            if ticket["guild_id"] == guild.id and ticket["status"] == "open":
                open_tickets += 1

        description = f"""
**Server:** {guild.name}
**Members:** {guild.member_count}
**Channels:** {len(guild.channels)}
**Roles:** {len(guild.roles)}
**Open Tickets:** {open_tickets}
**Boost Level:** {guild.premium_tier}
"""

        await interaction.response.send_message(embed=info_embed("Server Health", description), ephemeral=True)

    @app_commands.command(name="backup-create", description="Create a simple server backup snapshot.")
    @app_commands.checks.has_permissions(administrator=True)
    async def backup_create(self, interaction: discord.Interaction):
        guild = interaction.guild

        snapshot = {
            "name": guild.name,
            "roles": [
                {
                    "name": role.name,
                    "color": str(role.color),
                    "permissions": role.permissions.value
                }
                for role in guild.roles
                if not role.is_default()
            ],
            "channels": [
                {
                    "name": channel.name,
                    "type": str(channel.type),
                    "category": channel.category.name if getattr(channel, "category", None) else None
                }
                for channel in guild.channels
            ]
        }

        backup_id = self.bot.db.create_backup(guild.id, snapshot)

        await interaction.response.send_message(
            embed=success_embed(f"Backup created with ID `{backup_id}`. Restore code is intentionally not added yet because restore tools can be dangerous."),
            ephemeral=True
        )

    @app_commands.command(name="restore-roles", description="Manually restore saved roles for a user.")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def restore_roles(self, interaction: discord.Interaction, member: discord.Member):
        saved_role_ids = self.bot.db.get_saved_roles(interaction.guild.id, member.id)

        if not saved_role_ids:
            await interaction.response.send_message(embed=error_embed("No saved roles found for that member."), ephemeral=True)
            return

        restored = []

        for role_id in saved_role_ids:
            role = interaction.guild.get_role(role_id)

            if role and role < interaction.guild.me.top_role:
                try:
                    await member.add_roles(role, reason="Centari auto role restore")
                    restored.append(role.name)
                except discord.Forbidden:
                    pass

        await interaction.response.send_message(
            embed=success_embed(f"Restored roles: {', '.join(restored) if restored else 'None'}"),
            ephemeral=True
        )


class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.tree.add_command(ConfigGroup(bot))
        self.bot.tree.add_command(AdminTools(bot))


async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))

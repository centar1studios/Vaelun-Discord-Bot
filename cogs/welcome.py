import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import success_embed, info_embed


class WelcomeGroup(app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__(name="welcome", description="Welcome, leave, and verification tools.")
        self.bot = bot

    @app_commands.command(name="enable", description="Enable welcome messages.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def enable(self, interaction: discord.Interaction):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        guild_data["welcome"]["enabled"] = True
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(embed=success_embed("Welcome messages enabled."), ephemeral=True)

    @app_commands.command(name="disable", description="Disable welcome messages.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def disable(self, interaction: discord.Interaction):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        guild_data["welcome"]["enabled"] = False
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(embed=success_embed("Welcome messages disabled."), ephemeral=True)

    @app_commands.command(name="message", description="Set welcome message. Use {user} and {server}.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def message(self, interaction: discord.Interaction, message: str):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        guild_data["welcome"]["message"] = message
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(embed=success_embed("Welcome message updated."), ephemeral=True)

    @app_commands.command(name="test", description="Test the welcome message.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def test(self, interaction: discord.Interaction):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        text = guild_data["welcome"]["message"]
        text = text.replace("{user}", interaction.user.mention).replace("{server}", interaction.guild.name)

        await interaction.response.send_message(text)


class LeaveGroup(app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__(name="leave", description="Leave message tools.")
        self.bot = bot

    @app_commands.command(name="enable", description="Enable leave messages.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def enable(self, interaction: discord.Interaction):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        guild_data["leave"]["enabled"] = True
        self.bot.db.update_guild(interaction.guild.id, guild_data)
        await interaction.response.send_message(embed=success_embed("Leave messages enabled."), ephemeral=True)

    @app_commands.command(name="disable", description="Disable leave messages.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def disable(self, interaction: discord.Interaction):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        guild_data["leave"]["enabled"] = False
        self.bot.db.update_guild(interaction.guild.id, guild_data)
        await interaction.response.send_message(embed=success_embed("Leave messages disabled."), ephemeral=True)

    @app_commands.command(name="message", description="Set leave message. Use {user} and {server}.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def message(self, interaction: discord.Interaction, message: str):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        guild_data["leave"]["message"] = message
        self.bot.db.update_guild(interaction.guild.id, guild_data)
        await interaction.response.send_message(embed=success_embed("Leave message updated."), ephemeral=True)


class VerifyButton(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Verify", style=discord.ButtonStyle.success, custom_id="centari_verify_button")
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        role_id = self.bot.db.get_setting(interaction.guild.id, "verified_role_id")

        if not role_id:
            await interaction.response.send_message("No verified role has been configured.", ephemeral=True)
            return

        role = interaction.guild.get_role(int(role_id))

        if not role:
            await interaction.response.send_message("The verified role no longer exists.", ephemeral=True)
            return

        await interaction.user.add_roles(role, reason="Centari verification")
        await interaction.response.send_message("You are verified!", ephemeral=True)


class VerificationGroup(app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__(name="verification", description="Verification tools.")
        self.bot = bot

    @app_commands.command(name="panel", description="Send a verification panel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def panel(self, interaction: discord.Interaction):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        message = guild_data["verification"]["message"]

        embed = info_embed("Verification", message)

        await interaction.response.send_message(embed=embed, view=VerifyButton(self.bot))

    @app_commands.command(name="message", description="Set verification panel message.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def message(self, interaction: discord.Interaction, message: str):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        guild_data["verification"]["message"] = message
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(embed=success_embed("Verification message updated."), ephemeral=True)


class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.tree.add_command(WelcomeGroup(bot))
        self.bot.tree.add_command(LeaveGroup(bot))
        self.bot.tree.add_command(VerificationGroup(bot))

    async def cog_load(self):
        self.bot.add_view(VerifyButton(self.bot))

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild_data = self.bot.db.get_guild(member.guild.id)

        saved_roles = self.bot.db.get_saved_roles(member.guild.id, member.id)

        for role_id in saved_roles:
            role = member.guild.get_role(role_id)
            if role and role < member.guild.me.top_role:
                try:
                    await member.add_roles(role, reason="Centari auto restore roles")
                except discord.Forbidden:
                    pass

        autorole_id = guild_data["settings"].get("autorole_id")

        if autorole_id:
            role = member.guild.get_role(int(autorole_id))
            if role:
                try:
                    await member.add_roles(role, reason="Centari autorole")
                except discord.Forbidden:
                    pass

        if not guild_data["welcome"]["enabled"]:
            return

        channel_id = guild_data["settings"].get("welcome_channel_id")

        if not channel_id:
            return

        channel = member.guild.get_channel(int(channel_id))

        if not channel:
            return

        text = guild_data["welcome"]["message"]
        text = text.replace("{user}", member.mention).replace("{server}", member.guild.name)

        await channel.send(text)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        role_ids = [
            role.id for role in member.roles
            if not role.is_default()
        ]

        self.bot.db.save_roles(member.guild.id, member.id, role_ids)

        guild_data = self.bot.db.get_guild(member.guild.id)

        if not guild_data["leave"]["enabled"]:
            return

        channel_id = guild_data["settings"].get("leave_channel_id")

        if not channel_id:
            return

        channel = member.guild.get_channel(int(channel_id))

        if not channel:
            return

        text = guild_data["leave"]["message"]
        text = text.replace("{user}", str(member)).replace("{server}", member.guild.name)

        await channel.send(text)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        channel_id = self.bot.db.get_setting(guild.id, "ban_log_channel_id") or self.bot.db.get_setting(guild.id, "log_channel_id")

        if not channel_id:
            return

        channel = guild.get_channel(int(channel_id))

        if channel:
            await channel.send(embed=info_embed("Member Banned", f"{user} was banned from the server."))


async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot))

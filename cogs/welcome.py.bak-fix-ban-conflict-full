import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import success_embed, info_embed, error_embed


def format_welcome_message(message: str, member: discord.Member) -> str:
    return (
        message
        .replace("{user}", member.mention)
        .replace("{server}", member.guild.name)
    )


def format_leave_message(message: str, member: discord.Member) -> str:
    return (
        message
        .replace("{user}", str(member))
        .replace("{server}", member.guild.name)
    )


async def fetch_text_channel(guild: discord.Guild, channel_id):
    if not channel_id:
        return None

    try:
        channel = guild.get_channel(int(channel_id))

        if channel is None:
            channel = await guild.fetch_channel(int(channel_id))

        if isinstance(channel, discord.TextChannel):
            return channel

        return None

    except (discord.Forbidden, discord.NotFound, discord.HTTPException, ValueError, TypeError):
        return None


class WelcomeGroup(app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__(name="welcome", description="Welcome message tools.")
        self.bot = bot

    @app_commands.command(name="enable", description="Enable welcome messages.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def enable(self, interaction: discord.Interaction):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        guild_data["welcome"]["enabled"] = True
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(
            embed=success_embed("Welcome messages enabled."),
            ephemeral=True,
        )

    @app_commands.command(name="disable", description="Disable welcome messages.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def disable(self, interaction: discord.Interaction):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        guild_data["welcome"]["enabled"] = False
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(
            embed=success_embed("Welcome messages disabled."),
            ephemeral=True,
        )

    @app_commands.command(name="message", description="Set welcome message. Use {user} and {server}.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def message(self, interaction: discord.Interaction, message: str):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        guild_data["welcome"]["message"] = message
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(
            embed=success_embed("Welcome message updated."),
            ephemeral=True,
        )

    @app_commands.command(name="set-channel", description="Set the welcome channel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        self.bot.db.update_setting(interaction.guild.id, "welcome_channel_id", channel.id)

        await interaction.response.send_message(
            embed=success_embed(f"Welcome channel set to {channel.mention}."),
            ephemeral=True,
        )

    @app_commands.command(name="clear-channel", description="Clear the welcome channel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def clear_channel(self, interaction: discord.Interaction):
        self.bot.db.update_setting(interaction.guild.id, "welcome_channel_id", None)

        await interaction.response.send_message(
            embed=success_embed("Welcome channel cleared."),
            ephemeral=True,
        )

    @app_commands.command(name="show-channel", description="Show the current welcome channel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def show_channel(self, interaction: discord.Interaction):
        channel_id = self.bot.db.get_setting(interaction.guild.id, "welcome_channel_id")
        channel = await fetch_text_channel(interaction.guild, channel_id)

        if not channel:
            await interaction.response.send_message(
                embed=info_embed("Welcome Channel", "No welcome channel is configured."),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=info_embed("Welcome Channel", f"Welcome messages are currently sent to {channel.mention}."),
            ephemeral=True,
        )

    @app_commands.command(name="test", description="Test the welcome message here.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def test(self, interaction: discord.Interaction):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        text = format_welcome_message(guild_data["welcome"]["message"], interaction.user)

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

        await interaction.response.send_message(
            embed=success_embed("Leave messages enabled."),
            ephemeral=True,
        )

    @app_commands.command(name="disable", description="Disable leave messages.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def disable(self, interaction: discord.Interaction):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        guild_data["leave"]["enabled"] = False
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(
            embed=success_embed("Leave messages disabled."),
            ephemeral=True,
        )

    @app_commands.command(name="message", description="Set leave message. Use {user} and {server}.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def message(self, interaction: discord.Interaction, message: str):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        guild_data["leave"]["message"] = message
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(
            embed=success_embed("Leave message updated."),
            ephemeral=True,
        )

    @app_commands.command(name="set-channel", description="Set the leave channel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        self.bot.db.update_setting(interaction.guild.id, "leave_channel_id", channel.id)

        await interaction.response.send_message(
            embed=success_embed(f"Leave channel set to {channel.mention}."),
            ephemeral=True,
        )

    @app_commands.command(name="clear-channel", description="Clear the leave channel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def clear_channel(self, interaction: discord.Interaction):
        self.bot.db.update_setting(interaction.guild.id, "leave_channel_id", None)

        await interaction.response.send_message(
            embed=success_embed("Leave channel cleared."),
            ephemeral=True,
        )

    @app_commands.command(name="show-channel", description="Show the current leave channel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def show_channel(self, interaction: discord.Interaction):
        channel_id = self.bot.db.get_setting(interaction.guild.id, "leave_channel_id")
        channel = await fetch_text_channel(interaction.guild, channel_id)

        if not channel:
            await interaction.response.send_message(
                embed=info_embed("Leave Channel", "No leave channel is configured."),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=info_embed("Leave Channel", f"Leave messages are currently sent to {channel.mention}."),
            ephemeral=True,
        )


class BanLogGroup(app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__(name="ban-log", description="Ban log channel tools.")
        self.bot = bot

    @app_commands.command(name="set-channel", description="Set the ban log channel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        self.bot.db.update_setting(interaction.guild.id, "ban_log_channel_id", channel.id)

        await interaction.response.send_message(
            embed=success_embed(f"Ban log channel set to {channel.mention}."),
            ephemeral=True,
        )

    @app_commands.command(name="clear-channel", description="Clear the ban log channel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def clear_channel(self, interaction: discord.Interaction):
        self.bot.db.update_setting(interaction.guild.id, "ban_log_channel_id", None)

        await interaction.response.send_message(
            embed=success_embed(
                "Ban log channel cleared. Ban logs will fall back to the general log channel if one is configured."
            ),
            ephemeral=True,
        )

    @app_commands.command(name="show-channel", description="Show the current ban log channel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def show_channel(self, interaction: discord.Interaction):
        channel_id = self.bot.db.get_setting(interaction.guild.id, "ban_log_channel_id")
        channel = await fetch_text_channel(interaction.guild, channel_id)

        if not channel:
            await interaction.response.send_message(
                embed=info_embed("Ban Log Channel", "No dedicated ban log channel is configured."),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=info_embed("Ban Log Channel", f"Ban logs are currently sent to {channel.mention}."),
            ephemeral=True,
        )


class TestGroup(app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__(name="test", description="Test server messages safely.")
        self.bot = bot

    @app_commands.command(name="welcome", description="Test the configured welcome message in the welcome channel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def welcome(self, interaction: discord.Interaction):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        channel_id = guild_data["settings"].get("welcome_channel_id")
        channel = await fetch_text_channel(interaction.guild, channel_id)

        if not channel:
            await interaction.response.send_message(
                embed=error_embed("No valid welcome channel is configured."),
                ephemeral=True,
            )
            return

        text = format_welcome_message(guild_data["welcome"]["message"], interaction.user)

        try:
            await channel.send(text)
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=error_embed("I do not have permission to send in the welcome channel."),
                ephemeral=True,
            )
            return
        except discord.HTTPException as error:
            await interaction.response.send_message(
                embed=error_embed(f"Discord rejected the test welcome message: `{error}`"),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=success_embed(f"Test welcome message sent in {channel.mention}."),
            ephemeral=True,
        )

    @app_commands.command(name="leave", description="Test the configured leave message in the leave channel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def leave(self, interaction: discord.Interaction):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        channel_id = guild_data["settings"].get("leave_channel_id")
        channel = await fetch_text_channel(interaction.guild, channel_id)

        if not channel:
            await interaction.response.send_message(
                embed=error_embed("No valid leave channel is configured."),
                ephemeral=True,
            )
            return

        text = format_leave_message(guild_data["leave"]["message"], interaction.user)

        try:
            await channel.send(text)
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=error_embed("I do not have permission to send in the leave channel."),
                ephemeral=True,
            )
            return
        except discord.HTTPException as error:
            await interaction.response.send_message(
                embed=error_embed(f"Discord rejected the test leave message: `{error}`"),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=success_embed(f"Test leave message sent in {channel.mention}."),
            ephemeral=True,
        )

    @app_commands.command(name="ban", description="Test the ban log message without banning anyone.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def ban(self, interaction: discord.Interaction):
        channel_id = (
            self.bot.db.get_setting(interaction.guild.id, "ban_log_channel_id")
            or self.bot.db.get_setting(interaction.guild.id, "log_channel_id")
        )

        channel = await fetch_text_channel(interaction.guild, channel_id)

        if not channel:
            await interaction.response.send_message(
                embed=error_embed("No valid ban log channel or general log channel is configured."),
                ephemeral=True,
            )
            return

        embed = info_embed(
            "Member Banned",
            f"{interaction.user} was banned from the server.\n\nThis is a test message. No one was actually banned.",
        )

        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=error_embed("I do not have permission to send in the ban log channel."),
                ephemeral=True,
            )
            return
        except discord.HTTPException as error:
            await interaction.response.send_message(
                embed=error_embed(f"Discord rejected the test ban message: `{error}`"),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=success_embed(f"Test ban message sent in {channel.mention}."),
            ephemeral=True,
        )

    @app_commands.command(name="verification", description="Test the verification panel in the verification channel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def verification(self, interaction: discord.Interaction):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        channel_id = guild_data["settings"].get("verification_channel_id")
        channel = await fetch_text_channel(interaction.guild, channel_id)

        if not channel:
            await interaction.response.send_message(
                embed=error_embed("No valid verification channel is configured."),
                ephemeral=True,
            )
            return

        message = guild_data["verification"]["message"]
        embed = info_embed("Verification", message)

        try:
            await channel.send(embed=embed, view=VerifyButton(self.bot))
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=error_embed("I do not have permission to send in the verification channel."),
                ephemeral=True,
            )
            return
        except discord.HTTPException as error:
            await interaction.response.send_message(
                embed=error_embed(f"Discord rejected the test verification panel: `{error}`"),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=success_embed(f"Test verification panel sent in {channel.mention}."),
            ephemeral=True,
        )


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

        try:
            role = interaction.guild.get_role(int(role_id))
        except (ValueError, TypeError):
            role = None

        if not role:
            await interaction.response.send_message("The verified role no longer exists.", ephemeral=True)
            return

        try:
            await interaction.user.add_roles(role, reason="Centari verification")
        except discord.Forbidden:
            await interaction.response.send_message(
                "I do not have permission to give that role.",
                ephemeral=True,
            )
            return
        except discord.HTTPException:
            await interaction.response.send_message(
                "Discord rejected the role update.",
                ephemeral=True,
            )
            return

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

        channel_id = guild_data["settings"].get("verification_channel_id")
        channel = await fetch_text_channel(interaction.guild, channel_id)

        embed = info_embed("Verification", message)

        if channel:
            try:
                await channel.send(embed=embed, view=VerifyButton(self.bot))
            except discord.Forbidden:
                await interaction.response.send_message(
                    embed=error_embed("I do not have permission to send in the verification channel."),
                    ephemeral=True,
                )
                return
            except discord.HTTPException as error:
                await interaction.response.send_message(
                    embed=error_embed(f"Discord rejected the verification panel: `{error}`"),
                    ephemeral=True,
                )
                return

            await interaction.response.send_message(
                embed=success_embed(f"Verification panel sent in {channel.mention}."),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(embed=embed, view=VerifyButton(self.bot))

    @app_commands.command(name="message", description="Set verification panel message.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def message(self, interaction: discord.Interaction, message: str):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        guild_data["verification"]["message"] = message
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(
            embed=success_embed("Verification message updated."),
            ephemeral=True,
        )

    @app_commands.command(name="set-channel", description="Set the verification channel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        self.bot.db.update_setting(interaction.guild.id, "verification_channel_id", channel.id)

        await interaction.response.send_message(
            embed=success_embed(f"Verification channel set to {channel.mention}."),
            ephemeral=True,
        )

    @app_commands.command(name="clear-channel", description="Clear the verification channel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def clear_channel(self, interaction: discord.Interaction):
        self.bot.db.update_setting(interaction.guild.id, "verification_channel_id", None)

        await interaction.response.send_message(
            embed=success_embed("Verification channel cleared. `/verification panel` will send in the current channel."),
            ephemeral=True,
        )

    @app_commands.command(name="show-channel", description="Show the current verification channel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def show_channel(self, interaction: discord.Interaction):
        channel_id = self.bot.db.get_setting(interaction.guild.id, "verification_channel_id")
        channel = await fetch_text_channel(interaction.guild, channel_id)

        if not channel:
            await interaction.response.send_message(
                embed=info_embed("Verification Channel", "No verification channel is configured."),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=info_embed("Verification Channel", f"Verification panels are currently sent to {channel.mention}."),
            ephemeral=True,
        )

    @app_commands.command(name="set-role", description="Set the verified role.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_role(self, interaction: discord.Interaction, role: discord.Role):
        me = interaction.guild.me

        if role >= interaction.user.top_role and interaction.guild.owner_id != interaction.user.id:
            await interaction.response.send_message(
                embed=error_embed("You cannot configure a verified role equal to or higher than your highest role."),
                ephemeral=True,
            )
            return

        if me and role >= me.top_role:
            await interaction.response.send_message(
                embed=error_embed("I cannot give that role because it is equal to or higher than my highest role."),
                ephemeral=True,
            )
            return

        self.bot.db.update_setting(interaction.guild.id, "verified_role_id", role.id)

        await interaction.response.send_message(
            embed=success_embed(f"Verified role set to {role.mention}."),
            ephemeral=True,
        )

    @app_commands.command(name="clear-role", description="Clear the verified role.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def clear_role(self, interaction: discord.Interaction):
        self.bot.db.update_setting(interaction.guild.id, "verified_role_id", None)

        await interaction.response.send_message(
            embed=success_embed("Verified role cleared."),
            ephemeral=True,
        )

    @app_commands.command(name="show-role", description="Show the current verified role.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def show_role(self, interaction: discord.Interaction):
        role_id = self.bot.db.get_setting(interaction.guild.id, "verified_role_id")

        if not role_id:
            await interaction.response.send_message(
                embed=info_embed("Verified Role", "No verified role is configured."),
                ephemeral=True,
            )
            return

        try:
            role = interaction.guild.get_role(int(role_id))
        except (ValueError, TypeError):
            role = None

        if not role:
            await interaction.response.send_message(
                embed=info_embed("Verified Role", f"The configured role no longer exists: `{role_id}`"),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=info_embed("Verified Role", f"Verified users currently receive {role.mention}."),
            ephemeral=True,
        )


class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.tree.add_command(WelcomeGroup(bot))
        self.bot.tree.add_command(LeaveGroup(bot))
        self.bot.tree.add_command(BanLogGroup(bot))
        self.bot.tree.add_command(TestGroup(bot))
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
            try:
                role = member.guild.get_role(int(autorole_id))
            except (ValueError, TypeError):
                role = None

            if role:
                try:
                    await member.add_roles(role, reason="Centari autorole")
                except discord.Forbidden:
                    pass

        if not guild_data["welcome"]["enabled"]:
            return

        channel_id = guild_data["settings"].get("welcome_channel_id")
        channel = await fetch_text_channel(member.guild, channel_id)

        if not channel:
            return

        text = format_welcome_message(guild_data["welcome"]["message"], member)

        try:
            await channel.send(text)
        except (discord.Forbidden, discord.HTTPException):
            pass

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
        channel = await fetch_text_channel(member.guild, channel_id)

        if not channel:
            return

        text = format_leave_message(guild_data["leave"]["message"], member)

        try:
            await channel.send(text)
        except (discord.Forbidden, discord.HTTPException):
            pass

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        channel_id = (
            self.bot.db.get_setting(guild.id, "ban_log_channel_id")
            or self.bot.db.get_setting(guild.id, "log_channel_id")
        )

        channel = await fetch_text_channel(guild, channel_id)

        if channel:
            try:
                await channel.send(
                    embed=info_embed("Member Banned", f"{user} was banned from the server.")
                )
            except (discord.Forbidden, discord.HTTPException):
                pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot))

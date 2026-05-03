import datetime

import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import success_embed, error_embed, info_embed


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def log_action(self, guild: discord.Guild, embed: discord.Embed):
        log_id = self.bot.db.get_setting(guild.id, "log_channel_id")

        if not log_id:
            return

        channel = guild.get_channel(int(log_id))

        if channel:
            await channel.send(embed=embed)

    @app_commands.command(name="ban", description="Ban a member.")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided."):
        try:
            await member.ban(reason=reason)
            embed = success_embed(f"{member} was banned.\nReason: {reason}")
            await interaction.response.send_message(embed=embed)
            await self.log_action(interaction.guild, embed)
        except discord.Forbidden:
            await interaction.response.send_message(embed=error_embed("I cannot ban that member."), ephemeral=True)

    @app_commands.command(name="kick", description="Kick a member.")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided."):
        try:
            await member.kick(reason=reason)
            embed = success_embed(f"{member} was kicked.\nReason: {reason}")
            await interaction.response.send_message(embed=embed)
            await self.log_action(interaction.guild, embed)
        except discord.Forbidden:
            await interaction.response.send_message(embed=error_embed("I cannot kick that member."), ephemeral=True)

    @app_commands.command(name="timeout", description="Timeout a member.")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def timeout(self, interaction: discord.Interaction, member: discord.Member, minutes: app_commands.Range[int, 1, 40320], reason: str = "No reason provided."):
        until = discord.utils.utcnow() + datetime.timedelta(minutes=minutes)

        try:
            await member.timeout(until, reason=reason)
            embed = success_embed(f"{member} was timed out for {minutes} minute(s).\nReason: {reason}")
            await interaction.response.send_message(embed=embed)
            await self.log_action(interaction.guild, embed)
        except discord.Forbidden:
            await interaction.response.send_message(embed=error_embed("I cannot timeout that member."), ephemeral=True)

    @app_commands.command(name="warn", description="Warn a member.")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        warning = self.bot.db.add_warning(interaction.guild.id, member.id, interaction.user.id, reason)
        embed = success_embed(f"{member.mention} was warned.\nReason: {warning['reason']}")
        await interaction.response.send_message(embed=embed)
        await self.log_action(interaction.guild, embed)

    @app_commands.command(name="warnings", description="View warnings for a member.")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warnings(self, interaction: discord.Interaction, member: discord.Member):
        warnings = self.bot.db.get_warnings(interaction.guild.id, member.id)

        if not warnings:
            await interaction.response.send_message(embed=info_embed("Warnings", f"{member.mention} has no warnings."), ephemeral=True)
            return

        text = ""

        for index, warning in enumerate(warnings, start=1):
            text += f"**{index}.** {warning['reason']}\nModerator ID: `{warning['moderator_id']}`\n\n"

        await interaction.response.send_message(embed=info_embed(f"Warnings for {member}", text), ephemeral=True)

    @app_commands.command(name="clear", description="Clear messages from this channel.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clear(self, interaction: discord.Interaction, amount: app_commands.Range[int, 1, 100]):
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(embed=success_embed(f"Deleted {len(deleted)} message(s)."), ephemeral=True)

    @app_commands.command(name="lock", description="Lock this channel.")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def lock(self, interaction: discord.Interaction):
        await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
        await interaction.response.send_message(embed=success_embed("Channel locked."))

    @app_commands.command(name="unlock", description="Unlock this channel.")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def unlock(self, interaction: discord.Interaction):
        await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=None)
        await interaction.response.send_message(embed=success_embed("Channel unlocked."))


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))

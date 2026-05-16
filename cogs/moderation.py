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

        if not channel:
            return

        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            return
        except discord.HTTPException:
            return

    def clear_warning(self, guild_id: int, user_id: int, warning_number: int):
        data = self.bot.db.load()
        gid = str(guild_id)
        uid = str(user_id)

        warnings = data["warnings"].get(gid, {}).get(uid, [])

        if not warnings:
            return None

        index = warning_number - 1

        if index < 0 or index >= len(warnings):
            return None

        removed = warnings.pop(index)

        if not warnings:
            data["warnings"].get(gid, {}).pop(uid, None)

        self.bot.db.save(data)
        return removed

    def clear_all_warnings(self, guild_id: int, user_id: int):
        data = self.bot.db.load()
        gid = str(guild_id)
        uid = str(user_id)

        warnings = data["warnings"].get(gid, {}).get(uid, [])

        if not warnings:
            return []

        removed = warnings.copy()
        data["warnings"].get(gid, {}).pop(uid, None)

        self.bot.db.save(data)
        return removed

    @app_commands.command(name="ban", description="Ban a member.")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason provided.",
    ):
        try:
            await member.ban(reason=reason)
            embed = success_embed(f"{member} was banned.\nReason: {reason}")
            await interaction.response.send_message(embed=embed)
            await self.log_action(interaction.guild, embed)
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=error_embed("I cannot ban that member."),
                ephemeral=True,
            )

    @app_commands.command(name="kick", description="Kick a member.")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason provided.",
    ):
        try:
            await member.kick(reason=reason)
            embed = success_embed(f"{member} was kicked.\nReason: {reason}")
            await interaction.response.send_message(embed=embed)
            await self.log_action(interaction.guild, embed)
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=error_embed("I cannot kick that member."),
                ephemeral=True,
            )

    @app_commands.command(name="timeout", description="Timeout a member.")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def timeout(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        minutes: app_commands.Range[int, 1, 40320],
        reason: str = "No reason provided.",
    ):
        until = discord.utils.utcnow() + datetime.timedelta(minutes=minutes)

        try:
            await member.timeout(until, reason=reason)
            embed = success_embed(
                f"{member} was timed out for {minutes} minute(s).\nReason: {reason}"
            )
            await interaction.response.send_message(embed=embed)
            await self.log_action(interaction.guild, embed)
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=error_embed("I cannot timeout that member."),
                ephemeral=True,
            )

    @app_commands.command(name="warn", description="Warn a member.")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warn(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str,
    ):
        warning = self.bot.db.add_warning(
            interaction.guild.id,
            member.id,
            interaction.user.id,
            reason,
        )

        embed = success_embed(f"{member.mention} was warned.\nReason: {warning['reason']}")
        await interaction.response.send_message(embed=embed)
        await self.log_action(interaction.guild, embed)

    @app_commands.command(name="warnings", description="View warnings for a member.")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warnings(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
    ):
        warnings = self.bot.db.get_warnings(interaction.guild.id, member.id)

        if not warnings:
            await interaction.response.send_message(
                embed=info_embed("Warnings", f"{member.mention} has no warnings."),
                ephemeral=True,
            )
            return

        text = ""

        for index, warning in enumerate(warnings, start=1):
            text += (
                f"**{index}.** {warning['reason']}\n"
                f"Moderator ID: `{warning['moderator_id']}`\n\n"
            )

        if len(text) > 3800:
            text = text[:3800] + "\n..."

        await interaction.response.send_message(
            embed=info_embed(f"Warnings for {member}", text),
            ephemeral=True,
        )

    @app_commands.command(name="warn-clear", description="Clear one warning from a member.")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warn_clear(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        warning_number: app_commands.Range[int, 1, 100],
    ):
        removed = self.clear_warning(
            interaction.guild.id,
            member.id,
            warning_number,
        )

        if not removed:
            await interaction.response.send_message(
                embed=error_embed(
                    f"I could not find warning #{warning_number} for {member.mention}."
                ),
                ephemeral=True,
            )
            return

        embed = success_embed(
            f"Cleared warning #{warning_number} for {member.mention}.\n"
            f"Removed reason: {removed.get('reason', 'No reason found.')}"
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)
        await self.log_action(interaction.guild, embed)

    @app_commands.command(name="warn-clear-all", description="Clear all warnings from a member.")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warn_clear_all(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
    ):
        removed = self.clear_all_warnings(interaction.guild.id, member.id)

        if not removed:
            await interaction.response.send_message(
                embed=error_embed(f"{member.mention} has no warnings to clear."),
                ephemeral=True,
            )
            return

        embed = success_embed(
            f"Cleared **{len(removed)}** warning(s) from {member.mention}."
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)
        await self.log_action(interaction.guild, embed)

    @app_commands.command(name="clear", description="Clear messages from this channel.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clear(
        self,
        interaction: discord.Interaction,
        amount: app_commands.Range[int, 1, 100],
    ):
        await interaction.response.defer(ephemeral=True)

        try:
            deleted = await interaction.channel.purge(limit=amount)
        except discord.Forbidden:
            await interaction.followup.send(
                embed=error_embed("I do not have permission to delete messages here."),
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            embed=success_embed(f"Deleted {len(deleted)} message(s)."),
            ephemeral=True,
        )

    @app_commands.command(name="lock", description="Lock this channel.")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def lock(self, interaction: discord.Interaction):
        try:
            await interaction.channel.set_permissions(
                interaction.guild.default_role,
                send_messages=False,
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=error_embed("I do not have permission to lock this channel."),
                ephemeral=True,
            )
            return

        embed = success_embed("Channel locked.")
        await interaction.response.send_message(embed=embed)
        await self.log_action(interaction.guild, embed)

    @app_commands.command(name="unlock", description="Unlock this channel.")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def unlock(self, interaction: discord.Interaction):
        try:
            await interaction.channel.set_permissions(
                interaction.guild.default_role,
                send_messages=None,
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=error_embed("I do not have permission to unlock this channel."),
                ephemeral=True,
            )
            return

        embed = success_embed("Channel unlocked.")
        await interaction.response.send_message(embed=embed)
        await self.log_action(interaction.guild, embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))

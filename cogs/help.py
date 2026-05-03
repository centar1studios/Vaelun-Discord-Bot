import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import persona_embed


class Help(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="help", description="View Centari Studios commands and features.")
    async def help(self, interaction: discord.Interaction):
        persona = self.bot.db.get_persona(interaction.guild.id)

        embed = persona_embed(
            persona,
            "Centari Studios Help",
            "Choose a category below to view commands. Tiny command library goblin included."
        )

        embed.add_field(
            name="Core",
            value=(
                "`/help`\n"
                "`/persona view`\n"
                "`/admin health`\n"
                "`/config view`"
            ),
            inline=True
        )

        embed.add_field(
            name="Moderation",
            value=(
                "`/ban`\n"
                "`/kick`\n"
                "`/timeout`\n"
                "`/warn`\n"
                "`/warnings`\n"
                "`/clear`\n"
                "`/lock`\n"
                "`/unlock`"
            ),
            inline=True
        )

        embed.add_field(
            name="Tickets",
            value=(
                "`/ticket setup`\n"
                "`/ticket config`\n"
                "`/ticket close`\n"
                "`/ticket add`\n"
                "`/ticket remove`"
            ),
            inline=True
        )

        embed.add_field(
            name="Persona",
            value=(
                "`/persona view`\n"
                "`/persona name`\n"
                "`/persona bio`\n"
                "`/persona avatar`\n"
                "`/persona color`\n"
                "`/persona footer`\n"
                "`/persona nickname`\n"
                "`/persona reset`"
            ),
            inline=False
        )

        embed.add_field(
            name="Automod / Safety",
            value=(
                "`/automod toggle`\n"
                "`/automod mode`\n"
                "`/automod block-word`\n"
                "`/automod view`"
            ),
            inline=True
        )

        embed.add_field(
            name="Welcome / Leave / Verification",
            value=(
                "`/welcome enable`\n"
                "`/welcome disable`\n"
                "`/welcome message`\n"
                "`/welcome test`\n"
                "`/leave enable`\n"
                "`/leave disable`\n"
                "`/leave message`\n"
                "`/verification panel`\n"
                "`/verification message`"
            ),
            inline=True
        )

        embed.add_field(
            name="Community",
            value=(
                "`/community poll`\n"
                "`/community 8ball`\n"
                "`/community quote`\n"
                "`/community passport`\n"
                "`/roles button`\n"
                "`/level rank`\n"
                "`/economy balance`\n"
                "`/economy daily`"
            ),
            inline=True
        )

        embed.add_field(
            name="Resources / Suggestions / Mailbox",
            value=(
                "`/resource add`\n"
                "`/resource search`\n"
                "`/suggest submit`\n"
                "`/mailbox submit`"
            ),
            inline=True
        )

        embed.add_field(
            name="Study Tools",
            value=(
                "`/study pomodoro`\n"
                "`/study deadline`"
            ),
            inline=True
        )

        embed.add_field(
            name="Admin / Config",
            value=(
                "`/config set-log-channel`\n"
                "`/config set-staff-role`\n"
                "`/config set-welcome-channel`\n"
                "`/config set-leave-channel`\n"
                "`/config set-verified-role`\n"
                "`/admin backup-create`\n"
                "`/admin restore-roles`"
            ),
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Help(bot))

import datetime
import random
import time

import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import success_embed, error_embed, info_embed


class RoleButton(discord.ui.View):
    def __init__(self, role_id: int):
        super().__init__(timeout=None)
        self.role_id = role_id

    @discord.ui.button(label="Toggle Role", style=discord.ButtonStyle.primary)
    async def toggle_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = interaction.guild.get_role(self.role_id)

        if not role:
            await interaction.response.send_message("That role no longer exists.", ephemeral=True)
            return

        if role in interaction.user.roles:
            await interaction.user.remove_roles(role, reason="Centari reaction role remove")
            await interaction.response.send_message(f"Removed {role.mention}.", ephemeral=True)
        else:
            await interaction.user.add_roles(role, reason="Centari reaction role add")
            await interaction.response.send_message(f"Added {role.mention}.", ephemeral=True)


class RolesGroup(app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__(name="roles", description="Reaction role tools.")
        self.bot = bot

    @app_commands.command(name="button", description="Create a basic button role panel.")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def button(self, interaction: discord.Interaction, role: discord.Role, title: str = "Role Panel"):
        embed = info_embed(title, f"Click the button below to toggle {role.mention}.")
        await interaction.response.send_message(embed=embed, view=RoleButton(role.id))


class EconomyGroup(app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__(name="economy", description="Economy commands.")
        self.bot = bot

    @app_commands.command(name="balance", description="View your balance.")
    async def balance(self, interaction: discord.Interaction, member: discord.Member | None = None):
        member = member or interaction.user
        money = self.bot.db.get_money(interaction.guild.id, member.id)

        await interaction.response.send_message(
            embed=info_embed("Balance", f"{member.mention} has **{money['balance']}** coins.")
        )

    @app_commands.command(name="daily", description="Claim your daily coins.")
    async def daily(self, interaction: discord.Interaction):
        now = time.time()
        money = self.bot.db.get_money(interaction.guild.id, interaction.user.id)

        if now - money.get("last_daily", 0) < 86400:
            await interaction.response.send_message(
                embed=error_embed("You already claimed your daily reward."),
                ephemeral=True
            )
            return

        guild_data = self.bot.db.get_guild(interaction.guild.id)
        amount = guild_data["economy"]["daily_amount"]

        self.bot.db.add_money(interaction.guild.id, interaction.user.id, amount)
        self.bot.db.set_daily_time(interaction.guild.id, interaction.user.id, now)

        await interaction.response.send_message(embed=success_embed(f"You claimed **{amount}** coins."))


class LevelGroup(app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__(name="level", description="Leveling commands.")
        self.bot = bot

    @app_commands.command(name="rank", description="View your level.")
    async def rank(self, interaction: discord.Interaction, member: discord.Member | None = None):
        member = member or interaction.user
        level = self.bot.db.get_level(interaction.guild.id, member.id)

        await interaction.response.send_message(
            embed=info_embed("Rank", f"{member.mention}\n**Level:** {level['level']}\n**XP:** {level['xp']}")
        )


class CommunityGroup(app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__(name="community", description="Fun and community commands.")
        self.bot = bot

    @app_commands.command(name="poll", description="Create a simple yes/no poll.")
    async def poll(self, interaction: discord.Interaction, question: str):
        embed = info_embed("Poll", question)

        await interaction.response.send_message(embed=embed)
        message = await interaction.original_response()
        await message.add_reaction("✅")
        await message.add_reaction("❌")

    @app_commands.command(name="8ball", description="Ask the magic 8ball.")
    async def eight_ball(self, interaction: discord.Interaction, question: str):
        answers = [
            "Yes.",
            "No.",
            "Maybe.",
            "Ask again later.",
            "The goblin council says absolutely.",
            "The stars are being weird about this one."
        ]

        await interaction.response.send_message(embed=info_embed("8ball", random.choice(answers)))

    @app_commands.command(name="quote", description="Save a quote.")
    async def quote(self, interaction: discord.Interaction, quote: str):
        await interaction.response.send_message(embed=info_embed("Quote Saved", quote))

    @app_commands.command(name="passport", description="View a member passport profile.")
    async def passport(self, interaction: discord.Interaction, member: discord.Member | None = None):
        member = member or interaction.user
        level = self.bot.db.get_level(interaction.guild.id, member.id)
        money = self.bot.db.get_money(interaction.guild.id, member.id)

        joined = member.joined_at.strftime("%Y-%m-%d") if member.joined_at else "Unknown"

        description = f"""
**Member:** {member.mention}
**Joined:** {joined}
**Level:** {level["level"]}
**XP:** {level["xp"]}
**Coins:** {money["balance"]}
**Roles:** {len(member.roles) - 1}
"""

        await interaction.response.send_message(embed=info_embed("Member Passport", description))


class ResourceGroup(app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__(name="resource", description="Resource library and FAQ tools.")
        self.bot = bot

    @app_commands.command(name="add", description="Add a resource or FAQ entry.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def add(self, interaction: discord.Interaction, title: str, body: str, tags: str = "general"):
        resource_id = self.bot.db.add_resource(interaction.guild.id, title, body, tags)

        await interaction.response.send_message(
            embed=success_embed(f"Resource added with ID `{resource_id}`."),
            ephemeral=True
        )

    @app_commands.command(name="search", description="Search resources.")
    async def search(self, interaction: discord.Interaction, query: str):
        results = self.bot.db.search_resources(interaction.guild.id, query)

        if not results:
            await interaction.response.send_message(
                embed=error_embed("No resources found."),
                ephemeral=True
            )
            return

        text = ""

        for item in results[:5]:
            text += (
                f"**{item['id']}. {item['title']}**\n"
                f"{item['body'][:250]}\n"
                f"Tags: `{item['tags']}`\n\n"
            )

        await interaction.response.send_message(embed=info_embed("Resource Results", text))


class SuggestionsGroup(app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__(name="suggest", description="Suggestion system.")
        self.bot = bot

    @app_commands.command(name="submit", description="Submit a suggestion.")
    async def submit(self, interaction: discord.Interaction, suggestion: str):
        suggestion_id = self.bot.db.add_suggestion(interaction.guild.id, interaction.user.id, suggestion)

        channel_id = self.bot.db.get_setting(interaction.guild.id, "suggestion_channel_id")
        channel = interaction.guild.get_channel(int(channel_id)) if channel_id else None

        embed = info_embed(f"Suggestion #{suggestion_id}", suggestion)
        embed.add_field(name="Status", value="Under Review")

        if channel:
            msg = await channel.send(embed=embed)
            await msg.add_reaction("✅")
            await msg.add_reaction("❌")

        await interaction.response.send_message(
            embed=success_embed(f"Suggestion submitted with ID `{suggestion_id}`."),
            ephemeral=True
        )


class MailboxGroup(app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__(name="mailbox", description="Anonymous mailbox.")
        self.bot = bot

    @app_commands.command(name="submit", description="Submit an anonymous message to staff.")
    async def submit(self, interaction: discord.Interaction, message: str):
        channel_id = self.bot.db.get_setting(interaction.guild.id, "mailbox_review_channel_id")
        channel = interaction.guild.get_channel(int(channel_id)) if channel_id else None

        if not channel:
            await interaction.response.send_message(
                embed=error_embed("No mailbox review channel has been configured."),
                ephemeral=True
            )
            return

        embed = info_embed("Anonymous Mailbox Submission", message)
        embed.set_footer(text=f"Submitted by user ID {interaction.user.id}")

        await channel.send(embed=embed)

        await interaction.response.send_message(
            embed=success_embed("Your anonymous message was sent to staff."),
            ephemeral=True
        )


class StudyGroup(app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__(name="study", description="Study tools.")
        self.bot = bot

    @app_commands.command(name="pomodoro", description="Start a Pomodoro timer.")
    async def pomodoro(self, interaction: discord.Interaction, minutes: app_commands.Range[int, 1, 180] = 25):
        await interaction.response.send_message(
            embed=info_embed(
                "Pomodoro Started",
                f"{interaction.user.mention}, focus for **{minutes} minute(s)**. I will remind you here."
            )
        )

        await discord.utils.sleep_until(
            discord.utils.utcnow() + datetime.timedelta(minutes=minutes)
        )

        await interaction.channel.send(
            f"{interaction.user.mention}, Pomodoro done! Go stretch before your brain turns into soup."
        )

    @app_commands.command(name="deadline", description="Save a deadline reminder note.")
    async def deadline(self, interaction: discord.Interaction, title: str, due: str):
        await interaction.response.send_message(
            embed=success_embed(f"Deadline saved: **{title}** due **{due}**."),
            ephemeral=True
        )


class Community(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self.bot.tree.add_command(RolesGroup(bot))
        self.bot.tree.add_command(EconomyGroup(bot))
        self.bot.tree.add_command(LevelGroup(bot))
        self.bot.tree.add_command(CommunityGroup(bot))
        self.bot.tree.add_command(ResourceGroup(bot))
        self.bot.tree.add_command(SuggestionsGroup(bot))
        self.bot.tree.add_command(MailboxGroup(bot))
        self.bot.tree.add_command(StudyGroup(bot))

        self.level_cooldowns = {}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        guild_data = self.bot.db.get_guild(message.guild.id)

        if not guild_data["leveling"]["enabled"]:
            return

        key = (message.guild.id, message.author.id)
        now = time.time()

        cooldown = guild_data["leveling"]["cooldown_seconds"]

        if key in self.level_cooldowns and now - self.level_cooldowns[key] < cooldown:
            return

        self.level_cooldowns[key] = now

        amount = guild_data["leveling"]["xp_per_message"]
        level_data, leveled_up = self.bot.db.add_xp(message.guild.id, message.author.id, amount)

        if leveled_up:
            try:
                await message.channel.send(
                    f"{message.author.mention} leveled up to **Level {level_data['level']}**!"
                )
            except discord.Forbidden:
                pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Community(bot))

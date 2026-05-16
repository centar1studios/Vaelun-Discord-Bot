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
                ephemeral=True,
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


class EightBallAnswersGroup(app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__(name="8ball-answer", description="Manage custom 8-ball answers.")
        self.bot = bot

    @app_commands.command(name="add", description="Add a custom 8-ball answer.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def add(self, interaction: discord.Interaction, answer: str):
        if len(answer.strip()) > 200:
            await interaction.response.send_message(
                embed=error_embed("Please keep 8-ball answers under 200 characters."),
                ephemeral=True,
            )
            return

        added = self.bot.db.add_eight_ball_answer(interaction.guild.id, answer)

        if not added:
            await interaction.response.send_message(
                embed=error_embed("That answer is empty or already exists."),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=success_embed(f"Added 8-ball answer:\n`{answer.strip()}`"),
            ephemeral=True,
        )

    @app_commands.command(name="remove", description="Remove a custom 8-ball answer.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def remove(self, interaction: discord.Interaction, answer: str):
        removed = self.bot.db.remove_eight_ball_answer(interaction.guild.id, answer)

        if not removed:
            await interaction.response.send_message(
                embed=error_embed("I could not find that 8-ball answer."),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=success_embed(f"Removed 8-ball answer:\n`{answer.strip()}`"),
            ephemeral=True,
        )

    @app_commands.command(name="list", description="List this server's 8-ball answers.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def list_answers(self, interaction: discord.Interaction):
        answers = self.bot.db.get_eight_ball_answers(interaction.guild.id)

        text = ""

        for index, answer in enumerate(answers, start=1):
            text += f"**{index}.** {answer}\n"

        if len(text) > 3500:
            text = text[:3500] + "\n..."

        await interaction.response.send_message(
            embed=info_embed("8-ball Answers", text),
            ephemeral=True,
        )

    @app_commands.command(name="reset", description="Reset 8-ball answers back to defaults.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def reset(self, interaction: discord.Interaction):
        self.bot.db.reset_eight_ball_answers(interaction.guild.id)

        await interaction.response.send_message(
            embed=success_embed("8-ball answers reset to defaults."),
            ephemeral=True,
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

    @app_commands.command(name="8ball", description="Ask the magic 8-ball.")
    async def eight_ball(self, interaction: discord.Interaction, question: str):
        answers = self.bot.db.get_eight_ball_answers(interaction.guild.id)

        await interaction.response.send_message(
            embed=info_embed("8-ball", random.choice(answers))
        )

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
            ephemeral=True,
        )

    @app_commands.command(name="search", description="Search resources.")
    async def search(self, interaction: discord.Interaction, query: str):
        results = self.bot.db.search_resources(interaction.guild.id, query)

        if not results:
            await interaction.response.send_message(
                embed=error_embed("No resources found."),
                ephemeral=True,
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
            ephemeral=True,
        )


class StaffMailGroup(app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__(name="staffmail", description="Anonymous private messages to staff.")
        self.bot = bot

    @app_commands.command(name="config", description="Set the staffmail review channel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def config(self, interaction: discord.Interaction, review_channel: discord.TextChannel):
        self.bot.db.update_setting(interaction.guild.id, "mailbox_review_channel_id", review_channel.id)

        await interaction.response.send_message(
            embed=success_embed(f"Staffmail review channel set to {review_channel.mention}."),
            ephemeral=True,
        )

    @app_commands.command(name="submit", description="Send an anonymous private message/report to staff.")
    async def submit(
        self,
        interaction: discord.Interaction,
        message: str,
        link: str | None = None,
        attachment: discord.Attachment | None = None,
    ):
        channel_id = self.bot.db.get_setting(interaction.guild.id, "mailbox_review_channel_id")
        channel = interaction.guild.get_channel(int(channel_id)) if channel_id else None

        if not channel:
            await interaction.response.send_message(
                embed=error_embed("No staffmail review channel has been configured."),
                ephemeral=True,
            )
            return

        message = message.strip()
        link = link.strip() if link else None

        if not message:
            await interaction.response.send_message(
                embed=error_embed("Staffmail message cannot be empty."),
                ephemeral=True,
            )
            return

        if len(message) > 1800:
            await interaction.response.send_message(
                embed=error_embed("Please keep staffmail messages under 1800 characters."),
                ephemeral=True,
            )
            return

        if link and len(link) > 1000:
            await interaction.response.send_message(
                embed=error_embed("Please keep links under 1000 characters."),
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="Anonymous Staffmail",
            description=message,
            color=discord.Color.purple(),
        )

        embed.add_field(
            name="Submitted By",
            value=f"{interaction.user.mention}\n`{interaction.user.id}`",
            inline=False,
        )

        if link:
            embed.add_field(
                name="Reported Link / Message Link",
                value=link,
                inline=False,
            )

            if "discord.com/channels/" in link or "discordapp.com/channels/" in link:
                embed.add_field(
                    name="Link Type",
                    value="Discord message link",
                    inline=True,
                )
            else:
                embed.add_field(
                    name="Link Type",
                    value="External or general link",
                    inline=True,
                )

        file_to_send = None

        if attachment:
            embed.add_field(
                name="Attachment",
                value=f"[{attachment.filename}]({attachment.url})",
                inline=False,
            )

            if attachment.content_type and attachment.content_type.startswith("image/"):
                embed.set_image(url=attachment.url)

            try:
                file_to_send = await attachment.to_file()
            except discord.HTTPException:
                file_to_send = None

        embed.set_footer(text="Private staff message. Public users cannot see this.")

        try:
            if file_to_send:
                await channel.send(embed=embed, file=file_to_send)
            else:
                await channel.send(embed=embed)

        except discord.Forbidden:
            await interaction.response.send_message(
                embed=error_embed("I do not have permission to send in the staffmail review channel."),
                ephemeral=True,
            )
            return
        except discord.HTTPException as error:
            await interaction.response.send_message(
                embed=error_embed(f"Discord rejected the staffmail message: `{error}`"),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=success_embed("Your anonymous message/report was sent to staff."),
            ephemeral=True,
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
                f"{interaction.user.mention}, focus for **{minutes} minute(s)**. I will remind you here.",
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
            ephemeral=True,
        )


class Community(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self.bot.tree.add_command(RolesGroup(bot))
        self.bot.tree.add_command(EconomyGroup(bot))
        self.bot.tree.add_command(LevelGroup(bot))
        self.bot.tree.add_command(EightBallAnswersGroup(bot))
        self.bot.tree.add_command(CommunityGroup(bot))
        self.bot.tree.add_command(ResourceGroup(bot))
        self.bot.tree.add_command(SuggestionsGroup(bot))
        self.bot.tree.add_command(StaffMailGroup(bot))
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

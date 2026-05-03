import io
import re

import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import persona_embed, success_embed, error_embed
from utils.permissions import is_staff


def clean_channel_name(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9-]", "-", text)
    text = re.sub(r"-+", "-", text)
    return text[:80]


async def create_transcript(channel: discord.TextChannel) -> discord.File:
    lines = []

    async for message in channel.history(limit=None, oldest_first=True):
        content = message.content or ""
        attachments = ", ".join([a.url for a in message.attachments])
        if attachments:
            content += f" Attachments: {attachments}"

        lines.append(f"[{message.created_at}] {message.author}: {content}")

    data = io.BytesIO("\n".join(lines).encode("utf-8"))

    return discord.File(data, filename=f"transcript-{channel.name}.txt")


class TicketPanel(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.select(
        placeholder="Choose a ticket type...",
        custom_id="centari_ticket_select",
        options=[
            discord.SelectOption(label="Support", value="support", emoji="🛠️"),
            discord.SelectOption(label="Report", value="report", emoji="🚨"),
            discord.SelectOption(label="Appeal", value="appeal", emoji="📨"),
            discord.SelectOption(label="Commission", value="commission", emoji="🎨"),
            discord.SelectOption(label="Bug Report", value="bug-report", emoji="🐛"),
            discord.SelectOption(label="Custom Request", value="custom-request", emoji="✨"),
        ]
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        await open_ticket(self.bot, interaction, select.values[0])


class TicketControls(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.primary, custom_id="centari_ticket_claim")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticket = self.bot.db.get_ticket(interaction.channel.id)

        if not ticket:
            await interaction.response.send_message(embed=error_embed("This is not a ticket."), ephemeral=True)
            return

        staff_role_id = self.bot.db.get_setting(interaction.guild.id, "staff_role_id")

        if not is_staff(interaction, staff_role_id):
            await interaction.response.send_message(embed=error_embed("Only staff can claim tickets."), ephemeral=True)
            return

        ticket["claimed_by"] = interaction.user.id
        self.bot.db.update_ticket(interaction.channel.id, ticket)

        await interaction.response.send_message(embed=success_embed(f"Ticket claimed by {interaction.user.mention}."))

    @discord.ui.button(label="Transcript", style=discord.ButtonStyle.secondary, custom_id="centari_ticket_transcript")
    async def transcript(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticket = self.bot.db.get_ticket(interaction.channel.id)

        if not ticket:
            await interaction.response.send_message(embed=error_embed("This is not a ticket."), ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        file = await create_transcript(interaction.channel)

        await interaction.followup.send("Here is the transcript.", file=file, ephemeral=True)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, custom_id="centari_ticket_close")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await close_ticket(self.bot, interaction)


async def open_ticket(bot: commands.Bot, interaction: discord.Interaction, ticket_type: str):
    guild = interaction.guild
    user = interaction.user

    data = bot.db.load()

    for ticket in data["tickets"].values():
        if ticket["guild_id"] == guild.id and ticket["user_id"] == user.id and ticket["status"] == "open":
            channel = guild.get_channel(ticket["channel_id"])
            if channel:
                await interaction.response.send_message(embed=error_embed(f"You already have an open ticket: {channel.mention}"), ephemeral=True)
                return

    settings = bot.db.get_guild(guild.id)["settings"]

    category = None
    if settings.get("ticket_category_id"):
        found = guild.get_channel(int(settings["ticket_category_id"]))
        if isinstance(found, discord.CategoryChannel):
            category = found

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True, read_message_history=True)
    }

    if settings.get("staff_role_id"):
        role = guild.get_role(int(settings["staff_role_id"]))
        if role:
            overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

    channel = await guild.create_text_channel(
        name=clean_channel_name(f"{ticket_type}-{user.name}"),
        category=category,
        overwrites=overwrites,
        reason=f"Ticket opened by {user}"
    )

    bot.db.create_ticket(guild.id, channel.id, user.id, ticket_type)

    persona = bot.db.get_persona(guild.id)

    embed = persona_embed(
        persona,
        "Ticket Opened",
        f"{user.mention}, your **{ticket_type}** ticket has been opened.\n\nStaff will help you here."
    )

    await channel.send(content=user.mention, embed=embed, view=TicketControls(bot))
    await interaction.response.send_message(embed=success_embed(f"Ticket created: {channel.mention}"), ephemeral=True)


async def close_ticket(bot: commands.Bot, interaction: discord.Interaction):
    ticket = bot.db.get_ticket(interaction.channel.id)

    if not ticket:
        await interaction.response.send_message(embed=error_embed("This is not a ticket channel."), ephemeral=True)
        return

    staff_role_id = bot.db.get_setting(interaction.guild.id, "staff_role_id")

    if interaction.user.id != ticket["user_id"] and not is_staff(interaction, staff_role_id):
        await interaction.response.send_message(embed=error_embed("Only the ticket creator or staff can close this ticket."), ephemeral=True)
        return

    await interaction.response.send_message(embed=success_embed("Closing ticket..."))

    transcript_channel_id = bot.db.get_setting(interaction.guild.id, "transcript_channel_id")

    if transcript_channel_id:
        transcript_channel = interaction.guild.get_channel(int(transcript_channel_id))
        if transcript_channel:
            file = await create_transcript(interaction.channel)
            await transcript_channel.send(content=f"Transcript for `{interaction.channel.name}`", file=file)

    bot.db.close_ticket(interaction.channel.id)
    await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}")


class TicketGroup(app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__(name="ticket", description="Ticket system.")
        self.bot = bot

    @app_commands.command(name="setup", description="Send a ticket panel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setup(self, interaction: discord.Interaction):
        persona = self.bot.db.get_persona(interaction.guild.id)

        embed = persona_embed(
            persona,
            "Open a Ticket",
            "Need help? Choose a ticket type from the dropdown below."
        )

        await interaction.response.send_message(embed=embed, view=TicketPanel(self.bot))

    @app_commands.command(name="config", description="Configure ticket settings.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def config(
        self,
        interaction: discord.Interaction,
        staff_role: discord.Role | None = None,
        ticket_category: discord.CategoryChannel | None = None,
        transcript_channel: discord.TextChannel | None = None
    ):
        if staff_role:
            self.bot.db.update_setting(interaction.guild.id, "staff_role_id", staff_role.id)

        if ticket_category:
            self.bot.db.update_setting(interaction.guild.id, "ticket_category_id", ticket_category.id)

        if transcript_channel:
            self.bot.db.update_setting(interaction.guild.id, "transcript_channel_id", transcript_channel.id)

        await interaction.response.send_message(embed=success_embed("Ticket settings updated."), ephemeral=True)

    @app_commands.command(name="close", description="Close this ticket.")
    async def close(self, interaction: discord.Interaction):
        await close_ticket(self.bot, interaction)

    @app_commands.command(name="add", description="Add a user to this ticket.")
    async def add(self, interaction: discord.Interaction, member: discord.Member):
        staff_role_id = self.bot.db.get_setting(interaction.guild.id, "staff_role_id")

        if not is_staff(interaction, staff_role_id):
            await interaction.response.send_message(embed=error_embed("Only staff can add users."), ephemeral=True)
            return

        await interaction.channel.set_permissions(member, view_channel=True, send_messages=True, read_message_history=True)
        await interaction.response.send_message(embed=success_embed(f"{member.mention} added to this ticket."))

    @app_commands.command(name="remove", description="Remove a user from this ticket.")
    async def remove(self, interaction: discord.Interaction, member: discord.Member):
        staff_role_id = self.bot.db.get_setting(interaction.guild.id, "staff_role_id")

        if not is_staff(interaction, staff_role_id):
            await interaction.response.send_message(embed=error_embed("Only staff can remove users."), ephemeral=True)
            return

        await interaction.channel.set_permissions(member, overwrite=None)
        await interaction.response.send_message(embed=success_embed(f"{member.mention} removed from this ticket."))


class Tickets(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.tree.add_command(TicketGroup(bot))

    async def cog_load(self):
        self.bot.add_view(TicketPanel(self.bot))
        self.bot.add_view(TicketControls(self.bot))


async def setup(bot: commands.Bot):
    await bot.add_cog(Tickets(bot))

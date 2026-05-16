import io
import re
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import persona_embed, success_embed, error_embed, info_embed
from utils.permissions import is_staff


DEFAULT_TICKET_TYPES = [
    {"label": "Support", "value": "support", "emoji": "🛠️"},
    {"label": "Report", "value": "report", "emoji": "🚨"},
    {"label": "Appeal", "value": "appeal", "emoji": "📨"},
    {"label": "Commission", "value": "commission", "emoji": "🎨"},
    {"label": "Bug Report", "value": "bug-report", "emoji": "🐛"},
    {"label": "Custom Request", "value": "custom-request", "emoji": "✨"},
]

DEFAULT_TICKET_PANEL = {
    "title": "Open a Ticket",
    "description": "Need help? Choose a ticket type from the dropdown below.",
    "color": "#9B7BFF",
    "footer": "Dei Talvyrvei • Centari Studios",
    "types": DEFAULT_TICKET_TYPES.copy(),
}


def clean_channel_name(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9-]", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")[:80] or "ticket"


def clean_ticket_value(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9-]", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")[:80]


def normalize_hex_color(value: str | None) -> str:
    if not value:
        return "#9B7BFF"

    clean = value.strip().replace("#", "")

    if len(clean) != 6:
        return "#9B7BFF"

    try:
        int(clean, 16)
    except ValueError:
        return "#9B7BFF"

    return f"#{clean.upper()}"


def hex_to_color(value: str | None) -> discord.Color:
    clean = normalize_hex_color(value).replace("#", "")

    try:
        return discord.Color(int(clean, 16))
    except ValueError:
        return discord.Color.purple()


def clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None

    value = value.strip()
    return value or None


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


class TicketTypeSelect(discord.ui.Select):
    def __init__(self, bot: commands.Bot, options: list[discord.SelectOption]):
        super().__init__(
            placeholder="Choose a ticket type...",
            custom_id="centari_ticket_select",
            min_values=1,
            max_values=1,
            options=options,
        )
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        await open_ticket(self.bot, interaction, self.values[0])


class TicketPanel(discord.ui.View):
    def __init__(self, bot: commands.Bot, guild_id: int | None = None):
        super().__init__(timeout=None)
        self.bot = bot

        if guild_id:
            config = get_ticket_panel_config(bot, guild_id)
            ticket_types = config.get("types", DEFAULT_TICKET_TYPES)
        else:
            ticket_types = DEFAULT_TICKET_TYPES

        options = []

        for item in ticket_types[:25]:
            label = str(item.get("label", "Ticket"))[:100]
            value = clean_ticket_value(str(item.get("value", label))) or "ticket"
            emoji = item.get("emoji") or None

            try:
                options.append(
                    discord.SelectOption(
                        label=label,
                        value=value[:100],
                        emoji=emoji,
                    )
                )
            except Exception:
                options.append(
                    discord.SelectOption(
                        label=label,
                        value=value[:100],
                    )
                )

        if not options:
            options = [
                discord.SelectOption(label="Support", value="support", emoji="🛠️"),
            ]

        self.add_item(TicketTypeSelect(bot, options))


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

        try:
            file = await create_transcript(interaction.channel)
            await interaction.followup.send("Here is the transcript.", file=file, ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send(
                embed=error_embed("I do not have permission to read this ticket history."),
                ephemeral=True,
            )

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, custom_id="centari_ticket_close")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await close_ticket(self.bot, interaction)


def get_ticket_panel_config(bot: commands.Bot, guild_id: int) -> dict:
    guild_config = bot.db.get_guild(guild_id)
    panel = guild_config.get("ticket_panel")

    changed = False

    if not isinstance(panel, dict):
        panel = DEFAULT_TICKET_PANEL.copy()
        panel["types"] = [item.copy() for item in DEFAULT_TICKET_TYPES]
        guild_config["ticket_panel"] = panel
        changed = True

    for key, default_value in DEFAULT_TICKET_PANEL.items():
        if key not in panel:
            if key == "types":
                panel[key] = [item.copy() for item in DEFAULT_TICKET_TYPES]
            else:
                panel[key] = default_value
            changed = True

    if not isinstance(panel.get("types"), list) or not panel["types"]:
        panel["types"] = [item.copy() for item in DEFAULT_TICKET_TYPES]
        changed = True

    if changed:
        bot.db.update_guild(guild_id, guild_config)

    return panel


def save_ticket_panel_config(bot: commands.Bot, guild_id: int, panel: dict):
    guild_config = bot.db.get_guild(guild_id)
    guild_config["ticket_panel"] = panel
    bot.db.update_guild(guild_id, guild_config)


def build_ticket_panel_embed(bot: commands.Bot, guild_id: int) -> discord.Embed:
    panel = get_ticket_panel_config(bot, guild_id)

    embed = discord.Embed(
        title=panel.get("title") or DEFAULT_TICKET_PANEL["title"],
        description=panel.get("description") or DEFAULT_TICKET_PANEL["description"],
        color=hex_to_color(panel.get("color")),
    )

    footer = panel.get("footer")

    if footer:
        embed.set_footer(text=footer)

    return embed


async def open_ticket(bot: commands.Bot, interaction: discord.Interaction, ticket_type: str):
    guild = interaction.guild
    user = interaction.user

    if not guild:
        await interaction.response.send_message(embed=error_embed("This only works inside a server."), ephemeral=True)
        return

    data = bot.db.load()

    for ticket in data["tickets"].values():
        if ticket["guild_id"] == guild.id and ticket["user_id"] == user.id and ticket["status"] == "open":
            channel = guild.get_channel(ticket["channel_id"])

            if channel:
                await interaction.response.send_message(
                    embed=error_embed(f"You already have an open ticket: {channel.mention}"),
                    ephemeral=True,
                )
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
        guild.me: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            manage_channels=True,
            read_message_history=True,
        ),
    }

    if settings.get("staff_role_id"):
        role = guild.get_role(int(settings["staff_role_id"]))

        if role:
            overwrites[role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
            )

    try:
        channel = await guild.create_text_channel(
            name=clean_channel_name(f"{ticket_type}-{user.name}"),
            category=category,
            overwrites=overwrites,
            reason=f"Ticket opened by {user}",
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            embed=error_embed(
                "I do not have permission to create ticket channels. "
                "Give my role Manage Channels and access to the ticket category."
            ),
            ephemeral=True,
        )
        return
    except discord.HTTPException as error:
        await interaction.response.send_message(
            embed=error_embed(f"Discord rejected the ticket channel: `{error}`"),
            ephemeral=True,
        )
        return

    bot.db.create_ticket(guild.id, channel.id, user.id, ticket_type)

    persona = bot.db.get_persona(guild.id)

    embed = persona_embed(
        persona,
        "Ticket Opened",
        f"{user.mention}, your **{ticket_type}** ticket has been opened.\n\nStaff will help you here.",
    )

    try:
        await channel.send(content=user.mention, embed=embed, view=TicketControls(bot))
    except discord.Forbidden:
        await interaction.response.send_message(
            embed=error_embed(f"Ticket channel was created, but I cannot send messages in {channel.mention}."),
            ephemeral=True,
        )
        return

    await interaction.response.send_message(embed=success_embed(f"Ticket created: {channel.mention}"), ephemeral=True)


async def close_ticket(bot: commands.Bot, interaction: discord.Interaction):
    ticket = bot.db.get_ticket(interaction.channel.id)

    if not ticket:
        await interaction.response.send_message(embed=error_embed("This is not a ticket channel."), ephemeral=True)
        return

    staff_role_id = bot.db.get_setting(interaction.guild.id, "staff_role_id")

    if interaction.user.id != ticket["user_id"] and not is_staff(interaction, staff_role_id):
        await interaction.response.send_message(
            embed=error_embed("Only the ticket creator or staff can close this ticket."),
            ephemeral=True,
        )
        return

    await interaction.response.send_message(embed=success_embed("Closing ticket..."))

    transcript_channel_id = bot.db.get_setting(interaction.guild.id, "transcript_channel_id")

    if transcript_channel_id:
        transcript_channel = interaction.guild.get_channel(int(transcript_channel_id))

        if transcript_channel:
            try:
                file = await create_transcript(interaction.channel)
                await transcript_channel.send(content=f"Transcript for `{interaction.channel.name}`", file=file)
            except discord.Forbidden:
                pass

    bot.db.close_ticket(interaction.channel.id)

    try:
        await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}")
    except discord.Forbidden:
        await interaction.followup.send(
            embed=error_embed("Ticket was marked closed, but I do not have permission to delete this channel."),
            ephemeral=True,
        )


class TicketGroup(app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__(name="ticket", description="Ticket system.")
        self.bot = bot

    @app_commands.command(name="setup", description="Send a ticket panel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setup(self, interaction: discord.Interaction):
        embed = build_ticket_panel_embed(self.bot, interaction.guild.id)

        await interaction.response.send_message(
            embed=embed,
            view=TicketPanel(self.bot, interaction.guild.id),
        )

    @app_commands.command(name="config", description="Configure ticket settings.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def config(
        self,
        interaction: discord.Interaction,
        staff_role: discord.Role | None = None,
        ticket_category: discord.CategoryChannel | None = None,
        transcript_channel: discord.TextChannel | None = None,
    ):
        if staff_role:
            self.bot.db.update_setting(interaction.guild.id, "staff_role_id", staff_role.id)

        if ticket_category:
            self.bot.db.update_setting(interaction.guild.id, "ticket_category_id", ticket_category.id)

        if transcript_channel:
            self.bot.db.update_setting(interaction.guild.id, "transcript_channel_id", transcript_channel.id)

        await interaction.response.send_message(embed=success_embed("Ticket settings updated."), ephemeral=True)

    @app_commands.command(name="panel-config", description="Edit the ticket panel title, description, color, or footer.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def panel_config(
        self,
        interaction: discord.Interaction,
        title: str | None = None,
        description: str | None = None,
        color: str | None = None,
        footer: str | None = None,
    ):
        panel = get_ticket_panel_config(self.bot, interaction.guild.id)

        changed = False

        if title is not None:
            title = title.strip()

            if len(title) > 256:
                await interaction.response.send_message(
                    embed=error_embed("Ticket panel title must be 256 characters or less."),
                    ephemeral=True,
                )
                return

            panel["title"] = title or DEFAULT_TICKET_PANEL["title"]
            changed = True

        if description is not None:
            description = description.strip()

            if len(description) > 4000:
                await interaction.response.send_message(
                    embed=error_embed("Ticket panel description must be 4000 characters or less."),
                    ephemeral=True,
                )
                return

            panel["description"] = description or DEFAULT_TICKET_PANEL["description"]
            changed = True

        if color is not None:
            panel["color"] = normalize_hex_color(color)
            changed = True

        if footer is not None:
            panel["footer"] = footer.strip() or DEFAULT_TICKET_PANEL["footer"]
            changed = True

        if changed:
            panel["updated_at"] = datetime.now(timezone.utc).isoformat()
            panel["updated_by"] = interaction.user.id
            save_ticket_panel_config(self.bot, interaction.guild.id, panel)

        preview = build_ticket_panel_embed(self.bot, interaction.guild.id)

        await interaction.response.send_message(
            content="Ticket panel updated." if changed else "Current ticket panel preview:",
            embed=preview,
            ephemeral=True,
        )

    @app_commands.command(name="type-list", description="List ticket types for this server.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def type_list(self, interaction: discord.Interaction):
        panel = get_ticket_panel_config(self.bot, interaction.guild.id)
        ticket_types = panel.get("types", [])

        lines = []

        for index, item in enumerate(ticket_types, start=1):
            emoji = item.get("emoji") or ""
            lines.append(
                f"**{index}.** {emoji} **{item.get('label')}**\n"
                f"Value: `{item.get('value')}`"
            )

        await interaction.response.send_message(
            embed=info_embed("Ticket Types", "\n\n".join(lines) or "No ticket types configured."),
            ephemeral=True,
        )

    @app_commands.command(name="type-add", description="Add or update a ticket type.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def type_add(
        self,
        interaction: discord.Interaction,
        label: str,
        value: str | None = None,
        emoji: str | None = None,
    ):
        label = label.strip()

        if not label:
            await interaction.response.send_message(embed=error_embed("Ticket type label cannot be empty."), ephemeral=True)
            return

        if len(label) > 100:
            await interaction.response.send_message(embed=error_embed("Ticket type label must be 100 characters or less."), ephemeral=True)
            return

        value = clean_ticket_value(value or label)

        if not value:
            await interaction.response.send_message(embed=error_embed("Ticket type value cannot be empty."), ephemeral=True)
            return

        panel = get_ticket_panel_config(self.bot, interaction.guild.id)
        ticket_types = panel.get("types", [])

        existing = None

        for item in ticket_types:
            if str(item.get("value", "")).lower() == value.lower():
                existing = item
                break

        if existing:
            existing["label"] = label
            existing["emoji"] = clean_optional_text(emoji)
            action = "updated"
        else:
            if len(ticket_types) >= 25:
                await interaction.response.send_message(
                    embed=error_embed("Discord only allows up to 25 ticket types in one dropdown."),
                    ephemeral=True,
                )
                return

            ticket_types.append(
                {
                    "label": label,
                    "value": value,
                    "emoji": clean_optional_text(emoji),
                }
            )
            action = "added"

        panel["types"] = ticket_types
        panel["updated_at"] = datetime.now(timezone.utc).isoformat()
        panel["updated_by"] = interaction.user.id

        save_ticket_panel_config(self.bot, interaction.guild.id, panel)

        await interaction.response.send_message(
            embed=success_embed(f"Ticket type `{label}` {action}."),
            ephemeral=True,
        )

    @app_commands.command(name="type-remove", description="Remove a ticket type by value.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def type_remove(self, interaction: discord.Interaction, value: str):
        value = clean_ticket_value(value)

        panel = get_ticket_panel_config(self.bot, interaction.guild.id)
        ticket_types = panel.get("types", [])

        if len(ticket_types) <= 1:
            await interaction.response.send_message(
                embed=error_embed("You need at least one ticket type."),
                ephemeral=True,
            )
            return

        new_types = [item for item in ticket_types if str(item.get("value", "")).lower() != value.lower()]

        if len(new_types) == len(ticket_types):
            await interaction.response.send_message(
                embed=error_embed("I could not find a ticket type with that value."),
                ephemeral=True,
            )
            return

        panel["types"] = new_types
        panel["updated_at"] = datetime.now(timezone.utc).isoformat()
        panel["updated_by"] = interaction.user.id

        save_ticket_panel_config(self.bot, interaction.guild.id, panel)

        await interaction.response.send_message(
            embed=success_embed(f"Ticket type `{value}` removed."),
            ephemeral=True,
        )

    @app_commands.command(name="panel-reset", description="Reset ticket panel text and types back to defaults.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def panel_reset(self, interaction: discord.Interaction):
        panel = DEFAULT_TICKET_PANEL.copy()
        panel["types"] = [item.copy() for item in DEFAULT_TICKET_TYPES]
        panel["updated_at"] = datetime.now(timezone.utc).isoformat()
        panel["updated_by"] = interaction.user.id

        save_ticket_panel_config(self.bot, interaction.guild.id, panel)

        await interaction.response.send_message(
            embed=success_embed("Ticket panel reset to defaults."),
            ephemeral=True,
        )

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

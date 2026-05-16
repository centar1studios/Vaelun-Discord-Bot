import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import persona_embed


HELP_SECTIONS = {
    "core": {
        "label": "Core",
        "emoji": "🏠",
        "description": "Basic bot commands and server info.",
        "commands": [
            ("`/help`", "Open this help menu."),
            ("`/persona view`", "View this server's Persona."),
            ("`/admin health`", "View a basic server health report."),
            ("`/config view`", "View server configuration."),
        ],
    },
    "moderation": {
        "label": "Moderation",
        "emoji": "🛡️",
        "description": "Warnings, bans, timeouts, and channel controls.",
        "commands": [
            ("`/ban`", "Ban a member."),
            ("`/kick`", "Kick a member."),
            ("`/timeout`", "Timeout a member."),
            ("`/warn`", "Warn a member."),
            ("`/warnings`", "View member warnings."),
            ("`/clear`", "Clear messages."),
            ("`/lock`", "Lock a channel."),
            ("`/unlock`", "Unlock a channel."),
        ],
    },
    "tickets": {
        "label": "Tickets",
        "emoji": "🎫",
        "description": "Support tickets, ticket panels, and ticket types.",
        "commands": [
            ("`/ticket setup`", "Send a fresh ticket panel."),
            ("`/ticket config`", "Set staff role, category, and transcript channel."),
            ("`/ticket panel-config`", "Edit ticket panel title, description, color, or footer."),
            ("`/ticket panel-reset`", "Reset ticket panel settings."),
            ("`/ticket type-list`", "List ticket dropdown types."),
            ("`/ticket type-add`", "Add or update a ticket type."),
            ("`/ticket type-remove`", "Remove a ticket type."),
            ("`/ticket close`", "Close the current ticket."),
            ("`/ticket add`", "Add a user to a ticket."),
            ("`/ticket remove`", "Remove a user from a ticket."),
        ],
    },
    "embeds": {
        "label": "Embeds",
        "emoji": "🧩",
        "description": "Create, preview, save, and send embed templates.",
        "commands": [
            ("`/embed-save`", "Save or update an embed template."),
            ("`/embed-list`", "List saved embed templates."),
            ("`/embed-preview`", "Preview a saved embed privately."),
            ("`/embed-send`", "Send a saved embed to a channel."),
            ("`/embed-delete`", "Disable a saved embed template."),
            ("`/embed-restore`", "Restore a disabled embed template."),
        ],
    },
    "confessions": {
        "label": "Confessions",
        "emoji": "🕯️",
        "description": "Anonymous confessions with staff approval and anonymous replies.",
        "commands": [
            ("`/confession config`", "Set review/public channels and reply settings."),
            ("`/confession view-config`", "View confession configuration."),
            ("`/confession submit`", "Submit an anonymous confession for staff review."),
            ("Approve button", "Staff approves a confession and posts it anonymously."),
            ("Deny button", "Staff denies a confession privately."),
            ("Reply Anonymously button", "Creates a thread and posts anonymous replies."),
        ],
    },
    "staffmail": {
        "label": "Staffmail",
        "emoji": "📬",
        "description": "Private anonymous reports/messages sent only to staff.",
        "commands": [
            ("`/staffmail config`", "Set the staffmail review channel."),
            ("`/staffmail submit`", "Send a private anonymous message/report to staff."),
            ("`link:` option", "Attach a Discord message link or outside link."),
            ("`attachment:` option", "Attach an image, screenshot, or file."),
        ],
    },
    "community": {
        "label": "Community",
        "emoji": "🌟",
        "description": "Fun, engagement, levels, roles, and economy.",
        "commands": [
            ("`/community poll`", "Create a yes/no poll."),
            ("`/community 8ball`", "Ask the magic 8-ball."),
            ("`/community quote`", "Save a quote."),
            ("`/community passport`", "View a member profile."),
            ("`/roles button`", "Create a role button panel."),
            ("`/level rank`", "View a member level."),
            ("`/economy balance`", "View balance."),
            ("`/economy daily`", "Claim daily coins."),
        ],
    },
    "eightball": {
        "label": "8-ball Answers",
        "emoji": "🎱",
        "description": "Manage this server's custom 8-ball answers.",
        "commands": [
            ("`/8ball-answer list`", "List custom 8-ball answers."),
            ("`/8ball-answer add`", "Add a new 8-ball answer."),
            ("`/8ball-answer remove`", "Remove an 8-ball answer."),
            ("`/8ball-answer reset`", "Reset answers back to defaults."),
        ],
    },
    "resources": {
        "label": "Resources",
        "emoji": "📚",
        "description": "Resources, suggestions, and study tools.",
        "commands": [
            ("`/resource add`", "Add a resource or FAQ entry."),
            ("`/resource search`", "Search resources."),
            ("`/suggest submit`", "Submit a suggestion."),
            ("`/study pomodoro`", "Start a Pomodoro timer."),
            ("`/study deadline`", "Save a deadline reminder note."),
        ],
    },
    "fonts": {
        "label": "Fonts",
        "emoji": "🔤",
        "description": "Convert messages into Discord-safe Unicode styles.",
        "commands": [
            ("`/font list`", "View all available font styles."),
            ("`/font preview`", "Preview text in a selected style."),
            ("`/font say`", "Make Dei send styled text."),
        ],
    },
    "persona": {
        "label": "Persona",
        "emoji": "🎭",
        "description": "Customize how Dei presents itself in this server.",
        "commands": [
            ("`/persona view`", "View Persona settings."),
            ("`/persona name`", "Set Persona name."),
            ("`/persona bio`", "Set Persona bio."),
            ("`/persona avatar`", "Set Persona avatar URL."),
            ("`/persona color`", "Set Persona embed color."),
            ("`/persona footer`", "Set Persona footer."),
            ("`/persona nickname`", "Set Dei's server nickname."),
            ("`/persona reset`", "Reset Persona settings."),
        ],
    },
    "automod": {
        "label": "Automod",
        "emoji": "🚨",
        "description": "Automated safety and filtering tools.",
        "commands": [
            ("`/automod toggle`", "Turn automod on or off."),
            ("`/automod mode`", "Set automod strictness."),
            ("`/automod block-word`", "Add a blocked word."),
            ("`/automod view`", "View automod settings."),
        ],
    },
    "welcome": {
        "label": "Welcome",
        "emoji": "👋",
        "description": "Welcome, leave, and verification tools.",
        "commands": [
            ("`/welcome enable`", "Enable welcome messages."),
            ("`/welcome disable`", "Disable welcome messages."),
            ("`/welcome message`", "Set welcome message."),
            ("`/welcome test`", "Test welcome message."),
            ("`/leave enable`", "Enable leave messages."),
            ("`/leave disable`", "Disable leave messages."),
            ("`/leave message`", "Set leave message."),
            ("`/verification panel`", "Send verification panel."),
            ("`/verification message`", "Set verification message."),
        ],
    },
    "admin": {
        "label": "Admin",
        "emoji": "⚙️",
        "description": "Server configuration and admin utilities.",
        "commands": [
            ("`/config set-log-channel`", "Set the log channel."),
            ("`/config set-staff-role`", "Set the staff role."),
            ("`/config set-welcome-channel`", "Set the welcome channel."),
            ("`/config set-leave-channel`", "Set the leave channel."),
            ("`/config set-verified-role`", "Set the verified role."),
            ("`/admin backup`", "Create a server backup snapshot."),
            ("`/admin restore-roles`", "Restore saved roles for a user."),
        ],
    },
}


def build_home_embed(persona: dict) -> discord.Embed:
    embed = persona_embed(
        persona,
        "Centari Studios Help",
        "Pick a category from the dropdown below.",
    )

    embed.add_field(
        name="Quick Start",
        value=(
            "`/ticket setup` • Create a ticket panel\n"
            "`/embed-save` • Save an embed template\n"
            "`/confession config` • Set up anonymous confessions\n"
            "`/staffmail config` • Set up private staffmail\n"
            "`/config view` • View server settings"
        ),
        inline=False,
    )

    category_list = "\n".join(
        f"{section['emoji']} **{section['label']}** — {section['description']}"
        for section in HELP_SECTIONS.values()
    )

    if len(category_list) > 3800:
        category_list = category_list[:3800] + "\n..."

    embed.add_field(
        name="Categories",
        value=category_list,
        inline=False,
    )

    embed.set_footer(text="Use the dropdown to browse commands.")
    return embed


def build_section_embed(persona: dict, section_key: str) -> discord.Embed:
    section = HELP_SECTIONS[section_key]

    embed = persona_embed(
        persona,
        f"{section['emoji']} {section['label']} Commands",
        section["description"],
    )

    command_text = "\n".join(
        f"{command} — {description}"
        for command, description in section["commands"]
    )

    if len(command_text) > 3800:
        command_text = command_text[:3800] + "\n..."

    embed.add_field(
        name="Commands",
        value=command_text,
        inline=False,
    )

    embed.set_footer(text="Use the dropdown to switch categories.")
    return embed


class HelpSelect(discord.ui.Select):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        options = [
            discord.SelectOption(
                label="Home",
                value="home",
                description="Back to the main help overview.",
                emoji="🏠",
            )
        ]

        for key, section in HELP_SECTIONS.items():
            options.append(
                discord.SelectOption(
                    label=section["label"][:100],
                    value=key,
                    description=section["description"][:100],
                    emoji=section["emoji"],
                )
            )

        super().__init__(
            placeholder="Choose a help category...",
            min_values=1,
            max_values=1,
            options=options[:25],
        )

    async def callback(self, interaction: discord.Interaction):
        persona = self.bot.db.get_persona(interaction.guild.id)
        selected = self.values[0]

        if selected == "home":
            embed = build_home_embed(persona)
        else:
            embed = build_section_embed(persona, selected)

        await interaction.response.edit_message(embed=embed, view=self.view)


class HelpView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=180)
        self.add_item(HelpSelect(bot))


class Help(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="help", description="View Centari Studios commands and features.")
    async def help(self, interaction: discord.Interaction):
        persona = self.bot.db.get_persona(interaction.guild.id)

        embed = build_home_embed(persona)
        view = HelpView(self.bot)

        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Help(bot))

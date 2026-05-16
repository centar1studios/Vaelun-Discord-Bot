import re
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import persona_embed, success_embed, error_embed, info_embed


HEX_RE = re.compile(r"^#?[0-9A-Fa-f]{6}$")
KEY_RE = re.compile(r"^[a-z0-9_-]{2,32}$")

PERSONA_WEBHOOK_NAME = "Centari Persona Relay"

DEFAULT_PERSONA_KEY = "centari"
DEFAULT_PERSONA = {
    "key": DEFAULT_PERSONA_KEY,
    "name": "Centari Studios",
    "bio": (
        "A free all-in-one Discord bot for moderation, tickets, safety, "
        "community tools, and creative server management."
    ),
    "avatar_url": None,
    "color": "#9B7BFF",
    "footer": "Powered by Centari Studios",
    "enabled": True,
    "created_at": None,
    "created_by": None,
    "updated_at": None,
    "updated_by": None,
}


def normalize_hex_color(color: str | None) -> str:
    if not color:
        return "#9B7BFF"

    color = color.strip()

    if not HEX_RE.match(color):
        return "#9B7BFF"

    if not color.startswith("#"):
        color = f"#{color}"

    return color.upper()


def clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None

    value = value.strip()
    return value or None


def clean_optional_url(value: str | None) -> str | None:
    value = clean_optional_text(value)

    if not value:
        return None

    if not value.startswith(("http://", "https://")):
        return None

    return value


def clean_persona_key(key: str) -> str:
    return key.lower().strip()


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


async def get_or_create_persona_webhook(channel: discord.TextChannel) -> discord.Webhook | None:
    try:
        webhooks = await channel.webhooks()

        for webhook in webhooks:
            if webhook.name == PERSONA_WEBHOOK_NAME and webhook.user == channel.guild.me:
                return webhook

        return await channel.create_webhook(
            name=PERSONA_WEBHOOK_NAME,
            reason="Centari persona speak relay",
        )

    except (discord.Forbidden, discord.HTTPException):
        return None


class PersonaGroup(app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__(name="persona", description="Persona and character tools.")
        self.bot = bot

    def get_personas(self, guild_id: int) -> dict:
        guild_data = self.bot.db.get_guild(guild_id)

        if "personas" not in guild_data or not isinstance(guild_data["personas"], dict):
            old_persona = guild_data.get("persona", {}).copy()

            migrated = DEFAULT_PERSONA.copy()
            migrated.update(
                {
                    "name": old_persona.get("name", DEFAULT_PERSONA["name"]),
                    "bio": old_persona.get("bio", DEFAULT_PERSONA["bio"]),
                    "avatar_url": old_persona.get("avatar_url"),
                    "color": old_persona.get("color", DEFAULT_PERSONA["color"]),
                    "footer": old_persona.get("footer", DEFAULT_PERSONA["footer"]),
                    "enabled": True,
                }
            )

            guild_data["personas"] = {
                DEFAULT_PERSONA_KEY: migrated,
            }

            self.bot.db.update_guild(guild_id, guild_data)

        if DEFAULT_PERSONA_KEY not in guild_data["personas"]:
            guild_data["personas"][DEFAULT_PERSONA_KEY] = DEFAULT_PERSONA.copy()
            self.bot.db.update_guild(guild_id, guild_data)

        return guild_data["personas"]

    def save_personas(self, guild_id: int, personas: dict):
        guild_data = self.bot.db.get_guild(guild_id)
        guild_data["personas"] = personas

        if DEFAULT_PERSONA_KEY in personas:
            guild_data["persona"] = {
                "name": personas[DEFAULT_PERSONA_KEY].get("name", DEFAULT_PERSONA["name"]),
                "bio": personas[DEFAULT_PERSONA_KEY].get("bio", DEFAULT_PERSONA["bio"]),
                "avatar_url": personas[DEFAULT_PERSONA_KEY].get("avatar_url"),
                "color": personas[DEFAULT_PERSONA_KEY].get("color", DEFAULT_PERSONA["color"]),
                "footer": personas[DEFAULT_PERSONA_KEY].get("footer", DEFAULT_PERSONA["footer"]),
            }

        self.bot.db.update_guild(guild_id, guild_data)

    def get_persona_by_key(self, guild_id: int, key: str) -> dict | None:
        key = clean_persona_key(key)
        personas = self.get_personas(guild_id)
        return personas.get(key)

    async def send_persona_speak_log(
        self,
        interaction: discord.Interaction,
        persona_key: str,
        persona: dict,
        channel: discord.TextChannel,
        message: str,
    ):
        log_channel_id = self.bot.db.get_setting(interaction.guild.id, "log_channel_id")
        log_channel = await fetch_text_channel(interaction.guild, log_channel_id)

        if not log_channel:
            return

        embed = discord.Embed(
            title="Persona Speak Used",
            color=discord.Color.purple(),
            timestamp=discord.utils.utcnow(),
        )

        embed.add_field(
            name="Used By",
            value=f"{interaction.user.mention}\n`{interaction.user.id}`",
            inline=True,
        )
        embed.add_field(
            name="Persona",
            value=f"{persona.get('name', 'Unknown')}\n`{persona_key}`",
            inline=True,
        )
        embed.add_field(
            name="Sent To",
            value=channel.mention,
            inline=True,
        )

        safe_message = message

        if len(safe_message) > 1000:
            safe_message = safe_message[:1000] + "\n..."

        embed.add_field(
            name="Message",
            value=safe_message or "No message.",
            inline=False,
        )

        embed.set_footer(text="Centari Studios Persona Logging")

        try:
            await log_channel.send(embed=embed)
        except (discord.Forbidden, discord.HTTPException):
            return

    @app_commands.command(name="list", description="List this server's personas.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def list_personas(self, interaction: discord.Interaction):
        personas = self.get_personas(interaction.guild.id)

        if not personas:
            await interaction.response.send_message(
                embed=info_embed("Personas", "No personas are configured yet."),
                ephemeral=True,
            )
            return

        lines = []

        for key, persona in sorted(personas.items()):
            status = "Enabled" if persona.get("enabled", True) else "Disabled"
            lines.append(
                f"**{persona.get('name', 'Unnamed Persona')}**\n"
                f"Key: `{key}`\n"
                f"Status: `{status}`\n"
                f"Bio: {persona.get('bio', 'No bio')[:150]}"
            )

        text = "\n\n".join(lines)

        if len(text) > 3800:
            text = text[:3800] + "\n..."

        await interaction.response.send_message(
            embed=info_embed("Personas", text),
            ephemeral=True,
        )

    @app_commands.command(name="view", description="View a persona.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def view(self, interaction: discord.Interaction, key: str = DEFAULT_PERSONA_KEY):
        key = clean_persona_key(key)
        persona = self.get_persona_by_key(interaction.guild.id, key)

        if not persona:
            await interaction.response.send_message(
                embed=error_embed("I could not find a persona with that key."),
                ephemeral=True,
            )
            return

        description = f"""
**Key:** `{key}`
**Name:** {persona.get("name", "Unnamed Persona")}
**Bio:** {persona.get("bio", "No bio")}
**Color:** {persona.get("color", "#9B7BFF")}
**Footer:** {persona.get("footer") or "None"}
**Avatar URL:** {persona.get("avatar_url") or "None"}
**Enabled:** {persona.get("enabled", True)}
"""

        await interaction.response.send_message(
            embed=persona_embed(persona, "Server Persona", description),
            ephemeral=True,
        )

    @app_commands.command(name="create", description="Create a new persona.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def create(
        self,
        interaction: discord.Interaction,
        key: str,
        name: str,
        bio: str | None = None,
        avatar_url: str | None = None,
        color: str | None = "#9B7BFF",
        footer: str | None = None,
    ):
        key = clean_persona_key(key)

        if not KEY_RE.match(key):
            await interaction.response.send_message(
                embed=error_embed("Persona key must be 2-32 characters and use only lowercase letters, numbers, `_`, or `-`."),
                ephemeral=True,
            )
            return

        name = clean_optional_text(name)

        if not name:
            await interaction.response.send_message(
                embed=error_embed("Persona name cannot be empty."),
                ephemeral=True,
            )
            return

        if len(name) > 80:
            await interaction.response.send_message(
                embed=error_embed("Persona name must be 80 characters or less."),
                ephemeral=True,
            )
            return

        bio = clean_optional_text(bio) or "No bio set."
        footer = clean_optional_text(footer)
        avatar_url = clean_optional_url(avatar_url)
        color = normalize_hex_color(color)

        if len(bio) > 500:
            await interaction.response.send_message(
                embed=error_embed("Persona bio must be 500 characters or less."),
                ephemeral=True,
            )
            return

        personas = self.get_personas(interaction.guild.id)

        if key in personas:
            await interaction.response.send_message(
                embed=error_embed("A persona with that key already exists."),
                ephemeral=True,
            )
            return

        now = datetime.now(timezone.utc).isoformat()

        personas[key] = {
            "key": key,
            "name": name,
            "bio": bio,
            "avatar_url": avatar_url,
            "color": color,
            "footer": footer,
            "enabled": True,
            "created_at": now,
            "created_by": interaction.user.id,
            "updated_at": now,
            "updated_by": interaction.user.id,
        }

        self.save_personas(interaction.guild.id, personas)

        await interaction.response.send_message(
            embed=success_embed(f"Persona `{key}` created as **{name}**."),
            ephemeral=True,
        )

    @app_commands.command(name="edit", description="Edit an existing persona.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def edit(
        self,
        interaction: discord.Interaction,
        key: str,
        name: str | None = None,
        bio: str | None = None,
        avatar_url: str | None = None,
        color: str | None = None,
        footer: str | None = None,
    ):
        key = clean_persona_key(key)
        personas = self.get_personas(interaction.guild.id)
        persona = personas.get(key)

        if not persona:
            await interaction.response.send_message(
                embed=error_embed("I could not find a persona with that key."),
                ephemeral=True,
            )
            return

        changed_fields = []

        name = clean_optional_text(name)
        bio = clean_optional_text(bio)
        footer = clean_optional_text(footer)

        if name:
            if len(name) > 80:
                await interaction.response.send_message(
                    embed=error_embed("Persona name must be 80 characters or less."),
                    ephemeral=True,
                )
                return

            persona["name"] = name
            changed_fields.append("name")

        if bio:
            if len(bio) > 500:
                await interaction.response.send_message(
                    embed=error_embed("Persona bio must be 500 characters or less."),
                    ephemeral=True,
                )
                return

            persona["bio"] = bio
            changed_fields.append("bio")

        if avatar_url is not None:
            cleaned_avatar = clean_optional_url(avatar_url)

            if avatar_url.strip() and not cleaned_avatar:
                await interaction.response.send_message(
                    embed=error_embed("Avatar URL must start with `http://` or `https://`."),
                    ephemeral=True,
                )
                return

            persona["avatar_url"] = cleaned_avatar
            changed_fields.append("avatar")

        if color:
            if not HEX_RE.match(color):
                await interaction.response.send_message(
                    embed=error_embed("Use a valid hex color like #9B7BFF."),
                    ephemeral=True,
                )
                return

            persona["color"] = normalize_hex_color(color)
            changed_fields.append("color")

        if footer is not None:
            persona["footer"] = footer
            changed_fields.append("footer")

        if not changed_fields:
            await interaction.response.send_message(
                embed=error_embed("Nothing was changed. Give me at least one field to update."),
                ephemeral=True,
            )
            return

        persona["updated_at"] = datetime.now(timezone.utc).isoformat()
        persona["updated_by"] = interaction.user.id

        personas[key] = persona
        self.save_personas(interaction.guild.id, personas)

        await interaction.response.send_message(
            embed=success_embed(f"Persona `{key}` updated: {', '.join(changed_fields)}."),
            ephemeral=True,
        )

    @app_commands.command(name="delete", description="Disable a persona.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def delete(self, interaction: discord.Interaction, key: str):
        key = clean_persona_key(key)
        personas = self.get_personas(interaction.guild.id)
        persona = personas.get(key)

        if not persona:
            await interaction.response.send_message(
                embed=error_embed("I could not find a persona with that key."),
                ephemeral=True,
            )
            return

        if key == DEFAULT_PERSONA_KEY:
            await interaction.response.send_message(
                embed=error_embed("The default persona cannot be deleted. You can edit it instead."),
                ephemeral=True,
            )
            return

        persona["enabled"] = False
        persona["updated_at"] = datetime.now(timezone.utc).isoformat()
        persona["updated_by"] = interaction.user.id

        personas[key] = persona
        self.save_personas(interaction.guild.id, personas)

        await interaction.response.send_message(
            embed=success_embed(f"Persona `{key}` disabled."),
            ephemeral=True,
        )

    @app_commands.command(name="restore", description="Re-enable a disabled persona.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def restore(self, interaction: discord.Interaction, key: str):
        key = clean_persona_key(key)
        personas = self.get_personas(interaction.guild.id)
        persona = personas.get(key)

        if not persona:
            await interaction.response.send_message(
                embed=error_embed("I could not find a persona with that key."),
                ephemeral=True,
            )
            return

        persona["enabled"] = True
        persona["updated_at"] = datetime.now(timezone.utc).isoformat()
        persona["updated_by"] = interaction.user.id

        personas[key] = persona
        self.save_personas(interaction.guild.id, personas)

        await interaction.response.send_message(
            embed=success_embed(f"Persona `{key}` restored."),
            ephemeral=True,
        )

    @app_commands.command(name="speak", description="Send a webhook message as a persona.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def speak(
        self,
        interaction: discord.Interaction,
        key: str,
        channel: discord.TextChannel,
        message: str,
    ):
        key = clean_persona_key(key)
        persona = self.get_persona_by_key(interaction.guild.id, key)

        if not persona:
            await interaction.response.send_message(
                embed=error_embed("I could not find a persona with that key."),
                ephemeral=True,
            )
            return

        if not persona.get("enabled", True):
            await interaction.response.send_message(
                embed=error_embed("That persona is disabled."),
                ephemeral=True,
            )
            return

        if len(message) > 2000:
            await interaction.response.send_message(
                embed=error_embed("Persona messages must be 2000 characters or less."),
                ephemeral=True,
            )
            return

        webhook = await get_or_create_persona_webhook(channel)

        if not webhook:
            await interaction.response.send_message(
                embed=error_embed("I need `Manage Webhooks` permission in that channel to speak as a persona."),
                ephemeral=True,
            )
            return

        persona_name = persona.get("name", "Persona")[:80]
        avatar_url = persona.get("avatar_url")

        try:
            await webhook.send(
                content=message,
                username=persona_name,
                avatar_url=avatar_url,
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=error_embed("I do not have permission to use webhooks in that channel."),
                ephemeral=True,
            )
            return
        except discord.HTTPException as error:
            await interaction.response.send_message(
                embed=error_embed(f"Discord rejected the persona message: `{error}`"),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=success_embed(f"Persona `{key}` spoke in {channel.mention}."),
            ephemeral=True,
        )

        await self.send_persona_speak_log(
            interaction=interaction,
            persona_key=key,
            persona=persona,
            channel=channel,
            message=message,
        )

    @app_commands.command(name="name", description="Set the default Persona name.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_name(self, interaction: discord.Interaction, name: str):
        personas = self.get_personas(interaction.guild.id)
        persona = personas[DEFAULT_PERSONA_KEY]

        persona["name"] = name
        persona["updated_at"] = datetime.now(timezone.utc).isoformat()
        persona["updated_by"] = interaction.user.id

        personas[DEFAULT_PERSONA_KEY] = persona
        self.save_personas(interaction.guild.id, personas)

        await interaction.response.send_message(
            embed=success_embed("Default persona name updated."),
            ephemeral=True,
        )

    @app_commands.command(name="bio", description="Set the default Persona bio.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def bio(self, interaction: discord.Interaction, bio: str):
        if len(bio) > 500:
            await interaction.response.send_message(
                embed=error_embed("Bio must be 500 characters or less."),
                ephemeral=True,
            )
            return

        personas = self.get_personas(interaction.guild.id)
        persona = personas[DEFAULT_PERSONA_KEY]

        persona["bio"] = bio
        persona["updated_at"] = datetime.now(timezone.utc).isoformat()
        persona["updated_by"] = interaction.user.id

        personas[DEFAULT_PERSONA_KEY] = persona
        self.save_personas(interaction.guild.id, personas)

        await interaction.response.send_message(
            embed=success_embed("Default persona bio updated."),
            ephemeral=True,
        )

    @app_commands.command(name="avatar", description="Set the default Persona avatar URL.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def avatar(self, interaction: discord.Interaction, avatar_url: str):
        if not avatar_url.startswith("http://") and not avatar_url.startswith("https://"):
            await interaction.response.send_message(
                embed=error_embed("Use a valid image URL."),
                ephemeral=True,
            )
            return

        personas = self.get_personas(interaction.guild.id)
        persona = personas[DEFAULT_PERSONA_KEY]

        persona["avatar_url"] = avatar_url
        persona["updated_at"] = datetime.now(timezone.utc).isoformat()
        persona["updated_by"] = interaction.user.id

        personas[DEFAULT_PERSONA_KEY] = persona
        self.save_personas(interaction.guild.id, personas)

        await interaction.response.send_message(
            embed=success_embed("Default persona avatar updated."),
            ephemeral=True,
        )

    @app_commands.command(name="color", description="Set the default Persona color. Example: #9B7BFF")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def color(self, interaction: discord.Interaction, color: str):
        if not HEX_RE.match(color):
            await interaction.response.send_message(
                embed=error_embed("Use a valid hex color like #9B7BFF."),
                ephemeral=True,
            )
            return

        personas = self.get_personas(interaction.guild.id)
        persona = personas[DEFAULT_PERSONA_KEY]

        persona["color"] = normalize_hex_color(color)
        persona["updated_at"] = datetime.now(timezone.utc).isoformat()
        persona["updated_by"] = interaction.user.id

        personas[DEFAULT_PERSONA_KEY] = persona
        self.save_personas(interaction.guild.id, personas)

        await interaction.response.send_message(
            embed=success_embed("Default persona color updated."),
            ephemeral=True,
        )

    @app_commands.command(name="footer", description="Set the default Persona footer.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def footer(self, interaction: discord.Interaction, footer: str):
        personas = self.get_personas(interaction.guild.id)
        persona = personas[DEFAULT_PERSONA_KEY]

        persona["footer"] = footer
        persona["updated_at"] = datetime.now(timezone.utc).isoformat()
        persona["updated_by"] = interaction.user.id

        personas[DEFAULT_PERSONA_KEY] = persona
        self.save_personas(interaction.guild.id, personas)

        await interaction.response.send_message(
            embed=success_embed("Default persona footer updated."),
            ephemeral=True,
        )

    @app_commands.command(name="nickname", description="Set bot nickname in this server.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def nickname(self, interaction: discord.Interaction, nickname: str):
        try:
            await interaction.guild.me.edit(nick=nickname)
            await interaction.response.send_message(
                embed=success_embed("Bot nickname updated."),
                ephemeral=True,
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=error_embed("I need permission to change my nickname."),
                ephemeral=True,
            )

    @app_commands.command(name="reset", description="Reset the default Persona.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def reset(self, interaction: discord.Interaction):
        personas = self.get_personas(interaction.guild.id)
        now = datetime.now(timezone.utc).isoformat()

        reset_persona = DEFAULT_PERSONA.copy()
        reset_persona["created_at"] = personas.get(DEFAULT_PERSONA_KEY, {}).get("created_at")
        reset_persona["created_by"] = personas.get(DEFAULT_PERSONA_KEY, {}).get("created_by")
        reset_persona["updated_at"] = now
        reset_persona["updated_by"] = interaction.user.id

        personas[DEFAULT_PERSONA_KEY] = reset_persona
        self.save_personas(interaction.guild.id, personas)

        await interaction.response.send_message(
            embed=success_embed("Default persona reset."),
            ephemeral=True,
        )

    @view.autocomplete("key")
    @edit.autocomplete("key")
    @delete.autocomplete("key")
    @restore.autocomplete("key")
    @speak.autocomplete("key")
    async def persona_key_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ):
        personas = self.get_personas(interaction.guild.id)
        current = current.lower().strip()
        choices = []

        for key, persona in personas.items():
            if current and current not in key.lower() and current not in persona.get("name", "").lower():
                continue

            label = f"{key} | {persona.get('name', 'Unnamed Persona')}"

            if not persona.get("enabled", True):
                label += " (disabled)"

            choices.append(
                app_commands.Choice(
                    name=label[:100],
                    value=key[:100],
                )
            )

        return choices[:25]


class Persona(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.tree.add_command(PersonaGroup(bot))


async def setup(bot: commands.Bot):
    await bot.add_cog(Persona(bot))

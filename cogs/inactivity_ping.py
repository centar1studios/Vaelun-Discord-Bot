import time
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks

from utils.embeds import success_embed, error_embed, info_embed


PERSONA_WEBHOOK_NAME = "Centari Persona Relay"
DEFAULT_PERSONA_KEY = "centari"
DEFAULT_CHECK_INTERVAL_SECONDS = 300
DEFAULT_COOLDOWN_HOURS = 24


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
            reason="Centari inactivity ping persona relay",
        )

    except (discord.Forbidden, discord.HTTPException):
        return None


def get_personas_from_guild_data(guild_data: dict) -> dict:
    personas = guild_data.get("personas")

    if isinstance(personas, dict):
        return personas

    old_persona = guild_data.get("persona", {})

    default_persona = {
        "key": DEFAULT_PERSONA_KEY,
        "name": old_persona.get("name", "Centari Studios"),
        "bio": old_persona.get(
            "bio",
            "A free all-in-one Discord bot for moderation, tickets, safety, community tools, and creative server management.",
        ),
        "avatar_url": old_persona.get("avatar_url"),
        "color": old_persona.get("color", "#9B7BFF"),
        "footer": old_persona.get("footer", "Powered by Centari Studios"),
        "enabled": True,
    }

    guild_data["personas"] = {
        DEFAULT_PERSONA_KEY: default_persona,
    }

    return guild_data["personas"]


def get_persona(guild_data: dict, persona_key: str | None) -> dict | None:
    if not persona_key:
        return None

    persona_key = persona_key.lower().strip()
    personas = get_personas_from_guild_data(guild_data)
    persona = personas.get(persona_key)

    if not persona:
        return None

    if not persona.get("enabled", True):
        return None

    return persona


def get_inactivity_config(guild_data: dict) -> dict:
    config = guild_data.get("inactivity_ping")

    if not isinstance(config, dict):
        config = {}
        guild_data["inactivity_ping"] = config

    config.setdefault("channels", {})

    if not isinstance(config["channels"], dict):
        config["channels"] = {}

    return config


def clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None

    value = value.strip()
    return value or None


def now_ts() -> int:
    return int(time.time())


def format_seconds(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"

    minutes = seconds // 60

    if minutes < 60:
        return f"{minutes}m"

    hours = minutes // 60

    if hours < 24:
        return f"{hours}h"

    days = hours // 24
    remaining_hours = hours % 24

    if remaining_hours:
        return f"{days}d {remaining_hours}h"

    return f"{days}d"


def build_ping_content(message: str, role_id: int | None = None) -> str:
    if role_id:
        return f"<@&{role_id}> {message}"

    return message


class InactivityPingGroup(app_commands.Group):
    def __init__(self, bot: commands.Bot, cog: commands.Cog):
        super().__init__(name="inactivity-ping", description="Auto ping quiet channels.")
        self.bot = bot
        self.cog = cog

    @app_commands.command(name="set", description="Set an inactivity ping for a channel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_ping(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        hours: app_commands.Range[int, 1, 720],
        message: str,
        role: discord.Role | None = None,
        persona_key: str | None = None,
        cooldown_hours: app_commands.Range[int, 1, 720] = DEFAULT_COOLDOWN_HOURS,
    ):
        if len(message) > 1800:
            await interaction.response.send_message(
                embed=error_embed("Inactivity ping message must be 1800 characters or less."),
                ephemeral=True,
            )
            return

        permissions = channel.permissions_for(interaction.guild.me)

        if not permissions.view_channel:
            await interaction.response.send_message(
                embed=error_embed("I do not have permission to view that channel."),
                ephemeral=True,
            )
            return

        if not permissions.send_messages:
            await interaction.response.send_message(
                embed=error_embed("I need `Send Messages` in that channel."),
                ephemeral=True,
            )
            return

        if persona_key and not permissions.manage_webhooks:
            await interaction.response.send_message(
                embed=error_embed("I need `Manage Webhooks` in that channel to send inactivity pings as a persona."),
                ephemeral=True,
            )
            return

        guild_data = self.bot.db.get_guild(interaction.guild.id)
        config = get_inactivity_config(guild_data)

        persona_key = persona_key.lower().strip() if persona_key else None
        persona = get_persona(guild_data, persona_key)

        if persona_key and not persona:
            await interaction.response.send_message(
                embed=error_embed("I could not find an enabled persona with that key."),
                ephemeral=True,
            )
            return

        if role:
            if role.is_default():
                await interaction.response.send_message(
                    embed=error_embed("Use a real role instead of `@everyone`. We are not summoning the entire village."),
                    ephemeral=True,
                )
                return

            if role >= interaction.user.top_role and interaction.guild.owner_id != interaction.user.id:
                await interaction.response.send_message(
                    embed=error_embed("You cannot configure a ping role equal to or higher than your highest role."),
                    ephemeral=True,
                )
                return

        channel_key = str(channel.id)

        config["channels"][channel_key] = {
            "channel_id": channel.id,
            "enabled": True,
            "hours": int(hours),
            "cooldown_hours": int(cooldown_hours),
            "message": message,
            "role_id": role.id if role else None,
            "persona_key": persona_key,
            "last_message_at": now_ts(),
            "last_ping_at": None,
            "created_by": interaction.user.id,
            "updated_by": interaction.user.id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        guild_data["inactivity_ping"] = config
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        role_text = role.mention if role else "None"
        persona_text = persona_key or "None"

        await interaction.response.send_message(
            embed=success_embed(
                f"Inactivity ping set for {channel.mention}.\n"
                f"Trigger after: **{hours} hour(s)**\n"
                f"Cooldown: **{cooldown_hours} hour(s)**\n"
                f"Role: {role_text}\n"
                f"Persona: `{persona_text}`"
            ),
            ephemeral=True,
        )

    @app_commands.command(name="disable", description="Disable inactivity ping for a channel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def disable_ping(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
    ):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        config = get_inactivity_config(guild_data)
        channel_key = str(channel.id)

        if channel_key not in config["channels"]:
            await interaction.response.send_message(
                embed=error_embed("That channel does not have an inactivity ping configured."),
                ephemeral=True,
            )
            return

        config["channels"][channel_key]["enabled"] = False
        config["channels"][channel_key]["updated_by"] = interaction.user.id
        config["channels"][channel_key]["updated_at"] = datetime.now(timezone.utc).isoformat()

        guild_data["inactivity_ping"] = config
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(
            embed=success_embed(f"Inactivity ping disabled for {channel.mention}."),
            ephemeral=True,
        )

    @app_commands.command(name="clear", description="Remove inactivity ping config from a channel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def clear_ping(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
    ):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        config = get_inactivity_config(guild_data)
        channel_key = str(channel.id)

        if channel_key not in config["channels"]:
            await interaction.response.send_message(
                embed=error_embed("That channel does not have an inactivity ping configured."),
                ephemeral=True,
            )
            return

        config["channels"].pop(channel_key, None)

        guild_data["inactivity_ping"] = config
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(
            embed=success_embed(f"Inactivity ping cleared from {channel.mention}."),
            ephemeral=True,
        )

    @app_commands.command(name="list", description="List inactivity pings in this server.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def list_pings(self, interaction: discord.Interaction):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        config = get_inactivity_config(guild_data)
        channels = config.get("channels", {})

        if not channels:
            await interaction.response.send_message(
                embed=info_embed("Inactivity Pings", "No inactivity pings are configured yet."),
                ephemeral=True,
            )
            return

        lines = []
        current_time = now_ts()

        for channel_id, item in channels.items():
            channel = interaction.guild.get_channel(int(channel_id))
            channel_text = channel.mention if channel else f"Missing channel `{channel_id}`"

            enabled = item.get("enabled", False)
            hours = int(item.get("hours", 24))
            cooldown_hours = int(item.get("cooldown_hours", DEFAULT_COOLDOWN_HOURS))
            last_message_at = item.get("last_message_at")
            last_ping_at = item.get("last_ping_at")
            role_id = item.get("role_id")
            persona_key = item.get("persona_key")

            idle_text = "Unknown"

            if last_message_at:
                idle_text = format_seconds(current_time - int(last_message_at))

            last_ping_text = "Never"

            if last_ping_at:
                last_ping_text = f"{format_seconds(current_time - int(last_ping_at))} ago"

            role_text = f"<@&{role_id}>" if role_id else "None"

            preview = item.get("message", "")[:120]

            if len(item.get("message", "")) > 120:
                preview += "..."

            lines.append(
                f"**{channel_text}**\n"
                f"Enabled: `{enabled}`\n"
                f"Trigger: `{hours}h` | Cooldown: `{cooldown_hours}h`\n"
                f"Idle: `{idle_text}` | Last ping: `{last_ping_text}`\n"
                f"Role: {role_text} | Persona: `{persona_key or 'None'}`\n"
                f"Message: {preview}"
            )

        text = "\n\n".join(lines)

        if len(text) > 3800:
            text = text[:3800] + "\n..."

        await interaction.response.send_message(
            embed=info_embed("Inactivity Pings", text),
            ephemeral=True,
        )

    @app_commands.command(name="test", description="Send a test inactivity ping.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def test_ping(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
    ):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        config = get_inactivity_config(guild_data)
        item = config["channels"].get(str(channel.id))

        if not item:
            await interaction.response.send_message(
                embed=error_embed("That channel does not have an inactivity ping configured."),
                ephemeral=True,
            )
            return

        success = await self.cog.send_inactivity_ping(
            guild=interaction.guild,
            channel=channel,
            config=item,
            guild_data=guild_data,
            is_test=True,
        )

        if not success:
            await interaction.response.send_message(
                embed=error_embed("I could not send the test ping. Check permissions, webhook access, or persona settings."),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=success_embed(f"Test inactivity ping sent in {channel.mention}."),
            ephemeral=True,
        )

    @set_ping.autocomplete("persona_key")
    async def persona_key_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        personas = get_personas_from_guild_data(guild_data)
        current = current.lower().strip()
        choices = []

        for key, persona in personas.items():
            if current and current not in key.lower() and current not in persona.get("name", "").lower():
                continue

            if not persona.get("enabled", True):
                continue

            label = f"{key} | {persona.get('name', 'Unnamed Persona')}"

            choices.append(
                app_commands.Choice(
                    name=label[:100],
                    value=key[:100],
                )
            )

        return choices[:25]


class InactivityPing(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.tree.add_command(InactivityPingGroup(bot, self))
        self.inactivity_loop.start()

    def cog_unload(self):
        self.inactivity_loop.cancel()

    async def send_inactivity_ping(
        self,
        guild: discord.Guild,
        channel: discord.TextChannel,
        config: dict,
        guild_data: dict,
        is_test: bool = False,
    ) -> bool:
        message = config.get("message")

        if not message:
            return False

        role_id = config.get("role_id")
        persona_key = config.get("persona_key")
        content = build_ping_content(message, role_id)

        if is_test:
            content = f"**[Test Ping]** {content}"

        persona = get_persona(guild_data, persona_key)

        if persona:
            permissions = channel.permissions_for(guild.me)

            if permissions.manage_webhooks:
                webhook = await get_or_create_persona_webhook(channel)

                if webhook:
                    try:
                        await webhook.send(
                            content=content,
                            username=persona.get("name", "Persona")[:80],
                            avatar_url=persona.get("avatar_url"),
                            allowed_mentions=discord.AllowedMentions(
                                everyone=False,
                                users=False,
                                roles=True,
                            ),
                        )
                        return True
                    except (discord.Forbidden, discord.HTTPException):
                        return False

            return False

        try:
            await channel.send(
                content,
                allowed_mentions=discord.AllowedMentions(
                    everyone=False,
                    users=False,
                    roles=True,
                ),
            )
            return True
        except (discord.Forbidden, discord.HTTPException):
            return False

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild:
            return

        if message.author.bot:
            return

        guild_data = self.bot.db.get_guild(message.guild.id)
        config = get_inactivity_config(guild_data)
        channels = config.get("channels", {})

        channel_key = str(message.channel.id)

        if channel_key not in channels:
            return

        channels[channel_key]["last_message_at"] = now_ts()
        channels[channel_key]["last_user_id"] = message.author.id

        guild_data["inactivity_ping"] = config
        self.bot.db.update_guild(message.guild.id, guild_data)

    @tasks.loop(seconds=DEFAULT_CHECK_INTERVAL_SECONDS)
    async def inactivity_loop(self):
        for guild in self.bot.guilds:
            guild_data = self.bot.db.get_guild(guild.id)
            config = get_inactivity_config(guild_data)
            channels = config.get("channels", {})

            if not channels:
                continue

            changed = False
            current_time = now_ts()

            for channel_id, item in channels.items():
                if not item.get("enabled", False):
                    continue

                channel = await fetch_text_channel(guild, item.get("channel_id"))

                if not channel:
                    continue

                trigger_seconds = int(item.get("hours", 24)) * 3600
                cooldown_seconds = int(item.get("cooldown_hours", DEFAULT_COOLDOWN_HOURS)) * 3600
                last_message_at = item.get("last_message_at") or current_time
                last_ping_at = item.get("last_ping_at") or 0

                idle_seconds = current_time - int(last_message_at)
                since_ping_seconds = current_time - int(last_ping_at)

                if idle_seconds < trigger_seconds:
                    continue

                if since_ping_seconds < cooldown_seconds:
                    continue

                success = await self.send_inactivity_ping(
                    guild=guild,
                    channel=channel,
                    config=item,
                    guild_data=guild_data,
                    is_test=False,
                )

                if not success:
                    continue

                item["last_ping_at"] = current_time
                channels[channel_id] = item
                changed = True

            if changed:
                config["channels"] = channels
                guild_data["inactivity_ping"] = config
                self.bot.db.update_guild(guild.id, guild_data)

    @inactivity_loop.before_loop
    async def before_inactivity_loop(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(InactivityPing(bot))

import time

import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import success_embed, error_embed, info_embed


DEFAULT_STICKY_COOLDOWN = 60
PERSONA_WEBHOOK_NAME = "Centari Persona Relay"
DEFAULT_PERSONA_KEY = "centari"


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
            reason="Centari sticky persona relay",
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


class StickyGroup(app_commands.Group):
    def __init__(self, bot: commands.Bot, cog: commands.Cog):
        super().__init__(name="sticky", description="Sticky message tools.")
        self.bot = bot
        self.cog = cog

    @app_commands.command(name="set", description="Set a sticky message for a channel.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def set_sticky(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        message: str,
        cooldown_seconds: app_commands.Range[int, 15, 3600] = DEFAULT_STICKY_COOLDOWN,
        persona_key: str | None = None,
    ):
        if len(message) > 1800:
            await interaction.response.send_message(
                embed=error_embed("Sticky messages must be 1800 characters or less."),
                ephemeral=True,
            )
            return

        guild_data = self.bot.db.get_guild(interaction.guild.id)
        persona_key = persona_key.lower().strip() if persona_key else None
        persona = get_persona(guild_data, persona_key)

        if persona_key and not persona:
            await interaction.response.send_message(
                embed=error_embed("I could not find an enabled persona with that key."),
                ephemeral=True,
            )
            return

        channel_permissions = channel.permissions_for(interaction.guild.me)

        if not channel_permissions.send_messages:
            await interaction.response.send_message(
                embed=error_embed("I do not have permission to send messages in that channel."),
                ephemeral=True,
            )
            return

        if not channel_permissions.manage_messages:
            await interaction.response.send_message(
                embed=error_embed("I need `Manage Messages` in that channel so I can clean up old sticky messages."),
                ephemeral=True,
            )
            return

        if persona_key and not channel_permissions.manage_webhooks:
            await interaction.response.send_message(
                embed=error_embed("I need `Manage Webhooks` in that channel to post a sticky as a persona."),
                ephemeral=True,
            )
            return

        stickies = guild_data.setdefault("stickies", {})
        old_sticky = stickies.get(str(channel.id))

        if old_sticky and old_sticky.get("message_id"):
            await self.cog.delete_sticky_message(
                channel=channel,
                message_id=old_sticky.get("message_id"),
            )

        sent = await self.cog.send_sticky_message(
            channel=channel,
            sticky_text=message,
            persona=persona,
        )

        if not sent:
            await interaction.response.send_message(
                embed=error_embed("I could not send the sticky message. Check my channel permissions."),
                ephemeral=True,
            )
            return

        stickies[str(channel.id)] = {
            "channel_id": channel.id,
            "message": message,
            "message_id": sent.id,
            "cooldown_seconds": cooldown_seconds,
            "enabled": True,
            "persona_key": persona_key,
            "created_by": interaction.user.id,
            "updated_by": interaction.user.id,
            "updated_at": discord.utils.utcnow().isoformat(),
        }

        guild_data["stickies"] = stickies
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        persona_text = ""

        if persona_key:
            persona_text = f"\nPersona: `{persona_key}`"

        await interaction.response.send_message(
            embed=success_embed(
                f"Sticky message set in {channel.mention}.\n"
                f"Cooldown: **{cooldown_seconds} seconds**."
                f"{persona_text}"
            ),
            ephemeral=True,
        )

    @app_commands.command(name="clear", description="Clear a sticky message from a channel.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clear_sticky(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
    ):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        stickies = guild_data.setdefault("stickies", {})

        sticky = stickies.get(str(channel.id))

        if not sticky:
            await interaction.response.send_message(
                embed=error_embed("That channel does not have a sticky message configured."),
                ephemeral=True,
            )
            return

        await self.cog.delete_sticky_message(
            channel=channel,
            message_id=sticky.get("message_id"),
        )

        stickies.pop(str(channel.id), None)
        guild_data["stickies"] = stickies
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(
            embed=success_embed(f"Sticky message cleared from {channel.mention}."),
            ephemeral=True,
        )

    @app_commands.command(name="list", description="List sticky messages in this server.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def list_stickies(self, interaction: discord.Interaction):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        stickies = guild_data.get("stickies", {})

        if not isinstance(stickies, dict) or not stickies:
            await interaction.response.send_message(
                embed=info_embed("Sticky Messages", "No sticky messages are configured yet."),
                ephemeral=True,
            )
            return

        lines = []

        for channel_id, sticky in stickies.items():
            channel = interaction.guild.get_channel(int(channel_id))

            channel_text = channel.mention if channel else f"Missing channel `{channel_id}`"
            message = sticky.get("message", "")
            cooldown = sticky.get("cooldown_seconds", DEFAULT_STICKY_COOLDOWN)
            enabled = sticky.get("enabled", True)
            persona_key = sticky.get("persona_key")

            preview = message[:120]

            if len(message) > 120:
                preview += "..."

            status = "Enabled" if enabled else "Disabled"
            persona_text = persona_key or "None"

            lines.append(
                f"**{channel_text}**\n"
                f"Status: `{status}`\n"
                f"Cooldown: `{cooldown}s`\n"
                f"Persona: `{persona_text}`\n"
                f"Message: {preview}"
            )

        text = "\n\n".join(lines)

        if len(text) > 3800:
            text = text[:3800] + "\n..."

        await interaction.response.send_message(
            embed=info_embed("Sticky Messages", text),
            ephemeral=True,
        )

    @app_commands.command(name="refresh", description="Manually repost a sticky message.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def refresh_sticky(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
    ):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        stickies = guild_data.get("stickies", {})
        sticky = stickies.get(str(channel.id))

        if not sticky:
            await interaction.response.send_message(
                embed=error_embed("That channel does not have a sticky message configured."),
                ephemeral=True,
            )
            return

        if not sticky.get("enabled", True):
            await interaction.response.send_message(
                embed=error_embed("That sticky message is disabled."),
                ephemeral=True,
            )
            return

        success = await self.cog.repost_sticky(
            guild=interaction.guild,
            channel=channel,
            sticky=sticky,
        )

        if not success:
            await interaction.response.send_message(
                embed=error_embed("I could not refresh that sticky message. Check my channel permissions and persona settings."),
                ephemeral=True,
            )
            return

        stickies[str(channel.id)] = sticky
        guild_data["stickies"] = stickies
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(
            embed=success_embed(f"Sticky message refreshed in {channel.mention}."),
            ephemeral=True,
        )


class Sticky(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.tree.add_command(StickyGroup(bot, self))
        self.cooldowns = {}

    async def delete_sticky_message(self, channel: discord.TextChannel, message_id):
        if not message_id:
            return

        try:
            old_message = await channel.fetch_message(int(message_id))
            await old_message.delete()
        except (discord.Forbidden, discord.NotFound, discord.HTTPException, ValueError, TypeError):
            return

    async def send_sticky_message(
        self,
        channel: discord.TextChannel,
        sticky_text: str,
        persona: dict | None = None,
    ):
        if persona:
            webhook = await get_or_create_persona_webhook(channel)

            if not webhook:
                return None

            persona_name = persona.get("name", "Persona")[:80]
            avatar_url = persona.get("avatar_url")

            try:
                return await webhook.send(
                    content=sticky_text,
                    username=persona_name,
                    avatar_url=avatar_url,
                    allowed_mentions=discord.AllowedMentions.none(),
                    wait=True,
                )
            except (discord.Forbidden, discord.HTTPException):
                return None

        try:
            return await channel.send(
                sticky_text,
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except (discord.Forbidden, discord.HTTPException):
            return None

    async def repost_sticky(
        self,
        guild: discord.Guild,
        channel: discord.TextChannel,
        sticky: dict,
    ) -> bool:
        channel_permissions = channel.permissions_for(guild.me)

        if not channel_permissions.send_messages:
            return False

        if not channel_permissions.manage_messages:
            return False

        old_message_id = sticky.get("message_id")
        sticky_text = sticky.get("message")
        persona_key = sticky.get("persona_key")

        if not sticky_text:
            return False

        guild_data = self.bot.db.get_guild(guild.id)
        persona = get_persona(guild_data, persona_key)

        if persona_key and not persona:
            return False

        if persona_key and not channel_permissions.manage_webhooks:
            return False

        await self.delete_sticky_message(channel, old_message_id)

        sent = await self.send_sticky_message(
            channel=channel,
            sticky_text=sticky_text,
            persona=persona,
        )

        if not sent:
            return False

        sticky["message_id"] = sent.id
        sticky["updated_at"] = discord.utils.utcnow().isoformat()

        return True

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild:
            return

        if message.author.bot:
            return

        guild_data = self.bot.db.get_guild(message.guild.id)
        stickies = guild_data.get("stickies", {})

        if not isinstance(stickies, dict):
            return

        sticky = stickies.get(str(message.channel.id))

        if not sticky:
            return

        if not sticky.get("enabled", True):
            return

        cooldown_seconds = int(sticky.get("cooldown_seconds", DEFAULT_STICKY_COOLDOWN))
        cooldown_key = (message.guild.id, message.channel.id)
        now = time.time()

        last_run = self.cooldowns.get(cooldown_key, 0)

        if now - last_run < cooldown_seconds:
            return

        self.cooldowns[cooldown_key] = now

        channel = await fetch_text_channel(message.guild, sticky.get("channel_id"))

        if not channel:
            return

        success = await self.repost_sticky(
            guild=message.guild,
            channel=channel,
            sticky=sticky,
        )

        if not success:
            return

        stickies[str(channel.id)] = sticky
        guild_data["stickies"] = stickies
        self.bot.db.update_guild(message.guild.id, guild_data)


async def setup(bot: commands.Bot):
    await bot.add_cog(Sticky(bot))

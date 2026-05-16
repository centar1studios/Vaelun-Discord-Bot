import asyncio
import logging
import os
import re
import xml.etree.ElementTree as ET
from typing import Optional

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv

from utils.embeds import success_embed, error_embed, info_embed


load_dotenv()

logger = logging.getLogger("centari.social")

YOUTUBE_FEED_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
TWITCH_TOKEN_URL = "https://id.twitch.tv/oauth2/token"
TWITCH_USERS_URL = "https://api.twitch.tv/helix/users"
TWITCH_STREAMS_URL = "https://api.twitch.tv/helix/streams"

DEFAULT_CHECK_MINUTES = 10

KEY_RE = re.compile(r"^[a-z0-9_-]{2,32}$")
YOUTUBE_CHANNEL_ID_RE = re.compile(r"^UC[a-zA-Z0-9_-]{20,30}$")
TWITCH_LOGIN_RE = re.compile(r"^[a-zA-Z0-9_]{3,25}$")


def clean_key(key: str) -> str:
    return key.lower().strip()


def valid_key(key: str) -> bool:
    return bool(KEY_RE.match(key))


def clean_twitch_login(value: str) -> str:
    value = value.strip()

    if value.startswith("@"):
        value = value[1:]

    if "twitch.tv/" in value:
        value = value.rstrip("/").split("twitch.tv/")[-1].split("/")[0]

    return value.lower().strip()


def validate_twitch_login(value: str) -> tuple[bool, str]:
    login = clean_twitch_login(value)

    if not login:
        return False, "Twitch username cannot be empty."

    if not TWITCH_LOGIN_RE.match(login):
        return (
            False,
            "That does not look like a valid Twitch username. Use the channel name only, like `centaristudios`.",
        )

    return True, login


def clean_youtube_channel_id(value: str) -> str:
    return value.strip()


def validate_youtube_channel_id(value: str) -> tuple[bool, str]:
    value = clean_youtube_channel_id(value)

    if not value:
        return False, "YouTube channel ID cannot be empty."

    if value.startswith("@"):
        return (
            False,
            "That looks like a YouTube handle. I need the channel ID that starts with `UC`.",
        )

    if "youtube.com/@" in value:
        return (
            False,
            "That looks like a YouTube handle URL. Open the page source and search `channelId`, then copy the `UC...` value.",
        )

    if "youtube.com/channel/" in value:
        possible_id = value.rstrip("/").split("/channel/")[-1].split("/")[0]

        if YOUTUBE_CHANNEL_ID_RE.match(possible_id):
            return True, possible_id

        return (
            False,
            "That channel URL has a channel ID, but it does not look valid. It should start with `UC`.",
        )

    if not value.startswith("UC"):
        return False, "YouTube channel IDs usually start with `UC`."

    if not YOUTUBE_CHANNEL_ID_RE.match(value):
        return (
            False,
            "That does not look like a valid YouTube channel ID. It should start with `UC` and be around 24 characters long.",
        )

    return True, value


def get_social_config(guild_data: dict) -> dict:
    social = guild_data.get("social_notifications")

    if not isinstance(social, dict):
        social = {}
        guild_data["social_notifications"] = social

    youtube = social.get("youtube")

    if not isinstance(youtube, dict):
        youtube = {}
        social["youtube"] = youtube

    twitch = social.get("twitch")

    if not isinstance(twitch, dict):
        twitch = {}
        social["twitch"] = twitch

    return social


def get_youtube_configs(guild_data: dict) -> dict:
    social = get_social_config(guild_data)
    youtube = social.get("youtube", {})

    if not isinstance(youtube, dict):
        youtube = {}
        social["youtube"] = youtube

    for key, config in list(youtube.items()):
        if not isinstance(config, dict):
            youtube.pop(key, None)
            continue

        config.setdefault("key", key)
        config.setdefault("enabled", True)
        config.setdefault("discord_channel_id", None)
        config.setdefault("youtube_channel_id", None)
        config.setdefault("youtube_name", key)
        config.setdefault("last_video_id", None)
        config.setdefault("mention_role_id", None)

    return youtube


def get_twitch_configs(guild_data: dict) -> dict:
    social = get_social_config(guild_data)
    twitch = social.get("twitch", {})

    if not isinstance(twitch, dict):
        twitch = {}
        social["twitch"] = twitch

    for key, config in list(twitch.items()):
        if not isinstance(config, dict):
            twitch.pop(key, None)
            continue

        config.setdefault("key", key)
        config.setdefault("enabled", True)
        config.setdefault("discord_channel_id", None)
        config.setdefault("twitch_login", None)
        config.setdefault("twitch_name", key)
        config.setdefault("mention_role_id", None)
        config.setdefault("is_live", False)
        config.setdefault("last_stream_id", None)
        config.setdefault("last_started_at", None)

    return twitch


def build_youtube_embed(video: dict, youtube_name: str) -> discord.Embed:
    embed = discord.Embed(
        title=video["title"],
        url=video["url"],
        description=f"New upload from **{youtube_name}**",
        color=discord.Color.red(),
    )

    if video.get("published"):
        embed.add_field(
            name="Published",
            value=video["published"],
            inline=False,
        )

    if video.get("thumbnail"):
        embed.set_image(url=video["thumbnail"])

    embed.set_footer(text=f"YouTube Video ID: {video['video_id']}")

    return embed


def build_twitch_embed(stream: dict, twitch_name: str, twitch_login: str) -> discord.Embed:
    stream_url = f"https://www.twitch.tv/{twitch_login}"

    title = stream.get("title") or f"{twitch_name} is live!"
    game_name = stream.get("game_name") or "Unknown"
    viewer_count = stream.get("viewer_count")
    started_at = stream.get("started_at")
    thumbnail_url = stream.get("thumbnail_url")

    embed = discord.Embed(
        title=title,
        url=stream_url,
        description=f"**{twitch_name}** is live on Twitch!",
        color=discord.Color.purple(),
    )

    embed.add_field(
        name="Channel",
        value=f"[{twitch_name}]({stream_url})",
        inline=True,
    )

    embed.add_field(
        name="Category",
        value=game_name,
        inline=True,
    )

    if viewer_count is not None:
        embed.add_field(
            name="Viewers",
            value=str(viewer_count),
            inline=True,
        )

    if started_at:
        embed.add_field(
            name="Started",
            value=started_at,
            inline=False,
        )

    if thumbnail_url:
        thumbnail_url = thumbnail_url.replace("{width}", "1280").replace("{height}", "720")
        embed.set_image(url=thumbnail_url)

    if stream.get("id"):
        embed.set_footer(text=f"Twitch Stream ID: {stream['id']}")

    return embed


class SocialYoutubeGroup(app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__(name="youtube", description="YouTube notification tools.")
        self.bot = bot

    @app_commands.command(name="add", description="Add YouTube upload notifications.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def add(
        self,
        interaction: discord.Interaction,
        key: str,
        youtube_channel_id: str,
        discord_channel: discord.TextChannel,
        youtube_name: str,
        mention_role: Optional[discord.Role] = None,
    ):
        key = clean_key(key)

        if not valid_key(key):
            await interaction.response.send_message(
                embed=error_embed("Key must be 2-32 characters using lowercase letters, numbers, `_`, or `-`."),
                ephemeral=True,
            )
            return

        is_valid_id, cleaned_or_error = validate_youtube_channel_id(youtube_channel_id)

        if not is_valid_id:
            await interaction.response.send_message(
                embed=error_embed(cleaned_or_error),
                ephemeral=True,
            )
            return

        youtube_channel_id = cleaned_or_error

        permissions = discord_channel.permissions_for(interaction.guild.me)

        if not permissions.view_channel:
            await interaction.response.send_message(
                embed=error_embed("I do not have permission to view that Discord channel."),
                ephemeral=True,
            )
            return

        if not permissions.send_messages:
            await interaction.response.send_message(
                embed=error_embed("I do not have permission to send messages in that Discord channel."),
                ephemeral=True,
            )
            return

        if not permissions.embed_links:
            await interaction.response.send_message(
                embed=error_embed("I need `Embed Links` in that Discord channel."),
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        cog = self.bot.get_cog("Social")

        latest_video = None

        if cog:
            latest_video = await cog.fetch_latest_youtube_video(youtube_channel_id)

        if latest_video is None:
            await interaction.followup.send(
                embed=error_embed(
                    "I could not read that YouTube RSS feed. The ID format looks okay, but YouTube did not return a usable feed."
                ),
                ephemeral=True,
            )
            return

        guild_data = self.bot.db.get_guild(interaction.guild.id)
        youtube_configs = get_youtube_configs(guild_data)

        if key in youtube_configs:
            await interaction.followup.send(
                embed=error_embed("A YouTube notification with that key already exists."),
                ephemeral=True,
            )
            return

        youtube_configs[key] = {
            "key": key,
            "enabled": True,
            "discord_channel_id": discord_channel.id,
            "youtube_channel_id": youtube_channel_id,
            "youtube_name": youtube_name.strip(),
            "last_video_id": latest_video["video_id"],
            "mention_role_id": mention_role.id if mention_role else None,
            "created_by": interaction.user.id,
            "updated_by": interaction.user.id,
            "updated_at": discord.utils.utcnow().isoformat(),
        }

        guild_data["social_notifications"]["youtube"] = youtube_configs
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        mention_text = mention_role.mention if mention_role else "None"

        await interaction.followup.send(
            embed=success_embed(
                f"YouTube notifications added for `{key}`.\n"
                f"YouTube: **{youtube_name}**\n"
                f"YouTube Channel ID: `{youtube_channel_id}`\n"
                f"Discord Channel: {discord_channel.mention}\n"
                f"Mention Role: {mention_text}\n"
                f"Seeded latest video so old uploads will not spam the channel."
            ),
            ephemeral=True,
        )

    @app_commands.command(name="remove", description="Remove YouTube upload notifications.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def remove(self, interaction: discord.Interaction, key: str):
        key = clean_key(key)
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        youtube_configs = get_youtube_configs(guild_data)

        if key not in youtube_configs:
            await interaction.response.send_message(
                embed=error_embed("I could not find a YouTube notification with that key."),
                ephemeral=True,
            )
            return

        youtube_configs.pop(key, None)
        guild_data["social_notifications"]["youtube"] = youtube_configs
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(
            embed=success_embed(f"YouTube notification `{key}` removed."),
            ephemeral=True,
        )

    @app_commands.command(name="list", description="List YouTube upload notifications.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def list_notifications(self, interaction: discord.Interaction):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        youtube_configs = get_youtube_configs(guild_data)

        if not youtube_configs:
            await interaction.response.send_message(
                embed=info_embed("YouTube Notifications", "No YouTube notifications are configured yet."),
                ephemeral=True,
            )
            return

        lines = []

        for key, config in sorted(youtube_configs.items()):
            discord_channel = interaction.guild.get_channel(int(config.get("discord_channel_id") or 0))
            channel_text = discord_channel.mention if discord_channel else "Missing channel"

            role_id = config.get("mention_role_id")
            role = interaction.guild.get_role(int(role_id)) if role_id else None
            role_text = role.mention if role else "None"

            status = "Enabled" if config.get("enabled", True) else "Disabled"

            lines.append(
                f"**{key}**\n"
                f"Status: `{status}`\n"
                f"YouTube: **{config.get('youtube_name', key)}**\n"
                f"YouTube Channel ID: `{config.get('youtube_channel_id')}`\n"
                f"Discord Channel: {channel_text}\n"
                f"Mention Role: {role_text}\n"
                f"Last Video ID: `{config.get('last_video_id')}`"
            )

        text = "\n\n".join(lines)

        if len(text) > 3800:
            text = text[:3800] + "\n..."

        await interaction.response.send_message(
            embed=info_embed("YouTube Notifications", text),
            ephemeral=True,
        )

    @app_commands.command(name="enable", description="Enable a YouTube notification.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def enable(self, interaction: discord.Interaction, key: str):
        key = clean_key(key)
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        youtube_configs = get_youtube_configs(guild_data)
        config = youtube_configs.get(key)

        if not config:
            await interaction.response.send_message(
                embed=error_embed("I could not find a YouTube notification with that key."),
                ephemeral=True,
            )
            return

        config["enabled"] = True
        config["updated_by"] = interaction.user.id
        config["updated_at"] = discord.utils.utcnow().isoformat()

        youtube_configs[key] = config
        guild_data["social_notifications"]["youtube"] = youtube_configs
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(
            embed=success_embed(f"YouTube notification `{key}` enabled."),
            ephemeral=True,
        )

    @app_commands.command(name="disable", description="Disable a YouTube notification.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def disable(self, interaction: discord.Interaction, key: str):
        key = clean_key(key)
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        youtube_configs = get_youtube_configs(guild_data)
        config = youtube_configs.get(key)

        if not config:
            await interaction.response.send_message(
                embed=error_embed("I could not find a YouTube notification with that key."),
                ephemeral=True,
            )
            return

        config["enabled"] = False
        config["updated_by"] = interaction.user.id
        config["updated_at"] = discord.utils.utcnow().isoformat()

        youtube_configs[key] = config
        guild_data["social_notifications"]["youtube"] = youtube_configs
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(
            embed=success_embed(f"YouTube notification `{key}` disabled."),
            ephemeral=True,
        )

    @app_commands.command(name="set-channel", description="Change where a YouTube notification posts.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_channel(
        self,
        interaction: discord.Interaction,
        key: str,
        discord_channel: discord.TextChannel,
    ):
        key = clean_key(key)

        permissions = discord_channel.permissions_for(interaction.guild.me)

        if not permissions.view_channel:
            await interaction.response.send_message(
                embed=error_embed("I do not have permission to view that Discord channel."),
                ephemeral=True,
            )
            return

        if not permissions.send_messages:
            await interaction.response.send_message(
                embed=error_embed("I do not have permission to send messages in that Discord channel."),
                ephemeral=True,
            )
            return

        if not permissions.embed_links:
            await interaction.response.send_message(
                embed=error_embed("I need `Embed Links` in that Discord channel."),
                ephemeral=True,
            )
            return

        guild_data = self.bot.db.get_guild(interaction.guild.id)
        youtube_configs = get_youtube_configs(guild_data)
        config = youtube_configs.get(key)

        if not config:
            await interaction.response.send_message(
                embed=error_embed("I could not find a YouTube notification with that key."),
                ephemeral=True,
            )
            return

        config["discord_channel_id"] = discord_channel.id
        config["updated_by"] = interaction.user.id
        config["updated_at"] = discord.utils.utcnow().isoformat()

        youtube_configs[key] = config
        guild_data["social_notifications"]["youtube"] = youtube_configs
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(
            embed=success_embed(f"YouTube notification `{key}` will now post in {discord_channel.mention}."),
            ephemeral=True,
        )

    @app_commands.command(name="set-role", description="Set the role pinged by a YouTube notification.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_role(
        self,
        interaction: discord.Interaction,
        key: str,
        mention_role: discord.Role,
    ):
        key = clean_key(key)
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        youtube_configs = get_youtube_configs(guild_data)
        config = youtube_configs.get(key)

        if not config:
            await interaction.response.send_message(
                embed=error_embed("I could not find a YouTube notification with that key."),
                ephemeral=True,
            )
            return

        config["mention_role_id"] = mention_role.id
        config["updated_by"] = interaction.user.id
        config["updated_at"] = discord.utils.utcnow().isoformat()

        youtube_configs[key] = config
        guild_data["social_notifications"]["youtube"] = youtube_configs
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(
            embed=success_embed(f"YouTube notification `{key}` will now ping {mention_role.mention}."),
            ephemeral=True,
        )

    @app_commands.command(name="clear-role", description="Remove the role ping from a YouTube notification.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def clear_role(self, interaction: discord.Interaction, key: str):
        key = clean_key(key)
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        youtube_configs = get_youtube_configs(guild_data)
        config = youtube_configs.get(key)

        if not config:
            await interaction.response.send_message(
                embed=error_embed("I could not find a YouTube notification with that key."),
                ephemeral=True,
            )
            return

        config["mention_role_id"] = None
        config["updated_by"] = interaction.user.id
        config["updated_at"] = discord.utils.utcnow().isoformat()

        youtube_configs[key] = config
        guild_data["social_notifications"]["youtube"] = youtube_configs
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(
            embed=success_embed(f"YouTube notification `{key}` will no longer ping a role."),
            ephemeral=True,
        )

    @app_commands.command(name="set-name", description="Change the display name for a YouTube notification.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_name(
        self,
        interaction: discord.Interaction,
        key: str,
        youtube_name: str,
    ):
        key = clean_key(key)
        youtube_name = youtube_name.strip()

        if not youtube_name:
            await interaction.response.send_message(
                embed=error_embed("YouTube display name cannot be empty."),
                ephemeral=True,
            )
            return

        guild_data = self.bot.db.get_guild(interaction.guild.id)
        youtube_configs = get_youtube_configs(guild_data)
        config = youtube_configs.get(key)

        if not config:
            await interaction.response.send_message(
                embed=error_embed("I could not find a YouTube notification with that key."),
                ephemeral=True,
            )
            return

        config["youtube_name"] = youtube_name
        config["updated_by"] = interaction.user.id
        config["updated_at"] = discord.utils.utcnow().isoformat()

        youtube_configs[key] = config
        guild_data["social_notifications"]["youtube"] = youtube_configs
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(
            embed=success_embed(f"YouTube notification `{key}` display name set to **{youtube_name}**."),
            ephemeral=True,
        )

    @app_commands.command(name="refresh-latest", description="Save the newest YouTube video without posting it.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def refresh_latest(self, interaction: discord.Interaction, key: str):
        key = clean_key(key)
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        youtube_configs = get_youtube_configs(guild_data)
        config = youtube_configs.get(key)

        if not config:
            await interaction.response.send_message(
                embed=error_embed("I could not find a YouTube notification with that key."),
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        cog = self.bot.get_cog("Social")

        if not cog:
            await interaction.followup.send(
                embed=error_embed("Social cog is not loaded."),
                ephemeral=True,
            )
            return

        video = await cog.fetch_latest_youtube_video(config.get("youtube_channel_id"))

        if not video:
            await interaction.followup.send(
                embed=error_embed("I could not fetch the latest video for that YouTube channel."),
                ephemeral=True,
            )
            return

        old_video_id = config.get("last_video_id")
        config["last_video_id"] = video["video_id"]
        config["updated_by"] = interaction.user.id
        config["updated_at"] = discord.utils.utcnow().isoformat()

        youtube_configs[key] = config
        guild_data["social_notifications"]["youtube"] = youtube_configs
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.followup.send(
            embed=success_embed(
                f"YouTube notification `{key}` refreshed.\n"
                f"Old Last Video ID: `{old_video_id}`\n"
                f"New Last Video ID: `{video['video_id']}`\n"
                f"Latest Video: [{video['title']}]({video['url']})"
            ),
            ephemeral=True,
        )

    @app_commands.command(name="test", description="Send a test YouTube notification.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def test(self, interaction: discord.Interaction, key: str):
        key = clean_key(key)
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        youtube_configs = get_youtube_configs(guild_data)
        config = youtube_configs.get(key)

        if not config:
            await interaction.response.send_message(
                embed=error_embed("I could not find a YouTube notification with that key."),
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        cog = self.bot.get_cog("Social")

        if not cog:
            await interaction.followup.send(
                embed=error_embed("Social cog is not loaded."),
                ephemeral=True,
            )
            return

        video = await cog.fetch_latest_youtube_video(config.get("youtube_channel_id"))

        if not video:
            await interaction.followup.send(
                embed=error_embed("I could not fetch the latest video for that YouTube channel."),
                ephemeral=True,
            )
            return

        discord_channel = interaction.guild.get_channel(int(config.get("discord_channel_id") or 0))

        if not isinstance(discord_channel, discord.TextChannel):
            await interaction.followup.send(
                embed=error_embed("The saved Discord channel is missing or invalid."),
                ephemeral=True,
            )
            return

        await cog.send_youtube_notification(
            guild=interaction.guild,
            discord_channel=discord_channel,
            config=config,
            video=video,
            is_test=True,
        )

        await interaction.followup.send(
            embed=success_embed(f"Test notification sent to {discord_channel.mention}."),
            ephemeral=True,
        )

    @app_commands.command(name="check-now", description="Check YouTube notifications now.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def check_now(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        cog = self.bot.get_cog("Social")

        if not cog:
            await interaction.followup.send(
                embed=error_embed("Social cog is not loaded."),
                ephemeral=True,
            )
            return

        checked, posted = await cog.check_guild_youtube(interaction.guild)

        await interaction.followup.send(
            embed=success_embed(
                f"YouTube check complete.\n"
                f"Checked: **{checked}**\n"
                f"Posted: **{posted}**"
            ),
            ephemeral=True,
        )

    @remove.autocomplete("key")
    @enable.autocomplete("key")
    @disable.autocomplete("key")
    @set_channel.autocomplete("key")
    @set_role.autocomplete("key")
    @clear_role.autocomplete("key")
    @set_name.autocomplete("key")
    @refresh_latest.autocomplete("key")
    @test.autocomplete("key")
    async def youtube_key_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        youtube_configs = get_youtube_configs(guild_data)
        current = current.lower().strip()
        choices = []

        for key, config in sorted(youtube_configs.items()):
            if current and current not in key.lower():
                continue

            status = "on" if config.get("enabled", True) else "off"
            label = f"{key} | {config.get('youtube_name', key)} | {status}"

            choices.append(
                app_commands.Choice(
                    name=label[:100],
                    value=key[:100],
                )
            )

        return choices[:25]


class SocialTwitchGroup(app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__(name="twitch", description="Twitch notification tools.")
        self.bot = bot

    @app_commands.command(name="add", description="Add Twitch live notifications.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def add(
        self,
        interaction: discord.Interaction,
        key: str,
        twitch_login: str,
        discord_channel: discord.TextChannel,
        twitch_name: Optional[str] = None,
        mention_role: Optional[discord.Role] = None,
    ):
        key = clean_key(key)

        if not valid_key(key):
            await interaction.response.send_message(
                embed=error_embed("Key must be 2-32 characters using lowercase letters, numbers, `_`, or `-`."),
                ephemeral=True,
            )
            return

        is_valid_login, cleaned_or_error = validate_twitch_login(twitch_login)

        if not is_valid_login:
            await interaction.response.send_message(
                embed=error_embed(cleaned_or_error),
                ephemeral=True,
            )
            return

        twitch_login = cleaned_or_error

        permissions = discord_channel.permissions_for(interaction.guild.me)

        if not permissions.view_channel:
            await interaction.response.send_message(
                embed=error_embed("I do not have permission to view that Discord channel."),
                ephemeral=True,
            )
            return

        if not permissions.send_messages:
            await interaction.response.send_message(
                embed=error_embed("I do not have permission to send messages in that Discord channel."),
                ephemeral=True,
            )
            return

        if not permissions.embed_links:
            await interaction.response.send_message(
                embed=error_embed("I need `Embed Links` in that Discord channel."),
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        cog = self.bot.get_cog("Social")

        if not cog:
            await interaction.followup.send(
                embed=error_embed("Social cog is not loaded."),
                ephemeral=True,
            )
            return

        if not cog.twitch_is_configured():
            await interaction.followup.send(
                embed=error_embed(
                    "Twitch credentials are missing. Add `TWITCH_CLIENT_ID` and `TWITCH_CLIENT_SECRET` to `.env`, then restart the bot."
                ),
                ephemeral=True,
            )
            return

        twitch_user = await cog.fetch_twitch_user(twitch_login)

        if not twitch_user:
            await interaction.followup.send(
                embed=error_embed("I could not find that Twitch channel. Double-check the username."),
                ephemeral=True,
            )
            return

        stream = await cog.fetch_twitch_stream(twitch_login)

        guild_data = self.bot.db.get_guild(interaction.guild.id)
        twitch_configs = get_twitch_configs(guild_data)

        if key in twitch_configs:
            await interaction.followup.send(
                embed=error_embed("A Twitch notification with that key already exists."),
                ephemeral=True,
            )
            return

        display_name = twitch_name.strip() if twitch_name else twitch_user.get("display_name", twitch_login)

        twitch_configs[key] = {
            "key": key,
            "enabled": True,
            "discord_channel_id": discord_channel.id,
            "twitch_login": twitch_login,
            "twitch_name": display_name,
            "mention_role_id": mention_role.id if mention_role else None,
            "is_live": bool(stream),
            "last_stream_id": stream.get("id") if stream else None,
            "last_started_at": stream.get("started_at") if stream else None,
            "created_by": interaction.user.id,
            "updated_by": interaction.user.id,
            "updated_at": discord.utils.utcnow().isoformat(),
        }

        guild_data["social_notifications"]["twitch"] = twitch_configs
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        mention_text = mention_role.mention if mention_role else "None"
        live_text = "Currently live, so I seeded the stream and will wait for the next live session." if stream else "Currently offline."

        await interaction.followup.send(
            embed=success_embed(
                f"Twitch notifications added for `{key}`.\n"
                f"Twitch: **{display_name}**\n"
                f"Username: `{twitch_login}`\n"
                f"Discord Channel: {discord_channel.mention}\n"
                f"Mention Role: {mention_text}\n"
                f"{live_text}"
            ),
            ephemeral=True,
        )

    @app_commands.command(name="remove", description="Remove Twitch live notifications.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def remove(self, interaction: discord.Interaction, key: str):
        key = clean_key(key)
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        twitch_configs = get_twitch_configs(guild_data)

        if key not in twitch_configs:
            await interaction.response.send_message(
                embed=error_embed("I could not find a Twitch notification with that key."),
                ephemeral=True,
            )
            return

        twitch_configs.pop(key, None)
        guild_data["social_notifications"]["twitch"] = twitch_configs
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(
            embed=success_embed(f"Twitch notification `{key}` removed."),
            ephemeral=True,
        )

    @app_commands.command(name="list", description="List Twitch live notifications.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def list_notifications(self, interaction: discord.Interaction):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        twitch_configs = get_twitch_configs(guild_data)

        if not twitch_configs:
            await interaction.response.send_message(
                embed=info_embed("Twitch Notifications", "No Twitch notifications are configured yet."),
                ephemeral=True,
            )
            return

        lines = []

        for key, config in sorted(twitch_configs.items()):
            discord_channel = interaction.guild.get_channel(int(config.get("discord_channel_id") or 0))
            channel_text = discord_channel.mention if discord_channel else "Missing channel"

            role_id = config.get("mention_role_id")
            role = interaction.guild.get_role(int(role_id)) if role_id else None
            role_text = role.mention if role else "None"

            status = "Enabled" if config.get("enabled", True) else "Disabled"
            live_status = "Live" if config.get("is_live", False) else "Offline"

            lines.append(
                f"**{key}**\n"
                f"Status: `{status}`\n"
                f"Twitch: **{config.get('twitch_name', key)}**\n"
                f"Username: `{config.get('twitch_login')}`\n"
                f"Discord Channel: {channel_text}\n"
                f"Mention Role: {role_text}\n"
                f"Live Status: `{live_status}`\n"
                f"Last Stream ID: `{config.get('last_stream_id')}`"
            )

        text = "\n\n".join(lines)

        if len(text) > 3800:
            text = text[:3800] + "\n..."

        await interaction.response.send_message(
            embed=info_embed("Twitch Notifications", text),
            ephemeral=True,
        )

    @app_commands.command(name="enable", description="Enable a Twitch notification.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def enable(self, interaction: discord.Interaction, key: str):
        key = clean_key(key)
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        twitch_configs = get_twitch_configs(guild_data)
        config = twitch_configs.get(key)

        if not config:
            await interaction.response.send_message(
                embed=error_embed("I could not find a Twitch notification with that key."),
                ephemeral=True,
            )
            return

        config["enabled"] = True
        config["updated_by"] = interaction.user.id
        config["updated_at"] = discord.utils.utcnow().isoformat()

        twitch_configs[key] = config
        guild_data["social_notifications"]["twitch"] = twitch_configs
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(
            embed=success_embed(f"Twitch notification `{key}` enabled."),
            ephemeral=True,
        )

    @app_commands.command(name="disable", description="Disable a Twitch notification.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def disable(self, interaction: discord.Interaction, key: str):
        key = clean_key(key)
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        twitch_configs = get_twitch_configs(guild_data)
        config = twitch_configs.get(key)

        if not config:
            await interaction.response.send_message(
                embed=error_embed("I could not find a Twitch notification with that key."),
                ephemeral=True,
            )
            return

        config["enabled"] = False
        config["updated_by"] = interaction.user.id
        config["updated_at"] = discord.utils.utcnow().isoformat()

        twitch_configs[key] = config
        guild_data["social_notifications"]["twitch"] = twitch_configs
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(
            embed=success_embed(f"Twitch notification `{key}` disabled."),
            ephemeral=True,
        )

    @app_commands.command(name="set-channel", description="Change where a Twitch notification posts.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_channel(
        self,
        interaction: discord.Interaction,
        key: str,
        discord_channel: discord.TextChannel,
    ):
        key = clean_key(key)

        permissions = discord_channel.permissions_for(interaction.guild.me)

        if not permissions.view_channel:
            await interaction.response.send_message(
                embed=error_embed("I do not have permission to view that Discord channel."),
                ephemeral=True,
            )
            return

        if not permissions.send_messages:
            await interaction.response.send_message(
                embed=error_embed("I do not have permission to send messages in that Discord channel."),
                ephemeral=True,
            )
            return

        if not permissions.embed_links:
            await interaction.response.send_message(
                embed=error_embed("I need `Embed Links` in that Discord channel."),
                ephemeral=True,
            )
            return

        guild_data = self.bot.db.get_guild(interaction.guild.id)
        twitch_configs = get_twitch_configs(guild_data)
        config = twitch_configs.get(key)

        if not config:
            await interaction.response.send_message(
                embed=error_embed("I could not find a Twitch notification with that key."),
                ephemeral=True,
            )
            return

        config["discord_channel_id"] = discord_channel.id
        config["updated_by"] = interaction.user.id
        config["updated_at"] = discord.utils.utcnow().isoformat()

        twitch_configs[key] = config
        guild_data["social_notifications"]["twitch"] = twitch_configs
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(
            embed=success_embed(f"Twitch notification `{key}` will now post in {discord_channel.mention}."),
            ephemeral=True,
        )

    @app_commands.command(name="set-role", description="Set the role pinged by a Twitch notification.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_role(
        self,
        interaction: discord.Interaction,
        key: str,
        mention_role: discord.Role,
    ):
        key = clean_key(key)
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        twitch_configs = get_twitch_configs(guild_data)
        config = twitch_configs.get(key)

        if not config:
            await interaction.response.send_message(
                embed=error_embed("I could not find a Twitch notification with that key."),
                ephemeral=True,
            )
            return

        config["mention_role_id"] = mention_role.id
        config["updated_by"] = interaction.user.id
        config["updated_at"] = discord.utils.utcnow().isoformat()

        twitch_configs[key] = config
        guild_data["social_notifications"]["twitch"] = twitch_configs
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(
            embed=success_embed(f"Twitch notification `{key}` will now ping {mention_role.mention}."),
            ephemeral=True,
        )

    @app_commands.command(name="clear-role", description="Remove the role ping from a Twitch notification.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def clear_role(self, interaction: discord.Interaction, key: str):
        key = clean_key(key)
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        twitch_configs = get_twitch_configs(guild_data)
        config = twitch_configs.get(key)

        if not config:
            await interaction.response.send_message(
                embed=error_embed("I could not find a Twitch notification with that key."),
                ephemeral=True,
            )
            return

        config["mention_role_id"] = None
        config["updated_by"] = interaction.user.id
        config["updated_at"] = discord.utils.utcnow().isoformat()

        twitch_configs[key] = config
        guild_data["social_notifications"]["twitch"] = twitch_configs
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(
            embed=success_embed(f"Twitch notification `{key}` will no longer ping a role."),
            ephemeral=True,
        )

    @app_commands.command(name="set-name", description="Change the display name for a Twitch notification.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_name(
        self,
        interaction: discord.Interaction,
        key: str,
        twitch_name: str,
    ):
        key = clean_key(key)
        twitch_name = twitch_name.strip()

        if not twitch_name:
            await interaction.response.send_message(
                embed=error_embed("Twitch display name cannot be empty."),
                ephemeral=True,
            )
            return

        guild_data = self.bot.db.get_guild(interaction.guild.id)
        twitch_configs = get_twitch_configs(guild_data)
        config = twitch_configs.get(key)

        if not config:
            await interaction.response.send_message(
                embed=error_embed("I could not find a Twitch notification with that key."),
                ephemeral=True,
            )
            return

        config["twitch_name"] = twitch_name
        config["updated_by"] = interaction.user.id
        config["updated_at"] = discord.utils.utcnow().isoformat()

        twitch_configs[key] = config
        guild_data["social_notifications"]["twitch"] = twitch_configs
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(
            embed=success_embed(f"Twitch notification `{key}` display name set to **{twitch_name}**."),
            ephemeral=True,
        )

    @app_commands.command(name="refresh-status", description="Save the current Twitch live status without posting.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def refresh_status(self, interaction: discord.Interaction, key: str):
        key = clean_key(key)
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        twitch_configs = get_twitch_configs(guild_data)
        config = twitch_configs.get(key)

        if not config:
            await interaction.response.send_message(
                embed=error_embed("I could not find a Twitch notification with that key."),
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        cog = self.bot.get_cog("Social")

        if not cog:
            await interaction.followup.send(
                embed=error_embed("Social cog is not loaded."),
                ephemeral=True,
            )
            return

        if not cog.twitch_is_configured():
            await interaction.followup.send(
                embed=error_embed(
                    "Twitch credentials are missing. Add `TWITCH_CLIENT_ID` and `TWITCH_CLIENT_SECRET` to `.env`, then restart the bot."
                ),
                ephemeral=True,
            )
            return

        stream = await cog.fetch_twitch_stream(config.get("twitch_login"))

        old_status = "Live" if config.get("is_live", False) else "Offline"

        config["is_live"] = bool(stream)
        config["last_stream_id"] = stream.get("id") if stream else None
        config["last_started_at"] = stream.get("started_at") if stream else None
        config["updated_by"] = interaction.user.id
        config["updated_at"] = discord.utils.utcnow().isoformat()

        twitch_configs[key] = config
        guild_data["social_notifications"]["twitch"] = twitch_configs
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        new_status = "Live" if stream else "Offline"

        await interaction.followup.send(
            embed=success_embed(
                f"Twitch notification `{key}` refreshed.\n"
                f"Old Status: `{old_status}`\n"
                f"New Status: `{new_status}`\n"
                f"Stream ID: `{config.get('last_stream_id')}`"
            ),
            ephemeral=True,
        )

    @app_commands.command(name="test", description="Send a test Twitch live notification.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def test(self, interaction: discord.Interaction, key: str):
        key = clean_key(key)
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        twitch_configs = get_twitch_configs(guild_data)
        config = twitch_configs.get(key)

        if not config:
            await interaction.response.send_message(
                embed=error_embed("I could not find a Twitch notification with that key."),
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        cog = self.bot.get_cog("Social")

        if not cog:
            await interaction.followup.send(
                embed=error_embed("Social cog is not loaded."),
                ephemeral=True,
            )
            return

        if not cog.twitch_is_configured():
            await interaction.followup.send(
                embed=error_embed(
                    "Twitch credentials are missing. Add `TWITCH_CLIENT_ID` and `TWITCH_CLIENT_SECRET` to `.env`, then restart the bot."
                ),
                ephemeral=True,
            )
            return

        discord_channel = interaction.guild.get_channel(int(config.get("discord_channel_id") or 0))

        if not isinstance(discord_channel, discord.TextChannel):
            await interaction.followup.send(
                embed=error_embed("The saved Discord channel is missing or invalid."),
                ephemeral=True,
            )
            return

        stream = await cog.fetch_twitch_stream(config.get("twitch_login"))

        if not stream:
            stream = {
                "id": "test",
                "title": "Test stream notification",
                "game_name": "Testing",
                "viewer_count": 0,
                "started_at": "Test only",
                "thumbnail_url": None,
            }

        await cog.send_twitch_notification(
            guild=interaction.guild,
            discord_channel=discord_channel,
            config=config,
            stream=stream,
            is_test=True,
        )

        await interaction.followup.send(
            embed=success_embed(f"Test Twitch notification sent to {discord_channel.mention}."),
            ephemeral=True,
        )

    @app_commands.command(name="check-now", description="Check Twitch notifications now.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def check_now(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        cog = self.bot.get_cog("Social")

        if not cog:
            await interaction.followup.send(
                embed=error_embed("Social cog is not loaded."),
                ephemeral=True,
            )
            return

        if not cog.twitch_is_configured():
            await interaction.followup.send(
                embed=error_embed(
                    "Twitch credentials are missing. Add `TWITCH_CLIENT_ID` and `TWITCH_CLIENT_SECRET` to `.env`, then restart the bot."
                ),
                ephemeral=True,
            )
            return

        checked, posted = await cog.check_guild_twitch(interaction.guild)

        await interaction.followup.send(
            embed=success_embed(
                f"Twitch check complete.\n"
                f"Checked: **{checked}**\n"
                f"Posted: **{posted}**"
            ),
            ephemeral=True,
        )

    @remove.autocomplete("key")
    @enable.autocomplete("key")
    @disable.autocomplete("key")
    @set_channel.autocomplete("key")
    @set_role.autocomplete("key")
    @clear_role.autocomplete("key")
    @set_name.autocomplete("key")
    @refresh_status.autocomplete("key")
    @test.autocomplete("key")
    async def twitch_key_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        twitch_configs = get_twitch_configs(guild_data)
        current = current.lower().strip()
        choices = []

        for key, config in sorted(twitch_configs.items()):
            if current and current not in key.lower():
                continue

            status = "on" if config.get("enabled", True) else "off"
            label = f"{key} | {config.get('twitch_name', key)} | {status}"

            choices.append(
                app_commands.Choice(
                    name=label[:100],
                    value=key[:100],
                )
            )

        return choices[:25]


class SocialGroup(app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__(name="social", description="Social media notification tools.")
        self.bot = bot
        self.add_command(SocialYoutubeGroup(bot))
        self.add_command(SocialTwitchGroup(bot))


class Social(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.tree.add_command(SocialGroup(bot))
        self._session: Optional[aiohttp.ClientSession] = None
        self._twitch_token: Optional[str] = None
        self._twitch_token_expires_at: float = 0

    async def cog_load(self):
        self.social_checker.start()

    async def cog_unload(self):
        self.social_checker.cancel()

        if self._session and not self._session.closed:
            await self._session.close()

    async def get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()

        return self._session

    def twitch_is_configured(self) -> bool:
        return bool(os.getenv("TWITCH_CLIENT_ID") and os.getenv("TWITCH_CLIENT_SECRET"))

    async def fetch_latest_youtube_video(self, youtube_channel_id: str) -> Optional[dict]:
        if not youtube_channel_id:
            return None

        youtube_channel_id = youtube_channel_id.strip()
        url = YOUTUBE_FEED_URL.format(channel_id=youtube_channel_id)

        session = await self.get_session()

        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as response:
                if response.status != 200:
                    logger.warning(
                        "YouTube feed returned status=%s for channel_id=%s",
                        response.status,
                        youtube_channel_id,
                    )
                    return None

                text = await response.text()

        except (aiohttp.ClientError, asyncio.TimeoutError) as error:
            logger.warning("YouTube feed request failed for channel_id=%s: %s", youtube_channel_id, error)
            return None

        try:
            root = ET.fromstring(text)
        except ET.ParseError as error:
            logger.warning("YouTube feed XML parse failed for channel_id=%s: %s", youtube_channel_id, error)
            return None

        atom = "{http://www.w3.org/2005/Atom}"
        media = "{http://search.yahoo.com/mrss/}"
        yt = "{http://www.youtube.com/xml/schemas/2015}"

        entries = root.findall(f"{atom}entry")

        if not entries:
            return None

        entry = entries[0]

        video_id_node = entry.find(f"{yt}videoId")
        title_node = entry.find(f"{atom}title")
        link_node = entry.find(f"{atom}link")
        published_node = entry.find(f"{atom}published")
        media_group = entry.find(f"{media}group")

        thumbnail_url = None

        if media_group is not None:
            thumbnail_node = media_group.find(f"{media}thumbnail")

            if thumbnail_node is not None:
                thumbnail_url = thumbnail_node.attrib.get("url")

        video_id = video_id_node.text.strip() if video_id_node is not None and video_id_node.text else None
        title = title_node.text.strip() if title_node is not None and title_node.text else "New YouTube Upload"
        video_url = link_node.attrib.get("href") if link_node is not None else None
        published = published_node.text.strip() if published_node is not None and published_node.text else None

        if not video_id or not video_url:
            return None

        return {
            "video_id": video_id,
            "title": title,
            "url": video_url,
            "published": published,
            "thumbnail": thumbnail_url,
        }

    async def get_twitch_app_token(self) -> Optional[str]:
        if not self.twitch_is_configured():
            return None

        now = discord.utils.utcnow().timestamp()

        if self._twitch_token and now < self._twitch_token_expires_at:
            return self._twitch_token

        client_id = os.getenv("TWITCH_CLIENT_ID")
        client_secret = os.getenv("TWITCH_CLIENT_SECRET")

        session = await self.get_session()

        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
        }

        try:
            async with session.post(
                TWITCH_TOKEN_URL,
                data=data,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as response:
                if response.status != 200:
                    text = await response.text()
                    logger.warning("Twitch token request failed status=%s body=%s", response.status, text[:500])
                    return None

                payload = await response.json()

        except (aiohttp.ClientError, asyncio.TimeoutError) as error:
            logger.warning("Twitch token request failed: %s", error)
            return None

        access_token = payload.get("access_token")
        expires_in = int(payload.get("expires_in", 3600))

        if not access_token:
            logger.warning("Twitch token response did not include access_token")
            return None

        self._twitch_token = access_token
        self._twitch_token_expires_at = now + max(expires_in - 120, 60)

        return self._twitch_token

    async def twitch_get(self, url: str, params: dict) -> Optional[dict]:
        token = await self.get_twitch_app_token()

        if not token:
            return None

        client_id = os.getenv("TWITCH_CLIENT_ID")
        session = await self.get_session()

        headers = {
            "Client-ID": client_id,
            "Authorization": f"Bearer {token}",
        }

        try:
            async with session.get(
                url,
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as response:
                if response.status == 401:
                    self._twitch_token = None
                    self._twitch_token_expires_at = 0
                    logger.warning("Twitch request unauthorized. Token was cleared.")
                    return None

                if response.status != 200:
                    text = await response.text()
                    logger.warning("Twitch request failed status=%s body=%s", response.status, text[:500])
                    return None

                return await response.json()

        except (aiohttp.ClientError, asyncio.TimeoutError) as error:
            logger.warning("Twitch request failed: %s", error)
            return None

    async def fetch_twitch_user(self, twitch_login: str) -> Optional[dict]:
        twitch_login = clean_twitch_login(twitch_login)

        payload = await self.twitch_get(
            TWITCH_USERS_URL,
            params={"login": twitch_login},
        )

        if not payload:
            return None

        data = payload.get("data", [])

        if not data:
            return None

        return data[0]

    async def fetch_twitch_stream(self, twitch_login: str) -> Optional[dict]:
        twitch_login = clean_twitch_login(twitch_login)

        payload = await self.twitch_get(
            TWITCH_STREAMS_URL,
            params={"user_login": twitch_login},
        )

        if not payload:
            return None

        data = payload.get("data", [])

        if not data:
            return None

        return data[0]

    async def send_youtube_notification(
        self,
        guild: discord.Guild,
        discord_channel: discord.TextChannel,
        config: dict,
        video: dict,
        is_test: bool = False,
    ):
        youtube_name = config.get("youtube_name", "YouTube")
        embed = build_youtube_embed(video, youtube_name)

        role_id = config.get("mention_role_id")
        role = guild.get_role(int(role_id)) if role_id else None

        if is_test:
            content = f"🧪 **TEST** New YouTube upload from **{youtube_name}**"
        else:
            content = f"📺 New YouTube upload from **{youtube_name}**"

        if role:
            content = f"{role.mention} {content}"

        await discord_channel.send(
            content=content,
            embed=embed,
            allowed_mentions=discord.AllowedMentions(
                roles=True,
                users=False,
                everyone=False,
            ),
        )

    async def send_twitch_notification(
        self,
        guild: discord.Guild,
        discord_channel: discord.TextChannel,
        config: dict,
        stream: dict,
        is_test: bool = False,
    ):
        twitch_name = config.get("twitch_name", "Twitch")
        twitch_login = config.get("twitch_login", twitch_name)
        embed = build_twitch_embed(stream, twitch_name, twitch_login)

        role_id = config.get("mention_role_id")
        role = guild.get_role(int(role_id)) if role_id else None

        if is_test:
            content = f"🧪 **TEST** {twitch_name} is live on Twitch!"
        else:
            content = f"🔴 **LIVE** {twitch_name} is now live on Twitch!"

        if role:
            content = f"{role.mention} {content}"

        await discord_channel.send(
            content=content,
            embed=embed,
            allowed_mentions=discord.AllowedMentions(
                roles=True,
                users=False,
                everyone=False,
            ),
        )

    async def check_guild_youtube(self, guild: discord.Guild) -> tuple[int, int]:
        guild_data = self.bot.db.get_guild(guild.id)
        youtube_configs = get_youtube_configs(guild_data)

        checked = 0
        posted = 0
        updated_any = False

        for key, config in youtube_configs.items():
            if not config.get("enabled", True):
                continue

            checked += 1

            youtube_channel_id = config.get("youtube_channel_id")
            discord_channel_id = config.get("discord_channel_id")

            if not youtube_channel_id or not discord_channel_id:
                continue

            video = await self.fetch_latest_youtube_video(youtube_channel_id)

            if not video:
                continue

            last_video_id = config.get("last_video_id")

            if last_video_id == video["video_id"]:
                continue

            discord_channel = guild.get_channel(int(discord_channel_id))

            if not isinstance(discord_channel, discord.TextChannel):
                logger.warning("YouTube notification `%s` skipped: Discord channel missing", key)
                continue

            permissions = discord_channel.permissions_for(guild.me)

            if not permissions.view_channel or not permissions.send_messages or not permissions.embed_links:
                logger.warning("YouTube notification `%s` skipped: missing Discord channel permissions", key)
                continue

            try:
                await self.send_youtube_notification(
                    guild=guild,
                    discord_channel=discord_channel,
                    config=config,
                    video=video,
                    is_test=False,
                )
            except discord.Forbidden:
                logger.warning("YouTube notification `%s` skipped: forbidden sending message", key)
                continue
            except discord.HTTPException as error:
                logger.warning("YouTube notification `%s` skipped: Discord send failed: %s", key, error)
                continue

            config["last_video_id"] = video["video_id"]
            config["updated_at"] = discord.utils.utcnow().isoformat()
            youtube_configs[key] = config
            updated_any = True
            posted += 1

            logger.info("Posted YouTube notification `%s` for video_id=%s", key, video["video_id"])

        if updated_any:
            guild_data["social_notifications"]["youtube"] = youtube_configs
            self.bot.db.update_guild(guild.id, guild_data)

        return checked, posted

    async def check_guild_twitch(self, guild: discord.Guild) -> tuple[int, int]:
        guild_data = self.bot.db.get_guild(guild.id)
        twitch_configs = get_twitch_configs(guild_data)

        checked = 0
        posted = 0
        updated_any = False

        if not self.twitch_is_configured():
            return checked, posted

        for key, config in twitch_configs.items():
            if not config.get("enabled", True):
                continue

            checked += 1

            twitch_login = config.get("twitch_login")
            discord_channel_id = config.get("discord_channel_id")

            if not twitch_login or not discord_channel_id:
                continue

            stream = await self.fetch_twitch_stream(twitch_login)
            was_live = bool(config.get("is_live", False))
            is_live = bool(stream)

            if not is_live:
                if was_live:
                    config["is_live"] = False
                    config["last_stream_id"] = None
                    config["last_started_at"] = None
                    config["updated_at"] = discord.utils.utcnow().isoformat()
                    twitch_configs[key] = config
                    updated_any = True

                continue

            current_stream_id = stream.get("id")
            last_stream_id = config.get("last_stream_id")

            if was_live and last_stream_id == current_stream_id:
                continue

            discord_channel = guild.get_channel(int(discord_channel_id))

            if not isinstance(discord_channel, discord.TextChannel):
                logger.warning("Twitch notification `%s` skipped: Discord channel missing", key)
                continue

            permissions = discord_channel.permissions_for(guild.me)

            if not permissions.view_channel or not permissions.send_messages or not permissions.embed_links:
                logger.warning("Twitch notification `%s` skipped: missing Discord channel permissions", key)
                continue

            try:
                await self.send_twitch_notification(
                    guild=guild,
                    discord_channel=discord_channel,
                    config=config,
                    stream=stream,
                    is_test=False,
                )
            except discord.Forbidden:
                logger.warning("Twitch notification `%s` skipped: forbidden sending message", key)
                continue
            except discord.HTTPException as error:
                logger.warning("Twitch notification `%s` skipped: Discord send failed: %s", key, error)
                continue

            config["is_live"] = True
            config["last_stream_id"] = current_stream_id
            config["last_started_at"] = stream.get("started_at")
            config["updated_at"] = discord.utils.utcnow().isoformat()
            twitch_configs[key] = config
            updated_any = True
            posted += 1

            logger.info("Posted Twitch notification `%s` for stream_id=%s", key, current_stream_id)

        if updated_any:
            guild_data["social_notifications"]["twitch"] = twitch_configs
            self.bot.db.update_guild(guild.id, guild_data)

        return checked, posted

    @tasks.loop(minutes=DEFAULT_CHECK_MINUTES)
    async def social_checker(self):
        for guild in self.bot.guilds:
            try:
                await self.check_guild_youtube(guild)
            except Exception:
                logger.exception("Unexpected error while checking YouTube notifications for guild_id=%s", guild.id)

            try:
                await self.check_guild_twitch(guild)
            except Exception:
                logger.exception("Unexpected error while checking Twitch notifications for guild_id=%s", guild.id)

    @social_checker.before_loop
    async def before_social_checker(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Social(bot))

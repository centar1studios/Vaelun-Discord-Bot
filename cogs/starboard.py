import re

import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import success_embed, error_embed, info_embed


DEFAULT_EMOJI = "⭐"
DEFAULT_THRESHOLD = 3
KEY_RE = re.compile(r"^[a-z0-9_-]{2,32}$")
CUSTOM_EMOJI_RE = re.compile(r"^<a?:([A-Za-z0-9_]+):([0-9]+)>$")


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


def clean_key(key: str) -> str:
    return key.lower().strip()


def normalize_config_emoji(raw_emoji: str | None) -> tuple[str, str]:
    """
    Returns:
    emoji_key: stable value used for matching reactions
    emoji_display: value used in messages
    """
    if not raw_emoji:
        return DEFAULT_EMOJI, DEFAULT_EMOJI

    raw_emoji = raw_emoji.strip()

    custom_match = CUSTOM_EMOJI_RE.match(raw_emoji)

    if custom_match:
        emoji_id = custom_match.group(2)
        return emoji_id, raw_emoji

    return raw_emoji, raw_emoji


def payload_emoji_key(payload_emoji: discord.PartialEmoji) -> str:
    if payload_emoji.id:
        return str(payload_emoji.id)

    return str(payload_emoji)


def reaction_emoji_key(reaction: discord.Reaction) -> str:
    emoji = reaction.emoji

    if isinstance(emoji, discord.PartialEmoji):
        if emoji.id:
            return str(emoji.id)
        return str(emoji)

    if isinstance(emoji, discord.Emoji):
        return str(emoji.id)

    return str(emoji)


def get_starboards_config(guild_data: dict) -> dict:
    """
    New shape:
    guild_data["starboards"] = {
        "main": {
            "key": "main",
            "enabled": True,
            "channel_id": 123,
            "threshold": 3,
            "emoji_key": "⭐",
            "emoji_display": "⭐",
            "messages": {
                "original_message_id": "starboard_message_id"
            }
        }
    }

    Also migrates the old single-starboard shape if it exists.
    """
    starboards = guild_data.get("starboards")

    if not isinstance(starboards, dict):
        starboards = {}
        guild_data["starboards"] = starboards

    old_starboard = guild_data.get("starboard")

    if isinstance(old_starboard, dict) and "main" not in starboards:
        old_channel_id = old_starboard.get("channel_id")
        old_threshold = old_starboard.get("threshold", DEFAULT_THRESHOLD)
        old_enabled = old_starboard.get("enabled", False)
        old_messages = old_starboard.get("messages", {})

        if not isinstance(old_messages, dict):
            old_messages = {}

        starboards["main"] = {
            "key": "main",
            "enabled": old_enabled,
            "channel_id": old_channel_id,
            "threshold": old_threshold,
            "emoji_key": DEFAULT_EMOJI,
            "emoji_display": DEFAULT_EMOJI,
            "messages": old_messages,
        }

    for key, board in list(starboards.items()):
        if not isinstance(board, dict):
            starboards.pop(key, None)
            continue

        board.setdefault("key", key)
        board.setdefault("enabled", False)
        board.setdefault("channel_id", None)
        board.setdefault("threshold", DEFAULT_THRESHOLD)
        board.setdefault("emoji_key", DEFAULT_EMOJI)
        board.setdefault("emoji_display", DEFAULT_EMOJI)
        board.setdefault("messages", {})

        if not isinstance(board["messages"], dict):
            board["messages"] = {}

    return starboards


def build_starboard_embed(
    message: discord.Message,
    star_count: int,
    emoji_display: str,
) -> discord.Embed:
    description = message.content or "*No text content.*"

    if len(description) > 3500:
        description = description[:3500] + "\n..."

    embed = discord.Embed(
        description=description,
        color=discord.Color.gold(),
        timestamp=message.created_at,
    )

    author_icon = message.author.display_avatar.url if message.author.display_avatar else None

    embed.set_author(
        name=str(message.author),
        icon_url=author_icon,
    )

    embed.add_field(
        name="Source",
        value=f"[Jump to message]({message.jump_url})",
        inline=True,
    )

    embed.add_field(
        name="Reactions",
        value=f"{emoji_display} **{star_count}**",
        inline=True,
    )

    embed.add_field(
        name="Channel",
        value=message.channel.mention,
        inline=True,
    )

    if message.attachments:
        first_attachment = message.attachments[0]

        if first_attachment.content_type and first_attachment.content_type.startswith("image/"):
            embed.set_image(url=first_attachment.url)
        else:
            embed.add_field(
                name="Attachment",
                value=f"[{first_attachment.filename}]({first_attachment.url})",
                inline=False,
            )

    embed.set_footer(text=f"Message ID: {message.id}")

    return embed


class StarboardGroup(app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__(name="starboard", description="Starboard tools.")
        self.bot = bot

    @app_commands.command(name="create", description="Create a starboard.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def create(
        self,
        interaction: discord.Interaction,
        key: str,
        channel: discord.TextChannel,
        emoji: str = DEFAULT_EMOJI,
        threshold: app_commands.Range[int, 1, 50] = DEFAULT_THRESHOLD,
    ):
        key = clean_key(key)

        if not KEY_RE.match(key):
            await interaction.response.send_message(
                embed=error_embed("Starboard key must be 2-32 characters and use only lowercase letters, numbers, `_`, or `-`."),
                ephemeral=True,
            )
            return

        permissions = channel.permissions_for(interaction.guild.me)

        if not permissions.send_messages:
            await interaction.response.send_message(
                embed=error_embed("I do not have permission to send messages in that channel."),
                ephemeral=True,
            )
            return

        if not permissions.embed_links:
            await interaction.response.send_message(
                embed=error_embed("I need `Embed Links` in that channel for starboard posts."),
                ephemeral=True,
            )
            return

        emoji_key, emoji_display = normalize_config_emoji(emoji)

        guild_data = self.bot.db.get_guild(interaction.guild.id)
        starboards = get_starboards_config(guild_data)

        if key in starboards:
            await interaction.response.send_message(
                embed=error_embed("A starboard with that key already exists."),
                ephemeral=True,
            )
            return

        starboards[key] = {
            "key": key,
            "enabled": True,
            "channel_id": channel.id,
            "threshold": int(threshold),
            "emoji_key": emoji_key,
            "emoji_display": emoji_display,
            "messages": {},
            "created_by": interaction.user.id,
            "updated_by": interaction.user.id,
            "updated_at": discord.utils.utcnow().isoformat(),
        }

        guild_data["starboards"] = starboards
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(
            embed=success_embed(
                f"Starboard `{key}` created.\n"
                f"Channel: {channel.mention}\n"
                f"Emoji: {emoji_display}\n"
                f"Threshold: **{threshold}**"
            ),
            ephemeral=True,
        )

    @app_commands.command(name="set-channel", description="Set a starboard channel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_channel(
        self,
        interaction: discord.Interaction,
        key: str,
        channel: discord.TextChannel,
    ):
        key = clean_key(key)
        permissions = channel.permissions_for(interaction.guild.me)

        if not permissions.send_messages:
            await interaction.response.send_message(
                embed=error_embed("I do not have permission to send messages in that channel."),
                ephemeral=True,
            )
            return

        if not permissions.embed_links:
            await interaction.response.send_message(
                embed=error_embed("I need `Embed Links` in that channel for starboard posts."),
                ephemeral=True,
            )
            return

        guild_data = self.bot.db.get_guild(interaction.guild.id)
        starboards = get_starboards_config(guild_data)
        board = starboards.get(key)

        if not board:
            await interaction.response.send_message(
                embed=error_embed("I could not find a starboard with that key."),
                ephemeral=True,
            )
            return

        board["channel_id"] = channel.id
        board["updated_by"] = interaction.user.id
        board["updated_at"] = discord.utils.utcnow().isoformat()

        starboards[key] = board
        guild_data["starboards"] = starboards
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(
            embed=success_embed(f"Starboard `{key}` channel set to {channel.mention}."),
            ephemeral=True,
        )

    @app_commands.command(name="set-threshold", description="Set how many reactions a starboard needs.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_threshold(
        self,
        interaction: discord.Interaction,
        key: str,
        amount: app_commands.Range[int, 1, 50],
    ):
        key = clean_key(key)
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        starboards = get_starboards_config(guild_data)
        board = starboards.get(key)

        if not board:
            await interaction.response.send_message(
                embed=error_embed("I could not find a starboard with that key."),
                ephemeral=True,
            )
            return

        board["threshold"] = int(amount)
        board["updated_by"] = interaction.user.id
        board["updated_at"] = discord.utils.utcnow().isoformat()

        starboards[key] = board
        guild_data["starboards"] = starboards
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(
            embed=success_embed(f"Starboard `{key}` threshold set to **{amount}**."),
            ephemeral=True,
        )

    @app_commands.command(name="set-emoji", description="Set the emoji used for a starboard.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_emoji(
        self,
        interaction: discord.Interaction,
        key: str,
        emoji: str,
    ):
        key = clean_key(key)
        emoji_key, emoji_display = normalize_config_emoji(emoji)

        guild_data = self.bot.db.get_guild(interaction.guild.id)
        starboards = get_starboards_config(guild_data)
        board = starboards.get(key)

        if not board:
            await interaction.response.send_message(
                embed=error_embed("I could not find a starboard with that key."),
                ephemeral=True,
            )
            return

        board["emoji_key"] = emoji_key
        board["emoji_display"] = emoji_display
        board["updated_by"] = interaction.user.id
        board["updated_at"] = discord.utils.utcnow().isoformat()

        starboards[key] = board
        guild_data["starboards"] = starboards
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(
            embed=success_embed(f"Starboard `{key}` emoji set to {emoji_display}."),
            ephemeral=True,
        )

    @app_commands.command(name="enable", description="Enable a starboard.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def enable(self, interaction: discord.Interaction, key: str):
        key = clean_key(key)
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        starboards = get_starboards_config(guild_data)
        board = starboards.get(key)

        if not board:
            await interaction.response.send_message(
                embed=error_embed("I could not find a starboard with that key."),
                ephemeral=True,
            )
            return

        if not board.get("channel_id"):
            await interaction.response.send_message(
                embed=error_embed("Set a channel first with `/starboard set-channel`."),
                ephemeral=True,
            )
            return

        board["enabled"] = True
        board["updated_by"] = interaction.user.id
        board["updated_at"] = discord.utils.utcnow().isoformat()

        starboards[key] = board
        guild_data["starboards"] = starboards
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(
            embed=success_embed(f"Starboard `{key}` enabled."),
            ephemeral=True,
        )

    @app_commands.command(name="disable", description="Disable a starboard.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def disable(self, interaction: discord.Interaction, key: str):
        key = clean_key(key)
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        starboards = get_starboards_config(guild_data)
        board = starboards.get(key)

        if not board:
            await interaction.response.send_message(
                embed=error_embed("I could not find a starboard with that key."),
                ephemeral=True,
            )
            return

        board["enabled"] = False
        board["updated_by"] = interaction.user.id
        board["updated_at"] = discord.utils.utcnow().isoformat()

        starboards[key] = board
        guild_data["starboards"] = starboards
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(
            embed=success_embed(f"Starboard `{key}` disabled."),
            ephemeral=True,
        )

    @app_commands.command(name="delete", description="Delete a starboard config.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def delete(self, interaction: discord.Interaction, key: str):
        key = clean_key(key)
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        starboards = get_starboards_config(guild_data)

        if key not in starboards:
            await interaction.response.send_message(
                embed=error_embed("I could not find a starboard with that key."),
                ephemeral=True,
            )
            return

        starboards.pop(key, None)
        guild_data["starboards"] = starboards
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(
            embed=success_embed(f"Starboard `{key}` deleted."),
            ephemeral=True,
        )

    @app_commands.command(name="list", description="List all starboards.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def list_boards(self, interaction: discord.Interaction):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        starboards = get_starboards_config(guild_data)

        if not starboards:
            await interaction.response.send_message(
                embed=info_embed("Starboards", "No starboards are configured yet."),
                ephemeral=True,
            )
            return

        lines = []

        for key, board in sorted(starboards.items()):
            channel = await fetch_text_channel(interaction.guild, board.get("channel_id"))
            channel_text = channel.mention if channel else "Not configured"
            status = "Enabled" if board.get("enabled", False) else "Disabled"
            emoji_display = board.get("emoji_display", DEFAULT_EMOJI)
            threshold = board.get("threshold", DEFAULT_THRESHOLD)
            count = len(board.get("messages", {}))

            lines.append(
                f"**{key}**\n"
                f"Status: `{status}`\n"
                f"Channel: {channel_text}\n"
                f"Emoji: {emoji_display}\n"
                f"Threshold: `{threshold}`\n"
                f"Starred Messages: `{count}`"
            )

        text = "\n\n".join(lines)

        if len(text) > 3800:
            text = text[:3800] + "\n..."

        await interaction.response.send_message(
            embed=info_embed("Starboards", text),
            ephemeral=True,
        )

    @app_commands.command(name="status", description="Show one starboard's settings.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def status(self, interaction: discord.Interaction, key: str):
        key = clean_key(key)
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        starboards = get_starboards_config(guild_data)
        board = starboards.get(key)

        if not board:
            await interaction.response.send_message(
                embed=error_embed("I could not find a starboard with that key."),
                ephemeral=True,
            )
            return

        channel = await fetch_text_channel(interaction.guild, board.get("channel_id"))
        channel_text = channel.mention if channel else "Not configured"
        message_count = len(board.get("messages", {}))

        description = (
            f"**Key:** `{key}`\n"
            f"**Enabled:** {board.get('enabled', False)}\n"
            f"**Channel:** {channel_text}\n"
            f"**Emoji:** {board.get('emoji_display', DEFAULT_EMOJI)}\n"
            f"**Emoji Key:** `{board.get('emoji_key', DEFAULT_EMOJI)}`\n"
            f"**Threshold:** {board.get('threshold', DEFAULT_THRESHOLD)}\n"
            f"**Starred Messages:** {message_count}"
        )

        await interaction.response.send_message(
            embed=info_embed("Starboard Status", description),
            ephemeral=True,
        )

    @set_channel.autocomplete("key")
    @set_threshold.autocomplete("key")
    @set_emoji.autocomplete("key")
    @enable.autocomplete("key")
    @disable.autocomplete("key")
    @delete.autocomplete("key")
    @status.autocomplete("key")
    async def starboard_key_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        starboards = get_starboards_config(guild_data)
        current = current.lower().strip()
        choices = []

        for key, board in sorted(starboards.items()):
            if current and current not in key.lower():
                continue

            status = "on" if board.get("enabled", False) else "off"
            emoji_display = board.get("emoji_display", DEFAULT_EMOJI)
            label = f"{key} | {emoji_display} | {status}"

            choices.append(
                app_commands.Choice(
                    name=label[:100],
                    value=key[:100],
                )
            )

        return choices[:25]


class Starboard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.tree.add_command(StarboardGroup(bot))

    async def process_starboard_reaction(
        self,
        payload: discord.RawReactionActionEvent,
    ):
        if not payload.guild_id:
            return

        guild = self.bot.get_guild(payload.guild_id)

        if not guild:
            return

        guild_data = self.bot.db.get_guild(guild.id)
        starboards = get_starboards_config(guild_data)

        if not starboards:
            return

        reacted_emoji_key = payload_emoji_key(payload.emoji)

        matching_boards = [
            (key, board)
            for key, board in starboards.items()
            if board.get("enabled", False)
            and str(board.get("emoji_key", DEFAULT_EMOJI)) == reacted_emoji_key
        ]

        if not matching_boards:
            return

        source_channel = await fetch_text_channel(guild, payload.channel_id)

        if not source_channel:
            return

        try:
            message = await source_channel.fetch_message(payload.message_id)
        except (discord.Forbidden, discord.NotFound, discord.HTTPException):
            return

        if message.author.bot:
            return

        updated_any = False

        for key, board in matching_boards:
            starboard_channel = await fetch_text_channel(guild, board.get("channel_id"))

            if not starboard_channel:
                continue

            if payload.channel_id == starboard_channel.id:
                continue

            emoji_key = str(board.get("emoji_key", DEFAULT_EMOJI))
            emoji_display = board.get("emoji_display", DEFAULT_EMOJI)
            threshold = int(board.get("threshold", DEFAULT_THRESHOLD))

            reaction_count = 0

            for reaction in message.reactions:
                if reaction_emoji_key(reaction) == emoji_key:
                    reaction_count = reaction.count
                    break

            messages = board.setdefault("messages", {})
            message_key = str(message.id)
            existing_starboard_id = messages.get(message_key)

            if reaction_count < threshold:
                if existing_starboard_id:
                    try:
                        existing = await starboard_channel.fetch_message(int(existing_starboard_id))
                        await existing.delete()
                    except (discord.Forbidden, discord.NotFound, discord.HTTPException, ValueError, TypeError):
                        pass

                    messages.pop(message_key, None)
                    board["messages"] = messages
                    starboards[key] = board
                    updated_any = True

                continue

            embed = build_starboard_embed(
                message=message,
                star_count=reaction_count,
                emoji_display=emoji_display,
            )

            content = f"{emoji_display} **{reaction_count}** in {message.channel.mention}"

            if existing_starboard_id:
                try:
                    existing = await starboard_channel.fetch_message(int(existing_starboard_id))
                    await existing.edit(
                        content=content,
                        embed=embed,
                        allowed_mentions=discord.AllowedMentions.none(),
                    )
                    continue
                except (discord.Forbidden, discord.NotFound, discord.HTTPException, ValueError, TypeError):
                    messages.pop(message_key, None)

            try:
                sent = await starboard_channel.send(
                    content=content,
                    embed=embed,
                    allowed_mentions=discord.AllowedMentions.none(),
                )
            except (discord.Forbidden, discord.HTTPException):
                continue

            messages[message_key] = sent.id
            board["messages"] = messages
            starboards[key] = board
            updated_any = True

        if updated_any:
            guild_data["starboards"] = starboards
            self.bot.db.update_guild(guild.id, guild_data)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        await self.process_starboard_reaction(payload)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        await self.process_starboard_reaction(payload)


async def setup(bot: commands.Bot):
    await bot.add_cog(Starboard(bot))

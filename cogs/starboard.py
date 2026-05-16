import logging
import re

import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import success_embed, error_embed, info_embed


logger = logging.getLogger("centari.starboard")

DEFAULT_EMOJI = "⭐"
DEFAULT_THRESHOLD = 3
KEY_RE = re.compile(r"^[a-z0-9_-]{2,32}$")
CUSTOM_EMOJI_RE = re.compile(r"^<a?:([A-Za-z0-9_]+):([0-9]+)>$")
MESSAGE_LINK_RE = re.compile(
    r"https?://(?:canary\.|ptb\.)?discord(?:app)?\.com/channels/"
    r"(?P<guild_id>\d+)/(?P<channel_id>\d+)/(?P<message_id>\d+)"
)


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


def clean_standard_emoji(value: str) -> str:
    if not value:
        return value

    return value.strip().replace("\ufe0f", "")


def normalize_config_emoji(raw_emoji: str | None) -> tuple[str, str]:
    if not raw_emoji:
        return DEFAULT_EMOJI, DEFAULT_EMOJI

    raw_emoji = raw_emoji.strip()
    custom_match = CUSTOM_EMOJI_RE.match(raw_emoji)

    if custom_match:
        emoji_id = custom_match.group(2)
        return emoji_id, raw_emoji

    cleaned = clean_standard_emoji(raw_emoji)
    return cleaned, raw_emoji


def payload_emoji_key(payload_emoji: discord.PartialEmoji) -> str:
    if payload_emoji.id:
        return str(payload_emoji.id)

    return clean_standard_emoji(str(payload_emoji))


def reaction_emoji_key(reaction: discord.Reaction) -> str:
    emoji = reaction.emoji

    if isinstance(emoji, discord.PartialEmoji):
        if emoji.id:
            return str(emoji.id)
        return clean_standard_emoji(str(emoji))

    if isinstance(emoji, discord.Emoji):
        return str(emoji.id)

    return clean_standard_emoji(str(emoji))


def parse_message_link(link: str) -> tuple[int, int, int] | None:
    match = MESSAGE_LINK_RE.match(link.strip())

    if not match:
        return None

    return (
        int(match.group("guild_id")),
        int(match.group("channel_id")),
        int(match.group("message_id")),
    )


def get_starboards_config(guild_data: dict) -> dict:
    starboards = guild_data.get("starboards")

    if not isinstance(starboards, dict):
        starboards = {}
        guild_data["starboards"] = starboards

    old_starboard = guild_data.get("starboard")

    if isinstance(old_starboard, dict) and "main" not in starboards:
        old_messages = old_starboard.get("messages", {})

        if not isinstance(old_messages, dict):
            old_messages = {}

        starboards["main"] = {
            "key": "main",
            "enabled": old_starboard.get("enabled", False),
            "channel_id": old_starboard.get("channel_id"),
            "threshold": old_starboard.get("threshold", DEFAULT_THRESHOLD),
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

        board["emoji_key"] = clean_standard_emoji(str(board.get("emoji_key", DEFAULT_EMOJI)))

        if not isinstance(board["messages"], dict):
            board["messages"] = {}

    return starboards


def build_starboard_embed(
    message: discord.Message,
    reaction_count: int,
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

    embed.set_author(
        name=str(message.author),
        icon_url=message.author.display_avatar.url,
    )

    embed.add_field(
        name="Source",
        value=f"[Jump to message]({message.jump_url})",
        inline=True,
    )

    embed.add_field(
        name="Reactions",
        value=f"{emoji_display} **{reaction_count}**",
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
                f"Emoji key: `{emoji_key}`\n"
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
            embed=success_embed(f"Starboard `{key}` emoji set to {emoji_display}.\nEmoji key: `{emoji_key}`"),
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
            emoji_key = board.get("emoji_key", DEFAULT_EMOJI)
            threshold = board.get("threshold", DEFAULT_THRESHOLD)
            count = len(board.get("messages", {}))

            lines.append(
                f"**{key}**\n"
                f"Status: `{status}`\n"
                f"Channel: {channel_text}\n"
                f"Emoji: {emoji_display}\n"
                f"Emoji key: `{emoji_key}`\n"
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

    @app_commands.command(name="test-message", description="Force-test a message into a starboard using a message link.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def test_message(
        self,
        interaction: discord.Interaction,
        key: str,
        message_link: str,
    ):
        key = clean_key(key)
        parsed = parse_message_link(message_link)

        if not parsed:
            await interaction.response.send_message(
                embed=error_embed("That does not look like a valid Discord message link."),
                ephemeral=True,
            )
            return

        guild_id, channel_id, message_id = parsed

        if guild_id != interaction.guild.id:
            await interaction.response.send_message(
                embed=error_embed("That message link is not from this server."),
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

        source_channel = await fetch_text_channel(interaction.guild, channel_id)
        starboard_channel = await fetch_text_channel(interaction.guild, board.get("channel_id"))

        if not source_channel:
            await interaction.response.send_message(
                embed=error_embed("I could not access the source channel."),
                ephemeral=True,
            )
            return

        if not starboard_channel:
            await interaction.response.send_message(
                embed=error_embed("I could not access the starboard channel."),
                ephemeral=True,
            )
            return

        try:
            message = await source_channel.fetch_message(message_id)
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=error_embed("I do not have permission to read that message."),
                ephemeral=True,
            )
            return
        except discord.NotFound:
            await interaction.response.send_message(
                embed=error_embed("I could not find that message."),
                ephemeral=True,
            )
            return
        except discord.HTTPException as error:
            await interaction.response.send_message(
                embed=error_embed(f"Discord rejected the message lookup: `{error}`"),
                ephemeral=True,
            )
            return

        emoji_key = str(board.get("emoji_key", DEFAULT_EMOJI))
        emoji_display = board.get("emoji_display", DEFAULT_EMOJI)

        reaction_count = 0

        for reaction in message.reactions:
            if reaction_emoji_key(reaction) == emoji_key:
                reaction_count = reaction.count
                break

        if reaction_count < 1:
            reaction_count = 1

        embed = build_starboard_embed(
            message=message,
            reaction_count=reaction_count,
            emoji_display=emoji_display,
        )

        try:
            await starboard_channel.send(
                content=f"{emoji_display} **TEST** in {message.channel.mention}",
                embed=embed,
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=error_embed("I do not have permission to send in the starboard channel."),
                ephemeral=True,
            )
            return
        except discord.HTTPException as error:
            await interaction.response.send_message(
                embed=error_embed(f"Discord rejected the starboard test post: `{error}`"),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=success_embed(f"Test starboard post sent to {starboard_channel.mention}."),
            ephemeral=True,
        )

    @set_channel.autocomplete("key")
    @set_threshold.autocomplete("key")
    @set_emoji.autocomplete("key")
    @enable.autocomplete("key")
    @disable.autocomplete("key")
    @delete.autocomplete("key")
    @status.autocomplete("key")
    @test_message.autocomplete("key")
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
            logger.info("Starboard skipped: guild not found for payload guild_id=%s", payload.guild_id)
            return

        guild_data = self.bot.db.get_guild(guild.id)
        starboards = get_starboards_config(guild_data)

        if not starboards:
            logger.info("Starboard skipped: no starboards configured in guild %s", guild.id)
            return

        reacted_emoji_key = payload_emoji_key(payload.emoji)

        logger.info(
            "Starboard reaction event: guild=%s channel=%s message=%s emoji=%s key=%s",
            guild.id,
            payload.channel_id,
            payload.message_id,
            str(payload.emoji),
            reacted_emoji_key,
        )

        matching_boards = [
            (key, board)
            for key, board in starboards.items()
            if board.get("enabled", False)
            and str(board.get("emoji_key", DEFAULT_EMOJI)) == reacted_emoji_key
        ]

        if not matching_boards:
            logger.info("Starboard skipped: no enabled board matched emoji key=%s", reacted_emoji_key)
            return

        source_channel = await fetch_text_channel(guild, payload.channel_id)

        if not source_channel:
            logger.info("Starboard skipped: source channel not found or inaccessible")
            return

        try:
            message = await source_channel.fetch_message(payload.message_id)
        except discord.Forbidden:
            logger.info("Starboard skipped: forbidden fetching source message")
            return
        except discord.NotFound:
            logger.info("Starboard skipped: source message not found")
            return
        except discord.HTTPException as error:
            logger.info("Starboard skipped: HTTP error fetching source message: %s", error)
            return

        if message.author.bot:
            logger.info("Starboard skipped: source message is from a bot/webhook")
            return

        updated_any = False

        for key, board in matching_boards:
            starboard_channel = await fetch_text_channel(guild, board.get("channel_id"))

            if not starboard_channel:
                logger.info("Starboard `%s` skipped: starboard channel missing/inaccessible", key)
                continue

            if payload.channel_id == starboard_channel.id:
                logger.info("Starboard `%s` skipped: reaction happened inside starboard channel", key)
                continue

            permissions = starboard_channel.permissions_for(guild.me)

            if not permissions.send_messages:
                logger.info("Starboard `%s` skipped: missing Send Messages", key)
                continue

            if not permissions.embed_links:
                logger.info("Starboard `%s` skipped: missing Embed Links", key)
                continue

            emoji_key = str(board.get("emoji_key", DEFAULT_EMOJI))
            emoji_display = board.get("emoji_display", DEFAULT_EMOJI)
            threshold = int(board.get("threshold", DEFAULT_THRESHOLD))

            reaction_count = 0

            for reaction in message.reactions:
                current_key = reaction_emoji_key(reaction)

                logger.info(
                    "Starboard `%s`: reaction on message emoji=%s key=%s count=%s",
                    key,
                    str(reaction.emoji),
                    current_key,
                    reaction.count,
                )

                if current_key == emoji_key:
                    reaction_count = reaction.count
                    break

            logger.info(
                "Starboard `%s`: reaction_count=%s threshold=%s",
                key,
                reaction_count,
                threshold,
            )

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
                reaction_count=reaction_count,
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
                    logger.info("Starboard `%s`: updated existing starboard post", key)
                    continue
                except (discord.Forbidden, discord.NotFound, discord.HTTPException, ValueError, TypeError):
                    messages.pop(message_key, None)

            try:
                sent = await starboard_channel.send(
                    content=content,
                    embed=embed,
                    allowed_mentions=discord.AllowedMentions.none(),
                )
            except discord.Forbidden:
                logger.info("Starboard `%s` skipped: forbidden sending starboard post", key)
                continue
            except discord.HTTPException as error:
                logger.info("Starboard `%s` skipped: HTTP error sending post: %s", key, error)
                continue

            messages[message_key] = sent.id
            board["messages"] = messages
            starboards[key] = board
            updated_any = True

            logger.info("Starboard `%s`: sent new starboard post", key)

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

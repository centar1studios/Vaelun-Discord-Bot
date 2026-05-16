import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import success_embed, error_embed, info_embed


STAR_EMOJI = "⭐"
DEFAULT_THRESHOLD = 3


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


def get_starboard_config(guild_data: dict) -> dict:
    starboard = guild_data.setdefault(
        "starboard",
        {
            "enabled": False,
            "channel_id": None,
            "threshold": DEFAULT_THRESHOLD,
            "messages": {},
        },
    )

    if not isinstance(starboard, dict):
        guild_data["starboard"] = {
            "enabled": False,
            "channel_id": None,
            "threshold": DEFAULT_THRESHOLD,
            "messages": {},
        }
        starboard = guild_data["starboard"]

    starboard.setdefault("enabled", False)
    starboard.setdefault("channel_id", None)
    starboard.setdefault("threshold", DEFAULT_THRESHOLD)
    starboard.setdefault("messages", {})

    if not isinstance(starboard["messages"], dict):
        starboard["messages"] = {}

    return starboard


def build_starboard_embed(
    message: discord.Message,
    star_count: int,
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
        name="Stars",
        value=f"{STAR_EMOJI} **{star_count}**",
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

    @app_commands.command(name="set-channel", description="Set the starboard channel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
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
        starboard = get_starboard_config(guild_data)

        starboard["channel_id"] = channel.id
        guild_data["starboard"] = starboard
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(
            embed=success_embed(f"Starboard channel set to {channel.mention}."),
            ephemeral=True,
        )

    @app_commands.command(name="set-threshold", description="Set how many stars a message needs.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_threshold(
        self,
        interaction: discord.Interaction,
        amount: app_commands.Range[int, 1, 50],
    ):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        starboard = get_starboard_config(guild_data)

        starboard["threshold"] = int(amount)
        guild_data["starboard"] = starboard
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(
            embed=success_embed(f"Starboard threshold set to **{amount}** {STAR_EMOJI}."),
            ephemeral=True,
        )

    @app_commands.command(name="enable", description="Enable the starboard.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def enable(self, interaction: discord.Interaction):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        starboard = get_starboard_config(guild_data)

        if not starboard.get("channel_id"):
            await interaction.response.send_message(
                embed=error_embed("Set a starboard channel first with `/starboard set-channel`."),
                ephemeral=True,
            )
            return

        starboard["enabled"] = True
        guild_data["starboard"] = starboard
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(
            embed=success_embed("Starboard enabled."),
            ephemeral=True,
        )

    @app_commands.command(name="disable", description="Disable the starboard.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def disable(self, interaction: discord.Interaction):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        starboard = get_starboard_config(guild_data)

        starboard["enabled"] = False
        guild_data["starboard"] = starboard
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(
            embed=success_embed("Starboard disabled."),
            ephemeral=True,
        )

    @app_commands.command(name="status", description="Show starboard settings.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def status(self, interaction: discord.Interaction):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        starboard = get_starboard_config(guild_data)

        channel = await fetch_text_channel(interaction.guild, starboard.get("channel_id"))
        channel_text = channel.mention if channel else "Not configured"

        message_count = len(starboard.get("messages", {}))

        description = (
            f"**Enabled:** {starboard.get('enabled', False)}\n"
            f"**Channel:** {channel_text}\n"
            f"**Threshold:** {starboard.get('threshold', DEFAULT_THRESHOLD)} {STAR_EMOJI}\n"
            f"**Starred Messages:** {message_count}"
        )

        await interaction.response.send_message(
            embed=info_embed("Starboard Status", description),
            ephemeral=True,
        )


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

        if str(payload.emoji) != STAR_EMOJI:
            return

        guild = self.bot.get_guild(payload.guild_id)

        if not guild:
            return

        guild_data = self.bot.db.get_guild(guild.id)
        starboard = get_starboard_config(guild_data)

        if not starboard.get("enabled", False):
            return

        starboard_channel_id = starboard.get("channel_id")
        threshold = int(starboard.get("threshold", DEFAULT_THRESHOLD))

        starboard_channel = await fetch_text_channel(guild, starboard_channel_id)

        if not starboard_channel:
            return

        if payload.channel_id == starboard_channel.id:
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

        star_count = 0

        for reaction in message.reactions:
            if str(reaction.emoji) == STAR_EMOJI:
                star_count = reaction.count
                break

        if star_count < threshold:
            return

        messages = starboard.setdefault("messages", {})
        message_key = str(message.id)
        existing_starboard_id = messages.get(message_key)

        embed = build_starboard_embed(message, star_count)

        if existing_starboard_id:
            try:
                existing = await starboard_channel.fetch_message(int(existing_starboard_id))
                await existing.edit(
                    content=f"{STAR_EMOJI} **{star_count}** in {message.channel.mention}",
                    embed=embed,
                    allowed_mentions=discord.AllowedMentions.none(),
                )
                return
            except (discord.Forbidden, discord.NotFound, discord.HTTPException, ValueError, TypeError):
                messages.pop(message_key, None)

        try:
            sent = await starboard_channel.send(
                content=f"{STAR_EMOJI} **{star_count}** in {message.channel.mention}",
                embed=embed,
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except (discord.Forbidden, discord.HTTPException):
            return

        messages[message_key] = sent.id
        starboard["messages"] = messages
        guild_data["starboard"] = starboard
        self.bot.db.update_guild(guild.id, guild_data)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        await self.process_starboard_reaction(payload)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        await self.process_starboard_reaction(payload)


async def setup(bot: commands.Bot):
    await bot.add_cog(Starboard(bot))

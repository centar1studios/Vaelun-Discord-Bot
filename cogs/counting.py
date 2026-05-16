import re
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import success_embed, error_embed, info_embed


DEFAULT_COUNTING_MILESTONES = [10, 25, 50, 100, 250, 500, 1000]
PERSONA_WEBHOOK_NAME = "Centari Persona Relay"
DEFAULT_PERSONA_KEY = "centari"

NUMBER_RE = re.compile(r"^\s*(\d+)\s*([^\d].*)?$")


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
            reason="Centari counting persona relay",
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


def get_counting_config(guild_data: dict) -> dict:
    counting = guild_data.get("counting")

    if not isinstance(counting, dict):
        counting = {}
        guild_data["counting"] = counting

    counting.setdefault("enabled", False)
    counting.setdefault("channel_id", None)
    counting.setdefault("current_count", 0)
    counting.setdefault("high_score", 0)
    counting.setdefault("last_user_id", None)
    counting.setdefault("last_message_id", None)
    counting.setdefault("save_tokens", 0)
    counting.setdefault("shield_active", False)
    counting.setdefault("persona_key", None)
    counting.setdefault("stats", {})

    if not isinstance(counting["stats"], dict):
        counting["stats"] = {}

    return counting


def parse_count_message(content: str) -> int | None:
    match = NUMBER_RE.match(content)

    if not match:
        return None

    try:
        return int(match.group(1))
    except ValueError:
        return None


def get_user_stats(counting: dict, user_id: int) -> dict:
    stats = counting.setdefault("stats", {})
    user_key = str(user_id)

    if user_key not in stats or not isinstance(stats[user_key], dict):
        stats[user_key] = {
            "correct": 0,
            "milestones": 0,
            "resets_caused": 0,
            "saves_used": 0,
            "shields_triggered": 0,
        }

    stats[user_key].setdefault("correct", 0)
    stats[user_key].setdefault("milestones", 0)
    stats[user_key].setdefault("resets_caused", 0)
    stats[user_key].setdefault("saves_used", 0)
    stats[user_key].setdefault("shields_triggered", 0)

    return stats[user_key]


def build_counting_rules(channel: discord.TextChannel | None = None) -> str:
    channel_text = channel.mention if channel else "the configured counting channel"

    return (
        f"Count upward one number at a time in {channel_text}.\n\n"
        "**Rules:**\n"
        "1. The next message must be the next number.\n"
        "2. The same person cannot count twice in a row.\n"
        "3. Wrong numbers reset the count unless a shield is active.\n"
        "4. Milestones are celebrated at 10, 25, 50, 100, 250, 500, and 1000.\n"
        "5. Staff can use save tokens to restore a broken count.\n\n"
        "Example:\n"
        "`1` → `2` → `3`"
    )


class CountingGroup(app_commands.Group):
    def __init__(self, bot: commands.Bot, cog: commands.Cog):
        super().__init__(name="counting", description="Counting Rift game tools.")
        self.bot = bot
        self.cog = cog

    @app_commands.command(name="set-channel", description="Set the counting channel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
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

        if not permissions.add_reactions:
            await interaction.response.send_message(
                embed=error_embed("I need `Add Reactions` in that channel so I can react to counts."),
                ephemeral=True,
            )
            return

        guild_data = self.bot.db.get_guild(interaction.guild.id)
        counting = get_counting_config(guild_data)

        counting["enabled"] = True
        counting["channel_id"] = channel.id
        counting["updated_by"] = interaction.user.id
        counting["updated_at"] = datetime.now(timezone.utc).isoformat()

        guild_data["counting"] = counting
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(
            embed=success_embed(f"Counting Rift enabled in {channel.mention}."),
            ephemeral=True,
        )

    @app_commands.command(name="disable", description="Disable the counting game.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def disable(self, interaction: discord.Interaction):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        counting = get_counting_config(guild_data)

        counting["enabled"] = False
        counting["updated_by"] = interaction.user.id
        counting["updated_at"] = datetime.now(timezone.utc).isoformat()

        guild_data["counting"] = counting
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(
            embed=success_embed("Counting Rift disabled."),
            ephemeral=True,
        )

    @app_commands.command(name="status", description="Show counting game status.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def status(self, interaction: discord.Interaction):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        counting = get_counting_config(guild_data)

        channel = await fetch_text_channel(interaction.guild, counting.get("channel_id"))
        channel_text = channel.mention if channel else "Not configured"

        last_user_text = "None"

        if counting.get("last_user_id"):
            last_user_text = f"<@{counting.get('last_user_id')}>"

        persona_key = counting.get("persona_key") or "None"

        description = (
            f"**Enabled:** {counting.get('enabled', False)}\n"
            f"**Channel:** {channel_text}\n"
            f"**Current Count:** {counting.get('current_count', 0)}\n"
            f"**High Score:** {counting.get('high_score', 0)}\n"
            f"**Last Counter:** {last_user_text}\n"
            f"**Save Tokens:** {counting.get('save_tokens', 0)}\n"
            f"**Shield Active:** {counting.get('shield_active', False)}\n"
            f"**Persona Key:** `{persona_key}`"
        )

        await interaction.response.send_message(
            embed=info_embed("Counting Rift Status", description),
            ephemeral=True,
        )

    @app_commands.command(name="reset", description="Reset the current count.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def reset(self, interaction: discord.Interaction):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        counting = get_counting_config(guild_data)

        old_count = counting.get("current_count", 0)

        counting["current_count"] = 0
        counting["last_user_id"] = None
        counting["last_message_id"] = None
        counting["shield_active"] = False
        counting["updated_by"] = interaction.user.id
        counting["updated_at"] = datetime.now(timezone.utc).isoformat()

        guild_data["counting"] = counting
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(
            embed=success_embed(f"Counting Rift reset. Previous count was **{old_count}**."),
            ephemeral=True,
        )

    @app_commands.command(name="rules", description="Show the counting rules.")
    async def rules(self, interaction: discord.Interaction):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        counting = get_counting_config(guild_data)
        channel = await fetch_text_channel(interaction.guild, counting.get("channel_id"))

        await interaction.response.send_message(
            embed=info_embed("Counting Rift Rules", build_counting_rules(channel)),
            ephemeral=True,
        )

    @app_commands.command(name="leaderboard", description="Show the counting leaderboard.")
    async def leaderboard(self, interaction: discord.Interaction):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        counting = get_counting_config(guild_data)
        stats = counting.get("stats", {})

        if not stats:
            await interaction.response.send_message(
                embed=info_embed("Counting Leaderboard", "No counting stats yet."),
                ephemeral=True,
            )
            return

        sorted_stats = sorted(
            stats.items(),
            key=lambda item: item[1].get("correct", 0),
            reverse=True,
        )

        lines = []

        for index, (user_id, user_stats) in enumerate(sorted_stats[:10], start=1):
            correct = user_stats.get("correct", 0)
            milestones = user_stats.get("milestones", 0)
            resets = user_stats.get("resets_caused", 0)
            saves = user_stats.get("saves_used", 0)

            lines.append(
                f"**{index}. <@{user_id}>**\n"
                f"Correct: `{correct}` | Milestones: `{milestones}` | Saves: `{saves}` | Resets: `{resets}`"
            )

        await interaction.response.send_message(
            embed=info_embed("Counting Leaderboard", "\n\n".join(lines)),
            ephemeral=True,
        )

    @app_commands.command(name="set-persona", description="Set a persona for counting milestone messages.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_persona(self, interaction: discord.Interaction, persona_key: str):
        persona_key = persona_key.lower().strip()

        guild_data = self.bot.db.get_guild(interaction.guild.id)
        counting = get_counting_config(guild_data)
        persona = get_persona(guild_data, persona_key)

        if not persona:
            await interaction.response.send_message(
                embed=error_embed("I could not find an enabled persona with that key."),
                ephemeral=True,
            )
            return

        counting["persona_key"] = persona_key
        counting["updated_by"] = interaction.user.id
        counting["updated_at"] = datetime.now(timezone.utc).isoformat()

        guild_data["counting"] = counting
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(
            embed=success_embed(f"Counting milestone messages will now use persona `{persona_key}`."),
            ephemeral=True,
        )

    @app_commands.command(name="clear-persona", description="Clear the counting persona.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def clear_persona(self, interaction: discord.Interaction):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        counting = get_counting_config(guild_data)

        counting["persona_key"] = None
        counting["updated_by"] = interaction.user.id
        counting["updated_at"] = datetime.now(timezone.utc).isoformat()

        guild_data["counting"] = counting
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(
            embed=success_embed("Counting persona cleared."),
            ephemeral=True,
        )

    @app_commands.command(name="give-save", description="Give the Counting Rift a save token.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def give_save(self, interaction: discord.Interaction, amount: app_commands.Range[int, 1, 25] = 1):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        counting = get_counting_config(guild_data)

        counting["save_tokens"] = int(counting.get("save_tokens", 0)) + int(amount)
        counting["updated_by"] = interaction.user.id
        counting["updated_at"] = datetime.now(timezone.utc).isoformat()

        guild_data["counting"] = counting
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(
            embed=success_embed(
                f"Added **{amount}** save token(s).\n"
                f"Current save tokens: **{counting['save_tokens']}**"
            ),
            ephemeral=True,
        )

    @app_commands.command(name="use-save", description="Use a save token to activate a one-time shield.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def use_save(self, interaction: discord.Interaction):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        counting = get_counting_config(guild_data)

        if int(counting.get("save_tokens", 0)) <= 0:
            await interaction.response.send_message(
                embed=error_embed("There are no save tokens available."),
                ephemeral=True,
            )
            return

        if counting.get("shield_active", False):
            await interaction.response.send_message(
                embed=error_embed("A shield is already active."),
                ephemeral=True,
            )
            return

        counting["save_tokens"] = int(counting.get("save_tokens", 0)) - 1
        counting["shield_active"] = True

        user_stats = get_user_stats(counting, interaction.user.id)
        user_stats["saves_used"] = int(user_stats.get("saves_used", 0)) + 1

        counting["updated_by"] = interaction.user.id
        counting["updated_at"] = datetime.now(timezone.utc).isoformat()

        guild_data["counting"] = counting
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        channel = await fetch_text_channel(interaction.guild, counting.get("channel_id"))

        if channel:
            try:
                await channel.send(
                    "🛡️ **Archive Shield activated.** The next wrong count will be forgiven.",
                    allowed_mentions=discord.AllowedMentions.none(),
                )
            except (discord.Forbidden, discord.HTTPException):
                pass

        await interaction.response.send_message(
            embed=success_embed(
                f"Archive Shield activated.\n"
                f"Remaining save tokens: **{counting['save_tokens']}**"
            ),
            ephemeral=True,
        )

    @set_persona.autocomplete("persona_key")
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


class Counting(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.tree.add_command(CountingGroup(bot, self))

    async def send_persona_or_bot_message(
        self,
        channel: discord.TextChannel,
        guild_data: dict,
        content: str,
        persona_key: str | None = None,
    ):
        persona = get_persona(guild_data, persona_key)

        if persona:
            permissions = channel.permissions_for(channel.guild.me)

            if permissions.manage_webhooks:
                webhook = await get_or_create_persona_webhook(channel)

                if webhook:
                    try:
                        await webhook.send(
                            content=content,
                            username=persona.get("name", "Persona")[:80],
                            avatar_url=persona.get("avatar_url"),
                            allowed_mentions=discord.AllowedMentions.none(),
                        )
                        return
                    except (discord.Forbidden, discord.HTTPException):
                        pass

        try:
            await channel.send(
                content,
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except (discord.Forbidden, discord.HTTPException):
            pass

    async def handle_correct_count(
        self,
        message: discord.Message,
        guild_data: dict,
        counting: dict,
        number: int,
    ):
        old_high_score = int(counting.get("high_score", 0))

        counting["current_count"] = number
        counting["last_user_id"] = message.author.id
        counting["last_message_id"] = message.id

        if number > old_high_score:
            counting["high_score"] = number

        user_stats = get_user_stats(counting, message.author.id)
        user_stats["correct"] = int(user_stats.get("correct", 0)) + 1

        try:
            await message.add_reaction("✅")
        except (discord.Forbidden, discord.HTTPException):
            pass

        milestone_hit = number in DEFAULT_COUNTING_MILESTONES or (
            number > 0 and number % 1000 == 0
        )

        if milestone_hit:
            user_stats["milestones"] = int(user_stats.get("milestones", 0)) + 1

            if number >= 100 and number % 100 == 0:
                counting["save_tokens"] = int(counting.get("save_tokens", 0)) + 1

            persona_key = counting.get("persona_key")

            milestone_message = (
                f"🌟 **Counting Rift milestone reached: {number}!**\n"
                f"The Archive records this moment.\n"
                f"High score: **{counting.get('high_score', number)}**"
            )

            if number >= 100 and number % 100 == 0:
                milestone_message += "\n✨ Bonus: the server earned **1 save token**."

            await self.send_persona_or_bot_message(
                channel=message.channel,
                guild_data=guild_data,
                content=milestone_message,
                persona_key=persona_key,
            )

        guild_data["counting"] = counting
        self.bot.db.update_guild(message.guild.id, guild_data)

    async def handle_wrong_count(
        self,
        message: discord.Message,
        guild_data: dict,
        counting: dict,
        reason: str,
    ):
        current_count = int(counting.get("current_count", 0))

        try:
            await message.add_reaction("❌")
        except (discord.Forbidden, discord.HTTPException):
            pass

        user_stats = get_user_stats(counting, message.author.id)

        if counting.get("shield_active", False):
            counting["shield_active"] = False
            user_stats["shields_triggered"] = int(user_stats.get("shields_triggered", 0)) + 1

            guild_data["counting"] = counting
            self.bot.db.update_guild(message.guild.id, guild_data)

            await self.send_persona_or_bot_message(
                channel=message.channel,
                guild_data=guild_data,
                content=(
                    f"🛡️ **Archive Shield used.**\n"
                    f"{reason}\n"
                    f"The count survives at **{current_count}**."
                ),
                persona_key=counting.get("persona_key"),
            )
            return

        user_stats["resets_caused"] = int(user_stats.get("resets_caused", 0)) + 1

        counting["current_count"] = 0
        counting["last_user_id"] = None
        counting["last_message_id"] = None
        counting["shield_active"] = False

        guild_data["counting"] = counting
        self.bot.db.update_guild(message.guild.id, guild_data)

        await self.send_persona_or_bot_message(
            channel=message.channel,
            guild_data=guild_data,
            content=(
                f"💥 **The Counting Rift collapsed.**\n"
                f"{reason}\n"
                f"The count reset from **{current_count}** back to **0**."
            ),
            persona_key=counting.get("persona_key"),
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild:
            return

        if message.author.bot:
            return

        guild_data = self.bot.db.get_guild(message.guild.id)
        counting = get_counting_config(guild_data)

        if not counting.get("enabled", False):
            return

        if not counting.get("channel_id"):
            return

        if message.channel.id != int(counting.get("channel_id")):
            return

        number = parse_count_message(message.content)

        if number is None:
            return

        expected = int(counting.get("current_count", 0)) + 1
        last_user_id = counting.get("last_user_id")

        if last_user_id and int(last_user_id) == message.author.id:
            await self.handle_wrong_count(
                message=message,
                guild_data=guild_data,
                counting=counting,
                reason="The same user counted twice in a row.",
            )
            return

        if number != expected:
            await self.handle_wrong_count(
                message=message,
                guild_data=guild_data,
                counting=counting,
                reason=f"Expected **{expected}**, but got **{number}**.",
            )
            return

        await self.handle_correct_count(
            message=message,
            guild_data=guild_data,
            counting=counting,
            number=number,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Counting(bot))

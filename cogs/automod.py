import re
import time
from collections import defaultdict, deque

import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import success_embed, error_embed, info_embed


SCAM_PHRASES = [
    "free nitro",
    "gift nitro",
    "discord nitro free",
    "steam gift",
    "claim your prize",
    "verify your wallet",
    "connect your wallet",
    "scan this qr",
    "qr code login",
    "account will be disabled",
    "click here to verify"
]

INVITE_RE = re.compile(r"(discord\.gg/|discord\.com/invite/|discordapp\.com/invite/)", re.IGNORECASE)
URL_RE = re.compile(r"(https?://[^\s]+|www\.[^\s]+)", re.IGNORECASE)

SAFETY_TITLE = "⚠️ Potential Spam or Scam Detected"
SAFETY_MESSAGE = (
    "Centari Studios detected a message that may contain spam, scam content, phishing, unsafe links, "
    "or suspicious mass mentions.\n\n"
    "**Do not click unknown links, scan random QR codes, download suspicious files, or give out your Discord login information.**\n\n"
    "Staff have been notified."
)


class AutomodGroup(app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__(name="automod", description="Automod and safety settings.")
        self.bot = bot

    @app_commands.command(name="toggle", description="Turn automod on or off.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def toggle(self, interaction: discord.Interaction, enabled: bool):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        guild_data["automod"]["enabled"] = enabled
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(embed=success_embed(f"Automod enabled: `{enabled}`"), ephemeral=True)

    @app_commands.command(name="mode", description="Set automod mode.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.choices(mode=[
        app_commands.Choice(name="Chill", value="chill"),
        app_commands.Choice(name="Balanced", value="balanced"),
        app_commands.Choice(name="Strict", value="strict"),
    ])
    async def mode(self, interaction: discord.Interaction, mode: app_commands.Choice[str]):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        guild_data["automod"]["mode"] = mode.value
        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(embed=success_embed(f"Automod mode set to `{mode.value}`."), ephemeral=True)

    @app_commands.command(name="block-word", description="Add a blocked word.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def block_word(self, interaction: discord.Interaction, word: str):
        guild_data = self.bot.db.get_guild(interaction.guild.id)
        blocked = guild_data["automod"]["blocked_words"]

        if word.lower() not in blocked:
            blocked.append(word.lower())

        self.bot.db.update_guild(interaction.guild.id, guild_data)

        await interaction.response.send_message(embed=success_embed(f"Blocked word added: `{word}`"), ephemeral=True)

    @app_commands.command(name="view", description="View automod settings.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def view(self, interaction: discord.Interaction):
        automod = self.bot.db.get_guild(interaction.guild.id)["automod"]

        description = f"""
**Enabled:** {automod["enabled"]}
**Mode:** {automod["mode"]}
**Block Invites:** {automod["block_invites"]}
**Block Mass Mentions:** {automod["block_mass_mentions"]}
**Block Spam:** {automod["block_spam"]}
**Blocked Words:** {", ".join(automod["blocked_words"]) if automod["blocked_words"] else "None"}
"""

        await interaction.response.send_message(embed=info_embed("Automod Settings", description), ephemeral=True)


class Automod(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.recent_messages = defaultdict(lambda: defaultdict(lambda: deque(maxlen=8)))
        self.warning_cooldowns = defaultdict(float)
        self.bot.tree.add_command(AutomodGroup(bot))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        guild_data = self.bot.db.get_guild(message.guild.id)
        automod = guild_data["automod"]

        if not automod["enabled"]:
            return

        flagged, reason = self.is_suspicious(message, automod)

        if not flagged:
            return

        try:
            await message.delete()
        except discord.Forbidden:
            pass
        except discord.NotFound:
            pass

        await self.send_safety_warning(message.channel)
        await self.log_safety(message, reason)

    def is_suspicious(self, message: discord.Message, automod: dict) -> tuple[bool, str]:
        content = message.content.lower()
        mode = automod["mode"]

        for word in automod["blocked_words"]:
            if word in content:
                return True, f"Blocked word: {word}"

        for phrase in SCAM_PHRASES:
            if phrase in content:
                return True, f"Scam phrase: {phrase}"

        if automod["block_invites"] and INVITE_RE.search(content):
            return True, "Discord invite detected"

        mention_limit = 8 if mode == "chill" else 5 if mode == "balanced" else 3

        if automod["block_mass_mentions"] and (len(message.mentions) >= mention_limit or message.mention_everyone):
            return True, "Mass mention detected"

        link_limit = 5 if mode == "chill" else 3 if mode == "balanced" else 2

        if len(URL_RE.findall(content)) >= link_limit:
            return True, "Too many links"

        if automod["block_spam"]:
            now = time.time()
            user_messages = self.recent_messages[message.guild.id][message.author.id]
            user_messages.append((now, content))

            repeats = [
                timestamp for timestamp, old_content in user_messages
                if old_content == content and now - timestamp <= 20
            ]

            repeat_limit = 5 if mode == "chill" else 3 if mode == "balanced" else 2

            if len(repeats) >= repeat_limit:
                return True, "Repeated message spam"

        return False, ""

    async def send_safety_warning(self, channel: discord.TextChannel):
        now = time.time()

        if now - self.warning_cooldowns[channel.guild.id] < 30:
            return

        self.warning_cooldowns[channel.guild.id] = now

        embed = discord.Embed(
            title=SAFETY_TITLE,
            description=SAFETY_MESSAGE,
            color=discord.Color.red()
        )

        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            pass

    async def log_safety(self, message: discord.Message, reason: str):
        log_id = self.bot.db.get_setting(message.guild.id, "log_channel_id")

        if not log_id:
            return

        channel = message.guild.get_channel(int(log_id))

        if not channel:
            return

        embed = discord.Embed(
            title="Automod Action",
            color=discord.Color.red()
        )

        embed.add_field(name="User", value=f"{message.author.mention} (`{message.author.id}`)", inline=False)
        embed.add_field(name="Channel", value=message.channel.mention, inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Message", value=message.content[:1000] or "No content", inline=False)

        await channel.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Automod(bot))

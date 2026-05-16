import logging
from typing import Any, Dict, Optional

import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import info_embed, error_embed


logger = logging.getLogger("centari.reaction_roles")


def emoji_matches(config_emoji: str, payload_emoji: discord.PartialEmoji) -> bool:
    """
    Supports:
    - Unicode emoji: 🌙
    - Custom emoji string: <:name:id>
    - Animated custom emoji string: <a:name:id>
    - Raw custom emoji ID: 123456789
    - Custom emoji name: name
    """
    stored = str(config_emoji).strip()

    if not stored:
        return False

    candidates = {
        str(payload_emoji),
        payload_emoji.name or "",
    }

    if payload_emoji.id:
        candidates.add(str(payload_emoji.id))

    return stored in candidates


def get_reaction_role_match(
    reaction_roles: list[Dict[str, Any]],
    message_id: int,
    payload_emoji: discord.PartialEmoji,
) -> Optional[Dict[str, Any]]:
    for entry in reaction_roles:
        if not entry.get("enabled", True):
            continue

        entry_message_id = int(entry.get("message_id", 0) or 0)

        if entry_message_id != int(message_id):
            continue

        if emoji_matches(str(entry.get("emoji", "")), payload_emoji):
            return entry

    return None


class ReactionRoles(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def get_member_from_payload(self, payload: discord.RawReactionActionEvent) -> Optional[discord.Member]:
        guild = self.bot.get_guild(payload.guild_id)

        if not guild:
            return None

        member = guild.get_member(payload.user_id)

        if member:
            return member

        try:
            return await guild.fetch_member(payload.user_id)
        except discord.NotFound:
            return None
        except discord.Forbidden:
            return None
        except discord.HTTPException:
            return None

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.guild_id is None:
            return

        if payload.user_id == self.bot.user.id:
            return

        guild = self.bot.get_guild(payload.guild_id)

        if not guild:
            return

        guild_config = self.bot.db.get_guild(payload.guild_id)
        reaction_roles = guild_config.get("reaction_roles", [])

        match = get_reaction_role_match(
            reaction_roles=reaction_roles,
            message_id=payload.message_id,
            payload_emoji=payload.emoji,
        )

        if not match:
            return

        role_id = int(match.get("role_id", 0) or 0)
        role = guild.get_role(role_id)

        if not role:
            logger.warning("Reaction role not found: guild=%s role=%s", guild.id, role_id)
            return

        member = await self.get_member_from_payload(payload)

        if not member:
            return

        if role in member.roles:
            return

        try:
            await member.add_roles(role, reason="Reaction role added")
            logger.info(
                "Added reaction role: guild=%s user=%s role=%s message=%s emoji=%s",
                guild.id,
                member.id,
                role.id,
                payload.message_id,
                payload.emoji,
            )
        except discord.Forbidden:
            logger.warning(
                "Missing permissions to add reaction role: guild=%s role=%s",
                guild.id,
                role.id,
            )
        except discord.HTTPException:
            logger.exception(
                "Failed to add reaction role: guild=%s role=%s",
                guild.id,
                role.id,
            )

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if payload.guild_id is None:
            return

        guild = self.bot.get_guild(payload.guild_id)

        if not guild:
            return

        guild_config = self.bot.db.get_guild(payload.guild_id)
        reaction_roles = guild_config.get("reaction_roles", [])

        match = get_reaction_role_match(
            reaction_roles=reaction_roles,
            message_id=payload.message_id,
            payload_emoji=payload.emoji,
        )

        if not match:
            return

        role_id = int(match.get("role_id", 0) or 0)
        role = guild.get_role(role_id)

        if not role:
            return

        member = guild.get_member(payload.user_id)

        if not member:
            try:
                member = await guild.fetch_member(payload.user_id)
            except discord.NotFound:
                return
            except discord.Forbidden:
                return
            except discord.HTTPException:
                return

        if role not in member.roles:
            return

        try:
            await member.remove_roles(role, reason="Reaction role removed")
            logger.info(
                "Removed reaction role: guild=%s user=%s role=%s message=%s emoji=%s",
                guild.id,
                member.id,
                role.id,
                payload.message_id,
                payload.emoji,
            )
        except discord.Forbidden:
            logger.warning(
                "Missing permissions to remove reaction role: guild=%s role=%s",
                guild.id,
                role.id,
            )
        except discord.HTTPException:
            logger.exception(
                "Failed to remove reaction role: guild=%s role=%s",
                guild.id,
                role.id,
            )

    @app_commands.command(name="reaction-roles", description="View configured reaction roles.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def reaction_roles_view(self, interaction: discord.Interaction):
        guild_config = self.bot.db.get_guild(interaction.guild.id)
        reaction_roles = guild_config.get("reaction_roles", [])

        if not reaction_roles:
            await interaction.response.send_message(
                embed=error_embed("No reaction roles are configured for this server."),
                ephemeral=True,
            )
            return

        lines = []

        for entry in reaction_roles:
            status = "Enabled" if entry.get("enabled", True) else "Disabled"
            label = entry.get("label") or "Reaction Role"
            emoji = entry.get("emoji") or "?"
            role_id = entry.get("role_id")
            message_id = entry.get("message_id")

            lines.append(
                f"**{label}**\n"
                f"Emoji: `{emoji}`\n"
                f"Role ID: `{role_id}`\n"
                f"Message ID: `{message_id}`\n"
                f"Status: `{status}`"
            )

        await interaction.response.send_message(
            embed=info_embed("Reaction Roles", "\n\n".join(lines[:10])),
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(ReactionRoles(bot))

import discord


def is_staff(interaction: discord.Interaction, staff_role_id: int | None = None) -> bool:
    if not isinstance(interaction.user, discord.Member):
        return False

    permissions = interaction.user.guild_permissions

    if (
        permissions.administrator
        or permissions.manage_guild
        or permissions.moderate_members
        or permissions.kick_members
        or permissions.ban_members
    ):
        return True

    if staff_role_id:
        return any(role.id == staff_role_id for role in interaction.user.roles)

    return False

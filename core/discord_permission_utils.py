import discord


def has_role(
    interaction: discord.Interaction,
    role_id: int
) -> bool:
    if not hasattr(interaction.user, "roles"):
        return False

    return any(
        role.id == role_id
        for role in interaction.user.roles
    )
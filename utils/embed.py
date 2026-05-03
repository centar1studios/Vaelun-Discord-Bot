import discord


def parse_color(hex_color: str) -> discord.Color:
    try:
        clean = hex_color.replace("#", "")
        return discord.Color(int(clean, 16))
    except Exception:
        return discord.Color.blurple()


def persona_embed(persona: dict, title: str, description: str) -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=description,
        color=parse_color(persona.get("color", "#9B7BFF"))
    )

    name = persona.get("name", "Centari Studios")
    avatar_url = persona.get("avatar_url")
    footer = persona.get("footer", "Powered by Centari Studios")

    if avatar_url:
        embed.set_author(name=name, icon_url=avatar_url)
        embed.set_thumbnail(url=avatar_url)
    else:
        embed.set_author(name=name)

    embed.set_footer(text=footer)
    embed.timestamp = discord.utils.utcnow()

    return embed


def success_embed(message: str) -> discord.Embed:
    return discord.Embed(
        title="Success",
        description=message,
        color=discord.Color.green()
    )


def error_embed(message: str) -> discord.Embed:
    return discord.Embed(
        title="Something went wrong",
        description=message,
        color=discord.Color.red()
    )


def info_embed(title: str, message: str) -> discord.Embed:
    return discord.Embed(
        title=title,
        description=message,
        color=discord.Color.blurple()
    )

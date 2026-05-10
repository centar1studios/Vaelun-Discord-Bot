import discord


DEFAULT_COLOR = discord.Color.from_rgb(155, 123, 255)
SUCCESS_COLOR = discord.Color.green()
ERROR_COLOR = discord.Color.red()
INFO_COLOR = discord.Color.blurple()
WARNING_COLOR = discord.Color.orange()
PERSONA_COLOR = discord.Color.from_rgb(168, 85, 247)

DEFAULT_FOOTER = "Dei Talvyrvei • Centari Studios"


def _split_title_description(title: str, description: str | None = None):
    """
    Allows both styles:

    success_embed("Message only")

    and:

    success_embed("Title", "Description")
    """
    if description is None:
        return title, None

    return title, description


def _apply_footer(embed: discord.Embed, footer: str | None = DEFAULT_FOOTER) -> discord.Embed:
    if footer:
        embed.set_footer(text=footer)

    return embed


def basic_embed(title: str, description: str | None = None) -> discord.Embed:
    title, description = _split_title_description(title, description)

    embed = discord.Embed(
        title=title,
        description=description,
        color=DEFAULT_COLOR,
    )

    return _apply_footer(embed)


def success_embed(title: str, description: str | None = None) -> discord.Embed:
    title, description = _split_title_description(title, description)

    embed = discord.Embed(
        title=f"✅ {title}",
        description=description,
        color=SUCCESS_COLOR,
    )

    return _apply_footer(embed)


def error_embed(title: str, description: str | None = None) -> discord.Embed:
    title, description = _split_title_description(title, description)

    embed = discord.Embed(
        title=f"❌ {title}",
        description=description,
        color=ERROR_COLOR,
    )

    return _apply_footer(embed)


def info_embed(title: str, description: str | None = None) -> discord.Embed:
    title, description = _split_title_description(title, description)

    embed = discord.Embed(
        title=f"ℹ️ {title}",
        description=description,
        color=INFO_COLOR,
    )

    return _apply_footer(embed)


def warning_embed(title: str, description: str | None = None) -> discord.Embed:
    title, description = _split_title_description(title, description)

    embed = discord.Embed(
        title=f"⚠️ {title}",
        description=description,
        color=WARNING_COLOR,
    )

    return _apply_footer(embed)


def moderation_embed(title: str, description: str | None = None) -> discord.Embed:
    title, description = _split_title_description(title, description)

    embed = discord.Embed(
        title=f"🛡️ {title}",
        description=description,
        color=WARNING_COLOR,
    )

    return _apply_footer(embed)


def settings_embed(title: str, description: str | None = None) -> discord.Embed:
    title, description = _split_title_description(title, description)

    embed = discord.Embed(
        title=f"⚙️ {title}",
        description=description,
        color=INFO_COLOR,
    )

    return _apply_footer(embed)


def log_embed(title: str, description: str | None = None) -> discord.Embed:
    title, description = _split_title_description(title, description)

    embed = discord.Embed(
        title=f"📋 {title}",
        description=description,
        color=DEFAULT_COLOR,
    )

    return _apply_footer(embed)


def persona_embed(*args) -> discord.Embed:
    """
    Supports both newer and older calls:

    persona_embed("Title", "Description")

    and:

    persona_embed(persona, "Title", "Description")

    The second version uses persona values like:
    - name
    - bio
    - avatar_url
    - color
    - footer
    """
    persona = None

    if len(args) == 2:
        title, description = args

    elif len(args) == 3:
        persona, title, description = args

    else:
        raise TypeError(
            "persona_embed expected either "
            "(title, description) or (persona, title, description)."
        )

    color = PERSONA_COLOR
    footer = DEFAULT_FOOTER
    author_name = None
    avatar_url = None

    if isinstance(persona, dict):
        author_name = persona.get("name") or "Centari Studios"
        avatar_url = persona.get("avatar_url")
        footer = persona.get("footer") or DEFAULT_FOOTER

        hex_color = persona.get("color")

        if isinstance(hex_color, str):
            try:
                clean = hex_color.strip().replace("#", "")
                color = discord.Color(int(clean, 16))
            except ValueError:
                color = PERSONA_COLOR

    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
    )

    if author_name:
        if avatar_url:
            embed.set_author(name=author_name, icon_url=avatar_url)
        else:
            embed.set_author(name=author_name)

    if footer:
        embed.set_footer(text=footer)

    return embed


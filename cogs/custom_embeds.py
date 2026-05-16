import uuid
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from cogs.fonts import ALL_STYLE_NAMES, convert_font, font_autocomplete
from utils.embeds import success_embed, error_embed, info_embed


DEFAULT_COLOR = "#9B7BFF"


def hex_to_color(value: str, fallback: discord.Color = discord.Color.purple()) -> discord.Color:
    if not isinstance(value, str):
        return fallback

    clean = value.strip().replace("#", "")

    if len(clean) != 6:
        return fallback

    try:
        return discord.Color(int(clean, 16))
    except ValueError:
        return fallback


def normalize_hex_color(value: str | None) -> str:
    if not value:
        return DEFAULT_COLOR

    clean = value.strip().replace("#", "")

    if len(clean) != 6:
        return DEFAULT_COLOR

    try:
        int(clean, 16)
    except ValueError:
        return DEFAULT_COLOR

    return f"#{clean.upper()}"


def clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None

    value = value.strip()

    return value or None


def clean_optional_url(value: str | None) -> str | None:
    value = clean_optional_text(value)

    if not value:
        return None

    if not value.startswith(("http://", "https://")):
        return None

    return value


def clean_optional_font(value: str | None) -> str | None:
    value = clean_optional_text(value)

    if not value:
        return None

    value = value.lower().strip()

    if value not in ALL_STYLE_NAMES:
        return None

    return value


def apply_optional_font(text: str | None, font: str | None) -> str | None:
    if not text:
        return None

    if not font:
        return text

    if font not in ALL_STYLE_NAMES:
        return text

    return convert_font(text, font)


def build_custom_embed(template: dict) -> discord.Embed:
    title = apply_optional_font(
        template.get("title"),
        template.get("title_font"),
    )

    description = apply_optional_font(
        template.get("description"),
        template.get("description_font"),
    )

    footer = apply_optional_font(
        template.get("footer"),
        template.get("footer_font"),
    )

    embed = discord.Embed(
        title=title or None,
        description=description or None,
        color=hex_to_color(template.get("color", DEFAULT_COLOR)),
    )

    thumbnail_url = template.get("thumbnail_url")
    image_url = template.get("image_url")

    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)

    if image_url:
        embed.set_image(url=image_url)

    if footer:
        embed.set_footer(text=footer)

    return embed


class CustomEmbeds(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def get_templates(self, guild_id: int) -> list[dict]:
        guild_config = self.bot.db.get_guild(guild_id)
        embeds = guild_config.get("embeds", [])

        if not isinstance(embeds, list):
            guild_config["embeds"] = []
            self.bot.db.update_guild(guild_id, guild_config)
            return []

        return embeds

    def save_templates(self, guild_id: int, templates: list[dict]):
        guild_config = self.bot.db.get_guild(guild_id)
        guild_config["embeds"] = templates
        self.bot.db.update_guild(guild_id, guild_config)

    def find_template(self, guild_id: int, template_name: str) -> dict | None:
        template_name = template_name.lower().strip()

        for item in self.get_templates(guild_id):
            name = str(item.get("name", "")).lower().strip()

            if name == template_name:
                return item

        return None

    @app_commands.command(name="embed-save", description="Save or update an embed template.")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(
        name="Template name.",
        title="Embed title.",
        description="Embed description.",
        color="Hex color, like #9B7BFF.",
        thumbnail_url="Optional thumbnail image URL.",
        image_url="Optional large image URL.",
        footer="Optional footer text.",
        title_font="Optional font style for the title.",
        description_font="Optional font style for the description.",
        footer_font="Optional font style for the footer.",
    )
    @app_commands.autocomplete(
        title_font=font_autocomplete,
        description_font=font_autocomplete,
        footer_font=font_autocomplete,
    )
    async def embed_save(
        self,
        interaction: discord.Interaction,
        name: str,
        title: str | None = None,
        description: str | None = None,
        color: str | None = DEFAULT_COLOR,
        thumbnail_url: str | None = None,
        image_url: str | None = None,
        footer: str | None = None,
        title_font: str | None = None,
        description_font: str | None = None,
        footer_font: str | None = None,
    ):
        name = name.strip()

        if not name:
            await interaction.response.send_message(
                embed=error_embed("Template name cannot be empty."),
                ephemeral=True,
            )
            return

        if len(name) > 80:
            await interaction.response.send_message(
                embed=error_embed("Template name must be 80 characters or less."),
                ephemeral=True,
            )
            return

        title = clean_optional_text(title)
        description = clean_optional_text(description)
        footer = clean_optional_text(footer)
        thumbnail_url = clean_optional_url(thumbnail_url)
        image_url = clean_optional_url(image_url)
        color = normalize_hex_color(color)

        title_font = clean_optional_font(title_font)
        description_font = clean_optional_font(description_font)
        footer_font = clean_optional_font(footer_font)

        if not title and not description and not image_url:
            await interaction.response.send_message(
                embed=error_embed("An embed needs at least a title, description, or image URL."),
                ephemeral=True,
            )
            return

        if title and len(title) > 256:
            await interaction.response.send_message(
                embed=error_embed("Embed title must be 256 characters or less."),
                ephemeral=True,
            )
            return

        if description and len(description) > 4000:
            await interaction.response.send_message(
                embed=error_embed("Embed description must be 4000 characters or less."),
                ephemeral=True,
            )
            return

        if footer and len(footer) > 2048:
            await interaction.response.send_message(
                embed=error_embed("Embed footer must be 2048 characters or less."),
                ephemeral=True,
            )
            return

        if title_font and not title:
            await interaction.response.send_message(
                embed=error_embed("A title font was provided, but there is no title."),
                ephemeral=True,
            )
            return

        if description_font and not description:
            await interaction.response.send_message(
                embed=error_embed("A description font was provided, but there is no description."),
                ephemeral=True,
            )
            return

        if footer_font and not footer:
            await interaction.response.send_message(
                embed=error_embed("A footer font was provided, but there is no footer."),
                ephemeral=True,
            )
            return

        templates = self.get_templates(interaction.guild.id)
        now = datetime.now(timezone.utc).isoformat()

        existing = None

        for item in templates:
            if str(item.get("name", "")).lower().strip() == name.lower():
                existing = item
                break

        template_data = {
            "name": name,
            "title": title,
            "description": description,
            "color": color,
            "thumbnail_url": thumbnail_url,
            "image_url": image_url,
            "footer": footer,
            "title_font": title_font,
            "description_font": description_font,
            "footer_font": footer_font,
            "enabled": True,
            "updated_at": now,
            "updated_by": interaction.user.id,
        }

        if existing:
            existing.update(template_data)
            action = "updated"
        else:
            template_data.update(
                {
                    "id": str(uuid.uuid4())[:8],
                    "created_at": now,
                    "created_by": interaction.user.id,
                }
            )
            templates.append(template_data)
            action = "saved"

        self.save_templates(interaction.guild.id, templates)

        font_lines = []

        if title_font:
            font_lines.append(f"Title font: `{title_font}`")

        if description_font:
            font_lines.append(f"Description font: `{description_font}`")

        if footer_font:
            font_lines.append(f"Footer font: `{footer_font}`")

        font_text = ""

        if font_lines:
            font_text = "\n" + "\n".join(font_lines)

        await interaction.response.send_message(
            embed=success_embed(f"Embed template `{name}` {action}.{font_text}"),
            ephemeral=True,
        )

    @app_commands.command(name="embed-preview", description="Preview a saved embed template privately.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def embed_preview(self, interaction: discord.Interaction, template_name: str):
        selected = self.find_template(interaction.guild.id, template_name)

        if not selected or not selected.get("enabled", True):
            await interaction.response.send_message(
                embed=error_embed("Could not find an enabled embed template with that name."),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            content=f"Previewing `{selected.get('name')}`:",
            embed=build_custom_embed(selected),
            ephemeral=True,
        )

    @app_commands.command(name="embed-list", description="List saved embed templates.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def embed_list(self, interaction: discord.Interaction):
        templates = self.get_templates(interaction.guild.id)
        templates = [item for item in templates if item.get("enabled", True)]

        if not templates:
            await interaction.response.send_message(
                embed=error_embed("No enabled embed templates are saved for this server."),
                ephemeral=True,
            )
            return

        lines = []

        for item in templates[:20]:
            font_bits = []

            if item.get("title_font"):
                font_bits.append(f"title `{item.get('title_font')}`")

            if item.get("description_font"):
                font_bits.append(f"description `{item.get('description_font')}`")

            if item.get("footer_font"):
                font_bits.append(f"footer `{item.get('footer_font')}`")

            font_text = "None"

            if font_bits:
                font_text = ", ".join(font_bits)

            lines.append(
                f"**{item.get('name', 'Untitled')}**\n"
                f"ID: `{item.get('id')}`\n"
                f"Title: `{item.get('title') or 'No title'}`\n"
                f"Fonts: {font_text}"
            )

        await interaction.response.send_message(
            embed=info_embed("Saved Embed Templates", "\n\n".join(lines)),
            ephemeral=True,
        )

    @app_commands.command(name="embed-send", description="Send a saved embed template to a channel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def embed_send(
        self,
        interaction: discord.Interaction,
        template_name: str,
        channel: discord.TextChannel,
    ):
        selected = self.find_template(interaction.guild.id, template_name)

        if not selected or not selected.get("enabled", True):
            await interaction.response.send_message(
                embed=error_embed("Could not find an enabled embed template with that name."),
                ephemeral=True,
            )
            return

        try:
            embed = build_custom_embed(selected)
            await channel.send(embed=embed)

            await interaction.response.send_message(
                embed=success_embed(f"Embed `{selected.get('name')}` sent to {channel.mention}."),
                ephemeral=True,
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=error_embed("I do not have permission to send messages in that channel."),
                ephemeral=True,
            )
        except discord.HTTPException as error:
            await interaction.response.send_message(
                embed=error_embed(f"Discord rejected the embed: `{error}`"),
                ephemeral=True,
            )

    @app_commands.command(name="embed-delete", description="Disable a saved embed template.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def embed_delete(self, interaction: discord.Interaction, template_name: str):
        templates = self.get_templates(interaction.guild.id)
        selected = None

        for item in templates:
            if str(item.get("name", "")).lower().strip() == template_name.lower().strip():
                selected = item
                break

        if not selected:
            await interaction.response.send_message(
                embed=error_embed("Could not find an embed template with that name."),
                ephemeral=True,
            )
            return

        selected["enabled"] = False
        selected["updated_at"] = datetime.now(timezone.utc).isoformat()
        selected["updated_by"] = interaction.user.id

        self.save_templates(interaction.guild.id, templates)

        await interaction.response.send_message(
            embed=success_embed(f"Embed template `{selected.get('name')}` disabled."),
            ephemeral=True,
        )

    @app_commands.command(name="embed-restore", description="Re-enable a disabled embed template.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def embed_restore(self, interaction: discord.Interaction, template_name: str):
        templates = self.get_templates(interaction.guild.id)
        selected = None

        for item in templates:
            if str(item.get("name", "")).lower().strip() == template_name.lower().strip():
                selected = item
                break

        if not selected:
            await interaction.response.send_message(
                embed=error_embed("Could not find an embed template with that name."),
                ephemeral=True,
            )
            return

        selected["enabled"] = True
        selected["updated_at"] = datetime.now(timezone.utc).isoformat()
        selected["updated_by"] = interaction.user.id

        self.save_templates(interaction.guild.id, templates)

        await interaction.response.send_message(
            embed=success_embed(f"Embed template `{selected.get('name')}` restored."),
            ephemeral=True,
        )

    @embed_send.autocomplete("template_name")
    @embed_preview.autocomplete("template_name")
    @embed_delete.autocomplete("template_name")
    @embed_restore.autocomplete("template_name")
    async def embed_name_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ):
        templates = self.get_templates(interaction.guild.id)
        choices = []

        for item in templates:
            name = str(item.get("name", "")).strip()

            if not name:
                continue

            if current.lower() in name.lower():
                label = name

                if not item.get("enabled", True):
                    label = f"{name} (disabled)"

                choices.append(app_commands.Choice(name=label[:100], value=name[:100]))

        return choices[:25]


async def setup(bot: commands.Bot):
    await bot.add_cog(CustomEmbeds(bot))

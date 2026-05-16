import uuid
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import success_embed, error_embed, info_embed


DEFAULT_CONFESSION_CONFIG = {
    "review_channel_id": None,
    "public_channel_id": None,
    "enabled": True,
    "anonymous_replies_enabled": True,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def short_id() -> str:
    return str(uuid.uuid4())[:8]


def user_can_review(interaction: discord.Interaction, staff_role_id: int | None) -> bool:
    if interaction.user.guild_permissions.manage_guild:
        return True

    if interaction.user.guild_permissions.administrator:
        return True

    if staff_role_id:
        role = interaction.guild.get_role(int(staff_role_id))

        if role and role in interaction.user.roles:
            return True

    return False


def get_confession_config(bot: commands.Bot, guild_id: int) -> dict:
    guild_data = bot.db.get_guild(guild_id)
    config = guild_data.get("confessions")

    changed = False

    if not isinstance(config, dict):
        config = DEFAULT_CONFESSION_CONFIG.copy()
        guild_data["confessions"] = config
        changed = True

    for key, value in DEFAULT_CONFESSION_CONFIG.items():
        if key not in config:
            config[key] = value
            changed = True

    if changed:
        bot.db.update_guild(guild_id, guild_data)

    return config


def save_confession_config(bot: commands.Bot, guild_id: int, config: dict):
    guild_data = bot.db.get_guild(guild_id)
    guild_data["confessions"] = config
    bot.db.update_guild(guild_id, guild_data)


def save_submission(bot: commands.Bot, guild_id: int, submission_id: str, submission: dict):
    data = bot.db.load()
    gid = str(guild_id)

    data["mailbox"].setdefault(gid, {})

    if not isinstance(data["mailbox"][gid], dict):
        data["mailbox"][gid] = {}

    data["mailbox"][gid][submission_id] = submission
    bot.db.save(data)


def get_submission(bot: commands.Bot, guild_id: int, submission_id: str) -> dict | None:
    data = bot.db.load()
    gid = str(guild_id)

    return data["mailbox"].get(gid, {}).get(submission_id)


def add_anonymous_reply(
    bot: commands.Bot,
    guild_id: int,
    submission_id: str,
    user_id: int,
    username: str,
    message: str,
    thread_id: int,
):
    submission = get_submission(bot, guild_id, submission_id)

    if not submission:
        return

    replies = submission.setdefault("anonymous_replies", [])

    replies.append(
        {
            "id": short_id(),
            "user_id": user_id,
            "username": username,
            "message": message,
            "thread_id": thread_id,
            "created_at": utc_now(),
        }
    )

    save_submission(bot, guild_id, submission_id, submission)


def find_submission_id_from_review_message(message: discord.Message) -> str | None:
    if not message.embeds:
        return None

    embed = message.embeds[0]

    for field in embed.fields:
        if field.name.lower().strip() == "submission id":
            return field.value.replace("`", "").strip()

    return None


def find_submission_id_from_public_message(message: discord.Message) -> str | None:
    if not message.embeds:
        return None

    embed = message.embeds[0]

    footer_text = embed.footer.text if embed.footer else ""

    if footer_text and "Submission ID:" in footer_text:
        return footer_text.split("Submission ID:", 1)[1].strip()

    for field in embed.fields:
        if field.name.lower().strip() == "submission id":
            return field.value.replace("`", "").strip()

    return None


async def safe_log(bot: commands.Bot, guild: discord.Guild, embed: discord.Embed):
    log_channel_id = bot.db.get_setting(guild.id, "log_channel_id")

    if not log_channel_id:
        return

    channel = guild.get_channel(int(log_channel_id))

    if not channel:
        return

    try:
        await channel.send(embed=embed)
    except discord.Forbidden:
        return
    except discord.HTTPException:
        return


class AnonymousReplyModal(discord.ui.Modal, title="Anonymous Reply"):
    def __init__(self, bot: commands.Bot, confession_message: discord.Message):
        super().__init__()
        self.bot = bot
        self.confession_message = confession_message

        self.reply = discord.ui.TextInput(
            label="Your anonymous reply",
            placeholder="Type your reply here...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000,
        )

        self.add_item(self.reply)

    async def on_submit(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message(
                embed=error_embed("This only works inside a server."),
                ephemeral=True,
            )
            return

        config = get_confession_config(self.bot, interaction.guild.id)

        if not config.get("anonymous_replies_enabled", True):
            await interaction.response.send_message(
                embed=error_embed("Anonymous replies are currently disabled."),
                ephemeral=True,
            )
            return

        submission_id = find_submission_id_from_public_message(self.confession_message)

        if not submission_id:
            await interaction.response.send_message(
                embed=error_embed("I could not find the confession submission ID."),
                ephemeral=True,
            )
            return

        reply_text = str(self.reply.value).strip()

        if not reply_text:
            await interaction.response.send_message(
                embed=error_embed("Reply cannot be empty."),
                ephemeral=True,
            )
            return

        thread = self.confession_message.thread

        try:
            if thread is None:
                thread = await self.confession_message.create_thread(
                    name=f"confession-{submission_id}-replies",
                    auto_archive_duration=1440,
                )

            reply_embed = discord.Embed(
                title="Anonymous Reply",
                description=reply_text,
                color=discord.Color.blurple(),
            )
            reply_embed.set_footer(text=f"Reply to confession {submission_id}")

            await thread.send(embed=reply_embed)

        except discord.Forbidden:
            await interaction.response.send_message(
                embed=error_embed(
                    "I do not have permission to create or send in threads here. "
                    "I need Create Public Threads and Send Messages in Threads."
                ),
                ephemeral=True,
            )
            return
        except discord.HTTPException as error:
            await interaction.response.send_message(
                embed=error_embed(f"Discord rejected the anonymous reply: `{error}`"),
                ephemeral=True,
            )
            return

        add_anonymous_reply(
            self.bot,
            interaction.guild.id,
            submission_id,
            interaction.user.id,
            str(interaction.user),
            reply_text,
            thread.id,
        )

        await interaction.response.send_message(
            embed=success_embed("Your anonymous reply was posted in the thread."),
            ephemeral=True,
        )

        log_embed = info_embed(
            "Anonymous Reply Submitted",
            f"An anonymous reply was added to confession `{submission_id}`."
        )
        await safe_log(self.bot, interaction.guild, log_embed)


class ConfessionPublicView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(
        label="Reply Anonymously",
        style=discord.ButtonStyle.secondary,
        custom_id="centari_confession_reply",
    )
    async def reply_anonymously(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.guild:
            await interaction.response.send_message(
                embed=error_embed("This only works inside a server."),
                ephemeral=True,
            )
            return

        config = get_confession_config(self.bot, interaction.guild.id)

        if not config.get("anonymous_replies_enabled", True):
            await interaction.response.send_message(
                embed=error_embed("Anonymous replies are currently disabled."),
                ephemeral=True,
            )
            return

        await interaction.response.send_modal(
            AnonymousReplyModal(self.bot, interaction.message)
        )


class ConfessionReviewView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(
        label="Approve",
        style=discord.ButtonStyle.success,
        custom_id="centari_confession_approve",
    )
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        staff_role_id = self.bot.db.get_setting(interaction.guild.id, "staff_role_id")

        if not user_can_review(interaction, staff_role_id):
            await interaction.response.send_message(
                embed=error_embed("Only staff can approve confessions."),
                ephemeral=True,
            )
            return

        submission_id = find_submission_id_from_review_message(interaction.message)

        if not submission_id:
            await interaction.response.send_message(
                embed=error_embed("I could not find the submission ID on this message."),
                ephemeral=True,
            )
            return

        submission = get_submission(self.bot, interaction.guild.id, submission_id)

        if not submission:
            await interaction.response.send_message(
                embed=error_embed("I could not find that submission in the database."),
                ephemeral=True,
            )
            return

        if submission.get("status") == "approved":
            await interaction.response.send_message(
                embed=error_embed("This confession was already approved."),
                ephemeral=True,
            )
            return

        config = get_confession_config(self.bot, interaction.guild.id)
        public_channel_id = config.get("public_channel_id")

        if not public_channel_id:
            await interaction.response.send_message(
                embed=error_embed("No public confession channel has been configured."),
                ephemeral=True,
            )
            return

        public_channel = interaction.guild.get_channel(int(public_channel_id))

        if not public_channel:
            await interaction.response.send_message(
                embed=error_embed("I cannot find the configured public confession channel."),
                ephemeral=True,
            )
            return

        public_embed = discord.Embed(
            title="Anonymous Confession",
            description=submission.get("message", ""),
            color=discord.Color.purple(),
        )
        public_embed.set_footer(text=f"Submission ID: {submission_id}")

        try:
            sent_message = await public_channel.send(
                embed=public_embed,
                view=ConfessionPublicView(self.bot),
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=error_embed("I do not have permission to send in the public confession channel."),
                ephemeral=True,
            )
            return
        except discord.HTTPException as error:
            await interaction.response.send_message(
                embed=error_embed(f"Discord rejected the confession post: `{error}`"),
                ephemeral=True,
            )
            return

        submission["status"] = "approved"
        submission["approved_by"] = interaction.user.id
        submission["approved_at"] = utc_now()
        submission["public_channel_id"] = public_channel.id
        submission["public_message_id"] = sent_message.id

        save_submission(self.bot, interaction.guild.id, submission_id, submission)

        updated_embed = interaction.message.embeds[0]
        updated_embed.color = discord.Color.green()
        updated_embed.add_field(name="Status", value=f"Approved by {interaction.user.mention}", inline=False)

        await interaction.message.edit(embed=updated_embed, view=None)

        await interaction.response.send_message(
            embed=success_embed(f"Confession `{submission_id}` approved and posted."),
            ephemeral=True,
        )

        log_embed = info_embed(
            "Confession Approved",
            f"Submission `{submission_id}` was approved by {interaction.user.mention}."
        )
        await safe_log(self.bot, interaction.guild, log_embed)

    @discord.ui.button(
        label="Deny",
        style=discord.ButtonStyle.danger,
        custom_id="centari_confession_deny",
    )
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        staff_role_id = self.bot.db.get_setting(interaction.guild.id, "staff_role_id")

        if not user_can_review(interaction, staff_role_id):
            await interaction.response.send_message(
                embed=error_embed("Only staff can deny confessions."),
                ephemeral=True,
            )
            return

        submission_id = find_submission_id_from_review_message(interaction.message)

        if not submission_id:
            await interaction.response.send_message(
                embed=error_embed("I could not find the submission ID on this message."),
                ephemeral=True,
            )
            return

        submission = get_submission(self.bot, interaction.guild.id, submission_id)

        if not submission:
            await interaction.response.send_message(
                embed=error_embed("I could not find that submission in the database."),
                ephemeral=True,
            )
            return

        if submission.get("status") == "approved":
            await interaction.response.send_message(
                embed=error_embed("This confession was already approved, so I will not deny it."),
                ephemeral=True,
            )
            return

        submission["status"] = "denied"
        submission["denied_by"] = interaction.user.id
        submission["denied_at"] = utc_now()

        save_submission(self.bot, interaction.guild.id, submission_id, submission)

        updated_embed = interaction.message.embeds[0]
        updated_embed.color = discord.Color.red()
        updated_embed.add_field(name="Status", value=f"Denied by {interaction.user.mention}", inline=False)

        await interaction.message.edit(embed=updated_embed, view=None)

        await interaction.response.send_message(
            embed=success_embed(f"Confession `{submission_id}` denied."),
            ephemeral=True,
        )

        log_embed = info_embed(
            "Confession Denied",
            f"Submission `{submission_id}` was denied by {interaction.user.mention}."
        )
        await safe_log(self.bot, interaction.guild, log_embed)


class ConfessionGroup(app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__(name="confession", description="Anonymous confession tools.")
        self.bot = bot

    @app_commands.command(name="config", description="Configure confession channels and settings.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def config(
        self,
        interaction: discord.Interaction,
        review_channel: discord.TextChannel | None = None,
        public_channel: discord.TextChannel | None = None,
        enabled: bool | None = None,
        anonymous_replies_enabled: bool | None = None,
    ):
        config = get_confession_config(self.bot, interaction.guild.id)

        if review_channel:
            config["review_channel_id"] = review_channel.id

        if public_channel:
            config["public_channel_id"] = public_channel.id

        if enabled is not None:
            config["enabled"] = enabled

        if anonymous_replies_enabled is not None:
            config["anonymous_replies_enabled"] = anonymous_replies_enabled

        save_confession_config(self.bot, interaction.guild.id, config)

        review_value = f"<#{config['review_channel_id']}>" if config.get("review_channel_id") else "Not set"
        public_value = f"<#{config['public_channel_id']}>" if config.get("public_channel_id") else "Not set"

        description = (
            f"**Enabled:** `{config.get('enabled', True)}`\n"
            f"**Anonymous Replies Enabled:** `{config.get('anonymous_replies_enabled', True)}`\n"
            f"**Review Channel:** {review_value}\n"
            f"**Public Channel:** {public_value}"
        )

        await interaction.response.send_message(
            embed=success_embed(f"Confession config updated.\n\n{description}"),
            ephemeral=True,
        )

    @app_commands.command(name="view-config", description="View confession configuration.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def view_config(self, interaction: discord.Interaction):
        config = get_confession_config(self.bot, interaction.guild.id)

        review_value = f"<#{config['review_channel_id']}>" if config.get("review_channel_id") else "Not set"
        public_value = f"<#{config['public_channel_id']}>" if config.get("public_channel_id") else "Not set"

        description = (
            f"**Enabled:** `{config.get('enabled', True)}`\n"
            f"**Anonymous Replies Enabled:** `{config.get('anonymous_replies_enabled', True)}`\n"
            f"**Review Channel:** {review_value}\n"
            f"**Public Channel:** {public_value}"
        )

        await interaction.response.send_message(
            embed=info_embed("Confession Config", description),
            ephemeral=True,
        )

    @app_commands.command(name="submit", description="Submit an anonymous confession for staff review.")
    async def submit(self, interaction: discord.Interaction, message: str):
        config = get_confession_config(self.bot, interaction.guild.id)

        if not config.get("enabled", True):
            await interaction.response.send_message(
                embed=error_embed("Anonymous confessions are currently disabled."),
                ephemeral=True,
            )
            return

        review_channel_id = config.get("review_channel_id")

        if not review_channel_id:
            await interaction.response.send_message(
                embed=error_embed("No confession review channel has been configured yet."),
                ephemeral=True,
            )
            return

        review_channel = interaction.guild.get_channel(int(review_channel_id))

        if not review_channel:
            await interaction.response.send_message(
                embed=error_embed("I cannot find the configured confession review channel."),
                ephemeral=True,
            )
            return

        message = message.strip()

        if not message:
            await interaction.response.send_message(
                embed=error_embed("Confession message cannot be empty."),
                ephemeral=True,
            )
            return

        if len(message) > 1800:
            await interaction.response.send_message(
                embed=error_embed("Please keep confessions under 1800 characters."),
                ephemeral=True,
            )
            return

        submission_id = short_id()

        submission = {
            "id": submission_id,
            "guild_id": interaction.guild.id,
            "user_id": interaction.user.id,
            "username": str(interaction.user),
            "message": message,
            "status": "pending",
            "created_at": utc_now(),
            "anonymous_replies": [],
        }

        save_submission(self.bot, interaction.guild.id, submission_id, submission)

        review_embed = discord.Embed(
            title="Anonymous Confession Review",
            description=message,
            color=discord.Color.gold(),
        )
        review_embed.add_field(name="Submission ID", value=f"`{submission_id}`", inline=True)
        review_embed.add_field(name="Submitted By", value=f"{interaction.user.mention}\n`{interaction.user.id}`", inline=True)
        review_embed.add_field(name="Status", value="Pending review", inline=False)
        review_embed.set_footer(text="Approve posts anonymously. Deny keeps it private.")

        try:
            await review_channel.send(
                embed=review_embed,
                view=ConfessionReviewView(self.bot),
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=error_embed("I do not have permission to send in the confession review channel."),
                ephemeral=True,
            )
            return
        except discord.HTTPException as error:
            await interaction.response.send_message(
                embed=error_embed(f"Discord rejected the review post: `{error}`"),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            embed=success_embed("Your anonymous confession was submitted for review."),
            ephemeral=True,
        )

        log_embed = info_embed(
            "Confession Submitted",
            f"Submission `{submission_id}` was submitted for staff review."
        )
        await safe_log(self.bot, interaction.guild, log_embed)


class Confessions(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.tree.add_command(ConfessionGroup(bot))

    async def cog_load(self):
        self.bot.add_view(ConfessionReviewView(self.bot))
        self.bot.add_view(ConfessionPublicView(self.bot))


async def setup(bot: commands.Bot):
    await bot.add_cog(Confessions(bot))

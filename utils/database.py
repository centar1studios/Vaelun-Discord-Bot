import json
import os
import shutil
from datetime import datetime
from typing import Any, Dict, Optional


DEFAULT_EIGHT_BALL_ANSWERS = [
    "Yes.",
    "No.",
    "Maybe.",
    "Ask again later.",
    "Absolutely.",
    "Probably not.",
    "The stars are being weird about this one.",
]


DEFAULT_DATABASE = {
    "guilds": {},
    "warnings": {},
    "tickets": {},
    "levels": {},
    "economy": {},
    "forms": {},
    "resources": {},
    "suggestions": {},
    "mailbox": {},
    "saved_roles": {},
    "backups": {},
    "study": {},
}


DEFAULT_GUILD = {
    "persona": {
        "name": "Centari Studios",
        "bio": "A free all-in-one Discord bot for moderation, tickets, safety, community tools, and creative server management.",
        "avatar_url": None,
        "color": "#9B7BFF",
        "footer": "Powered by Centari Studios",
    },
    "settings": {
        "staff_role_id": None,
        "log_channel_id": None,
        "ticket_category_id": None,
        "transcript_channel_id": None,
        "welcome_channel_id": None,
        "leave_channel_id": None,
        "ban_log_channel_id": None,
        "verified_role_id": None,
        "autorole_id": None,
        "suggestion_channel_id": None,
        "mailbox_review_channel_id": None,
        "resource_channel_id": None,
    },
    "welcome": {
        "enabled": False,
        "message": "Welcome {user} to {server}!",
    },
    "leave": {
        "enabled": False,
        "message": "{user} left {server}.",
    },
    "automod": {
        "enabled": True,
        "mode": "balanced",
        "blocked_words": [],
        "block_invites": True,
        "block_mass_mentions": True,
        "block_spam": True,
    },
    "leveling": {
        "enabled": True,
        "xp_per_message": 10,
        "cooldown_seconds": 60,
    },
    "economy": {
        "enabled": True,
        "daily_amount": 100,
    },
    "verification": {
        "enabled": False,
        "message": "Click the button below to verify.",
    },
    "eight_ball": {
        "answers": DEFAULT_EIGHT_BALL_ANSWERS.copy(),
    },
}


class Database:
    def __init__(self, path: str):
        self.path = path
        self.ensure_file()
        self.validate_and_repair()

    def ensure_file(self):
        folder = os.path.dirname(self.path)

        if folder and not os.path.exists(folder):
            os.makedirs(folder)

        if not os.path.exists(self.path):
            self.save(DEFAULT_DATABASE)

    def backup_file(self):
        if not os.path.exists(self.path):
            return

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = f"{self.path}.auto-backup-{timestamp}"

        shutil.copy2(self.path, backup_path)

    def load_raw(self) -> Dict[str, Any]:
        with open(self.path, "r", encoding="utf-8") as file:
            return json.load(file)

    def load(self) -> Dict[str, Any]:
        data = self.load_raw()
        changed = False

        for key, default_value in DEFAULT_DATABASE.items():
            if key not in data:
                data[key] = default_value.copy()
                changed = True

        for key in DEFAULT_DATABASE:
            if isinstance(data.get(key), list):
                if len(data[key]) == 0:
                    data[key] = {}
                    changed = True
                else:
                    raise TypeError(
                        f"Database section '{key}' is a non-empty list. "
                        f"This needs manual conversion before the bot can safely continue."
                    )

            if not isinstance(data.get(key), dict):
                raise TypeError(
                    f"Database section '{key}' must be a dict, got {type(data.get(key)).__name__}."
                )

        if changed:
            self.save(data)

        return data

    def validate_and_repair(self):
        try:
            data = self.load_raw()
        except json.JSONDecodeError as error:
            raise RuntimeError(
                f"database.json is not valid JSON: {error}"
            ) from error

        changed = False

        for key, default_value in DEFAULT_DATABASE.items():
            if key not in data:
                data[key] = default_value.copy()
                changed = True

            elif isinstance(data[key], list):
                if len(data[key]) == 0:
                    data[key] = {}
                    changed = True
                else:
                    raise RuntimeError(
                        f"Database section '{key}' is a non-empty list. "
                        f"Back up database.json and convert it manually."
                    )

            elif not isinstance(data[key], dict):
                raise RuntimeError(
                    f"Database section '{key}' must be a dict, got {type(data[key]).__name__}."
                )

        if changed:
            self.backup_file()
            self.save(data)

    def save(self, data: Dict[str, Any]):
        with open(self.path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)

    def make_default_guild(self) -> Dict[str, Any]:
        return {
            "persona": DEFAULT_GUILD["persona"].copy(),
            "settings": DEFAULT_GUILD["settings"].copy(),
            "welcome": DEFAULT_GUILD["welcome"].copy(),
            "leave": DEFAULT_GUILD["leave"].copy(),
            "automod": DEFAULT_GUILD["automod"].copy(),
            "leveling": DEFAULT_GUILD["leveling"].copy(),
            "economy": DEFAULT_GUILD["economy"].copy(),
            "verification": DEFAULT_GUILD["verification"].copy(),
            "eight_ball": {
                "answers": DEFAULT_EIGHT_BALL_ANSWERS.copy(),
            },
        }

    def repair_guild_data(self, guild_data: Dict[str, Any]) -> bool:
        changed = False

        for section, default_section in DEFAULT_GUILD.items():
            if section not in guild_data or not isinstance(guild_data[section], dict):
                guild_data[section] = default_section.copy()

                if section == "eight_ball":
                    guild_data[section] = {
                        "answers": DEFAULT_EIGHT_BALL_ANSWERS.copy(),
                    }

                changed = True
                continue

            for key, default_value in default_section.items():
                if key not in guild_data[section]:
                    if section == "eight_ball" and key == "answers":
                        guild_data[section][key] = DEFAULT_EIGHT_BALL_ANSWERS.copy()
                    else:
                        guild_data[section][key] = default_value

                    changed = True

        if "eight_ball" in guild_data:
            answers = guild_data["eight_ball"].get("answers")

            if not isinstance(answers, list) or not answers:
                guild_data["eight_ball"]["answers"] = DEFAULT_EIGHT_BALL_ANSWERS.copy()
                changed = True

        return changed

    def get_guild(self, guild_id: int) -> Dict[str, Any]:
        data = self.load()
        gid = str(guild_id)

        if gid not in data["guilds"]:
            data["guilds"][gid] = self.make_default_guild()
            self.save(data)
            return data["guilds"][gid]

        guild_data = data["guilds"][gid]
        changed = self.repair_guild_data(guild_data)

        if changed:
            data["guilds"][gid] = guild_data
            self.save(data)

        return guild_data

    def update_guild(self, guild_id: int, guild_data: Dict[str, Any]):
        data = self.load()
        data["guilds"][str(guild_id)] = guild_data
        self.save(data)

    def get_setting(self, guild_id: int, key: str) -> Any:
        return self.get_guild(guild_id)["settings"].get(key)

    def update_setting(self, guild_id: int, key: str, value: Any):
        guild_data = self.get_guild(guild_id)
        guild_data["settings"][key] = value
        self.update_guild(guild_id, guild_data)

    def get_persona(self, guild_id: int) -> Dict[str, Any]:
        return self.get_guild(guild_id)["persona"]

    def update_persona(self, guild_id: int, key: str, value: Any):
        guild_data = self.get_guild(guild_id)
        guild_data["persona"][key] = value
        self.update_guild(guild_id, guild_data)

    def get_eight_ball_answers(self, guild_id: int) -> list[str]:
        guild_data = self.get_guild(guild_id)
        answers = guild_data["eight_ball"].get("answers", [])

        if not isinstance(answers, list) or not answers:
            answers = DEFAULT_EIGHT_BALL_ANSWERS.copy()
            guild_data["eight_ball"]["answers"] = answers
            self.update_guild(guild_id, guild_data)

        return answers

    def add_eight_ball_answer(self, guild_id: int, answer: str) -> bool:
        answer = answer.strip()

        if not answer:
            return False

        guild_data = self.get_guild(guild_id)
        answers = guild_data["eight_ball"].setdefault("answers", DEFAULT_EIGHT_BALL_ANSWERS.copy())

        if answer in answers:
            return False

        answers.append(answer)
        self.update_guild(guild_id, guild_data)
        return True

    def remove_eight_ball_answer(self, guild_id: int, answer: str) -> bool:
        answer = answer.strip()
        guild_data = self.get_guild(guild_id)
        answers = guild_data["eight_ball"].setdefault("answers", DEFAULT_EIGHT_BALL_ANSWERS.copy())

        for existing in answers:
            if existing.lower() == answer.lower():
                answers.remove(existing)
                self.update_guild(guild_id, guild_data)
                return True

        return False

    def reset_eight_ball_answers(self, guild_id: int):
        guild_data = self.get_guild(guild_id)
        guild_data["eight_ball"]["answers"] = DEFAULT_EIGHT_BALL_ANSWERS.copy()
        self.update_guild(guild_id, guild_data)

    def add_warning(self, guild_id: int, user_id: int, moderator_id: int, reason: str):
        data = self.load()
        gid = str(guild_id)
        uid = str(user_id)

        data["warnings"].setdefault(gid, {})
        data["warnings"][gid].setdefault(uid, [])

        warning = {
            "moderator_id": moderator_id,
            "reason": reason,
        }

        data["warnings"][gid][uid].append(warning)
        self.save(data)
        return warning

    def get_warnings(self, guild_id: int, user_id: int):
        data = self.load()
        return data["warnings"].get(str(guild_id), {}).get(str(user_id), [])

    def create_ticket(self, guild_id: int, channel_id: int, user_id: int, ticket_type: str):
        data = self.load()

        data["tickets"][str(channel_id)] = {
            "guild_id": guild_id,
            "channel_id": channel_id,
            "user_id": user_id,
            "ticket_type": ticket_type,
            "status": "open",
            "claimed_by": None,
        }

        self.save(data)

    def get_ticket(self, channel_id: int) -> Optional[Dict[str, Any]]:
        data = self.load()
        return data["tickets"].get(str(channel_id))

    def update_ticket(self, channel_id: int, ticket_data: Dict[str, Any]):
        data = self.load()
        data["tickets"][str(channel_id)] = ticket_data
        self.save(data)

    def close_ticket(self, channel_id: int):
        ticket = self.get_ticket(channel_id)

        if ticket:
            ticket["status"] = "closed"
            self.update_ticket(channel_id, ticket)

    def add_xp(self, guild_id: int, user_id: int, amount: int):
        data = self.load()
        gid = str(guild_id)
        uid = str(user_id)

        data["levels"].setdefault(gid, {})
        data["levels"][gid].setdefault(uid, {"xp": 0, "level": 1, "last_message": 0})

        data["levels"][gid][uid]["xp"] += amount

        xp = data["levels"][gid][uid]["xp"]
        new_level = max(1, xp // 100 + 1)
        leveled_up = new_level > data["levels"][gid][uid]["level"]

        data["levels"][gid][uid]["level"] = new_level

        self.save(data)
        return data["levels"][gid][uid], leveled_up

    def get_level(self, guild_id: int, user_id: int):
        data = self.load()
        return data["levels"].get(str(guild_id), {}).get(
            str(user_id),
            {"xp": 0, "level": 1, "last_message": 0},
        )

    def add_money(self, guild_id: int, user_id: int, amount: int):
        data = self.load()
        gid = str(guild_id)
        uid = str(user_id)

        data["economy"].setdefault(gid, {})
        data["economy"][gid].setdefault(uid, {"balance": 0, "last_daily": 0})

        data["economy"][gid][uid]["balance"] += amount

        self.save(data)
        return data["economy"][gid][uid]

    def get_money(self, guild_id: int, user_id: int):
        data = self.load()
        return data["economy"].get(str(guild_id), {}).get(
            str(user_id),
            {"balance": 0, "last_daily": 0},
        )

    def set_daily_time(self, guild_id: int, user_id: int, timestamp: float):
        data = self.load()
        gid = str(guild_id)
        uid = str(user_id)

        data["economy"].setdefault(gid, {})
        data["economy"][gid].setdefault(uid, {"balance": 0, "last_daily": 0})
        data["economy"][gid][uid]["last_daily"] = timestamp

        self.save(data)

    def save_roles(self, guild_id: int, user_id: int, role_ids: list[int]):
        data = self.load()

        data["saved_roles"].setdefault(str(guild_id), {})
        data["saved_roles"][str(guild_id)][str(user_id)] = role_ids

        self.save(data)

    def get_saved_roles(self, guild_id: int, user_id: int) -> list[int]:
        data = self.load()
        return data["saved_roles"].get(str(guild_id), {}).get(str(user_id), [])

    def add_resource(self, guild_id: int, title: str, body: str, tags: str):
        data = self.load()
        gid = str(guild_id)

        data["resources"].setdefault(gid, [])

        resource_id = len(data["resources"][gid]) + 1

        data["resources"][gid].append(
            {
                "id": resource_id,
                "title": title,
                "body": body,
                "tags": tags,
            }
        )

        self.save(data)
        return resource_id

    def search_resources(self, guild_id: int, query: str):
        data = self.load()
        resources = data["resources"].get(str(guild_id), [])
        query = query.lower()

        return [
            item
            for item in resources
            if query in item["title"].lower()
            or query in item["body"].lower()
            or query in item["tags"].lower()
        ]

    def add_suggestion(self, guild_id: int, user_id: int, text: str):
        data = self.load()
        gid = str(guild_id)

        data["suggestions"].setdefault(gid, [])

        suggestion_id = len(data["suggestions"][gid]) + 1

        data["suggestions"][gid].append(
            {
                "id": suggestion_id,
                "user_id": user_id,
                "text": text,
                "status": "Under Review",
            }
        )

        self.save(data)
        return suggestion_id

    def create_backup(self, guild_id: int, snapshot: Dict[str, Any]):
        data = self.load()
        gid = str(guild_id)

        data["backups"].setdefault(gid, [])

        backup_id = len(data["backups"][gid]) + 1
        snapshot["id"] = backup_id

        data["backups"][gid].append(snapshot)

        self.save(data)
        return backup_id

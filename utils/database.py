import json
import os
from typing import Any, Dict, Optional


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
    "study": {}
}


DEFAULT_GUILD = {
    "persona": {
        "name": "Centari Studios",
        "bio": "A free all-in-one Discord bot for moderation, tickets, safety, community tools, and creative server management.",
        "avatar_url": None,
        "color": "#9B7BFF",
        "footer": "Powered by Centari Studios"
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
        "resource_channel_id": None
    },
    "welcome": {
        "enabled": False,
        "message": "Welcome {user} to {server}!"
    },
    "leave": {
        "enabled": False,
        "message": "{user} left {server}."
    },
    "automod": {
        "enabled": True,
        "mode": "balanced",
        "blocked_words": [],
        "block_invites": True,
        "block_mass_mentions": True,
        "block_spam": True
    },
    "leveling": {
        "enabled": True,
        "xp_per_message": 10,
        "cooldown_seconds": 60
    },
    "economy": {
        "enabled": True,
        "daily_amount": 100
    },
    "verification": {
        "enabled": False,
        "message": "Click the button below to verify."
    }
}


class Database:
    def __init__(self, path: str):
        self.path = path
        self.ensure_file()

    def ensure_file(self):
        folder = os.path.dirname(self.path)

        if folder and not os.path.exists(folder):
            os.makedirs(folder)

        if not os.path.exists(self.path):
            self.save(DEFAULT_DATABASE)

    def load(self) -> Dict[str, Any]:
        with open(self.path, "r", encoding="utf-8") as file:
            data = json.load(file)

        for key, value in DEFAULT_DATABASE.items():
            if key not in data:
                data[key] = value

        return data

    def save(self, data: Dict[str, Any]):
        with open(self.path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)

    def get_guild(self, guild_id: int) -> Dict[str, Any]:
        data = self.load()
        gid = str(guild_id)

        if gid not in data["guilds"]:
            data["guilds"][gid] = DEFAULT_GUILD.copy()
            data["guilds"][gid]["persona"] = DEFAULT_GUILD["persona"].copy()
            data["guilds"][gid]["settings"] = DEFAULT_GUILD["settings"].copy()
            data["guilds"][gid]["welcome"] = DEFAULT_GUILD["welcome"].copy()
            data["guilds"][gid]["leave"] = DEFAULT_GUILD["leave"].copy()
            data["guilds"][gid]["automod"] = DEFAULT_GUILD["automod"].copy()
            data["guilds"][gid]["leveling"] = DEFAULT_GUILD["leveling"].copy()
            data["guilds"][gid]["economy"] = DEFAULT_GUILD["economy"].copy()
            data["guilds"][gid]["verification"] = DEFAULT_GUILD["verification"].copy()
            self.save(data)

        return data["guilds"][gid]

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

    def add_warning(self, guild_id: int, user_id: int, moderator_id: int, reason: str):
        data = self.load()
        gid = str(guild_id)
        uid = str(user_id)

        data["warnings"].setdefault(gid, {})
        data["warnings"][gid].setdefault(uid, [])

        warning = {
            "moderator_id": moderator_id,
            "reason": reason
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
            "claimed_by": None
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
        return data["levels"].get(str(guild_id), {}).get(str(user_id), {"xp": 0, "level": 1})

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
        return data["economy"].get(str(guild_id), {}).get(str(user_id), {"balance": 0, "last_daily": 0})

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

        data["resources"][gid].append({
            "id": resource_id,
            "title": title,
            "body": body,
            "tags": tags
        })

        self.save(data)
        return resource_id

    def search_resources(self, guild_id: int, query: str):
        data = self.load()
        resources = data["resources"].get(str(guild_id), [])
        query = query.lower()

        return [
            item for item in resources
            if query in item["title"].lower()
            or query in item["body"].lower()
            or query in item["tags"].lower()
        ]

    def add_suggestion(self, guild_id: int, user_id: int, text: str):
        data = self.load()
        gid = str(guild_id)
        data["suggestions"].setdefault(gid, [])

        suggestion_id = len(data["suggestions"][gid]) + 1

        data["suggestions"][gid].append({
            "id": suggestion_id,
            "user_id": user_id,
            "text": text,
            "status": "Under Review"
        })

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

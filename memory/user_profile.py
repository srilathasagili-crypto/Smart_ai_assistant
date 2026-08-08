"""Long-term, cross-session user memory.

This is separate from memory/chat_history.py on purpose:
- chat_history.py (SqliteSaver) stores the *message log* for a thread_id.
- user_profile.py stores durable *facts about the user* (name, preferences,
  favourite technologies) keyed by a stable user_id, independent of any one
  conversation thread.

Both use SQLite in the same temp directory so no new infra is required.
"""
import json
import os
import sqlite3
import tempfile

from graph.logger import get_logger

logger = get_logger("memory.user_profile")

_DB_DIR = os.path.join(tempfile.gettempdir(), "intelligent-ai-assistant")
_DB_PATH = os.path.join(_DB_DIR, "user_profiles.sqlite")


def _connect() -> sqlite3.Connection:
    os.makedirs(_DB_DIR, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS profiles (
            user_id TEXT PRIMARY KEY,
            name TEXT,
            preferences TEXT NOT NULL DEFAULT '{}'
        )"""
    )
    return conn


def get_profile(user_id: str) -> dict:
    """Returns {'name': str|None, 'preferences': dict}. Never raises."""
    try:
        with _connect() as conn:
            row = conn.execute(
                "SELECT name, preferences FROM profiles WHERE user_id = ?", (user_id,)
            ).fetchone()
        if not row:
            return {"name": None, "preferences": {}}
        name, prefs_json = row
        try:
            preferences = json.loads(prefs_json or "{}")
        except json.JSONDecodeError:
            preferences = {}
        return {"name": name, "preferences": preferences}
    except sqlite3.Error:
        logger.exception(f"Failed to read profile for user_id={user_id!r}")
        return {"name": None, "preferences": {}}


def update_profile(user_id: str, name: str | None = None, preferences: dict | None = None) -> dict:
    """Merges new name/preferences into the existing profile. Never raises."""
    current = get_profile(user_id)
    new_name = name if name else current["name"]
    new_preferences = {**current["preferences"], **(preferences or {})}

    try:
        with _connect() as conn:
            conn.execute(
                """INSERT INTO profiles (user_id, name, preferences) VALUES (?, ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET
                       name = excluded.name,
                       preferences = excluded.preferences""",
                (user_id, new_name, json.dumps(new_preferences)),
            )
        logger.info(f"Updated profile for user_id={user_id!r}")
    except sqlite3.Error:
        logger.exception(f"Failed to update profile for user_id={user_id!r}")

    return {"name": new_name, "preferences": new_preferences}


def format_profile_for_prompt(user_id: str) -> str:
    """Small helper used by graph/nodes.py to inject known facts into the system prompt."""
    profile = get_profile(user_id)
    if not profile["name"] and not profile["preferences"]:
        return ""
    parts = []
    if profile["name"]:
        parts.append(f"The user's name is {profile['name']}.")
    if profile["preferences"]:
        prefs_str = "; ".join(f"{k}: {v}" for k, v in profile["preferences"].items())
        parts.append(f"Known preferences — {prefs_str}.")
    return " ".join(parts)

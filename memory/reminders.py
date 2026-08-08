"""Persistent reminder storage.

Note on "notify when due" (see tools/reminders_tool.py and app.py):
Streamlit apps only run code while a user has the page open and is interacting
with it — there is no background process on Streamlit Cloud / HF Spaces free
tiers. So "notification" here means: every time the app reruns (page load or
a new chat message), we check for reminders that are now due and haven't been
shown yet, and surface them as a banner. This is honest, zero-infra behavior.
For true push notifications you'd need an external scheduler (e.g. a cron job
calling a notification webhook) — see README "Future improvements".
"""
import os
import sqlite3
import tempfile
import uuid
from datetime import datetime

from graph.logger import get_logger

logger = get_logger("memory.reminders")

_DB_DIR = os.path.join(tempfile.gettempdir(), "intelligent-ai-assistant")
_DB_PATH = os.path.join(_DB_DIR, "reminders.sqlite")


def _connect() -> sqlite3.Connection:
    os.makedirs(_DB_DIR, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS reminders (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            text TEXT NOT NULL,
            due_at TEXT NOT NULL,
            notified INTEGER NOT NULL DEFAULT 0
        )"""
    )
    return conn


def create_reminder(user_id: str, text: str, due_at_iso: str) -> dict:
    reminder_id = str(uuid.uuid4())[:8]
    try:
        with _connect() as conn:
            conn.execute(
                "INSERT INTO reminders (id, user_id, text, due_at, notified) VALUES (?, ?, ?, ?, 0)",
                (reminder_id, user_id, text, due_at_iso),
            )
        logger.info(f"Created reminder {reminder_id} for user_id={user_id!r}")
        return {"id": reminder_id, "text": text, "due_at": due_at_iso}
    except sqlite3.Error:
        logger.exception("Failed to create reminder")
        return {}


def list_reminders(user_id: str) -> list[dict]:
    try:
        with _connect() as conn:
            rows = conn.execute(
                "SELECT id, text, due_at, notified FROM reminders WHERE user_id = ? ORDER BY due_at ASC",
                (user_id,),
            ).fetchall()
        return [{"id": r[0], "text": r[1], "due_at": r[2], "notified": bool(r[3])} for r in rows]
    except sqlite3.Error:
        logger.exception("Failed to list reminders")
        return []


def delete_reminder(user_id: str, reminder_id: str) -> bool:
    try:
        with _connect() as conn:
            cur = conn.execute(
                "DELETE FROM reminders WHERE id = ? AND user_id = ?", (reminder_id, user_id)
            )
        deleted = cur.rowcount > 0
        if deleted:
            logger.info(f"Deleted reminder {reminder_id} for user_id={user_id!r}")
        return deleted
    except sqlite3.Error:
        logger.exception("Failed to delete reminder")
        return False


def get_due_unnotified(user_id: str) -> list[dict]:
    """Reminders whose due time has passed and haven't been shown yet. Marks them notified."""
    now = datetime.now().isoformat()
    try:
        with _connect() as conn:
            rows = conn.execute(
                "SELECT id, text, due_at FROM reminders WHERE user_id = ? AND notified = 0 AND due_at <= ?",
                (user_id, now),
            ).fetchall()
            if rows:
                ids = [r[0] for r in rows]
                conn.executemany("UPDATE reminders SET notified = 1 WHERE id = ?", [(i,) for i in ids])
        return [{"id": r[0], "text": r[1], "due_at": r[2]} for r in rows]
    except sqlite3.Error:
        logger.exception("Failed to check due reminders")
        return []

import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone

from graph.logger import get_logger

logger = get_logger("security.db")

_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
_DB_PATH = os.path.join(_DB_DIR, "app.db")

# sqlite3 connections aren't safe to share across threads, and Streamlit's
# script-rerun model can touch this from more than one thread — serialize
# all access with a simple lock rather than fighting connection-per-thread.
_lock = threading.Lock()


def _connect() -> sqlite3.Connection:
    os.makedirs(_DB_DIR, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


@contextmanager
def get_conn():
    with _lock:
        conn = _connect()
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


def init_db():
    """Creates tables if they don't exist. Safe to call on every app startup."""
    with get_conn() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                email TEXT,
                name TEXT,
                is_admin INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                last_login TEXT
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS request_log (
                user_id TEXT NOT NULL,
                ts REAL NOT NULL
            )"""
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_request_log_user_ts ON request_log(user_id, ts)")
        conn.execute(
            """CREATE TABLE IF NOT EXISTS daily_usage (
                user_id TEXT NOT NULL,
                date TEXT NOT NULL,
                request_count INTEGER NOT NULL DEFAULT 0,
                prompt_tokens INTEGER NOT NULL DEFAULT 0,
                completion_tokens INTEGER NOT NULL DEFAULT 0,
                total_tokens INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, date)
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS usage_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                ts TEXT NOT NULL,
                model TEXT,
                prompt_tokens INTEGER,
                completion_tokens INTEGER,
                total_tokens INTEGER
            )"""
        )
    logger.info(f"Database ready at {_DB_PATH}")


def upsert_user(user_id: str, email: str | None, name: str | None, is_admin: bool):
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO users (user_id, email, name, is_admin, created_at, last_login)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
                   email = excluded.email,
                   name = excluded.name,
                   is_admin = excluded.is_admin,
                   last_login = excluded.last_login""",
            (user_id, email, name, int(is_admin), now, now),
        )


def is_admin(user_id: str) -> bool:
    with get_conn() as conn:
        row = conn.execute("SELECT is_admin FROM users WHERE user_id = ?", (user_id,)).fetchone()
    return bool(row and row[0])

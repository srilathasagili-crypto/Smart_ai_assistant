"""Persistent LangGraph checkpointing for conversation threads.

This is separate from memory/user_profile.py on purpose:
- chat_history.py (SqliteSaver) stores the *message log* for a thread_id, so a
  conversation can be resumed (e.g. after a Streamlit rerun or app restart)
  without losing context.
- user_profile.py stores durable *facts about the user* (name, preferences),
  keyed by a stable user_id, independent of any one conversation thread.

Both use SQLite in the same temp directory so no new infra is required.
"""
import os
import sqlite3
import tempfile

from langgraph.checkpoint.sqlite import SqliteSaver

from graph.logger import get_logger

logger = get_logger("memory.chat_history")

_DB_DIR = os.path.join(tempfile.gettempdir(), "intelligent-ai-assistant")
_DB_PATH = os.path.join(_DB_DIR, "chat_history.sqlite")

_checkpointer: SqliteSaver | None = None


def get_checkpointer() -> SqliteSaver:
    """Builds (and caches, per-process) a SQLite-backed LangGraph checkpointer.

    Used by graph/builder.py to compile the graph with persistent, per-thread
    conversation memory.
    """
    global _checkpointer
    if _checkpointer is None:
        os.makedirs(_DB_DIR, exist_ok=True)
        # check_same_thread=False: Streamlit may reuse this connection across
        # the script-rerun threading model; SqliteSaver serializes access internally.
        conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
        _checkpointer = SqliteSaver(conn)
        logger.info(f"Initialized chat history checkpointer at {_DB_PATH}")
    return _checkpointer


def get_thread_config(thread_id: str) -> dict:
    """Returns the LangGraph config dict that scopes graph.invoke() / update_state()
    calls to a specific conversation thread."""
    return {"configurable": {"thread_id": thread_id}}

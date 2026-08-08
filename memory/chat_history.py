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
   
    return {"configurable": {"thread_id": thread_id}}

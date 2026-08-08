from datetime import datetime, timezone

from graph.logger import get_logger
from security import db

logger = get_logger("security.usage_tracker")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def record_token_usage(user_id: str, model: str, prompt_tokens: int, completion_tokens: int) -> None:
    prompt_tokens = prompt_tokens or 0
    completion_tokens = completion_tokens or 0
    total = prompt_tokens + completion_tokens
    today = _today()
    now_iso = datetime.now(timezone.utc).isoformat()

    with db.get_conn() as conn:
        conn.execute(
            """INSERT INTO daily_usage (user_id, date, request_count, prompt_tokens, completion_tokens, total_tokens)
               VALUES (?, ?, 0, ?, ?, ?)
               ON CONFLICT(user_id, date) DO UPDATE SET
                   prompt_tokens = prompt_tokens + excluded.prompt_tokens,
                   completion_tokens = completion_tokens + excluded.completion_tokens,
                   total_tokens = total_tokens + excluded.total_tokens""",
            (user_id, today, prompt_tokens, completion_tokens, total),
        )
        conn.execute(
            """INSERT INTO usage_events (user_id, ts, model, prompt_tokens, completion_tokens, total_tokens)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, now_iso, model, prompt_tokens, completion_tokens, total),
        )
    logger.info(f"Logged usage user_id={user_id!r} model={model} tokens={total}")

import time
from datetime import datetime, timezone

from graph.config import RATE_LIMIT_PER_MINUTE, DAILY_REQUEST_LIMIT, DAILY_TOKEN_LIMIT
from graph.logger import get_logger
from security import db

logger = get_logger("security.rate_limiter")


class RateLimitExceeded(Exception):


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def check_and_record_request(user_id: str) -> None:
    now = time.time()

    with db.get_conn() as conn:
        # 1) Burst limit: requests in the last rolling 60 seconds.
        conn.execute("DELETE FROM request_log WHERE ts < ?", (now - 60,))
        recent = conn.execute(
            "SELECT COUNT(*) FROM request_log WHERE user_id = ? AND ts >= ?",
            (user_id, now - 60),
        ).fetchone()[0]
        if recent >= RATE_LIMIT_PER_MINUTE:
            raise RateLimitExceeded(
                f"You're sending messages too quickly (limit: {RATE_LIMIT_PER_MINUTE}/minute). "
                "Please wait a few seconds and try again."
            )

        # 2) Daily budget: requests and tokens per UTC day.
        today = _today()
        row = conn.execute(
            "SELECT request_count, total_tokens FROM daily_usage WHERE user_id = ? AND date = ?",
            (user_id, today),
        ).fetchone()
        request_count, total_tokens = row if row else (0, 0)

        if request_count >= DAILY_REQUEST_LIMIT:
            raise RateLimitExceeded(
                f"You've reached today's message limit ({DAILY_REQUEST_LIMIT}/day). "
                "It resets at midnight UTC — thanks for your patience!"
            )
        if total_tokens >= DAILY_TOKEN_LIMIT:
            raise RateLimitExceeded(
                f"You've reached today's usage limit ({DAILY_TOKEN_LIMIT:,} tokens/day). "
                "It resets at midnight UTC."
            )

        conn.execute("INSERT INTO request_log (user_id, ts) VALUES (?, ?)", (user_id, now))
        conn.execute(
            """INSERT INTO daily_usage (user_id, date, request_count) VALUES (?, ?, 1)
               ON CONFLICT(user_id, date) DO UPDATE SET request_count = request_count + 1""",
            (user_id, today),
        )

    logger.info(f"Request recorded for user_id={user_id!r} ({request_count + 1}/{DAILY_REQUEST_LIMIT} today)")


def get_usage_summary(user_id: str) -> dict:
    """Used by the sidebar to show 'X/50 messages, Y/100000 tokens used today'."""
    today = _today()
    with db.get_conn() as conn:
        row = conn.execute(
            "SELECT request_count, prompt_tokens, completion_tokens, total_tokens "
            "FROM daily_usage WHERE user_id = ? AND date = ?",
            (user_id, today),
        ).fetchone()
    request_count, prompt_tokens, completion_tokens, total_tokens = row or (0, 0, 0, 0)
    return {
        "date": today,
        "requests_used": request_count,
        "requests_limit": DAILY_REQUEST_LIMIT,
        "tokens_used": total_tokens,
        "tokens_limit": DAILY_TOKEN_LIMIT,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
    }

import os
import streamlit as st
from dotenv import load_dotenv

from graph.logger import get_logger

load_dotenv()
logger = get_logger("config")


def get_env_var(key: str, required: bool = True):
    """Fetch a config value from Streamlit secrets first, then the environment.

    Set required=False for optional integrations (news, web search, calendar, ...)
    so the app can still start and run with those features simply disabled,
    instead of crashing at import time.
    """
    # Streamlit Cloud / local .streamlit/secrets.toml
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass

    # Local .env file / plain environment variable (e.g. HF Spaces "Repository secrets")
    value = os.getenv(key)
    if value:
        return value

    if required:
        raise ValueError(f"Missing required environment variable: {key}")

    logger.warning(f"Optional environment variable '{key}' is not set — related feature(s) will be disabled.")
    return None


# Required — the app cannot function at all without a working LLM.
GROQ_API_KEY = get_env_var("GROQ_API_KEY", required=True)

# Existing optional integrations (previously required — now degrade gracefully instead
# of crashing the whole app if one key is missing).
OPENWEATHER_API_KEY = get_env_var("OPENWEATHER_API_KEY", required=False)
GMAIL_ADDRESS = get_env_var("GMAIL_ADDRESS", required=False)
GMAIL_APP_PASSWORD = get_env_var("GMAIL_APP_PASSWORD", required=False)

# New optional integrations.
NEWS_API_KEY = get_env_var("NEWS_API_KEY", required=False)
TAVILY_API_KEY = get_env_var("TAVILY_API_KEY", required=False)
GOOGLE_CALENDAR_CREDENTIALS_PATH = get_env_var("GOOGLE_CALENDAR_CREDENTIALS_PATH", required=False)
GOOGLE_CALENDAR_TOKEN_PATH = get_env_var("GOOGLE_CALENDAR_TOKEN_PATH", required=False) or "token.json"

# --- Multi-user / public-deployment settings -------------------------------

# Emails allowed to use owner-only tools (Gmail send, Google Calendar) and to
# see the "admin" badge. These tools operate on a SINGLE shared Gmail/Calendar
# account (yours), so letting arbitrary public users trigger them would let
# them send email as you / edit your calendar — see tools/gmail.py and
# tools/calendar_tool.py for the enforcement.
_admin_emails_raw = get_env_var("ADMIN_EMAILS", required=False) or ""
ADMIN_EMAILS = {e.strip().lower() for e in _admin_emails_raw.split(",") if e.strip()}


def _has_auth_section() -> bool:
    """True once a real [auth] section (Google OAuth client) exists in secrets.toml.
    client_id/client_secret/server_metadata_url live flat inside [auth] for a
    single default provider — see .streamlit/secrets.toml.example."""
    try:
        auth = st.secrets.get("auth", {})
        return bool(auth.get("client_id") and auth.get("cookie_secret") and auth.get("redirect_uri"))
    except Exception:
        return False


AUTH_CONFIGURED = _has_auth_section()

# Per-user rate limits (see security/rate_limiter.py). All overridable via
# secrets/env without touching code.
RATE_LIMIT_PER_MINUTE = int(get_env_var("RATE_LIMIT_PER_MINUTE", required=False) or 6)
DAILY_REQUEST_LIMIT = int(get_env_var("DAILY_REQUEST_LIMIT", required=False) or 50)
DAILY_TOKEN_LIMIT = int(get_env_var("DAILY_TOKEN_LIMIT", required=False) or 100_000)


def validate_config() -> dict:
    """Return a {feature_name: is_configured} map, and log a one-time startup summary.

    Used by the UI to show tool status in the sidebar, and by app startup to warn
    about disabled features without stopping the app.
    """
    status = {
        "Groq LLM": bool(GROQ_API_KEY),
        "Weather": bool(OPENWEATHER_API_KEY),
        "Gmail": bool(GMAIL_ADDRESS and GMAIL_APP_PASSWORD),
        "News Search": bool(NEWS_API_KEY),
        "Web Search": True,  # DuckDuckGo fallback needs no key; Tavily is used if TAVILY_API_KEY is set
        "Calendar": bool(GOOGLE_CALENDAR_CREDENTIALS_PATH),
        "Google Sign-In": AUTH_CONFIGURED,
    }
    for feature, ok in status.items():
        if not ok:
            logger.warning(f"Feature disabled (missing config): {feature}")
    return status

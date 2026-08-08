import streamlit as st

from graph.config import ADMIN_EMAILS, AUTH_CONFIGURED
from graph.logger import get_logger
from security import db

logger = get_logger("auth")


def require_login() -> dict:
  
    if AUTH_CONFIGURED:
        return _require_google_login()
    return _require_dev_login()


def _require_google_login() -> dict:
    if not st.user.is_logged_in:
        st.title("🤖 Intelligent AI Assistant")
        st.info("Please sign in with Google to continue.")
        st.button("🔐 Sign in with Google", on_click=st.login, type="primary")
        st.stop()

    email = (st.user.email or "").lower()
    name = getattr(st.user, "name", None) or email
    is_admin = email in ADMIN_EMAILS

    db.upsert_user(user_id=email, email=email, name=name, is_admin=is_admin)
    logger.info(f"Logged in: {email} (admin={is_admin})")

    with st.sidebar:
        col_name, col_out = st.columns([3, 1])
        col_name.markdown(f"👤 **{name}**" + (" 🛡️" if is_admin else ""))
        if col_out.button("Log out", key="logout_btn"):
            st.logout()

    return {"user_id": email, "email": email, "name": name, "is_admin": is_admin}


def _require_dev_login() -> dict:
    st.sidebar.warning(
        "⚠️ **Dev mode** — Google auth isn't configured yet, so anyone can type "
        "any name to enter. Set up `[auth]` in `secrets.toml` before making "
        "this app public. See README.md → 'Authentication setup'.",
        icon="⚠️",
    )
    name_input = st.sidebar.text_input("Your name (dev mode)", value=st.session_state.get("dev_user", ""))
    if not name_input.strip():
        st.info("Enter a name in the sidebar to continue (dev mode).")
        st.stop()

    user_id = name_input.strip().lower().replace(" ", "_")
    st.session_state.dev_user = name_input.strip()
    # Best-effort admin check in dev mode: matches the local part of an admin email.
    is_admin = user_id in {a.split("@")[0] for a in ADMIN_EMAILS}
    db.upsert_user(user_id=user_id, email=None, name=name_input.strip(), is_admin=is_admin)

    return {"user_id": user_id, "email": None, "name": name_input.strip(), "is_admin": is_admin}

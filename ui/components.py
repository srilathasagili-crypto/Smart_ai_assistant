import streamlit as st


def apply_theme():
    st.markdown(
        """
        <style>
        .stChatMessage { border-radius: 12px; }
        div[data-testid="stSidebarUserContent"] { padding-top: 1rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_tool_status(status: dict):
    st.sidebar.markdown("### 🛠️ Tool status")
    for name, ok in status.items():
        icon = "🟢" if ok else "⚪"
        st.sidebar.markdown(f"{icon} {name}")
    if not all(status.values()):
        st.sidebar.caption("⚪ = not configured (missing API key) — the assistant still works, that tool just stays off.")


def render_memory_status(profile: dict):
    st.sidebar.markdown("### 🧠 Memory")
    if profile.get("name"):
        st.sidebar.markdown(f"**Name:** {profile['name']}")
    else:
        st.sidebar.caption("No name saved yet — just tell the assistant your name.")

    preferences = profile.get("preferences") or {}
    if preferences:
        for key, value in preferences.items():
            st.sidebar.markdown(f"- **{key.replace('_', ' ').title()}:** {value}")


def render_reminder_banner(due_reminders: list):
    for reminder in due_reminders:
        st.toast(f"⏰ Reminder: {reminder['text']}", icon="⏰")


def render_usage_status(usage: dict):
    """Shows today's per-user request/token usage against configured daily limits."""
    st.sidebar.markdown("### 📊 Today's usage")
    req_frac = min(usage["requests_used"] / usage["requests_limit"], 1.0) if usage["requests_limit"] else 0
    tok_frac = min(usage["tokens_used"] / usage["tokens_limit"], 1.0) if usage["tokens_limit"] else 0

    st.sidebar.progress(req_frac, text=f"Messages: {usage['requests_used']}/{usage['requests_limit']}")
    st.sidebar.progress(tok_frac, text=f"Tokens: {usage['tokens_used']:,}/{usage['tokens_limit']:,}")

    if req_frac >= 1.0 or tok_frac >= 1.0:
        st.sidebar.caption("Limit reached for today — resets at midnight UTC.")

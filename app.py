import uuid

import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage
from graph.config import validate_config, AUTH_CONFIGURED

from auth.authentication import require_login
from graph.builder import build_graph
from graph.config import validate_config
from graph.logger import get_logger
from memory.chat_history import get_thread_config
from memory.user_profile import get_profile
from memory.reminders import get_due_unnotified
from security import db as security_db
from security.rate_limiter import check_and_record_request, get_usage_summary, RateLimitExceeded
from tools.pdf_extract import extract_pdf_text
from ui.components import (
    apply_theme,
    render_tool_status,
    render_memory_status,
    render_reminder_banner,
    render_usage_status,
)

logger = get_logger("app")

st.set_page_config(page_title="Intelligent AI Assistant", page_icon="🤖", layout="wide")
apply_theme()
security_db.init_db()


@st.cache_resource
def get_graph():
    logger.info("Building graph...")
    return build_graph()


def init_session(user_id: str):
    # Namespace the thread_id by user so two different logged-in users never
    # share (or collide on) the same LangGraph checkpointed conversation.
    thread_key = f"thread_id::{user_id}"
    if thread_key not in st.session_state:
        st.session_state[thread_key] = str(uuid.uuid4())
        logger.info(f"Started new conversation thread for {user_id}: {st.session_state[thread_key]}")
    st.session_state.thread_id = st.session_state[thread_key]

    if "history" not in st.session_state:
        st.session_state.history = []
    if "pdf_uploaded_name" not in st.session_state:
        st.session_state.pdf_uploaded_name = None
    if "voice_enabled" not in st.session_state:
        st.session_state.voice_enabled = False


def render_history():
    for message in st.session_state.history:
        role = "user" if isinstance(message, HumanMessage) else "assistant"
        with st.chat_message(role):
            st.markdown(message.content)


def render_sidebar(status: dict, user_id: str) -> "st.runtime.uploaded_file_manager.UploadedFile | None":
    st.sidebar.title("⚙️ Assistant")

    st.sidebar.divider()
    render_usage_status(get_usage_summary(user_id))

    st.sidebar.divider()
    render_tool_status(status)

    st.sidebar.divider()
    profile = get_profile(user_id)
    render_memory_status(profile)

    st.sidebar.divider()
    st.sidebar.markdown("### 📄 PDF Analysis")
    uploaded_file = st.sidebar.file_uploader("Upload a PDF", type=["pdf"])

    st.sidebar.divider()
    st.session_state.voice_enabled = st.sidebar.checkbox("🎤 Voice mode", value=st.session_state.voice_enabled)

    st.sidebar.divider()
    if st.sidebar.button("🗑️ Clear chat"):
        st.session_state.history = []
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.pdf_uploaded_name = None
        st.rerun()

    return uploaded_file


def handle_pdf_upload(uploaded_file, graph, config, user_id: str, is_admin: bool):
    """Extracts text from a newly uploaded PDF and stores it directly into the graph's
    checkpointed state (via update_state) — deliberately NOT graph.invoke(), so this
    doesn't trigger an extra, invisible LLM turn."""
    if uploaded_file is None:
        return
    if st.session_state.pdf_uploaded_name == uploaded_file.name:
        return

    # Basic size guard so one user can't feed the app huge files that burn LLM
    # tokens (and processing time) once the extracted text is fed to the model.
    max_mb = 15
    if uploaded_file.size > max_mb * 1024 * 1024:
        st.sidebar.error(f"PDF is too large (max {max_mb}MB).")
        return

    with st.spinner("Reading PDF..."):
        text = extract_pdf_text(uploaded_file)

    if not text:
        st.sidebar.error("Couldn't extract text from this PDF (it may be scanned/image-only).")
        return

    graph.update_state(
        config,
        {"pdf_context": text, "user_id": user_id, "is_admin": is_admin},
    )
    st.session_state.pdf_uploaded_name = uploaded_file.name
    st.sidebar.success(f"'{uploaded_file.name}' loaded — ask me to summarize it or answer questions about it.")


def handle_voice_input() -> str | None:
    try:
        from streamlit_mic_recorder import mic_recorder
    except ImportError:
        st.sidebar.warning("Voice mode needs the 'streamlit-mic-recorder' package (see requirements.txt).")
        return None

    audio = mic_recorder(start_prompt="🎙️ Speak", stop_prompt="⏹ Stop", key="recorder")
    if not audio:
        return None

    try:
        from groq import Groq
        from graph.config import GROQ_API_KEY

        client = Groq(api_key=GROQ_API_KEY)
        tmp_path = "/tmp/voice_input.wav"
        with open(tmp_path, "wb") as f:
            f.write(audio["bytes"])
        with open(tmp_path, "rb") as f:
            result = client.audio.transcriptions.create(file=f, model="whisper-large-v3")
        return result.text
    except Exception as e:
        logger.exception("Voice transcription failed")
        st.warning(f"Couldn't transcribe audio: {e}")
        return None


def speak(text: str):
    try:
        from gtts import gTTS
        import io

        tts = gTTS(text=text, lang="en")
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        st.audio(buf, format="audio/mp3")
    except Exception as e:
        logger.exception("Text-to-speech failed")
        st.caption(f"(voice output unavailable: {e})")


def main():
    # Authentication gate — everything below only runs for a signed-in user.
    # See auth/authentication.py for the Google Sign-In / dev-mode logic.
    st.write("LOGIN STATUS:", st.user.is_logged_in)
    st.write("USER:", st.user)
    st.write("AUTH CONFIGURED:", AUTH_CONFIGURED)
    identity = require_login()
    user_id = identity["user_id"]
    is_admin = identity["is_admin"]

    st.title("🤖 Intelligent AI Assistant")
    init_session(user_id)

    status = validate_config()
    graph = get_graph()
    config = get_thread_config(st.session_state.thread_id)

    uploaded_file = render_sidebar(status, user_id)
    handle_pdf_upload(uploaded_file, graph, config, user_id, is_admin)

    render_reminder_banner(get_due_unnotified(user_id))

    render_history()

    user_input = st.chat_input("Ask me anything...")

    if st.session_state.voice_enabled:
        voice_text = handle_voice_input()
        if voice_text:
            user_input = voice_text

    if not user_input:
        return

    # Rate limiting / quota enforcement (security/rate_limiter.py) — checked
    # once per incoming user message, BEFORE we touch the LLM at all. This is
    # what stops one user from burning through your whole Groq quota.
    try:
        check_and_record_request(user_id)
    except RateLimitExceeded as e:
        st.session_state.history.append(HumanMessage(content=user_input))
        with st.chat_message("user"):
            st.markdown(user_input)
        with st.chat_message("assistant"):
            st.warning(str(e))
        st.session_state.history.append(AIMessage(content=str(e)))
        return

    user_message = HumanMessage(content=user_input)
    st.session_state.history.append(user_message)
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                result = graph.invoke(
                    {"messages": [user_message], "user_id": user_id, "is_admin": is_admin},
                    config=config,
                )
                reply = result["messages"][-1].content
            except Exception:
                # graph/nodes.py already turns LLM/API errors into friendly AIMessages;
                # this is the last-resort catch for anything outside that (e.g. a bug
                # in a tool, or a checkpointer/DB hiccup) so the app never hard-crashes.
                logger.exception("Error while processing user input")
                reply = "Sorry, something went wrong on our end. Please try again."
        st.markdown(reply)
        if st.session_state.voice_enabled:
            speak(reply)

    st.session_state.history.append(AIMessage(content=reply))


if __name__ == "__main__":
    main()

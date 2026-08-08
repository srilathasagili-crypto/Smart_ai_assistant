from langchain_core.messages import AIMessage, SystemMessage
from langgraph.prebuilt import ToolNode

from graph.state import AssistantState
from graph.llm import get_llm
from graph.logger import get_logger
from memory.user_profile import format_profile_for_prompt
from security.usage_tracker import record_token_usage

from tools.calculator import calculator
from tools.weather import get_weather
from tools.gmail import send_email
from tools.news import search_news, get_top_headlines
from tools.web_search import web_search
from tools.calendar_tool import add_calendar_event, list_today_events, delete_calendar_event
from tools.pdf_tools import ask_pdf_question, summarize_pdf, extract_pdf_key_info
from tools.reminders_tool import add_reminder, show_reminders, remove_reminder
from tools.memory_tool import remember_user_info, recall_user_info

logger = get_logger("graph.nodes")

TOOLS = [
    # Existing tools — unchanged.
    calculator,
    get_weather,
    send_email,
    # News
    search_news,
    get_top_headlines,
    # Web search
    web_search,
    # Calendar
    add_calendar_event,
    list_today_events,
    delete_calendar_event,
    # PDF analysis
    ask_pdf_question,
    summarize_pdf,
    extract_pdf_key_info,
    # Reminders
    add_reminder,
    show_reminders,
    remove_reminder,
    # Long-term memory
    remember_user_info,
    recall_user_info,
]

_llm = get_llm()
_llm_with_tools = _llm.bind_tools(TOOLS)

BASE_SYSTEM_PROMPT = (
    "You are a helpful, concise AI assistant. "
    "Use the calculator tool for any math. "
    "Use the weather tool for current weather questions. "
    "Use the send_email tool only when the user explicitly asks to send an email — "
    "if they mention attaching a file, pass its path as attachment_path. "
    "Use search_news for news about a specific topic, and get_top_headlines for general/today's headlines. "
    "Use web_search for general knowledge or current-events questions you're not confident about. "
    "Use the calendar tools to create, list, or delete Google Calendar events. "
    "Use the PDF tools (ask_pdf_question, summarize_pdf, extract_pdf_key_info) only when the user "
    "has uploaded a PDF and is asking about it. "
    "Use the reminder tools to create, list, or delete reminders for the user. "
    "Whenever the user states their name or a clear preference (favourite language, food, topic, etc.), "
    "call remember_user_info to save it. If asked what you remember about them, call recall_user_info. "
    "Never call a tool unless it's clearly needed. "
    "If a tool returns an error message, explain it to the user in plain language instead of retrying blindly."
)


def _build_system_message(user_id: str) -> SystemMessage:
    profile_facts = format_profile_for_prompt(user_id) if user_id else ""
    prompt = BASE_SYSTEM_PROMPT + (f"\n\nWhat you already know about this user: {profile_facts}" if profile_facts else "")
    return SystemMessage(content=prompt)


def _friendly_error_message(e: Exception) -> str:
    """Turns raw Groq/API exceptions into a message that's safe and useful to show
    end users — never leaks stack traces or internal details, and calls out
    quota/rate-limit errors specifically so users understand it's temporary."""
    status_code = getattr(e, "status_code", None)
    text = str(e).lower()

    if status_code == 429 or "rate limit" in text or "quota" in text:
        logger.warning(f"Upstream rate limit/quota hit: {e}")
        return (
            "⚠️ The AI service is receiving a lot of requests right now (rate limit reached). "
            "Please wait a minute and try again."
        )
    if status_code == 401 or "invalid api key" in text or "authentication" in text:
        logger.error(f"Upstream auth failure — check GROQ_API_KEY: {e}")
        return "⚠️ There's a configuration issue on our end. Please contact the admin."
    if status_code is not None and 500 <= status_code < 600:
        logger.error(f"Upstream server error: {e}")
        return "⚠️ The AI service is temporarily unavailable. Please try again shortly."

    logger.exception("LLM invocation failed")
    return f"Sorry, I hit an unexpected error talking to the model ({type(e).__name__}). Please try again."


def chat_node(state: AssistantState) -> dict:
    messages = state["messages"]
    user_id = state.get("user_id", "default_user")

    system_message = _build_system_message(user_id)
    if not messages or messages[0].type != "system":
        messages = [system_message] + list(messages)
    else:
        # Refresh the system message each turn so newly-learned profile facts show up
        # without growing the message list.
        messages = [system_message] + list(messages[1:])

    try:
        response = _llm_with_tools.invoke(messages)
    except Exception as e:
        # Never let an LLM/API hiccup crash the app — surface a friendly message instead.
        return {"messages": [AIMessage(content=_friendly_error_message(e))]}

    # Per-user token tracking (usage_tracker.py) — feeds both the sidebar usage
    # display and the daily quota check in security/rate_limiter.py. There can be
    # more than one LLM call per user turn (each tool-calling round trip), so this
    # accumulates rather than overwrites.
    usage = getattr(response, "usage_metadata", None)
    if usage and user_id:
        record_token_usage(
            user_id=user_id,
            model=getattr(_llm, "model_name", "groq"),
            prompt_tokens=usage.get("input_tokens", 0),
            completion_tokens=usage.get("output_tokens", 0),
        )

    if getattr(response, "tool_calls", None):
        logger.info(f"Tool calls requested: {[tc['name'] for tc in response.tool_calls]}")

    return {"messages": [response]}


# handle_tool_errors=True (the default) means a tool raising an exception is caught by
# LangGraph itself and turned into a ToolMessage with the error text, instead of crashing
# the graph — this is the last line of defense on top of each tool's own try/except.
tool_node = ToolNode(TOOLS, handle_tool_errors=True)

from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class AssistantState(TypedDict, total=False):
    # Existing field — unchanged behavior.
    messages: Annotated[list[BaseMessage], add_messages]

    # New: stable identifier used for long-term memory (profile, reminders).
    # Not a reducer field — once set, it persists across turns via the checkpointer
    # because LangGraph merges partial updates onto the last checkpointed state.
    user_id: str

    # New: text extracted from the most recently uploaded PDF, used by the
    # PDF analysis tools (ask_pdf_question, summarize_pdf). Empty until a PDF
    # is uploaded; persists across turns the same way as user_id.
    pdf_context: str

    # New: True only for emails listed in ADMIN_EMAILS (graph/config.py).
    # Read by tools/gmail.py and tools/calendar_tool.py — those tools act on
    # a single shared owner account, so they're gated to admins only in a
    # public multi-user deployment. Set once per turn from app.py based on
    # the logged-in user, never settable by the LLM itself.
    is_admin: bool

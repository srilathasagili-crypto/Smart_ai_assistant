from typing import Annotated

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from memory.reminders import create_reminder, delete_reminder, list_reminders
from graph.logger import get_logger

logger = get_logger("tools.reminders")


@tool
def add_reminder(text: str, due_at_iso: str, state: Annotated[dict, InjectedState]) -> str:
    """Create a reminder. due_at_iso must be an ISO 8601 datetime, e.g. '2026-08-05T18:00:00'.
    Use this when the user asks to be reminded about something."""
    user_id = state.get("user_id", "default_user")
    result = create_reminder(user_id, text.strip(), due_at_iso)
    if not result:
        return "Couldn't create the reminder due to a storage error. Please try again."
    return f"Reminder set: '{result['text']}' at {result['due_at']} (id: {result['id']})."


@tool
def show_reminders(state: Annotated[dict, InjectedState]) -> str:
    """List all of the user's reminders."""
    user_id = state.get("user_id", "default_user")
    reminders = list_reminders(user_id)
    if not reminders:
        return "You have no reminders set."
    lines = [f"- [{r['id']}] {r['text']} — due {r['due_at']}" + (" (notified)" if r["notified"] else "") for r in reminders]
    return "Your reminders:\n" + "\n".join(lines)


@tool
def remove_reminder(reminder_id: str, state: Annotated[dict, InjectedState]) -> str:
    """Delete a reminder by its id (shown in brackets by show_reminders)."""
    user_id = state.get("user_id", "default_user")
    deleted = delete_reminder(user_id, reminder_id.strip())
    if deleted:
        return f"Reminder {reminder_id} deleted."
    return f"No reminder found with id '{reminder_id}'."

from typing import Annotated

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from memory.user_profile import get_profile, update_profile

_ = InjectedState  # imported for the Annotated type below


@tool
def remember_user_info(
    state: Annotated[dict, InjectedState],
    name: str = "",
    preference_key: str = "",
    preference_value: str = "",
) -> str:
    """Save a durable fact about the user for future conversations: their name, or a
    preference such as a favourite programming language/technology, food, or topic.
    Call this whenever the user states their name or a clear preference — for example
    'my name is Sri' -> name='Sri', or 'I love Python' -> preference_key='favourite_technology',
    preference_value='Python'."""
    user_id = state.get("user_id", "default_user")
    preferences = {preference_key: preference_value} if preference_key else None
    update_profile(user_id, name=name or None, preferences=preferences)
    return "Got it — I'll remember that."


@tool
def recall_user_info(state: Annotated[dict, InjectedState]) -> str:
    """Recall everything currently remembered about the user (name and preferences)."""
    user_id = state.get("user_id", "default_user")
    profile = get_profile(user_id)
    if not profile["name"] and not profile["preferences"]:
        return "I don't have anything saved about you yet."
    parts = []
    if profile["name"]:
        parts.append(f"Name: {profile['name']}")
    for k, v in profile["preferences"].items():
        parts.append(f"{k}: {v}")
    return "Here's what I remember about you:\n" + "\n".join(f"- {p}" for p in parts)

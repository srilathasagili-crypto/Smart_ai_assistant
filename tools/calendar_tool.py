"""Google Calendar integration.

Uses the OAuth "installed app" flow: the first time any calendar tool runs
locally, a browser window opens for one-time consent, and a token is cached
at GOOGLE_CALENDAR_TOKEN_PATH (default: token.json) for reuse after that.

Deployment note: the browser consent flow needs a local browser, so it will
NOT work the first time on Streamlit Cloud / HF Spaces. Run it once locally
to generate token.json, then include that file as a secret/deploy-time asset.
See README.md "Calendar setup" for details.
"""
import datetime
import os
from typing import Annotated, Any

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from graph.config import (
    GOOGLE_CALENDAR_CREDENTIALS_PATH,
    GOOGLE_CALENDAR_TOKEN_PATH,
)
from graph.logger import get_logger

logger = get_logger("tools.calendar")

_SCOPES = ["https://www.googleapis.com/auth/calendar"]
_NOT_CONFIGURED_MSG = (
    "Calendar tool is not configured (missing GOOGLE_CALENDAR_CREDENTIALS_PATH). "
    "Ask the admin to set up Google Calendar credentials."
)
_ADMIN_ONLY_MSG = (
    "Calendar access isn't available to you in this deployment — it's a single shared "
    "Google Calendar (the admin's), so it's restricted to the assistant's admin."
)


def _is_admin(state) -> bool:
    return bool(state and state.get("is_admin"))


def _get_service():
    """Builds (and caches, per-process) an authorized Google Calendar API client."""
    if not GOOGLE_CALENDAR_CREDENTIALS_PATH:
        return None

    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    if os.path.exists(GOOGLE_CALENDAR_TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(GOOGLE_CALENDAR_TOKEN_PATH, _SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(GOOGLE_CALENDAR_CREDENTIALS_PATH, _SCOPES)
            creds = flow.run_local_server(port=0)
        with open(GOOGLE_CALENDAR_TOKEN_PATH, "w") as f:
            f.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


@tool
def add_calendar_event(
    title: str,
    start_iso: str,
    end_iso: str,
    state: Annotated[Any, InjectedState] = None,
) -> str:
    """Create a Google Calendar event. start_iso and end_iso must be ISO 8601
    datetimes with timezone, e.g. '2026-08-05T10:00:00+05:30'."""
    if not _is_admin(state):
        return _ADMIN_ONLY_MSG
    if not GOOGLE_CALENDAR_CREDENTIALS_PATH:
        return _NOT_CONFIGURED_MSG
    try:
        service = _get_service()
        event = {"summary": title, "start": {"dateTime": start_iso}, "end": {"dateTime": end_iso}}
        created = service.events().insert(calendarId="primary", body=event).execute()
        logger.info(f"Created calendar event: {title}")
        return f"Event '{title}' created: {created.get('htmlLink')}"
    except ValueError:
        return "Couldn't understand the date/time given. Please use ISO format, e.g. '2026-08-05T10:00:00+05:30'."
    except Exception as e:
        logger.exception("Failed to create calendar event")
        return f"Couldn't create the calendar event: {e}"


@tool
def list_today_events(state: Annotated[Any, InjectedState] = None) -> str:
    """List today's events on the user's primary Google Calendar."""
    if not _is_admin(state):
        return _ADMIN_ONLY_MSG
    if not GOOGLE_CALENDAR_CREDENTIALS_PATH:
        return _NOT_CONFIGURED_MSG
    try:
        service = _get_service()
        now = datetime.datetime.now(datetime.timezone.utc)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=0).isoformat()

        events = (
            service.events()
            .list(calendarId="primary", timeMin=start_of_day, timeMax=end_of_day,
                  singleEvents=True, orderBy="startTime")
            .execute()
            .get("items", [])
        )
        if not events:
            return "No events scheduled for today."
        lines = [
            f"- [{e['id']}] {e.get('summary', '(no title)')} at {e['start'].get('dateTime', e['start'].get('date'))}"
            for e in events
        ]
        return "Today's events:\n" + "\n".join(lines)
    except Exception as e:
        logger.exception("Failed to list today's calendar events")
        return f"Couldn't fetch today's events: {e}"


@tool
def delete_calendar_event(event_id: str, state: Annotated[Any, InjectedState] = None) -> str:
    """Delete a Google Calendar event by its event_id (shown in brackets by list_today_events)."""
    if not _is_admin(state):
        return _ADMIN_ONLY_MSG
    if not GOOGLE_CALENDAR_CREDENTIALS_PATH:
        return _NOT_CONFIGURED_MSG
    try:
        service = _get_service()
        service.events().delete(calendarId="primary", eventId=event_id).execute()
        logger.info(f"Deleted calendar event {event_id}")
        return f"Event {event_id} deleted."
    except Exception as e:
        logger.exception(f"Failed to delete calendar event {event_id}")
        return f"Couldn't delete event '{event_id}': {e}"

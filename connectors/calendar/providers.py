"""
Calendar providers: Google Calendar (default), Microsoft Outlook / Graph.

Methods are STUBS returning sample events so the meeting-prep agent runs with no
credentials. The `# --- REAL CALL ---` block in each shows the env var, endpoint/
SDK, and response mapping to turn the stub into a real integration.
"""

from __future__ import annotations

import datetime
import os

from connectors.calendar.base import Event


def _sample_events() -> list[Event]:
    """Two realistic upcoming events, anchored to the next two days."""
    now = datetime.datetime.now(datetime.timezone.utc)
    t1 = (now + datetime.timedelta(days=1)).replace(hour=15, minute=0, second=0, microsecond=0)
    t2 = (now + datetime.timedelta(days=2)).replace(hour=10, minute=30, second=0, microsecond=0)
    return [
        Event(
            id="evt_stub_001",
            title="Northwind Labs <> Linkup — discovery call",
            start=t1.isoformat(),
            attendees=[
                {"name": "Jordan Avery", "email": "jordan.avery@northwind.example"},
                {"name": "You", "email": "me@linkup.so"},
            ],
        ),
        Event(
            id="evt_stub_002",
            title="Quarterly roadmap sync",
            start=t2.isoformat(),
            attendees=[
                {"name": "Priya Nadkarni", "email": "priya@acme.example"},
                {"name": "You", "email": "me@linkup.so"},
            ],
        ),
    ]


class GoogleCalendar:
    """Google Calendar. Env var: GOOGLE_CALENDAR_CREDENTIALS_JSON (OAuth/service-account)."""

    def __init__(self, credentials_json: str | None = None) -> None:
        self.credentials_json = credentials_json or os.environ.get(
            "GOOGLE_CALENDAR_CREDENTIALS_JSON"
        )

    def upcoming_events(self, days: int = 7) -> list[Event]:
        # --- STUB: sample events so the agent runs with no creds ---
        return _sample_events()
        # --- REAL CALL: Google Calendar API v3 (events.list) ---
        # https://developers.google.com/calendar/api/v3/reference/events/list
        # pip install google-api-python-client google-auth
        # from google.oauth2.service_account import Credentials
        # from googleapiclient.discovery import build
        # creds = Credentials.from_service_account_file(
        #     self.credentials_json,
        #     scopes=["https://www.googleapis.com/auth/calendar.readonly"],
        # )
        # service = build("calendar", "v3", credentials=creds)
        # now = datetime.datetime.now(datetime.timezone.utc)
        # resp = service.events().list(
        #     calendarId="primary",
        #     timeMin=now.isoformat(),
        #     timeMax=(now + datetime.timedelta(days=days)).isoformat(),
        #     singleEvents=True,
        #     orderBy="startTime",
        # ).execute()
        # return [
        #     Event(
        #         id=e["id"],
        #         title=e.get("summary", "(no title)"),
        #         start=e["start"].get("dateTime") or e["start"].get("date"),
        #         attendees=[
        #             {"name": a.get("displayName", ""), "email": a.get("email", "")}
        #             for a in e.get("attendees", [])
        #         ],
        #     )
        #     for e in resp.get("items", [])
        # ]


class OutlookCalendar:
    """Microsoft Outlook via Graph. Env var: MS_GRAPH_ACCESS_TOKEN."""

    def __init__(self, access_token: str | None = None) -> None:
        self.access_token = access_token or os.environ.get("MS_GRAPH_ACCESS_TOKEN")

    def upcoming_events(self, days: int = 7) -> list[Event]:
        # --- STUB ---
        return _sample_events()
        # --- REAL CALL: Microsoft Graph calendarView ---
        # https://learn.microsoft.com/graph/api/calendar-list-calendarview
        # import requests
        # now = datetime.datetime.now(datetime.timezone.utc)
        # resp = requests.get(
        #     "https://graph.microsoft.com/v1.0/me/calendarView",
        #     headers={"Authorization": f"Bearer {self.access_token}"},
        #     params={
        #         "startDateTime": now.isoformat(),
        #         "endDateTime": (now + datetime.timedelta(days=days)).isoformat(),
        #         "$orderby": "start/dateTime",
        #     },
        # )
        # return [
        #     Event(
        #         id=e["id"],
        #         title=e.get("subject", "(no title)"),
        #         start=e["start"]["dateTime"],
        #         attendees=[
        #             {
        #                 "name": a["emailAddress"].get("name", ""),
        #                 "email": a["emailAddress"].get("address", ""),
        #             }
        #             for a in e.get("attendees", [])
        #         ],
        #     )
        #     for e in resp.json().get("value", [])
        # ]

"""
connectors/calendar/ — read upcoming events behind one tiny interface.

    from connectors.calendar import get_calendar
    cal = get_calendar()                    # Google Calendar (default)
    cal = get_calendar(provider="outlook")

A calendar provider exposes one method:

    upcoming_events(days=7) -> list[Event]

`Event` is a dataclass: id, title, start (ISO str), attendees (list of
{name, email} dicts).

The default provider returns sample events so the meeting-prep agent runs with no
credentials. Each provider carries commented real-API snippets + the env var it
reads.
"""

from __future__ import annotations

from connectors.calendar.base import Calendar, Event
from connectors.calendar.providers import GoogleCalendar, OutlookCalendar

_PROVIDERS = {
    "google": GoogleCalendar,
    "outlook": OutlookCalendar,
    "microsoft": OutlookCalendar,  # alias
}


def get_calendar(provider: str = "google", **kwargs) -> Calendar:
    """Return a calendar provider instance. Default: Google Calendar (stub)."""
    try:
        cls = _PROVIDERS[provider.lower()]
    except KeyError:
        raise ValueError(
            f"Unknown calendar provider {provider!r}. "
            f"Supported: {', '.join(sorted(_PROVIDERS))}."
        )
    return cls(**kwargs)


__all__ = ["get_calendar", "Calendar", "Event"]

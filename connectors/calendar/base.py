"""Shared types + interface for calendar providers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class Event:
    """A calendar event, normalized across providers."""

    id: str
    title: str
    start: str  # ISO 8601 string, e.g. "2026-06-20T15:00:00+00:00"
    attendees: list[dict] = field(default_factory=list)  # {"name": ..., "email": ...}


class Calendar(Protocol):
    """The interface every calendar provider implements."""

    def upcoming_events(self, days: int = 7) -> list[Event]:
        """Events starting within the next `days` days, soonest first."""
        ...

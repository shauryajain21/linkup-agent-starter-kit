"""Shared types + interface for CRM providers."""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Protocol


@dataclass
class Contact:
    """A CRM contact, normalized across providers."""

    name: str
    title: str
    company: str
    email: str


class CRM(Protocol):
    """The interface every CRM provider implements (and agents depend on)."""

    def find_contact(self, email: str) -> Contact | None:
        """Look up a contact by email. Returns None if not found."""
        ...

    def last_touch(self, email: str) -> datetime.date | None:
        """Date of the most recent logged activity with this contact, or None."""
        ...

    def create_note(self, contact_email: str, body: str) -> dict:
        """Log a note against a contact. Returns the created note (id, etc.)."""
        ...

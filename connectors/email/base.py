"""Shared interface for email providers."""

from __future__ import annotations

from typing import Protocol


class EmailSender(Protocol):
    """The interface every email provider implements."""

    def send(self, to: str, subject: str, body_markdown: str) -> dict:
        """Send an email. `body_markdown` is the body in Markdown.

        Returns at least {"id": ...}. Stubs return a fake message id.
        """
        ...

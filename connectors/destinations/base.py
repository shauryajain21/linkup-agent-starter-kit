"""Shared interface for destination providers."""

from __future__ import annotations

from typing import Protocol


class Destination(Protocol):
    """The interface every destination provider implements."""

    def create_page(self, title: str, markdown_body: str, **meta) -> dict:
        """Publish a page/record/message. `**meta` carries provider-specific
        extras (channel, team_id, table, ...).

        Returns at least {"url": ...} or {"id": ...}. Stubs return a fake one.
        """
        ...

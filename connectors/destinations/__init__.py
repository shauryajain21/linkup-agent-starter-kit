"""
connectors/destinations/ — write an agent's output somewhere, behind one interface.

    from connectors.destinations import get_destination
    dest = get_destination()                  # Notion (default)
    dest = get_destination(provider="slack")

A destination provider exposes one method:

    create_page(title, markdown_body, **meta) -> dict   (returns {"url": ...} / {"id": ...})

`**meta` carries provider-specific extras (e.g. Slack `channel`, Linear `team_id`,
Airtable `table`). Stubs ignore them and return a fake url/id so agents run with no
credentials. Each provider carries commented real-API snippets + the env var it reads.
"""

from __future__ import annotations

from connectors.destinations.base import Destination
from connectors.destinations.providers import (
    AirtableDestination,
    GoogleDocsDestination,
    LinearDestination,
    NotionDestination,
    SlackDestination,
)

_PROVIDERS = {
    "notion": NotionDestination,
    "slack": SlackDestination,
    "linear": LinearDestination,
    "airtable": AirtableDestination,
    "googledocs": GoogleDocsDestination,
    "google_docs": GoogleDocsDestination,  # alias
}


def get_destination(provider: str = "notion", **kwargs) -> Destination:
    """Return a destination provider instance. Default: Notion (stub)."""
    try:
        cls = _PROVIDERS[provider.lower()]
    except KeyError:
        raise ValueError(
            f"Unknown destination provider {provider!r}. "
            f"Supported: {', '.join(sorted(_PROVIDERS))}."
        )
    return cls(**kwargs)


__all__ = ["get_destination", "Destination"]

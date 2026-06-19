"""
connectors/ — swappable integration stubs for the agents in this starter kit.

Linkup is the engine (live-web search/fetch/research). The connectors are the
*edges* of an agent: where it reads context (CRM, calendar) and where it writes
results (email, destinations like Notion/Slack). None of it is locked to one
vendor — each category is a factory that returns a provider object behind a tiny,
documented interface.

    from connectors.crm import get_crm
    from connectors.calendar import get_calendar
    from connectors.email import get_email
    from connectors.destinations import get_destination

Every default provider ships as a STUB: it returns realistic sample data so the
example agents run end to end with zero real credentials. Each stub also carries
commented-out, copy-pasteable real-API snippets (and the env var to set) so
turning a stub into a real integration is a ~10-line change. See README.md.
"""

from __future__ import annotations

from connectors.calendar import Calendar, Event, get_calendar
from connectors.crm import CRM, Contact, get_crm
from connectors.destinations import Destination, get_destination
from connectors.email import EmailSender, get_email

__all__ = [
    "get_crm",
    "CRM",
    "Contact",
    "get_calendar",
    "Calendar",
    "Event",
    "get_email",
    "EmailSender",
    "get_destination",
    "Destination",
]

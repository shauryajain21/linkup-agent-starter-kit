"""
connectors/crm/ — read/write a customer's CRM behind one tiny interface.

    from connectors.crm import get_crm
    crm = get_crm()                      # HubSpot (default)
    crm = get_crm(provider="salesforce")

A CRM provider exposes exactly three methods:

    find_contact(email)          -> Contact | None
    last_touch(email)            -> datetime.date | None   (date of last activity)
    create_note(contact_email,
                body)            -> dict

`Contact` is a dataclass: name, title, company, email.

The default provider's methods are STUBS that return realistic sample data so the
example agents run with no credentials. Each provider module contains commented
real-API snippets + the env var it reads. Swap providers in one line; the agent
code never changes.
"""

from __future__ import annotations

from connectors.crm.base import CRM, Contact
from connectors.crm.providers import (
    AttioCRM,
    HubSpotCRM,
    PipedriveCRM,
    SalesforceCRM,
)

_PROVIDERS = {
    "hubspot": HubSpotCRM,
    "salesforce": SalesforceCRM,
    "attio": AttioCRM,
    "pipedrive": PipedriveCRM,
}


def get_crm(provider: str = "hubspot", **kwargs) -> CRM:
    """Return a CRM provider instance. Default: HubSpot (stub)."""
    try:
        cls = _PROVIDERS[provider.lower()]
    except KeyError:
        raise ValueError(
            f"Unknown CRM provider {provider!r}. "
            f"Supported: {', '.join(sorted(_PROVIDERS))}."
        )
    return cls(**kwargs)


__all__ = ["get_crm", "CRM", "Contact"]

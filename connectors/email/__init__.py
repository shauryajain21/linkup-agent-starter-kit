"""
connectors/email/ — send email behind one tiny interface.

    from connectors.email import get_email
    mailer = get_email()                     # Resend (default)
    mailer = get_email(provider="sendgrid")

An email provider exposes one method:

    send(to, subject, body_markdown) -> dict   (returns at least a message id)

The default provider prints the message and returns a fake id, so agents can
"send" with no credentials. Each provider carries commented real-API snippets +
the env var it reads.
"""

from __future__ import annotations

from connectors.email.base import EmailSender
from connectors.email.providers import (
    GmailSender,
    MicrosoftGraphSender,
    ResendSender,
    SendGridSender,
)

_PROVIDERS = {
    "resend": ResendSender,
    "gmail": GmailSender,
    "sendgrid": SendGridSender,
    "microsoft": MicrosoftGraphSender,
    "outlook": MicrosoftGraphSender,  # alias
}


def get_email(provider: str = "resend", **kwargs) -> EmailSender:
    """Return an email provider instance. Default: Resend (stub)."""
    try:
        cls = _PROVIDERS[provider.lower()]
    except KeyError:
        raise ValueError(
            f"Unknown email provider {provider!r}. "
            f"Supported: {', '.join(sorted(_PROVIDERS))}."
        )
    return cls(**kwargs)


__all__ = ["get_email", "EmailSender"]

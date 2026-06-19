"""
Email providers: Resend (default), Gmail API, SendGrid, Microsoft Graph / Outlook.

`send()` is a STUB: it prints a summary and returns a fake message id so agents can
"send" with no credentials. The `# --- REAL CALL ---` block in each shows the env
var, endpoint/SDK, and payload to wire it up for real. Most providers want HTML,
so the real blocks note where to convert Markdown (e.g. the `markdown` package).
"""

from __future__ import annotations

import os
import uuid

# The sender identity used by the real-call snippets. Set EMAIL_FROM to a verified
# sender/domain for whichever provider you enable.
_FROM = os.environ.get("EMAIL_FROM", "agent@your-domain.example")


def _stub_send(provider: str, to: str, subject: str, body_markdown: str) -> dict:
    """Shared stub: print a summary, return a fake message id."""
    msg_id = f"{provider}_msg_{uuid.uuid4().hex[:12]}"
    print(
        f"[email stub:{provider}] -> {to}\n"
        f"  subject: {subject}\n"
        f"  body ({len(body_markdown)} chars markdown): "
        f"{body_markdown[:80]}{'...' if len(body_markdown) > 80 else ''}"
    )
    return {"id": msg_id, "to": to, "subject": subject, "provider": provider}


class ResendSender:
    """Resend. Env var: RESEND_API_KEY (Resend renders Markdown-ish HTML happily)."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("RESEND_API_KEY")

    def send(self, to: str, subject: str, body_markdown: str) -> dict:
        # --- STUB ---
        return _stub_send("resend", to, subject, body_markdown)
        # --- REAL CALL: Resend API ---  https://resend.com/docs/api-reference
        # pip install resend
        # import resend, markdown
        # resend.api_key = self.api_key
        # return resend.Emails.send({
        #     "from": _FROM,
        #     "to": to,
        #     "subject": subject,
        #     "html": markdown.markdown(body_markdown),
        # })


class GmailSender:
    """Gmail API. Env var: GOOGLE_GMAIL_CREDENTIALS_JSON (OAuth with gmail.send scope)."""

    def __init__(self, credentials_json: str | None = None) -> None:
        self.credentials_json = credentials_json or os.environ.get(
            "GOOGLE_GMAIL_CREDENTIALS_JSON"
        )

    def send(self, to: str, subject: str, body_markdown: str) -> dict:
        # --- STUB ---
        return _stub_send("gmail", to, subject, body_markdown)
        # --- REAL CALL: Gmail API users.messages.send ---
        # https://developers.google.com/gmail/api/guides/sending
        # pip install google-api-python-client google-auth markdown
        # import base64, markdown
        # from email.mime.text import MIMEText
        # from google.oauth2.credentials import Credentials
        # from googleapiclient.discovery import build
        # creds = Credentials.from_authorized_user_file(
        #     self.credentials_json, ["https://www.googleapis.com/auth/gmail.send"]
        # )
        # service = build("gmail", "v1", credentials=creds)
        # mime = MIMEText(markdown.markdown(body_markdown), "html")
        # mime["to"], mime["from"], mime["subject"] = to, _FROM, subject
        # raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
        # return service.users().messages().send(userId="me", body={"raw": raw}).execute()


class SendGridSender:
    """SendGrid. Env var: SENDGRID_API_KEY."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("SENDGRID_API_KEY")

    def send(self, to: str, subject: str, body_markdown: str) -> dict:
        # --- STUB ---
        return _stub_send("sendgrid", to, subject, body_markdown)
        # --- REAL CALL: SendGrid v3 mail/send ---
        # https://docs.sendgrid.com/api-reference/mail-send/mail-send
        # pip install sendgrid markdown
        # import markdown
        # from sendgrid import SendGridAPIClient
        # from sendgrid.helpers.mail import Mail
        # message = Mail(
        #     from_email=_FROM, to_emails=to, subject=subject,
        #     html_content=markdown.markdown(body_markdown),
        # )
        # resp = SendGridAPIClient(self.api_key).send(message)
        # return {"id": resp.headers.get("X-Message-Id"), "status": resp.status_code}


class MicrosoftGraphSender:
    """Microsoft Graph / Outlook. Env var: MS_GRAPH_ACCESS_TOKEN."""

    def __init__(self, access_token: str | None = None) -> None:
        self.access_token = access_token or os.environ.get("MS_GRAPH_ACCESS_TOKEN")

    def send(self, to: str, subject: str, body_markdown: str) -> dict:
        # --- STUB ---
        return _stub_send("microsoft", to, subject, body_markdown)
        # --- REAL CALL: Microsoft Graph sendMail ---
        # https://learn.microsoft.com/graph/api/user-sendmail
        # import requests, markdown
        # resp = requests.post(
        #     "https://graph.microsoft.com/v1.0/me/sendMail",
        #     headers={"Authorization": f"Bearer {self.access_token}"},
        #     json={"message": {
        #         "subject": subject,
        #         "body": {"contentType": "HTML",
        #                  "content": markdown.markdown(body_markdown)},
        #         "toRecipients": [{"emailAddress": {"address": to}}],
        #     }},
        # )
        # # 202 Accepted, empty body — Graph doesn't return a message id here.
        # return {"id": None, "status": resp.status_code}

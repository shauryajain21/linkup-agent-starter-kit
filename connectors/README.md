# connectors/ — swappable integration stubs

Linkup is the **engine** of an agent (live-web search / fetch / research). The
connectors are its **edges**: where an agent reads context (CRM, calendar) and
where it writes results (email, destinations like Notion or Slack).

## Philosophy: nothing is locked to one vendor

Every category is a **factory** that returns a **provider** object behind a tiny,
documented interface. Your agent code talks to the interface; the vendor is a
one-line config choice.

```python
from connectors.crm import get_crm

crm = get_crm()                       # HubSpot (default)
crm = get_crm(provider="salesforce")  # swap the vendor, agent code unchanged
contact = crm.find_contact("jordan.avery@northwind.example")
```

Unknown provider names raise a `ValueError` listing the supported ones.

## The four categories

| Import | Factory | Interface |
|--------|---------|-----------|
| `from connectors.crm import get_crm` | `get_crm(provider="hubspot")` | `find_contact(email) -> Contact \| None` · `last_touch(email) -> date \| None` · `create_note(contact_email, body) -> dict` |
| `from connectors.calendar import get_calendar` | `get_calendar(provider="google")` | `upcoming_events(days=7) -> list[Event]` |
| `from connectors.email import get_email` | `get_email(provider="resend")` | `send(to, subject, body_markdown) -> dict` |
| `from connectors.destinations import get_destination` | `get_destination(provider="notion")` | `create_page(title, markdown_body, **meta) -> dict` |

Data shapes (dataclasses):

- `Contact(name, title, company, email)`
- `Event(id, title, start, attendees)` — `start` is an ISO 8601 string, `attendees`
  is a list of `{"name", "email"}` dicts.

## The stub-vs-real pattern

Every **default** provider ships as a **stub**: its methods return realistic sample
data (a sample `Contact`, sample `Event`s, a fake message/page id) so the example
agents run **end to end with zero real credentials**.

Inside each stub method, right after the stub `return`, is a clearly-marked
`# --- REAL CALL ---` block: the env var to set, the endpoint/SDK to call, and how
to map the response onto our normalized types. Turning a stub into a real
integration is a ~10-line change:

```python
def find_contact(self, email):
    # --- STUB ---            <- delete this line
    return _sample_contact_for(email)   # <- and this one
    # --- REAL CALL: HubSpot CRM API v3 ---  <- uncomment the block below it
    # resp = requests.post(... search contacts by email ...)
    # ...map fields...
    # return Contact(name=..., title=..., company=..., email=...)
```

The stub `return` sits *above* the real block on purpose: while it's there, the
real code never runs. Remove the two stub lines and uncomment the block to go live.

## Supported providers + env vars

### CRM — `get_crm(provider=...)`
| provider | default | env var(s) | real API |
|----------|:------:|-----------|----------|
| `hubspot` | ✓ | `HUBSPOT_ACCESS_TOKEN` | HubSpot CRM API v3 |
| `salesforce` | | `SALESFORCE_ACCESS_TOKEN`, `SALESFORCE_INSTANCE_URL` | Salesforce REST (SOQL) |
| `attio` | | `ATTIO_API_KEY` | Attio API v2 |
| `pipedrive` | | `PIPEDRIVE_API_TOKEN` | Pipedrive API v1 |

### Calendar — `get_calendar(provider=...)`
| provider | default | env var(s) | real API |
|----------|:------:|-----------|----------|
| `google` | ✓ | `GOOGLE_CALENDAR_CREDENTIALS_JSON` | Google Calendar API v3 |
| `outlook` / `microsoft` | | `MS_GRAPH_ACCESS_TOKEN` | Microsoft Graph `calendarView` |

### Email — `get_email(provider=...)`
| provider | default | env var(s) | real API |
|----------|:------:|-----------|----------|
| `resend` | ✓ | `RESEND_API_KEY` | Resend API |
| `gmail` | | `GOOGLE_GMAIL_CREDENTIALS_JSON` | Gmail API `messages.send` |
| `sendgrid` | | `SENDGRID_API_KEY` | SendGrid v3 `mail/send` |
| `microsoft` / `outlook` | | `MS_GRAPH_ACCESS_TOKEN` | Microsoft Graph `sendMail` |

All email providers also read `EMAIL_FROM` (the verified sender address).

### Destinations — `get_destination(provider=...)`
| provider | default | env var(s) | `**meta` | real API |
|----------|:------:|-----------|----------|----------|
| `notion` | ✓ | `NOTION_API_KEY`, `NOTION_PARENT_PAGE_ID` | — | Notion API (create page) |
| `slack` | | `SLACK_BOT_TOKEN` | `channel` (or `SLACK_DEFAULT_CHANNEL`) | Slack `chat.postMessage` |
| `linear` | | `LINEAR_API_KEY`, `LINEAR_TEAM_ID` | `team_id` | Linear GraphQL `issueCreate` |
| `airtable` | | `AIRTABLE_API_KEY`, `AIRTABLE_BASE_ID` | `table` | Airtable REST (create record) |
| `googledocs` / `google_docs` | | `GOOGLE_DOCS_CREDENTIALS_JSON` | — | Google Docs API |

Only set the env vars for the providers a given agent actually uses. With none set,
every default provider runs as a stub and the example agents still work end to end.

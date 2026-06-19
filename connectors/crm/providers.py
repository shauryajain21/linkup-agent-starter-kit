"""
CRM providers: HubSpot (default), Salesforce, Attio, Pipedrive.

Each class implements the CRM interface (see base.py). The methods here are STUBS
that return sample data so the example agents run with no credentials. Inside each
method, the `# --- REAL CALL ---` block shows exactly how you'd implement it for
real: which env var to read, which endpoint/SDK to hit, and how to map the response
onto our normalized types. Delete the stub return, uncomment the real block, done.
"""

from __future__ import annotations

import datetime
import os

from connectors.crm.base import Contact

# A single sample contact + sample activity date, reused by every stub so the
# example agents get consistent, realistic data regardless of provider.
_SAMPLE_CONTACT = Contact(
    name="Jordan Avery",
    title="VP of Engineering",
    company="Northwind Labs",
    email="jordan.avery@northwind.example",
)
_SAMPLE_LAST_TOUCH = datetime.date.today() - datetime.timedelta(days=12)


def _sample_contact_for(email: str) -> Contact:
    """Return the sample contact, but with the requested email filled in."""
    return Contact(
        name=_SAMPLE_CONTACT.name,
        title=_SAMPLE_CONTACT.title,
        company=_SAMPLE_CONTACT.company,
        email=email,
    )


class HubSpotCRM:
    """HubSpot CRM. Env var: HUBSPOT_ACCESS_TOKEN (private-app token)."""

    def __init__(self, access_token: str | None = None) -> None:
        self.access_token = access_token or os.environ.get("HUBSPOT_ACCESS_TOKEN")

    def find_contact(self, email: str) -> Contact | None:
        # --- STUB: returns sample data so agents run with no creds ---
        return _sample_contact_for(email)
        # --- REAL CALL: HubSpot CRM API v3 (search contacts by email) ---
        # https://developers.hubspot.com/docs/api/crm/contacts
        # import requests
        # resp = requests.post(
        #     "https://api.hubapi.com/crm/v3/objects/contacts/search",
        #     headers={"Authorization": f"Bearer {self.access_token}"},
        #     json={
        #         "filterGroups": [{"filters": [
        #             {"propertyName": "email", "operator": "EQ", "value": email}
        #         ]}],
        #         "properties": ["firstname", "lastname", "jobtitle", "company", "email"],
        #     },
        # )
        # results = resp.json().get("results", [])
        # if not results:
        #     return None
        # p = results[0]["properties"]
        # return Contact(
        #     name=f"{p.get('firstname', '')} {p.get('lastname', '')}".strip(),
        #     title=p.get("jobtitle", ""),
        #     company=p.get("company", ""),
        #     email=p.get("email", email),
        # )

    def last_touch(self, email: str) -> datetime.date | None:
        # --- STUB ---
        return _SAMPLE_LAST_TOUCH
        # --- REAL CALL ---
        # Look up the contact id (as above), then read the
        # `notes_last_contacted` / `hs_last_sales_activity_timestamp` property,
        # or query the engagements/activity timeline:
        #   GET /crm/v3/objects/contacts/{id}?properties=notes_last_contacted
        # Parse the ISO timestamp and return its .date().

    def create_note(self, contact_email: str, body: str) -> dict:
        # --- STUB ---
        return {"id": "note_stub_001", "contact_email": contact_email, "body": body}
        # --- REAL CALL: create a note engagement + associate to the contact ---
        # import requests
        # contact = self.find_contact(contact_email)  # to resolve the contact id
        # resp = requests.post(
        #     "https://api.hubapi.com/crm/v3/objects/notes",
        #     headers={"Authorization": f"Bearer {self.access_token}"},
        #     json={
        #         "properties": {
        #             "hs_note_body": body,
        #             "hs_timestamp": datetime.datetime.utcnow().isoformat(),
        #         },
        #         "associations": [{
        #             "to": {"id": "<contact_id>"},
        #             "types": [{"associationCategory": "HUBSPOT_DEFINED",
        #                        "associationTypeId": 202}],
        #         }],
        #     },
        # )
        # return resp.json()


class SalesforceCRM:
    """Salesforce. Env vars: SALESFORCE_ACCESS_TOKEN, SALESFORCE_INSTANCE_URL."""

    def __init__(
        self,
        access_token: str | None = None,
        instance_url: str | None = None,
    ) -> None:
        self.access_token = access_token or os.environ.get("SALESFORCE_ACCESS_TOKEN")
        self.instance_url = instance_url or os.environ.get("SALESFORCE_INSTANCE_URL")

    def find_contact(self, email: str) -> Contact | None:
        # --- STUB ---
        return _sample_contact_for(email)
        # --- REAL CALL: Salesforce REST API SOQL query ---
        # https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/
        # import requests
        # soql = (
        #     "SELECT Name, Title, Account.Name, Email FROM Contact "
        #     f"WHERE Email = '{email}' LIMIT 1"
        # )
        # resp = requests.get(
        #     f"{self.instance_url}/services/data/v60.0/query",
        #     headers={"Authorization": f"Bearer {self.access_token}"},
        #     params={"q": soql},
        # )
        # records = resp.json().get("records", [])
        # if not records:
        #     return None
        # r = records[0]
        # return Contact(
        #     name=r.get("Name", ""),
        #     title=r.get("Title", ""),
        #     company=(r.get("Account") or {}).get("Name", ""),
        #     email=r.get("Email", email),
        # )

    def last_touch(self, email: str) -> datetime.date | None:
        # --- STUB ---
        return _SAMPLE_LAST_TOUCH
        # --- REAL CALL ---
        # SOQL the contact's LastActivityDate, or the most recent Task/Event:
        #   SELECT LastActivityDate FROM Contact WHERE Email = '...' LIMIT 1
        # Return datetime.date.fromisoformat(records[0]["LastActivityDate"]).

    def create_note(self, contact_email: str, body: str) -> dict:
        # --- STUB ---
        return {"id": "sf_note_stub_001", "contact_email": contact_email, "body": body}
        # --- REAL CALL: create a Note (or ContentNote) linked to the contact ---
        # import requests
        # resp = requests.post(
        #     f"{self.instance_url}/services/data/v60.0/sobjects/Note",
        #     headers={"Authorization": f"Bearer {self.access_token}"},
        #     json={"Title": "Agent note", "Body": body, "ParentId": "<contact_id>"},
        # )
        # return resp.json()


class AttioCRM:
    """Attio. Env var: ATTIO_API_KEY."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("ATTIO_API_KEY")

    def find_contact(self, email: str) -> Contact | None:
        # --- STUB ---
        return _sample_contact_for(email)
        # --- REAL CALL: Attio API — query the `people` object by email ---
        # https://developers.attio.com/reference
        # import requests
        # resp = requests.post(
        #     "https://api.attio.com/v2/objects/people/records/query",
        #     headers={"Authorization": f"Bearer {self.api_key}"},
        #     json={"filter": {"email_addresses": email}, "limit": 1},
        # )
        # data = resp.json().get("data", [])
        # if not data:
        #     return None
        # values = data[0]["values"]
        # return Contact(
        #     name=values["name"][0]["full_name"],
        #     title=values.get("job_title", [{}])[0].get("value", ""),
        #     company=values.get("company", [{}])[0].get("value", ""),
        #     email=email,
        # )

    def last_touch(self, email: str) -> datetime.date | None:
        # --- STUB ---
        return _SAMPLE_LAST_TOUCH
        # --- REAL CALL ---
        # Attio tracks `last_interaction` on person records; read that attribute
        # from the query above, or list notes/activities and take the newest.

    def create_note(self, contact_email: str, body: str) -> dict:
        # --- STUB ---
        return {"id": "attio_note_stub_001", "contact_email": contact_email, "body": body}
        # --- REAL CALL: POST a note attached to the person record ---
        # import requests
        # resp = requests.post(
        #     "https://api.attio.com/v2/notes",
        #     headers={"Authorization": f"Bearer {self.api_key}"},
        #     json={
        #         "data": {
        #             "parent_object": "people",
        #             "parent_record_id": "<record_id>",
        #             "title": "Agent note",
        #             "format": "plaintext",
        #             "content": body,
        #         }
        #     },
        # )
        # return resp.json()


class PipedriveCRM:
    """Pipedrive. Env var: PIPEDRIVE_API_TOKEN (sent as the ?api_token= query param)."""

    def __init__(self, api_token: str | None = None) -> None:
        self.api_token = api_token or os.environ.get("PIPEDRIVE_API_TOKEN")

    def find_contact(self, email: str) -> Contact | None:
        # --- STUB ---
        return _sample_contact_for(email)
        # --- REAL CALL: Pipedrive Persons search ---
        # https://developers.pipedrive.com/docs/api/v1
        # import requests
        # resp = requests.get(
        #     "https://api.pipedrive.com/v1/persons/search",
        #     params={"term": email, "fields": "email", "api_token": self.api_token},
        # )
        # items = resp.json().get("data", {}).get("items", [])
        # if not items:
        #     return None
        # p = items[0]["item"]
        # return Contact(
        #     name=p.get("name", ""),
        #     title=p.get("job_title", ""),
        #     company=(p.get("organization") or {}).get("name", ""),
        #     email=email,
        # )

    def last_touch(self, email: str) -> datetime.date | None:
        # --- STUB ---
        return _SAMPLE_LAST_TOUCH
        # --- REAL CALL ---
        # A person record carries `last_activity_date`; read it from the person
        # detail (GET /v1/persons/{id}) and return datetime.date.fromisoformat(...).

    def create_note(self, contact_email: str, body: str) -> dict:
        # --- STUB ---
        return {"id": "pd_note_stub_001", "contact_email": contact_email, "body": body}
        # --- REAL CALL: create a note linked to the person ---
        # import requests
        # resp = requests.post(
        #     "https://api.pipedrive.com/v1/notes",
        #     params={"api_token": self.api_token},
        #     json={"content": body, "person_id": "<person_id>"},
        # )
        # return resp.json()

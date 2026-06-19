"""
Destination providers: Notion (default), Slack, Linear, Airtable, Google Docs.

`create_page()` is a STUB returning a fake url/id so agents run with no
credentials. The `# --- REAL CALL ---` block in each shows the env var, endpoint/
SDK, and payload. Markdown handling differs per provider (Notion/Slack/Linear take
text/markdown directly; Airtable stores it in a field; Google Docs needs the Docs
API) — the real blocks note where conversion is needed.
"""

from __future__ import annotations

import os
import uuid


class NotionDestination:
    """Notion. Env vars: NOTION_API_KEY, NOTION_PARENT_PAGE_ID (parent page/db)."""

    def __init__(
        self, api_key: str | None = None, parent_page_id: str | None = None
    ) -> None:
        self.api_key = api_key or os.environ.get("NOTION_API_KEY")
        self.parent_page_id = parent_page_id or os.environ.get("NOTION_PARENT_PAGE_ID")

    def create_page(self, title: str, markdown_body: str, **meta) -> dict:
        # --- STUB ---
        page_id = uuid.uuid4().hex
        return {"id": page_id, "url": f"https://notion.so/{page_id}", "title": title}
        # --- REAL CALL: Notion API — create a page under a parent ---
        # https://developers.notion.com/reference/post-page
        # import requests
        # # Notion blocks aren't Markdown; convert (e.g. `md2notion`) or send the
        # # body as one paragraph block as shown here for the simplest case.
        # resp = requests.post(
        #     "https://api.notion.com/v1/pages",
        #     headers={
        #         "Authorization": f"Bearer {self.api_key}",
        #         "Notion-Version": "2022-06-28",
        #     },
        #     json={
        #         "parent": {"page_id": self.parent_page_id},
        #         "properties": {"title": [{"text": {"content": title}}]},
        #         "children": [{
        #             "object": "block", "type": "paragraph",
        #             "paragraph": {"rich_text": [
        #                 {"text": {"content": markdown_body[:2000]}}
        #             ]},
        #         }],
        #     },
        # )
        # data = resp.json()
        # return {"id": data["id"], "url": data.get("url")}


class SlackDestination:
    """Slack. Env var: SLACK_BOT_TOKEN. meta: channel="#..." (or SLACK_DEFAULT_CHANNEL)."""

    def __init__(self, bot_token: str | None = None) -> None:
        self.bot_token = bot_token or os.environ.get("SLACK_BOT_TOKEN")

    def create_page(self, title: str, markdown_body: str, **meta) -> dict:
        channel = meta.get("channel") or os.environ.get("SLACK_DEFAULT_CHANNEL", "#general")
        # --- STUB ---
        ts = f"{uuid.uuid4().int % 10**10}.{uuid.uuid4().int % 10**6}"
        return {"id": ts, "url": f"https://slack.com/archives/STUB/p{ts}", "channel": channel}
        # --- REAL CALL: Slack chat.postMessage ---
        # https://api.slack.com/methods/chat.postMessage
        # import requests
        # # Slack uses *mrkdwn*, not full Markdown — for rich layout build Block Kit
        # # blocks; here we post title + body as a single mrkdwn message.
        # resp = requests.post(
        #     "https://slack.com/api/chat.postMessage",
        #     headers={"Authorization": f"Bearer {self.bot_token}"},
        #     json={"channel": channel, "text": f"*{title}*\n{markdown_body}"},
        # )
        # data = resp.json()
        # return {"id": data.get("ts"), "channel": data.get("channel")}


class LinearDestination:
    """Linear. Env vars: LINEAR_API_KEY, LINEAR_TEAM_ID. meta: team_id overrides env."""

    def __init__(
        self, api_key: str | None = None, team_id: str | None = None
    ) -> None:
        self.api_key = api_key or os.environ.get("LINEAR_API_KEY")
        self.team_id = team_id or os.environ.get("LINEAR_TEAM_ID")

    def create_page(self, title: str, markdown_body: str, **meta) -> dict:
        team_id = meta.get("team_id") or self.team_id
        # --- STUB ---
        ident = f"ENG-{uuid.uuid4().int % 1000}"
        return {"id": ident, "url": f"https://linear.app/issue/{ident}", "title": title}
        # --- REAL CALL: Linear GraphQL — issueCreate ---
        # https://developers.linear.app/docs/graphql/working-with-the-graphql-api
        # import requests
        # query = """
        #   mutation($title: String!, $desc: String!, $teamId: String!) {
        #     issueCreate(input: {title: $title, description: $desc, teamId: $teamId}) {
        #       issue { identifier url }
        #     }
        #   }"""
        # resp = requests.post(
        #     "https://api.linear.app/graphql",
        #     headers={"Authorization": self.api_key},  # Linear takes the raw key
        #     json={"query": query, "variables": {
        #         "title": title, "desc": markdown_body, "teamId": team_id,
        #     }},
        # )
        # issue = resp.json()["data"]["issueCreate"]["issue"]
        # return {"id": issue["identifier"], "url": issue["url"]}


class AirtableDestination:
    """Airtable. Env vars: AIRTABLE_API_KEY, AIRTABLE_BASE_ID. meta: table="..."."""

    def __init__(
        self, api_key: str | None = None, base_id: str | None = None
    ) -> None:
        self.api_key = api_key or os.environ.get("AIRTABLE_API_KEY")
        self.base_id = base_id or os.environ.get("AIRTABLE_BASE_ID")

    def create_page(self, title: str, markdown_body: str, **meta) -> dict:
        table = meta.get("table", "Records")
        # --- STUB ---
        rec_id = f"rec{uuid.uuid4().hex[:14]}"
        return {"id": rec_id, "url": f"https://airtable.com/{self.base_id or 'STUB'}/{rec_id}"}
        # --- REAL CALL: Airtable REST — create record ---
        # https://airtable.com/developers/web/api/create-records
        # import requests
        # resp = requests.post(
        #     f"https://api.airtable.com/v0/{self.base_id}/{table}",
        #     headers={"Authorization": f"Bearer {self.api_key}"},
        #     json={"fields": {"Title": title, "Body": markdown_body}},
        # )
        # data = resp.json()
        # return {"id": data["id"]}


class GoogleDocsDestination:
    """Google Docs. Env var: GOOGLE_DOCS_CREDENTIALS_JSON (OAuth/service-account)."""

    def __init__(self, credentials_json: str | None = None) -> None:
        self.credentials_json = credentials_json or os.environ.get(
            "GOOGLE_DOCS_CREDENTIALS_JSON"
        )

    def create_page(self, title: str, markdown_body: str, **meta) -> dict:
        # --- STUB ---
        doc_id = uuid.uuid4().hex[:24]
        return {"id": doc_id, "url": f"https://docs.google.com/document/d/{doc_id}/edit"}
        # --- REAL CALL: Google Docs API — create then batchUpdate to insert text ---
        # https://developers.google.com/docs/api/how-tos/move-text
        # pip install google-api-python-client google-auth
        # from google.oauth2.service_account import Credentials
        # from googleapiclient.discovery import build
        # creds = Credentials.from_service_account_file(
        #     self.credentials_json,
        #     scopes=["https://www.googleapis.com/auth/documents"],
        # )
        # service = build("docs", "v1", credentials=creds)
        # doc = service.documents().create(body={"title": title}).execute()
        # # Docs has no Markdown import; insert plain text (or parse md into requests).
        # service.documents().batchUpdate(
        #     documentId=doc["documentId"],
        #     body={"requests": [
        #         {"insertText": {"location": {"index": 1}, "text": markdown_body}}
        #     ]},
        # ).execute()
        # return {
        #     "id": doc["documentId"],
        #     "url": f"https://docs.google.com/document/d/{doc['documentId']}/edit",
        # }

# meeting_prep — external connections + Linkup

Generates a one-page prep brief for each of your upcoming meetings. Your
**connected systems** (calendar + CRM) say *who* you're meeting and *when*;
**Linkup** supplies the live, public truth about those people and their
companies; the **LLM** turns it into a skimmable brief. The LLM never recalls
facts on its own — everything factual flows through Linkup.

## What it shows

The connectors-driven agent pattern: trigger from systems you already have
(calendar/CRM), enrich with Linkup, write with the LLM, and keep every claim
cited back to a source URL.

## The flow (and the Linkup choice at each step + why)

1. **Calendar → upcoming meetings.** `connectors.calendar.get_calendar().upcoming_events(days)`.
   No Linkup yet — this is a connected system telling us *who/when*.
2. **CRM → enrich attendees.** `connectors.crm.get_crm().find_contact(email)` for
   title/company, and `.last_touch(email)` for the date of your last interaction.
   `last_touch` is what scopes step 4 to *new* developments only.
3. **Linkup `/search` ×2 per external attendee, in parallel, `depth="standard"`.**
   One query for the person's recent public activity
   (`prompts.ATTENDEE_RECENT_ACTIVITY`), one for what changed at their company
   since the last touchpoint (`prompts.COMPANY_SINCE_LAST_TOUCH`). They're
   independent questions, so we fan them out in parallel rather than chaining —
   `standard` (one agentic iteration, ~1-3s) is the right depth; `deep` would
   only pay off if one query depended on the other's output. Output type is
   `searchResults` (`{name,url,content}`) because it feeds an LLM for grounding,
   not an end user.
4. **Linkup `/fetch` on the top surfaced post (optional).** Search returns
   snippets; `fetch_markdown(url, render_js=True)` pulls the *full* text of the
   single most relevant post so the LLM can quote and reason over it accurately.
   `render_js=True` because most modern post/profile pages are client-rendered.
   Disable with `--no-fetch`.
5. **LLM → one-page brief.** Sections: who you're meeting, company context,
   recent activity & signals, suggested talking points, smart questions —
   grounded strictly in the Linkup findings, with inline `[source](url)` cites.

A single `Linkup()` instance is reused across every search/fetch.

## How connectors plug in (and the sample fallback)

The agent imports two swappable stubs — it does **not** build real integrations:

```python
from connectors.calendar import get_calendar   # .upcoming_events(days) -> [Event]
from connectors.crm import get_crm              # .find_contact(email), .last_touch(email)
```

`Event` has `id, title, start, attendees[{name,email}]`; `Contact` has
`name, title, company, email`. Wire real providers (Google Calendar, HubSpot,
Salesforce, Attio…) behind these interfaces and set the matching env vars in
`.env`. Pick the provider per run with `--calendar` / `--crm`.

If a connector import fails or returns nothing, `load_meetings()` falls back to
the `SAMPLE_EVENTS` constant in `agent.py`, so the demo runs end to end with
**only** `LINKUP_API_KEY` + an LLM key set. Attendees on your own domain
(`DEFAULT_INTERNAL_DOMAINS`, e.g. `linkup.so`) are treated as internal and skipped.

## Run it

```bash
pip install -r requirements.txt          # from the repo root
# set LINKUP_API_KEY and ANTHROPIC_API_KEY in .env

python -m agents.meeting_prep.run            # next 7 days (sample fallback if no creds)
python -m agents.meeting_prep.run --days 14
python -m agents.meeting_prep.run --no-fetch # skip the /fetch step
```

Programmatic use:

```python
from agents.meeting_prep import run_meeting_prep
briefs = run_meeting_prep(days=7)            # list[Brief] with .brief_markdown + .sources
```

## Extension ideas

- **Deliver the brief.** Push each `brief.brief_markdown` to Slack/email the
  morning of the meeting via a destination connector instead of printing.
- **Schedule it.** Run on a cron or Linkup `/tasks` batch each morning so briefs
  land before your first call without you triggering anything.
- **Deep-dive big accounts.** For high-value meetings, swap the two `standard`
  searches for a Linkup `/research` run (`mode="investigate"`) to produce a
  longer, multi-source account dossier.

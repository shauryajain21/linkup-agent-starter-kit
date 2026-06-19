"""
meeting_prep agent — external connections + Linkup.

The shape of this agent is the point: *connected systems tell you WHO and WHEN
(calendar + CRM); Linkup tells you the live, public truth about them.* The LLM
only ever reasons over what Linkup returns — it never recalls facts on its own.

Pipeline (one pass per upcoming meeting):

    calendar.upcoming_events ─┐
                              ├─▶ enrich_attendee (CRM: title/company/last touch)
    crm.find_contact ─────────┘
                              └─▶ research_attendee (Linkup /search x2 in parallel,
                                     optional /fetch on a surfaced post URL)
                                  └─▶ write_brief (LLM grounds on findings only)

Connectors are imported stubs (connectors.calendar / connectors.crm). If they
are missing or return nothing, we fall back to SAMPLE_EVENTS so the demo always
runs end to end — see load_meetings().
"""

from __future__ import annotations

import datetime as _dt
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

from linkup_engine import Linkup, get_llm, prompts

# --- Data shapes -----------------------------------------------------------
# Plain dataclasses so briefs are easy to serialize, print, or push downstream
# (Slack/email/Notion). Nothing here depends on a specific connector.


@dataclass
class Attendee:
    """An external person you're meeting, after CRM enrichment."""

    name: str
    email: str
    title: str = ""
    company: str = ""
    last_touch: str | None = None  # ISO date of last logged interaction, if any


@dataclass
class AttendeeResearch:
    """Everything Linkup surfaced about one attendee + their company."""

    attendee: Attendee
    recent_activity: list[dict] = field(default_factory=list)  # {name,url,content}
    company_changes: list[dict] = field(default_factory=list)  # {name,url,content}
    fetched_post: dict | None = None  # {"url", "markdown"} when we pulled a full post
    sources: list[str] = field(default_factory=list)


@dataclass
class Brief:
    """A one-page prep brief for a single meeting."""

    event_id: str
    title: str
    start: str
    attendees: list[AttendeeResearch]
    brief_markdown: str
    sources: list[str] = field(default_factory=list)


# --- Sample fallback -------------------------------------------------------
# Keeps the demo runnable before any calendar/CRM credentials are wired. This is
# the ONLY hard-coded data in the agent; everything factual still flows through
# Linkup at research time.

SAMPLE_EVENTS: list[dict] = [
    {
        "id": "sample-1",
        "title": "Intro call — Acme Robotics",
        "start": (_dt.datetime.now() + _dt.timedelta(days=2)).isoformat(),
        "attendees": [
            {"name": "Jensen Huang", "email": "jensen@nvidia.com"},
            {"name": "You", "email": "shaurya@linkup.so"},  # your own org -> skipped
        ],
    }
]

# Treat attendees on your own domain as internal and skip them. Override via the
# `internal_domains` argument to run_meeting_prep() / load_meetings().
DEFAULT_INTERNAL_DOMAINS = ("linkup.so",)


# --- Step 1: load meetings (calendar + sample fallback) --------------------


def load_meetings(
    days: int = 7,
    provider: str = "google",
    internal_domains: tuple[str, ...] = DEFAULT_INTERNAL_DOMAINS,
) -> list[dict]:
    """Pull upcoming events from the calendar connector.

    Connectors are swappable stubs (another part of the kit wires real creds).
    If the import fails or the connector returns nothing, we fall back to
    SAMPLE_EVENTS so `run.py` demonstrates the full flow with zero setup.
    """
    events: list[Any] = []
    try:
        from connectors.calendar import get_calendar  # imported, not built here

        cal = get_calendar(provider=provider)
        events = cal.upcoming_events(days=days) or []
    except Exception as exc:  # missing connector, no creds, etc.
        print(f"[meeting_prep] calendar connector unavailable ({exc!r}); using SAMPLE_EVENTS")

    if not events:
        events = SAMPLE_EVENTS

    # Normalize Event objects / dicts into a single dict shape we control.
    return [_normalize_event(e) for e in events]


def _normalize_event(e: Any) -> dict:
    """Accept either an Event object (attrs) or a dict and emit a plain dict."""
    get = (lambda k, d=None: getattr(e, k, d)) if not isinstance(e, dict) else e.get
    start = get("start")
    if isinstance(start, _dt.datetime):
        start = start.isoformat()
    return {
        "id": str(get("id", "")),
        "title": get("title", "(untitled meeting)"),
        "start": str(start or ""),
        "attendees": list(get("attendees", []) or []),
    }


def _is_external(email: str, internal_domains: tuple[str, ...]) -> bool:
    domain = email.split("@")[-1].lower() if "@" in email else ""
    return bool(domain) and domain not in internal_domains


# --- Step 2: enrich attendee from CRM --------------------------------------


def enrich_attendee(raw: dict, provider: str = "hubspot") -> Attendee:
    """Look the attendee up in the CRM to get title, company, and last touch.

    The calendar only knows name + email. The CRM is where the relationship
    context lives — title/company anchor the Linkup queries, and last_touch
    scopes the "what changed since" search so we surface only NEW developments.
    Falls back gracefully to just the calendar fields if the CRM has no match.
    """
    name = raw.get("name", "")
    email = raw.get("email", "")
    title = company = ""
    last_touch: str | None = None

    try:
        from connectors.crm import get_crm  # imported, not built here

        crm = get_crm(provider=provider)
        contact = crm.find_contact(email)
        if contact is not None:
            name = getattr(contact, "name", name) or name
            title = getattr(contact, "title", "") or ""
            company = getattr(contact, "company", "") or ""
        touch = crm.last_touch(email)
        if touch is not None:
            last_touch = touch.isoformat() if hasattr(touch, "isoformat") else str(touch)
    except Exception as exc:
        print(f"[meeting_prep] CRM connector unavailable for {email} ({exc!r}); using calendar fields only")

    # If we still have no company, infer it from the email domain so the Linkup
    # queries have *something* concrete to anchor on.
    if not company and "@" in email:
        company = email.split("@")[-1].split(".")[0].title()

    return Attendee(name=name, email=email, title=title, company=company, last_touch=last_touch)


# --- Step 3: research the attendee with Linkup -----------------------------


def research_attendee(lk: Linkup, attendee: Attendee, fetch_top_post: bool = True) -> AttendeeResearch:
    """Two parallel `standard` Linkup searches + an optional `fetch`.

    Why this shape:
      - The two questions (what THEY said vs. what changed at their COMPANY) are
        independent, so we fire them in parallel at `standard` depth — the
        everyday default: one agentic iteration, ~1-3s each. No need for `deep`
        here because neither query depends on the other's output.
      - We use `search_results` (the {name,url,content} shape) because the output
        feeds an LLM for grounding, not an end user.
      - We then optionally `/fetch` the single most relevant surfaced post URL to
        pull its *full* text — search returns snippets; a fetch gives the LLM the
        whole article/post to quote and reason over accurately.
    """
    activity_q = prompts.fill(
        prompts.ATTENDEE_RECENT_ACTIVITY,
        name=attendee.name,
        title=attendee.title or "their role",
        company=attendee.company or "their company",
    )
    since = attendee.last_touch or "the last 6 months"
    company_q = prompts.fill(
        prompts.COMPANY_SINCE_LAST_TOUCH,
        company=attendee.company or "their company",
        since_date=since,
    )

    # Reuse the one Linkup() instance; just fan out the two independent searches.
    with ThreadPoolExecutor(max_workers=2) as pool:
        f_activity = pool.submit(lk.search_results, activity_q, depth="standard")
        f_company = pool.submit(lk.search_results, company_q, depth="standard")
        recent_activity = f_activity.result() or []
        company_changes = f_company.result() or []

    fetched_post: dict | None = None
    if fetch_top_post and recent_activity:
        top_url = recent_activity[0].get("url")
        if top_url:
            try:
                # render_js=True by default — most modern post/profile pages are
                # client-rendered. Pull the full markdown for the richest grounding.
                markdown = lk.fetch_markdown(top_url, render_js=True)
                if markdown:
                    fetched_post = {"url": top_url, "markdown": markdown[:6000]}
            except Exception as exc:
                print(f"[meeting_prep] fetch failed for {top_url} ({exc!r}); continuing with snippets")

    sources = [
        r["url"]
        for r in (recent_activity + company_changes)
        if isinstance(r, dict) and r.get("url")
    ]
    return AttendeeResearch(
        attendee=attendee,
        recent_activity=recent_activity,
        company_changes=company_changes,
        fetched_post=fetched_post,
        sources=sources,
    )


# --- Step 4: write the prep brief with the LLM -----------------------------

_BRIEF_SYSTEM = (
    "You are a meeting-prep assistant for a sales/CS rep. Write a tight, "
    "one-page prep brief. Ground EVERY factual claim in the supplied Linkup "
    "findings and cite the source URL inline like [source](url). If the findings "
    "don't cover something, say so plainly — never invent facts, dates, or "
    "quotes. No emojis. Be concise and useful for someone skimming 5 minutes "
    "before the call."
)


def _format_findings(research: list[AttendeeResearch]) -> str:
    """Render the Linkup findings into a compact text block for the LLM."""
    lines: list[str] = []
    for r in research:
        a = r.attendee
        lines.append(f"## Attendee: {a.name} — {a.title or 'unknown title'} at {a.company or 'unknown company'}")
        if a.last_touch:
            lines.append(f"Last logged touchpoint: {a.last_touch}")
        lines.append("### Recent public activity (Linkup /search):")
        for item in r.recent_activity[:5] or ["(none found)"]:
            if isinstance(item, dict):
                lines.append(f"- {item.get('name','')}: {item.get('content','')[:400]} ({item.get('url','')})")
            else:
                lines.append(f"- {item}")
        lines.append(f"### Company changes since {a.last_touch or 'last touch'} (Linkup /search):")
        for item in r.company_changes[:5] or ["(none found)"]:
            if isinstance(item, dict):
                lines.append(f"- {item.get('name','')}: {item.get('content','')[:400]} ({item.get('url','')})")
            else:
                lines.append(f"- {item}")
        if r.fetched_post:
            lines.append(f"### Full text of top post (Linkup /fetch — {r.fetched_post['url']}):")
            lines.append(r.fetched_post["markdown"][:3000])
        lines.append("")
    return "\n".join(lines)


def write_brief(llm, event: dict, research: list[AttendeeResearch]) -> str:
    """Have the LLM compose the one-page brief from the Linkup findings only."""
    if not research:
        return (
            f"# {event['title']}\n\n"
            "No external attendees to research for this meeting."
        )

    user = (
        f"Meeting: {event['title']}\n"
        f"Starts: {event['start']}\n\n"
        "Write a one-page prep brief with these sections:\n"
        "1. Who you're meeting (name, title, company — one line each)\n"
        "2. Company context (what's changed recently / why it matters now)\n"
        "3. Recent activity & what it signals\n"
        "4. Suggested talking points (3-4)\n"
        "5. Smart questions to ask (3-4)\n\n"
        "Base everything strictly on these Linkup findings:\n\n"
        f"{_format_findings(research)}"
    )
    return llm.complete(system=_BRIEF_SYSTEM, user=user, max_tokens=1400)


# --- Orchestrator ----------------------------------------------------------


def run_meeting_prep(
    days: int = 7,
    calendar_provider: str = "google",
    crm_provider: str = "hubspot",
    internal_domains: tuple[str, ...] = DEFAULT_INTERNAL_DOMAINS,
    fetch_top_post: bool = True,
) -> list[Brief]:
    """End-to-end: calendar -> CRM enrich -> Linkup research -> LLM brief.

    Returns one structured Brief per upcoming meeting that has at least one
    external attendee. Reuses a single Linkup() instance across all searches.
    """
    lk = Linkup()
    llm = get_llm()

    events = load_meetings(days=days, provider=calendar_provider, internal_domains=internal_domains)
    briefs: list[Brief] = []

    for event in events:
        # Enrich only EXTERNAL attendees — internal folks need no public research.
        externals = [
            a for a in event["attendees"]
            if isinstance(a, dict) and _is_external(a.get("email", ""), internal_domains)
        ]
        if not externals:
            print(f"[meeting_prep] '{event['title']}' has no external attendees; skipping")
            continue

        attendees = [enrich_attendee(a, provider=crm_provider) for a in externals]

        # Research attendees in parallel; each call already parallelizes its own
        # two searches, so cap workers to keep total concurrency reasonable.
        with ThreadPoolExecutor(max_workers=max(1, len(attendees))) as pool:
            research = list(
                pool.map(lambda att: research_attendee(lk, att, fetch_top_post=fetch_top_post), attendees)
            )

        brief_md = write_brief(llm, event, research)
        sources = sorted({s for r in research for s in r.sources})
        briefs.append(
            Brief(
                event_id=event["id"],
                title=event["title"],
                start=event["start"],
                attendees=research,
                brief_markdown=brief_md,
                sources=sources,
            )
        )

    return briefs

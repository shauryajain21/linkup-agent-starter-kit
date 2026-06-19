# Patterns

The three reference agents in `agents/` are concrete instances of three reusable
patterns. This page generalizes each one so you can lift it into your own agent.
Every pattern is the same backbone — *trigger → LLM plans → Linkup grounds → LLM
writes → destination* — with a different Linkup shape in the middle.

For the runnable versions, see [`agents/lead_research`](../agents/lead_research),
[`agents/meeting_prep`](../agents/meeting_prep), and
[`agents/seo_content`](../agents/seo_content).

---

## Pattern 1 — Chained search (lead research)

**Idea.** Discover entities, then research each one at progressively finer grain,
each Linkup call grounding the next. The LLM appears only at the end, to *write*.

```
discover ──▶ research company ──▶ find people ──▶ research top person ──▶ draft note
   │              │  │                 │                  │                   │
structured    standard standard    structured          standard             LLM
(optional)    (overview)(signal)   (extract)          (depends on          (grounded
              └─ parallel ─┘                          picked person)        in findings)
```

**When to use it.** You start from a seed (a query or a name) and need to build up
a layered profile: company → people → a specific person. Each layer narrows based
on the previous one.

**Endpoint sequence.**

1. `search` `structured` (optional) — turn a discovery query into a clean list of
   entity names.
2. `search` `standard` ×N **in parallel** — independent facts per entity (overview
   + a recent signal). They don't depend on each other, so don't pay for `deep`.
3. `search` `structured` — extract decision-makers as `{name, title, url}` rows so
   you can pick a target and parameterize the next query.
4. `search` `standard` — research the *specific* person you picked. This is a
   genuine chain (the query is built from step 3's output), still `standard`
   unless you need to chain into their posts/commentary (then `deep`).
5. LLM — draft the output grounded *only* in steps 2-4.

**Code sketch.**

```python
from concurrent.futures import ThreadPoolExecutor
from linkup_engine import Linkup, get_llm

lk, llm = Linkup(), get_llm()

# 1. discover (structured) — or skip if you already have the entity
names = lk.search_structured("seed-stage devtools startups that raised recently",
                             schema_companies)["companies"]

for company in names:
    # 2. independent facts -> parallel standard searches
    with ThreadPoolExecutor(max_workers=2) as pool:
        overview, signal = pool.map(
            lambda q: lk.search_results(q, depth="standard"),
            [f"What does {company} do?", f"{company} recent funding/news, with URL"],
        )
    # 3. extract people (structured, shallow schema)
    people = lk.search_structured(f"Current C-suite at {company}, name/title/url",
                                  schema_people)["people"]
    # 4. chain on the picked person
    bg = lk.search_results(f"Background on {people[0]['name']} at {company}",
                           depth="standard") if people else []
    # 5. LLM writes, grounded only in the above
    note = llm.complete(system=OUTREACH_SYS, user=render(overview, signal, bg))
```

See `agents/lead_research/agent.py` for the full version with source-carrying and
dataclasses.

---

## Pattern 2 — External connections (meeting prep)

**Idea.** A connected system tells you **who** and **when** (calendar + CRM);
Linkup tells you the live, public **truth** about them; the LLM writes the brief;
a connector delivers it.

```
calendar.upcoming_events ─┐
                          ├─▶ CRM.enrich (title, company, last_touch)
crm.find_contact ─────────┘            │
                                       ├─▶ Linkup /search ×2 parallel (activity + company change)
                                       │       └─▶ optional /fetch the top post (full text)
                                       └─▶ LLM writes brief ─▶ connector out (Slack/email/Notion)
```

**When to use it.** The trigger and the *targets* come from your own systems
(calendar event, CRM record, support ticket), and you need to enrich each target
with current public facts before acting.

**Endpoint sequence.**

1. Connector in — pull entities from calendar/CRM (the "who/when").
2. Connector enrich — CRM lookup for title, company, and `last_touch` (which
   scopes the "what changed since" search).
3. `search` `standard` ×2 **in parallel** per entity — what *they* said vs. what
   changed at their *company*. Independent → parallel.
4. `fetch` (optional) — pull the full markdown of the single most relevant
   surfaced URL, because search returns snippets and the LLM reasons better over
   full text. `render_js=True` by default.
5. LLM — write the brief, citing source URLs inline.
6. Connector out — deliver to a destination.

**Code sketch.**

```python
events = calendar.upcoming_events(days=7)
for event in events:
    for raw in external_attendees(event):
        attendee = crm.enrich(raw)                       # title, company, last_touch
        with ThreadPoolExecutor(max_workers=2) as pool:  # independent -> parallel
            activity, company_news = pool.map(
                lambda q: lk.search_results(q, depth="standard"),
                [activity_query(attendee), company_since_query(attendee)],
            )
        full = lk.fetch_markdown(activity[0]["url"]) if activity else ""  # optional depth
        brief = llm.complete(system=BRIEF_SYS, user=render(attendee, activity,
                                                           company_news, full))
        # destination.send(brief)  # Slack / email / Notion
```

See `agents/meeting_prep/agent.py`. Connectors are swappable stubs in
`connectors/` (each is a tiny interface — e.g. CRM exposes `find_contact`,
`last_touch`, `create_note`).

---

## Pattern 3 — Fetch + research (SEO content)

**Idea.** Use `fetch` for the pages you *already know* (yours, competitors'), use
`research` for the open-ended "what should this say?" question, and have the LLM
do the gap analysis and the writing.

```
fetch your URL ──┐
                 ├─▶ LLM gap analysis (what's missing / best angle)
fetch competitor ┘            │
URLs (parallel)               ▼
                       /research the topic (deep, cited) ──▶ LLM writes article ──▶ destination (Notion)
```

**When to use it.** You have a set of known reference URLs to ground against and a
broad question whose answer needs minutes of synthesis with citations.

**Endpoint sequence.**

1. `fetch` ×N **in parallel** — your page and each competitor page → clean
   markdown. Deterministic; you have the URLs.
2. LLM — read the markdown, name the content gap and the best angle.
3. `research` `mode="research"` (or `investigate`) — deep, cited synthesis of what
   the article should cover. Async: `start_research` → poll `get_research`.
4. LLM — write the full article, grounded in the research.
5. Connector out — publish the draft (e.g. Notion), with a local-file fallback.

**Code sketch.**

```python
# 1. fetch known URLs in parallel
with ThreadPoolExecutor(max_workers=4) as pool:
    pages = list(pool.map(lk.fetch_markdown, [our_url, *competitor_urls]))

# 2. LLM finds the gap
gap = llm.complete(system=GAP_SYS, user=render_pages(pages, keyword))

# 3. deep research (async; poll in real apps)
rid = lk.start_research(seo_research_query(keyword, gap), mode="research",
                        reasoning_depth="L")
research = poll_until_complete(lk, rid)          # get_research until completed

# 4. LLM writes, grounded in the research
article = llm.complete(system=WRITE_SYS, user=research["answer"])
# 5. destination.publish(article)  # Notion, with local fallback
```

See `agents/seo_content/` for the reference implementation of this pattern.

---

## Composing patterns

These aren't mutually exclusive — real agents stack them:

- **Lead research → meeting prep**: chained search discovers and qualifies a lead,
  then the external-connections pattern preps the call once it's booked.
- **Fetch+research inside chained search**: when researching one entity needs a
  cited report rather than a quick search, swap that step's `search` for a
  `research` call.
- **Any pattern → destination connector**: every pattern ends by writing somewhere
  (CRM note, Slack, Notion, email). The destination is just the last edge.

The constant is the discipline: facts come from Linkup, the LLM only synthesizes,
and sources carry through to the output.

---

## Bulk and scheduled runs via /tasks

Any single-entity pattern becomes a batch job by wrapping its Linkup calls in
`/tasks` (1-100 per call, types mixed freely) and putting a scheduler in front of
the trigger.

```python
# Enrich a whole list overnight: one batch of mixed tasks
batch = lk.tasks([
    {"type": "search",  "input": {"q": f"{c} recent funding", "depth": "standard"}}
    for c in companies
] + [
    {"type": "research", "input": {"q": f"{c} competitive position", "mode": "investigate"}}
    for c in priority_companies
])
```

Pair `/tasks` with cron, Temporal, Airflow, Prefect, Inngest, Trigger.dev, GitHub
Actions, or Modal (see [06-providers.md](./06-providers.md)) to run lead lists
nightly, refresh briefs each morning, or regenerate content weekly.

Next: the [exhaustive provider menu](./06-providers.md) for everything you can
plug in around Linkup.

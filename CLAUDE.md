# Building agents with Linkup — instructions for the coding agent

You (Claude Code, or any coding agent reading this) are working in a starter kit
for building **AI agents powered by [Linkup](https://linkup.so)**. Linkup is the
agent's connection to the **live web**: real-time search, clean page extraction,
and autonomous deep research. Your job is to help the user build agents where
**Linkup is the engine** — the source of fresh, grounded facts — and the LLM is
the reasoning/formatting layer on top.

Read this file before writing code. It is the contract for how to use Linkup well.

## The mental model

```
        ┌─────────────────────── your agent ───────────────────────┐
  trigger ─▶  LLM plans  ─▶  LINKUP (search / fetch / research)  ─▶  LLM writes  ─▶  destination
                              ▲  the engine: fresh web facts         (Notion, CRM, Slack, email)
                              └── everything grounded here ──┘
```

If a step needs a fact that isn't in the prompt or a connected system, it comes
from Linkup. Never let the LLM invent facts about the world — fetch them.

## The four endpoints (this is the whole API surface)

Use `linkup_engine.Linkup` (see `linkup_engine/client.py`). It maps 1:1 to REST.

| Endpoint | Method | When to use | Latency |
|----------|--------|-------------|---------|
| **search** | `lk.search(query, depth=...)` | Find/answer something on the live web | `fast` <1s · `standard` ~1-3s · `deep` ~5-30s |
| **fetch** | `lk.fetch(url)` | You already have a URL → clean markdown | ~1s |
| **research** | `lk.research(query, mode=...)` | A question one query can't resolve | 2-20 min (async) |
| **tasks** | `lk.tasks([...])` | Batch up to 100 of the above | async |

### Choosing search depth
- **`fast`** — keyword lookup, no scraping, sub-second. Autocomplete, cheap checks.
- **`standard`** — the everyday default. One agentic iteration. Can scrape **one**
  URL if you put it in the query. Fire several in **parallel** to cover many angles.
- **`deep`** — up to 10 iterations. Use **only when the next step depends on the
  previous one** (search → pick a result → scrape it → search again).

### Choosing output type
- **`searchResults`** — array of `{name, url, content}`. Best for **LLM grounding**.
- **`sourcedAnswer`** — prose + sources. Best for **showing an end user**.
- **`structured`** — JSON matching your schema. Best for **pipelines**. Keep schemas
  shallow. Always pair extraction prompts with this so you get clean fields, not prose.

### research modes
`answer` (precise evidence-backed answer) · `investigate` (focused report on one
subject) · `research` (broad multi-topic report). Set `mode` explicitly for
predictable latency/shape. `reasoningDepth`: `S`/`M`/`L`/`XL` (more = slower, deeper).
research is **async** — in real apps use `start_research()` + `get_research()` and
poll; the blocking `research()` helper is for scripts/demos only.

## How to write a Linkup query (highest-leverage skill)

Linkup runs an **agentic** search, so write a clear natural-language **goal**, not
keywords. The templates in `linkup_engine/prompts.py` are the reference.

1. **State the goal, not keywords.** ✅ "Find the current CFO of {company} and their
   prior roles, with a source URL." ❌ "{company} CFO".
2. **Name the source to scrape it.** A URL in the query → Linkup fetches that page.
   `standard` scrapes one; `deep` chains several.
3. **Constrain with parameters, not prose.** Use `include_domains`, `from_date`/
   `to_date` instead of "from official sites" / "recently".
4. **Ask for the fields you'll use**, and pair with a `structured` schema.
5. **Parallelize independent lookups**; **chain (deep) dependent ones.**

## Repo layout

```
linkup_engine/      The engine. Linkup client + pluggable LLM + prompt templates.
agents/             Three runnable reference agents (the patterns below). Copy one to start.
connectors/         Stub integrations (CRM, email, calendar, destinations). Show how to plug in.
docs/               Deep dives: endpoints, prompting, patterns, and an exhaustive provider menu.
```

## The three reference patterns (in `agents/`)

1. **`lead_research/` — chained `/search`.** Find companies → research each company →
   research the people → LLM drafts a personalized outreach note.
2. **`meeting_prep/` — external connections.** Pull events from calendar + CRM →
   for each attendee, `/search` recent activity and `/fetch` their latest posts →
   LLM writes a one-page prep brief.
3. **`seo_content/` — `/fetch` + `/research`.** `/fetch` your site and competitors' →
   `/research` the SEO topic deeply → LLM writes the article → push to Notion.

## Working agreements for this repo

- **Keep Linkup the engine.** Any real-world fact flows through search/fetch/research.
- **Ground, then reason.** Pass Linkup output to the LLM; don't ask the LLM to recall.
- **Connectors are swappable stubs.** Each exposes a tiny interface; the user wires
  real credentials. Don't hard-code one CRM/LLM — read the provider from config.
- **Cite sources.** Carry `url`s through to the final output wherever you can.
- **Prefer `standard` + parallel** over `deep` unless steps are genuinely dependent.
- When the user names a library/SDK, check current docs (context7 / official docs)
  rather than relying on memory.

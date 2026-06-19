# Linkup Agent Starter Kit

> Build production AI agents on the live web. **Linkup is the engine** — real-time
> search, clean page extraction, and autonomous research — and your LLM is the
> reasoning layer on top. This repo shows, with three runnable agents, how little
> code it takes to wire that together.

Hand this repo to your coding agent (Claude Code, Cursor, etc.) and start building.
It will read [`CLAUDE.md`](./CLAUDE.md) and already know how to use Linkup well.

## Why Linkup is the engine

LLMs are frozen at their training cutoff and hallucinate about the present. An agent
is only as good as the facts it acts on. Linkup is the layer that gives an agent
**current, sourced reality**:

- **`/search`** — agentic web search in one call. `fast` (sub-second), `standard`
  (~1-3s, scrapes a URL you name), `deep` (chains search→scrape→search).
- **`/fetch`** — any URL → clean LLM-ready markdown in ~1s.
- **`/research`** — an autonomous agent that runs for minutes and returns a synthesized,
  **cited** report.
- **`/tasks`** — batch up to 100 of the above for bulk/scheduled jobs.

One small client (`linkup_engine/client.py`, ~zero magic, just REST) is all four.

## Quickstart

```bash
git clone <this-repo> && cd linkup-agent-starter-kit
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # add LINKUP_API_KEY + your LLM key

# Smoke-test the engine:
python -c "from linkup_engine import Linkup; print(Linkup().search('what is Linkup?', depth='standard'))"

# Run a reference agent:
python -m agents.lead_research.run --company "Linkup"
```

Get a Linkup key at **https://app.linkup.so**.

## Three reference agents

Each is a small, real, end-to-end example of one core pattern. Copy one and adapt.

| Agent | Pattern | What it does |
|-------|---------|--------------|
| [`agents/lead_research`](./agents/lead_research) | **Chained `/search`** | Company → people → personalized outreach note |
| [`agents/meeting_prep`](./agents/meeting_prep) | **External connections** | Calendar + CRM → per-attendee research → prep brief |
| [`agents/seo_content`](./agents/seo_content) | **`/fetch` + `/research`** | Your site + competitors → researched, written article → Notion |

## What's in the box

- **`linkup_engine/`** — the shared core: the Linkup client, a one-line-swappable LLM
  layer (Claude by default), and a library of battle-tested Linkup query templates.
- **`connectors/`** — drop-in stubs for CRMs, email, calendar, and destinations so you
  can see exactly where real credentials plug in. **Nothing is locked to one vendor.**
- **`docs/`** — deep dives on the endpoints, how to prompt Linkup, the patterns above,
  and an **exhaustive menu of providers** (LLMs, CRMs, email, calendars, destinations,
  frameworks) you can build on top.

## Make it yours

- **Pick your LLM**: `LLM_PROVIDER=anthropic` (default) or `openai`; add any other in
  `linkup_engine/llm.py`. See [`docs/06-providers.md`](./docs/06-providers.md).
- **Pick your connectors**: wire HubSpot/Salesforce/Attio, Gmail/Resend, Google
  Calendar, Notion/Slack — or anything else — into the stubs in `connectors/`.
- **Pick your framework**: the engine is plain Python and works standalone or inside
  LangChain, CrewAI, LlamaIndex, the Vercel AI SDK, an MCP server, etc.

## Docs map

| File | What |
|------|------|
| [`docs/01-linkup-as-the-engine.md`](./docs/01-linkup-as-the-engine.md) | The philosophy and architecture |
| [`docs/02-the-four-endpoints.md`](./docs/02-the-four-endpoints.md) | search / fetch / research / tasks in depth |
| [`docs/03-prompting-linkup.md`](./docs/03-prompting-linkup.md) | How to write queries that get great results |
| [`docs/04-depth-and-output.md`](./docs/04-depth-and-output.md) | Choosing depth and output type |
| [`docs/05-patterns.md`](./docs/05-patterns.md) | The three patterns, generalized |
| [`docs/06-providers.md`](./docs/06-providers.md) | Exhaustive provider menu |

---

Built on [Linkup](https://linkup.so) · [Docs](https://docs.linkup.so) · [API ref](https://api.linkup.so/v1/openapi.json)

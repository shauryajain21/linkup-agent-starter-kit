# The four endpoints

Linkup's entire API surface is four endpoints. Everything else in this kit is a
thin wrapper over them.

Base URL: `https://api.linkup.so/v1`
Auth: `Authorization: Bearer <LINKUP_API_KEY>` on every request.

| Endpoint | Method | What it does | Latency | Sync/async |
|----------|--------|--------------|---------|------------|
| `/search` | POST | Web search in one call | `fast` <1s · `standard` ~1-3s · `deep` ~5-30s | sync |
| `/fetch` | POST | URL → clean markdown | ~1s | sync |
| `/research` | POST | Autonomous multi-step research → cited report | 2-20 min | async (poll) |
| `/tasks` | POST | Batch of 1-100 of the above | varies | async |

In Python, all four are on one client:

```python
from linkup_engine import Linkup
lk = Linkup()   # reads LINKUP_API_KEY from the environment
```

The client maps 1:1 to REST (`linkup_engine/client.py`), so the curl below and
the Python above do the same thing.

---

## /search — synchronous web search

**What it is.** An agentic web search that, in a single call, can plan, search,
and (at `standard`/`deep`) scrape pages — then return either raw results, a
written answer, or structured JSON. This is your default tool.

**Request fields.**

| Field | Type | Notes |
|-------|------|-------|
| `q` | string | The query. Write a natural-language **goal**, not keywords. |
| `depth` | `fast` \| `standard` \| `deep` | See below. Default `standard`. |
| `outputType` | `searchResults` \| `sourcedAnswer` \| `structured` | What shape to return. Default `searchResults`. |
| `structuredOutputSchema` | JSON Schema | Required when `outputType=structured`. Keep it shallow. |
| `includeImages` | bool | Return image URLs alongside results. |
| `includeDomains` | string[] | Allow-list (max 100). Constrain instead of saying "official sites" in prose. |
| `excludeDomains` | string[] | Block-list. |
| `fromDate` / `toDate` | ISO 8601 | Time-box results instead of saying "recently". |
| `maxResults` | int | Cap the number of results. |
| `includeSources` | bool | Attach source metadata. |

**Depth — the most important choice.**

- **`fast`** — sub-second, keyword-only, no LLM, no scraping (beta). For
  autocomplete, cheap existence checks, latency-critical lookups.
- **`standard`** — the everyday default. One agentic iteration, ~1-3s. Can scrape
  **one** URL if you name it in the query. Fire several in **parallel** to cover
  many independent angles cheaply.
- **`deep`** — up to 10 iterations, ~5-30s. Can chain search → pick a result →
  scrape it → search again. Use **only when the next step depends on the previous
  step's output**.

**Output types** (full decision guide in [04-depth-and-output.md](./04-depth-and-output.md)):

- `searchResults` → array of `{name, url, content}`. Best for **LLM grounding**.
- `sourcedAnswer` → `{answer, sources}` — prose + sources. Best for **end-user display**.
- `structured` → JSON matching your schema. Best for **pipelines**.

**Python (engine API).**

```python
# Grounding: raw results to feed an LLM
results = lk.search_results("What does Linkup do and who funded it?", depth="standard")
# -> [{"name": ..., "url": ..., "content": ...}, ...]

# End-user answer with sources
ans = lk.sourced_answer("Who is the current CEO of Linkup?")
# -> {"answer": "...", "sources": [...]}

# Structured extraction for a pipeline (keep the schema shallow)
schema = {
    "type": "object",
    "properties": {"ceo": {"type": "string"}, "source_url": {"type": "string"}},
    "required": ["ceo"],
}
data = lk.search_structured("Find the current CEO of Linkup with a source URL", schema)

# Constrain with parameters, not prose
recent = lk.search_results(
    "Latest funding news for Linkup",
    include_domains=["techcrunch.com", "linkup.so"],
    from_date="2025-01-01",
)
```

**Raw REST (curl).**

```bash
curl -s https://api.linkup.so/v1/search \
  -H "Authorization: Bearer $LINKUP_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "q": "What does Linkup do and who funded it?",
    "depth": "standard",
    "outputType": "searchResults"
  }'
```

---

## /fetch — URL to clean markdown

**What it is.** Hand it a URL; get back clean, LLM-ready markdown in about a
second. Deterministic — no search, no reasoning. Use it when you **already have
the URL** (your own pages, a competitor's page, a link a search surfaced).

**Request fields.**

| Field | Type | Notes |
|-------|------|-------|
| `url` | string | The page to fetch. **HTML only** — PDFs/ZIPs and pages >20MB return 400. |
| `renderJs` | bool | Default false in REST, but **set true by default in agentic pipelines** — most modern sites are client-rendered. Flip to false only after confirming a site renders server-side (faster, cheaper). |
| `extractImages` | bool | Pull image URLs out of the page. |
| `includeRawHtml` | bool | Also return the raw HTML. |

The engine helper `fetch(url)` defaults `render_js=True` for exactly this reason.

**Python (engine API).**

```python
# Full markdown of a known page
md = lk.fetch_markdown("https://linkup.so")          # render_js=True by default

# Full response object (markdown + metadata)
page = lk.fetch("https://linkup.so", render_js=True)

# Once you've confirmed a site is server-rendered, skip JS for speed:
md = lk.fetch_markdown("https://example.com/blog/post", render_js=False)
```

**Raw REST (curl).**

```bash
curl -s https://api.linkup.so/v1/fetch \
  -H "Authorization: Bearer $LINKUP_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{ "url": "https://linkup.so", "renderJs": true }'
```

---

## The Search → Fetch pattern

The two sync endpoints compose into the single most common agentic loop:

```
search ("what's the best X?")  ─▶  pick the top result's URL  ─▶  fetch(url)  ─▶  full markdown to the LLM
   (snippets, breadth)                  (decision)                  (depth)
```

`search` gives you breadth and snippets; `fetch` gives you the *full* text of the
one page that matters, so the LLM can quote and reason over it accurately. The
`meeting_prep` agent does exactly this: search for an attendee's recent activity,
then `fetch` the single most relevant post for its full text.

```python
results = lk.search_results("Linkup latest blog post about agents", depth="standard")
if results:
    full_text = lk.fetch_markdown(results[0]["url"])   # full page, not a snippet
```

> Note: at `standard` depth you can also name a URL directly in the query to make
> Linkup scrape it inline, and `deep` can chain search→scrape→search on its own.
> Use the explicit search→fetch above when you want deterministic control over
> *which* page gets fetched.

---

## /research — autonomous deep research

**What it is.** An autonomous agent that runs for minutes (not seconds),
performing many searches and fetches, and returns a **synthesized answer with
inline citations**. Use it for open-ended questions a single search can't
resolve.

**Request fields.**

| Field | Type | Notes |
|-------|------|-------|
| `q` | string | The research goal. |
| `outputType` | `sourcedAnswer` \| `structured` | (No raw `searchResults` for research.) |
| `mode` | `auto` \| `answer` \| `investigate` \| `research` | `answer` = precise evidence-backed answer; `investigate` = focused report on one subject; `research` = broad multi-topic report. Set explicitly for predictable shape. |
| `reasoningDepth` | `S` \| `M` \| `L` \| `XL` | `S` 2-5min · `M` 3-7min · `L` 5-10min (default) · `XL` 10-20min. |
| `structuredOutputSchema` | JSON Schema | When `outputType=structured`. |
| `includeDomains` / `excludeDomains` / `fromDate` / `toDate` | — | Same filters as search. |

**Lifecycle — it's async.** A POST returns an `id`; you then GET
`/research/{id}` until `status` is `completed` (statuses: `queued`, `running`,
`completed`, `failed`).

**Python (engine API).** In real apps, kick it off and poll later so you don't
hold a thread for up to 20 minutes:

```python
# Real apps: store the id, poll on a schedule
rid = lk.start_research(
    "Competitive landscape for web-search APIs for AI agents in 2025",
    mode="research",
    reasoning_depth="L",
)
# ... later, e.g. from a cron job or webhook ...
result = lk.get_research(rid)
if result["status"] == "completed":
    print(result["answer"])

# Scripts/demos only: blocking helper that starts + polls until done
result = lk.research("How does Linkup's deep search work?", mode="answer")
```

**Raw REST (curl).**

```bash
# 1) start it -> {"id": "..."}
curl -s https://api.linkup.so/v1/research \
  -H "Authorization: Bearer $LINKUP_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{ "q": "Competitive landscape for web-search APIs", "mode": "research", "reasoningDepth": "L" }'

# 2) poll until status == "completed"
curl -s https://api.linkup.so/v1/research/RESEARCH_ID \
  -H "Authorization: Bearer $LINKUP_API_KEY"
```

---

## /tasks — async batch wrapper

**What it is.** Submit 1-100 tasks in one call, mixing types freely. Each task is
`{type, input}` where `input` mirrors the corresponding endpoint's request body.
Same parameters and pricing as direct calls — this is purely a batching wrapper
for bulk and scheduled jobs.

**Task types.** `search` | `fetch` | `research` | `extract`.

**Python (engine API).**

```python
batch = lk.tasks([
    {"type": "search", "input": {"q": "Acme Corp recent funding", "depth": "standard"}},
    {"type": "fetch",  "input": {"url": "https://acme.com/about", "renderJs": True}},
    {"type": "research", "input": {"q": "Acme Corp competitive position", "mode": "investigate"}},
])
```

**Raw REST (curl).**

```bash
curl -s https://api.linkup.so/v1/tasks \
  -H "Authorization: Bearer $LINKUP_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "tasks": [
      {"type": "search", "input": {"q": "Acme Corp recent funding", "depth": "standard"}},
      {"type": "fetch",  "input": {"url": "https://acme.com/about", "renderJs": true}}
    ]
  }'
```

Pair `/tasks` with a scheduler (cron, Temporal, Airflow, GitHub Actions, Modal —
see [06-providers.md](./06-providers.md)) to enrich a whole CRM list or refresh a
dashboard nightly.

---

## Picking the right endpoint

| You have / want | Use |
|-----------------|-----|
| A question or thing to find on the web, answer in seconds | `/search` |
| A URL already, want its clean text | `/fetch` |
| Search results, then the full text of one of them | search → fetch |
| An open-ended question needing minutes of digging + citations | `/research` |
| Many of the above to run in bulk / on a schedule | `/tasks` |

Next: [how to prompt Linkup](./03-prompting-linkup.md) — the highest-leverage
skill for getting great results.

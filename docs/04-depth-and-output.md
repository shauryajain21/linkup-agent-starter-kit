# Depth and output — the decision guide

Three knobs decide the cost, latency, and shape of a Linkup call:

1. **depth** (search) — how hard Linkup works: `fast` / `standard` / `deep`.
2. **outputType** — what shape comes back: `searchResults` / `sourcedAnswer` / `structured`.
3. **mode + reasoningDepth** (research) — how the autonomous agent behaves.

This page tells you which to pick for what.

---

## Choosing search depth

Decision flow, in prose:

- Do you just need a cheap keyword lookup or a yes/no existence check, with
  sub-second latency and no page reading? → **`fast`**.
- Otherwise, is this a single self-contained lookup (even if it needs to read one
  page you name)? → **`standard`**. This is the everyday default. If you have
  several such lookups that don't depend on each other, run several `standard`
  calls **in parallel**.
- Does the query genuinely need Linkup to chain steps — search, pick a result,
  scrape it, then search again based on what it found? → **`deep`**.

| Depth | Latency | What it does | Scraping | Pick it when |
|-------|---------|--------------|----------|--------------|
| `fast` | <1s | Keyword lookup, no LLM, no scraping (beta) | None | Autocomplete; "does X exist?"; cheap pre-checks; latency-critical paths |
| `standard` | ~1-3s | One agentic iteration | Scrapes **one** URL you name in the query | The default. Most lookups. Parallelize for breadth. |
| `deep` | ~5-30s | Up to 10 iterations | Chains search→scrape→search across pages | The next step depends on the previous step's output |

**"If you're doing X, use Y" rows:**

| If you're doing... | Use |
|--------------------|-----|
| Checking whether a company has raised funding (yes/no) | `fast` |
| Looking up a company's overview and a recent news signal | `standard` (×2 parallel) |
| Extracting a list of decision-makers | `standard` + `structured` |
| Reading one specific page you can name | `standard` (URL in query) or `/fetch` |
| Finding a person, then digging into *their* latest post's comment thread | `deep` |
| Resolving a question where you don't know the right page until you've searched | `deep` |

**Cost/latency intuition.** `fast` ≪ `standard` < `deep`. Two parallel `standard`
calls finish in roughly the time of one and almost always beat a single `deep`
call on both cost and latency — so default to `standard` + parallel, and treat
`deep` as the deliberate choice for genuinely dependent chains.

---

## Choosing output type

| Output type | Shape | Best for | Pick it when |
|-------------|-------|----------|--------------|
| `searchResults` | `[{name, url, content}]` | **LLM grounding** | You're feeding the result into an LLM to reason/write over |
| `sourcedAnswer` | `{answer, sources}` | **End-user display** | You're showing the result to a person, prose + citations |
| `structured` | JSON matching your schema | **Pipelines** | The next code step needs clean fields, not prose |

Decision flow, in prose:

- Will an **LLM** consume the result next? → `searchResults`. Raw snippets are the
  best grounding material; let the LLM do the synthesis.
- Will a **person** read it directly? → `sourcedAnswer`. You get display-ready
  prose with sources attached.
- Will **code** consume it (extract fields, populate a CRM, drive a branch)? →
  `structured` with a **shallow** schema. Never re-parse prose you could have
  asked for as JSON.

| If you're doing... | Use |
|--------------------|-----|
| Building context to hand an LLM for a brief or an email | `searchResults` |
| Answering a user's question in a chat UI | `sourcedAnswer` |
| Extracting `{name, title, url}` rows to loop over | `structured` |
| Populating a CRM field or a dashboard cell | `structured` |

---

## Choosing research mode + reasoningDepth

`/research` is the autonomous, minutes-long endpoint. Two knobs shape it.

**Mode — what kind of output you want:**

| Mode | Produces | Pick it when |
|------|----------|--------------|
| `auto` | Linkup decides | You're unsure; let it choose (less predictable shape) |
| `answer` | A precise, evidence-backed **answer** | One well-defined question that still needs deep digging |
| `investigate` | A focused **report on one subject** | A single entity/topic you want thoroughly profiled |
| `research` | A broad, **multi-topic report** | A landscape, market map, or wide survey |

Set `mode` explicitly in real apps — `auto` trades predictability for convenience.

**reasoningDepth — how long it runs:**

| Depth | Wall-clock | Pick it when |
|-------|-----------|--------------|
| `S` | 2-5 min | Quick deep-dive; you want an answer fast |
| `M` | 3-7 min | Moderate breadth |
| `L` | 5-10 min | **Default.** Most thorough reports |
| `XL` | 10-20 min | Exhaustive, high-stakes research |

| If you're doing... | mode / reasoningDepth |
|--------------------|------------------------|
| "What's the precise answer to this hard question?" | `answer` / `S`-`M` |
| Profiling one company in depth for a brief | `investigate` / `M`-`L` |
| Mapping a competitive landscape | `research` / `L`-`XL` |

Output for research is `sourcedAnswer` or `structured` (there's no raw
`searchResults` for research). Remember it's **async**: `start_research()` returns
an `id`, then poll `get_research(id)` until `status == "completed"`.

---

## /search deep vs. /research — the key fork

Both can do multi-step work, so when do you escalate from `deep` search to full
`research`?

| | `/search` `deep` | `/research` |
|---|------------------|-------------|
| Latency | ~5-30s (sync) | 2-20 min (async, poll) |
| Iterations | up to ~10 | many, autonomous |
| Output | results / answer / structured | cited synthesized report |
| Holds a thread? | Yes (seconds) | No — fire and poll |
| Use when | A bounded chain (search→scrape→search) resolves it in seconds | An open-ended question needing a synthesized, cited report over many sources |

Rule of thumb:

- If a **bounded chain of a few steps** resolves it and you can wait seconds →
  `/search deep`.
- If it's **open-ended**, needs **many sources synthesized**, and you want
  **inline citations** in a written report → `/research`. Don't block a request
  thread on it; kick it off and poll.

---

## Defaults to start from

| Situation | Start with |
|-----------|-----------|
| Any everyday lookup | `search`, `depth="standard"`, `outputType="searchResults"` |
| Feeding an LLM | `searchResults` |
| Showing a user | `sourcedAnswer` |
| Driving code | `structured` (shallow schema) |
| Several independent lookups | several `standard` calls in parallel |
| Genuinely dependent steps (seconds) | `search`, `depth="deep"` |
| Open-ended, cited report (minutes) | `research`, explicit `mode`, `reasoningDepth="L"` |

Next: [reusable patterns](./05-patterns.md) that compose these choices into whole
agents.

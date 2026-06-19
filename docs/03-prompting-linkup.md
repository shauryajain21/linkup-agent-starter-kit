# Prompting Linkup

The single biggest lever on agent quality is the query you hand Linkup. Get this
right and everything downstream — the grounding, the synthesis, the final output
— gets better for free.

Here is the core idea: **Linkup runs an *agentic* search, not a keyword index.**
It plans, searches, and (at `standard`/`deep`) scrapes on your behalf. So you do
not feed it search terms — you give it a clear, natural-language **goal**, the way
you'd brief a sharp research assistant. The reference query templates live in
`linkup_engine/prompts.py`; the rules below are what's baked into them.

---

## Rule 1 — State the goal, not keywords

Tell Linkup what you're trying to learn and in what shape. A bag of keywords
throws away the very thing that makes the search agentic.

| | Query |
|---|---|
| Bad | `Linkup CFO` |
| Good | `Find the current CFO of Linkup and their two most recent prior roles. Return the name, exact title, and a source URL.` |

| | Query |
|---|---|
| Bad | `Acme funding` |
| Good | `Has Acme Robotics announced any funding round in the last 12 months? Give the round, amount, lead investor, date, and a source URL.` |

The good versions name the entities, the facts you want, and ask for a source.
That's a brief, not a search box.

---

## Rule 2 — Name the source to scrape it

Putting a URL directly in the query tells Linkup to fetch that page as part of the
search. `standard` depth scrapes one named URL; `deep` can chain several.

| | Query |
|---|---|
| Bad | `pricing` (hoping Linkup guesses the right page) |
| Good | `Summarize the pricing tiers and limits on https://linkup.so/pricing — list each plan, its price, and its included quota.` |

If you already have the URL and just want its clean text with no searching, reach
for `/fetch` instead (see [02-the-four-endpoints.md](./02-the-four-endpoints.md)).

---

## Rule 3 — Constrain with parameters, not prose

Don't bury constraints in the sentence where the search has to interpret them.
Use the request parameters — they're deterministic.

| | Approach |
|---|---|
| Bad | `Latest Acme news from reputable sources in the last month` |
| Good | `Latest Acme Robotics product and funding news.` + `include_domains=["techcrunch.com", "reuters.com"]`, `from_date="2025-05-01"` |

```python
lk.search_results(
    "Latest Acme Robotics product and funding news",
    include_domains=["techcrunch.com", "reuters.com"],
    from_date="2025-05-01",
)
```

Same goes for "official sites only" (`include_domains`), "exclude this competitor"
(`exclude_domains`), and any date window (`from_date`/`to_date`).

---

## Rule 4 — Ask for exactly the fields you'll use, paired with a schema

If the next step in your pipeline needs structured data, don't ask for prose and
then re-parse it with regex. Ask for the exact fields *and* pass a
`structuredOutputSchema` so you get clean JSON back.

| | Approach |
|---|---|
| Bad | `Tell me about the leadership team at Acme` → returns paragraphs |
| Good | `List the current C-suite at Acme Robotics — name, title, and a profile URL for each.` + a shallow array schema |

```python
schema = {
    "type": "object",
    "properties": {
        "people": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name":  {"type": "string"},
                    "title": {"type": "string"},
                    "url":   {"type": "string"},
                },
                "required": ["name"],
            },
        }
    },
    "required": ["people"],
}
people = lk.search_structured(
    "List the current C-suite at Acme Robotics — name, title, profile URL each.",
    schema,
)
```

This is exactly how the `lead_research` agent extracts its decision-maker list.

---

## Rule 5 — Parallelize independent lookups, chain dependent ones

Two questions that don't depend on each other should be **two parallel `standard`
searches**, not one slow `deep` call. A question whose query depends on a previous
result is a genuine chain — make it sequential (parameterize the next query with
the last result) and reach for `deep` only when Linkup itself needs to chain
search→scrape→search internally.

```python
from concurrent.futures import ThreadPoolExecutor

# INDEPENDENT -> parallel standard searches (cheap, fast)
queries = [
    "What does Acme Robotics do? Product, customers, business model.",
    "Acme Robotics recent funding or major partnership, with date and source URL.",
]
with ThreadPoolExecutor(max_workers=2) as pool:
    overview, signal = pool.map(lambda q: lk.search_results(q, depth="standard"), queries)

# DEPENDENT -> chain: the second query is built from the first's result
top_person = people[0]
bg = lk.search_results(
    f"Background brief on {top_person['name']}, {top_person['title']} at Acme — "
    f"career history, prior companies, recent talks. Source URL per claim.",
    depth="standard",
)
```

Default to `standard` + parallel. Only pay for `deep` when steps are genuinely
dependent *within a single call*. See [04-depth-and-output.md](./04-depth-and-output.md)
for the full depth decision guide.

---

## More before/after rewrites

**Existence / freshness check (use `fast`).**

| | Query |
|---|---|
| Bad | `Acme Robotics Series B announcement details and analysis` at `deep` |
| Good | `Has Acme Robotics announced a Series B?` at `fast` — sub-second yes/no, then escalate only if yes |

**End-user answer vs. grounding.**

| | Query + output |
|---|---|
| Bad | `searchResults` for a question you're going to show a user verbatim |
| Good | `What is Linkup and how is it different from a traditional search API?` with `outputType=sourcedAnswer` → prose + sources, display-ready |

**Open-ended vs. one-shot.**

| | Query + endpoint |
|---|---|
| Bad | `/search deep`: `Everything about the web-search-API market, players, pricing, and trends` |
| Good | `/research` with `mode="research"`: `Map the competitive landscape for web-search APIs aimed at AI agents — players, positioning, pricing, and recent moves. Cite sources.` |

---

## Structured output schema tips

- **Keep schemas shallow.** A flat object or a single array of flat objects
  extracts far more reliably than deeply nested structures. If you need depth, run
  two extractions instead of one.
- **Mark only the truly-required fields `required`.** Forcing optional fields
  invites the model to fabricate them.
- **Name fields the way the source phrases them** (`title`, `funding_round`,
  `source_url`) — it improves extraction accuracy.
- **Always ask for a `url`/`source_url` field** so citations survive into your
  output.

---

## Checklist before you fire a query

1. Is it a **goal** in natural language, not keywords?
2. If you know the page, did you **name the URL** (or use `/fetch`)?
3. Are constraints in **parameters** (`include_domains`, `from_date`), not prose?
4. Did you ask for **exactly the fields** you need, with a **shallow schema** if
   structured?
5. Is the **depth** right (`fast`/`standard`/`deep`) and are independent lookups
   **parallel**?

Next: [depth and output decision guide](./04-depth-and-output.md).

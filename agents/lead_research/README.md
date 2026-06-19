# lead_research — chained `/search`

Turns a seed (a company name **or** a discovery query) into a researched lead and
a short, personalized outreach note. It demonstrates the **chained `/search`**
pattern: each Linkup call grounds the next, and the LLM is used only at the end to
*write* — never to recall facts.

```
seed ─▶ [discover] ─▶ research company ─▶ find people ─▶ research top person ─▶ draft note
          structured     2× standard         structured       standard            LLM
          (optional)     (parallel)          (extract)       (chained)        (grounded only)
```

## The flow, step by step (and which Linkup setting, and why)

| Step | Linkup call | Depth | Output | Why |
|------|-------------|-------|--------|-----|
| 1. Discover (only if given a query) | `search_structured` | `standard` | `structured` | One broad lookup; a **shallow schema** gives a clean list of company names instead of prose to re-parse. No chaining ⇒ no `deep`. |
| 2. Research company | 2× `search_results` **in parallel** | `standard` | `searchResults` | Overview and funding/news signal are **independent** lookups, so they run as parallel `standard` searches (`ThreadPoolExecutor`) rather than one slow `deep` chain. `searchResults` = best raw grounding for the LLM. |
| 3. Find decision-makers | `search_structured` | `standard` | `structured` | We need parseable `name/title/url` fields to pick a target and parameterize the next step. A shallow schema beats regexing prose. |
| 4. Research top person | `search_results` | `standard` | `searchResults` | Genuinely **chained** — the query is parameterized by the person picked in step 3 — but a single person's public bio/press is shallow, so `standard` is enough. (Bump to `deep` to chain bio → posts → commentary.) |
| 5. Draft outreach note | LLM (`llm.complete`) | — | — | No new facts. The LLM phrases a note **grounded only** in steps 2–4, and is instructed to invent nothing. Source URLs are carried through to the output. |

Rule of thumb followed throughout: **parallel `standard`** for independent
lookups; reserve `deep` for steps that truly depend on a prior result. One
`Linkup()` and one LLM are created once and reused across all companies.

## Run it

```bash
cp ../../.env.example ../../.env   # set LINKUP_API_KEY + ANTHROPIC_API_KEY
pip install -r ../../requirements.txt

# Known company (skips discovery):
python -m agents.lead_research.run --company "Linkup"

# Discovery query (fans out to several companies):
python -m agents.lead_research.run --discover "seed-stage devtools startups that raised funding recently"

# Optional flags:
python -m agents.lead_research.run --company "Vercel" \
  --roles "VP of Engineering, Head of Developer Relations" \
  --sender "Jane at Acme" --offering "Acme, an observability platform"
```

Programmatic use:

```python
from agents.lead_research import run_lead_research
results = run_lead_research(company="Linkup")        # -> list[LeadResult]
print(results[0].outreach_note)
print(results[0].sources)
```

## Extend it

- **Push to CRM.** Map each `LeadResult` to a contact/company record and upsert via
  a `connectors/` integration (HubSpot/Salesforce/Attio) — the `sources` list makes
  a clean activity-log note.
- **Batch the discovery fan-out with `/tasks`.** When discovery returns many
  companies, submit the per-company searches as a single `lk.tasks([...])` batch
  (up to 100) instead of looping, for bulk/scheduled runs.
- **Deepen the person step.** Swap step 4 to `depth="deep"` (or `lk.research(...)`)
  to chain a person's bio → their recent posts → talk transcripts for a richer,
  more specific note.

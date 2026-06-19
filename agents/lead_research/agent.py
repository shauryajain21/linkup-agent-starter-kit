"""
lead_research agent — the chained /search pattern.

The flow is a chain of Linkup calls, each grounding the next, with the LLM only
at the very end to *write* (never to recall facts):

    discover ─▶ research company ─▶ find people ─▶ research top person ─▶ draft note
       │              │                  │                 │                  │
    structured   2x standard         structured        standard            LLM
    (optional)   (parallel)          (extract)        (depends on          (grounded
                                                       picked person)       in findings)

Linkup-choice rationale lives next to each call. The short version:
  - Independent lookups (overview + funding signal) run as PARALLEL `standard`
    searches — they don't depend on each other, so there's no reason to pay for
    `deep`.
  - Steps that DEPEND on a prior step's output (researching the *specific* person
    we just picked) are still `standard`, but they're chained sequentially because
    the query is parameterized by the previous result.
  - Extraction steps (the candidate company list, the decision-maker list) use
    `structured` so the LLM downstream gets clean fields, not prose to re-parse.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, asdict
from typing import Any

from linkup_engine import Linkup, get_llm, prompts


# --- result shapes -----------------------------------------------------------


@dataclass
class Person:
    name: str
    title: str = ""
    url: str = ""
    background: str = ""


@dataclass
class LeadResult:
    """Everything the agent learned about one company, plus the drafted note."""

    company: str
    overview: str = ""
    signal: str = ""
    people: list[Person] = field(default_factory=list)
    top_person: Person | None = None
    outreach_note: str = ""
    sources: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# --- helpers -----------------------------------------------------------------


def _collect_sources(results: list[dict], into: list[str]) -> None:
    """Carry source URLs through the pipeline so the final note can cite them."""
    for r in results or []:
        url = r.get("url")
        if url and url not in into:
            into.append(url)


def _join(results: list[dict], limit: int = 6) -> str:
    """Flatten searchResults into a compact text block for LLM grounding."""
    chunks = []
    for r in (results or [])[:limit]:
        name = r.get("name", "")
        url = r.get("url", "")
        content = (r.get("content") or "").strip()
        chunks.append(f"## {name}\n{url}\n{content}")
    return "\n\n".join(chunks)


# --- step 1: discovery (optional) --------------------------------------------


def discover_companies(lk: Linkup, query: str, limit: int = 5) -> list[str]:
    """Turn a discovery query into a clean list of company names.

    Linkup choice: `structured` output with a SHALLOW schema. We want a parseable
    list of names, not prose we'd have to regex. `standard` depth is plenty — this
    is a single broad lookup, not a dependent chain.
    """
    schema = {
        "type": "object",
        "properties": {
            "companies": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "reason": {"type": "string"},
                    },
                    "required": ["name"],
                },
            }
        },
        "required": ["companies"],
    }
    goal = (
        f"Find specific, real companies matching this brief: {query}. "
        f"Return up to {limit} companies as a list of name + a one-line reason "
        f"each matches. Only name companies you can actually source."
    )
    data = lk.search_structured(goal, schema, depth="standard")
    companies = (data or {}).get("companies", []) if isinstance(data, dict) else []
    names = [c["name"] for c in companies if c.get("name")]
    return names[:limit]


# --- step 2: research the company (parallel standard searches) ---------------


def research_company(lk: Linkup, company: str, sources: list[str]) -> dict[str, str]:
    """What the company does + a recent funding/news signal.

    Linkup choice: two INDEPENDENT lookups, so we fire them as PARALLEL `standard`
    searches rather than one `deep` chain. searchResults output gives the LLM raw,
    citable grounding for the note later.
    """
    queries = {
        "overview": prompts.fill(prompts.COMPANY_OVERVIEW, company=company),
        "signal": prompts.fill(prompts.COMPANY_FUNDING_SIGNAL, company=company),
    }

    def _run(q: str) -> list[dict]:
        return lk.search_results(q, depth="standard")

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = dict(zip(queries, pool.map(_run, queries.values())))

    for res in results.values():
        _collect_sources(res, sources)

    return {
        "overview": _join(results["overview"]),
        "signal": _join(results["signal"]),
    }


# --- step 3: find decision-makers (structured extraction) --------------------

DEFAULT_ROLES = "founder, CEO, CTO, VP of Engineering, or Head of Growth"


def find_people(
    lk: Linkup, company: str, roles: str = DEFAULT_ROLES, sources: list[str] | None = None
) -> list[Person]:
    """Extract the current decision-makers as clean name/title/url fields.

    Linkup choice: `structured` with a shallow person schema. We need parseable
    fields to pick a target and to parameterize the next search — prose would force
    a brittle re-parse. `standard` depth: one targeted lookup, no chaining needed.
    """
    schema = {
        "type": "object",
        "properties": {
            "people": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "title": {"type": "string"},
                        "url": {"type": "string"},
                    },
                    "required": ["name"],
                },
            }
        },
        "required": ["people"],
    }
    goal = prompts.fill(prompts.FIND_DECISION_MAKERS, roles=roles, company=company)
    data = lk.search_structured(goal, schema, depth="standard")
    raw = (data or {}).get("people", []) if isinstance(data, dict) else []

    people: list[Person] = []
    for p in raw:
        if not p.get("name"):
            continue
        person = Person(name=p["name"], title=p.get("title", ""), url=p.get("url", ""))
        people.append(person)
        if sources is not None and person.url and person.url not in sources:
            sources.append(person.url)
    return people


# --- step 4: research the top person (chained — depends on the picked person) -


def research_person(
    lk: Linkup, person: Person, company: str, sources: list[str]
) -> str:
    """Background brief on a specific person.

    Linkup choice: this query is PARAMETERIZED by the person we just picked, so it
    is genuinely a chained step. Still `standard` (one person, public bio/press is
    shallow), with searchResults for citable grounding. Bump to `deep` here if you
    need to chain bio -> their posts -> commentary.
    """
    goal = prompts.fill(
        prompts.PERSON_BACKGROUND,
        name=person.name,
        title=person.title or "a decision-maker",
        company=company,
    )
    results = lk.search_results(goal, depth="standard")
    _collect_sources(results, sources)
    return _join(results)


# --- step 5: draft the outreach note (LLM, grounded only in findings) --------

_DRAFT_SYSTEM = (
    "You are an SDR who writes short, specific, non-generic cold outreach. "
    "You write ONLY from the research provided — never invent facts, titles, or "
    "events. If a detail isn't in the research, don't claim it. No flattery, no "
    "buzzwords, no emojis. 90 words max, plus a one-line subject. Reference one "
    "concrete, recent detail about the company and one about the person."
)


def draft_outreach(
    llm,
    company: str,
    overview: str,
    signal: str,
    person: Person | None,
    sender: str = "the Linkup team",
    offering: str = "Linkup, a live-web search/research API for AI agents",
) -> str:
    """LLM writes the note. Linkup did all the fact-finding; the LLM only phrases.

    Grounding-only: we pass the assembled findings and instruct the model to use
    nothing else, so the note stays truthful and citable.
    """
    target = (
        f"{person.name} ({person.title})" if person and person.title else
        (person.name if person else "the right decision-maker")
    )
    user = (
        f"Sender: {sender}\n"
        f"What we're offering: {offering}\n"
        f"Target company: {company}\n"
        f"Recipient: {target}\n\n"
        f"=== COMPANY OVERVIEW (research) ===\n{overview or '(none found)'}\n\n"
        f"=== RECENT SIGNAL (research) ===\n{signal or '(none found)'}\n\n"
        f"=== PERSON BACKGROUND (research) ===\n"
        f"{person.background if person and person.background else '(none found)'}\n\n"
        "Write the outreach note now. Format:\nSubject: <subject>\n\n<body>"
    )
    return llm.complete(system=_DRAFT_SYSTEM, user=user, max_tokens=512).strip()


# --- orchestrator ------------------------------------------------------------


def run_lead_research(
    seed: str | None = None,
    *,
    company: str | None = None,
    discover: str | None = None,
    roles: str = DEFAULT_ROLES,
    sender: str = "the Linkup team",
    offering: str = "Linkup, a live-web search/research API for AI agents",
    lk: Linkup | None = None,
    llm=None,
) -> list[LeadResult]:
    """Run the full chained-search pipeline.

    Pass exactly one of: `company` (skip discovery), `discover` (a discovery query),
    or a positional `seed` (auto-detected: treated as a discovery query if it looks
    like a sentence, otherwise as a company name).

    Returns one LeadResult per company (a list, so discovery fans out cleanly).
    One Linkup() and one LLM are created and REUSED across all companies — the
    client is thread-safe and reuses a single requests.Session.
    """
    lk = lk or Linkup()
    llm = llm or get_llm()

    # Resolve the seed into a list of company names.
    if company:
        names = [company]
    elif discover:
        names = discover_companies(lk, discover)
    elif seed:
        # Heuristic: a multi-word, sentence-like seed is a discovery query.
        looks_like_query = len(seed.split()) >= 4 or any(
            w in seed.lower() for w in ("startup", "compan", "raised", "recently", "stage")
        )
        names = discover_companies(lk, seed) if looks_like_query else [seed]
    else:
        raise ValueError("Provide one of: company=, discover=, or a positional seed.")

    if not names:
        return []

    results: list[LeadResult] = []
    for name in names:
        result = LeadResult(company=name)

        # Step 2: company facts (parallel standard searches).
        facts = research_company(lk, name, result.sources)
        result.overview = facts["overview"]
        result.signal = facts["signal"]

        # Step 3: decision-makers (structured extraction).
        result.people = find_people(lk, name, roles=roles, sources=result.sources)

        # Step 4: research the top person (chained on the picked person).
        if result.people:
            top = result.people[0]
            top.background = research_person(lk, top, name, result.sources)
            result.top_person = top

        # Step 5: draft the note (LLM, grounded only in the above).
        result.outreach_note = draft_outreach(
            llm,
            company=name,
            overview=result.overview,
            signal=result.signal,
            person=result.top_person,
            sender=sender,
            offering=offering,
        )

        results.append(result)

    return results

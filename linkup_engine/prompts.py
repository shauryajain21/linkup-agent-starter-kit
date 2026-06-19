"""
A library of *Linkup query templates*.

The single biggest lever on agent quality is the query you hand Linkup. Linkup
runs an agentic search, so it rewards a clear, specific, natural-language goal —
not a bag of keywords. These templates are the prompts behind the reference
agents; reuse and adapt them.

Rules of thumb baked into these templates (see docs/03-prompting-linkup.md):
  1. State the *goal*, not keywords. "Find the founders of {company} and their
     prior companies" beats "{company} founders".
  2. Name the source when you know it. Putting a URL in the query tells Linkup to
     scrape that page (standard depth scrapes one; deep can chain several).
  3. Constrain with structure, not prose. Prefer include_domains / from_date over
     "from sites like..." or "in the last month".
  4. Ask for exactly the fields you'll use downstream — pair with a structured
     output schema so the LLM gets clean JSON, not paragraphs to re-parse.
"""

from __future__ import annotations

# --- Lead research (chained /search) -------------------------------------

COMPANY_OVERVIEW = (
    "What does the company {company} do? Summarize its product, target customers, "
    "business model, headcount range, headquarters, and the most recent notable "
    "news or funding event. Prefer the company's own site and reputable press."
)

COMPANY_FUNDING_SIGNAL = (
    "Has {company} announced any funding round, major partnership, new product "
    "launch, or executive hire recently? Give the event, date, and a source URL."
)

FIND_DECISION_MAKERS = (
    "Who are the current {roles} at {company}? For each person give their name, "
    "exact title, and a LinkedIn or company-bio URL. Only people currently in role."
)

PERSON_BACKGROUND = (
    "Build a background brief on {name}, who is {title} at {company}. Cover their "
    "career history, prior companies, education, and any recent talks, posts, or "
    "interviews. Include source URLs for each claim."
)

# --- Meeting prep (external connections + /search + /fetch) ---------------

ATTENDEE_RECENT_ACTIVITY = (
    "What has {name} ({title} at {company}) said or published recently? Look for "
    "recent posts, interviews, podcast appearances, or press quotes. Return the "
    "topic, a one-line summary, the date, and the source URL for each item."
)

COMPANY_SINCE_LAST_TOUCH = (
    "What has changed at {company} since {since_date}? Funding, launches, leadership "
    "changes, layoffs, press, or strategy shifts. One line and a source URL each."
)

# --- SEO content (/fetch + /research) -------------------------------------

SEO_TOPIC_RESEARCH = (
    "Write a thoroughly-researched brief for an article targeting the keyword "
    "'{keyword}'. Cover: what the top-ranking pages currently say, the questions "
    "readers actually ask, credible statistics with sources and dates, common "
    "misconceptions, and angles competitors are NOT covering. Cite every claim."
)

COMPETITOR_CONTENT_GAP = (
    "Compare the content at {our_url} against {competitor_urls}. What topics, "
    "questions, and keywords do the competitors cover that we do not? List concrete "
    "article ideas that would close the gap, each with a one-line rationale."
)


def fill(template: str, **kwargs) -> str:
    """Format a template, surfacing any missing field as a clear error."""
    try:
        return template.format(**kwargs)
    except KeyError as e:
        raise KeyError(f"Prompt template missing variable: {e}") from e

"""
lead_research — a reference agent built on the *chained /search* pattern.

Seed (a company name, or a discovery query) -> Linkup finds/researches the
company -> finds decision-makers -> researches the top person -> the LLM drafts
a personalized outreach note grounded ONLY in the Linkup findings.

    from agents.lead_research import run_lead_research
    result = run_lead_research(company="Linkup")
    result = run_lead_research(discover="seed-stage devtools startups that raised recently")
"""

from .agent import (
    LeadResult,
    draft_outreach,
    discover_companies,
    find_people,
    research_company,
    research_person,
    run_lead_research,
)

__all__ = [
    "LeadResult",
    "run_lead_research",
    "discover_companies",
    "research_company",
    "find_people",
    "research_person",
    "draft_outreach",
]

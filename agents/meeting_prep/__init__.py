"""
meeting_prep — a reference agent built on the *external connections + Linkup* pattern.

Pull upcoming meetings from a calendar connector and enrich attendees from a CRM
connector (both swappable stubs) -> for each external attendee, Linkup /search
finds their recent public activity and what changed at their company since your
last touchpoint, with an optional /fetch to pull a full post -> the LLM writes a
one-page prep brief grounded ONLY in the Linkup findings, with source URLs.

    from agents.meeting_prep import run_meeting_prep
    briefs = run_meeting_prep(days=7)
"""

from .agent import (
    Brief,
    AttendeeResearch,
    enrich_attendee,
    load_meetings,
    research_attendee,
    run_meeting_prep,
    write_brief,
)

__all__ = [
    "Brief",
    "AttendeeResearch",
    "run_meeting_prep",
    "load_meetings",
    "enrich_attendee",
    "research_attendee",
    "write_brief",
]

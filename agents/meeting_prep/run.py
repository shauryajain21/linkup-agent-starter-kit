"""
CLI for the meeting_prep agent.

    python -m agents.meeting_prep.run            # next 7 days
    python -m agents.meeting_prep.run --days 14
    python -m agents.meeting_prep.run --no-fetch # skip the optional /fetch step

Runs end to end on the SAMPLE_EVENTS fallback even with no calendar/CRM creds —
you only need LINKUP_API_KEY and an LLM key set in your .env.
"""

from __future__ import annotations

import argparse

from dotenv import load_dotenv

from .agent import run_meeting_prep


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Generate one-page prep briefs for upcoming meetings.")
    parser.add_argument("--days", type=int, default=7, help="Look-ahead window in days (default: 7).")
    parser.add_argument("--calendar", default="google", help="Calendar connector provider (default: google).")
    parser.add_argument("--crm", default="hubspot", help="CRM connector provider (default: hubspot).")
    parser.add_argument("--no-fetch", action="store_true", help="Skip the optional /fetch of the top post.")
    args = parser.parse_args()

    briefs = run_meeting_prep(
        days=args.days,
        calendar_provider=args.calendar,
        crm_provider=args.crm,
        fetch_top_post=not args.no_fetch,
    )

    if not briefs:
        print("No upcoming meetings with external attendees in the window.")
        return

    for i, brief in enumerate(briefs, 1):
        print("\n" + "=" * 78)
        print(f"BRIEF {i}/{len(briefs)} — {brief.title}  ({brief.start})")
        print("=" * 78)
        print(brief.brief_markdown.strip())
        if brief.sources:
            print("\nSources:")
            for url in brief.sources:
                print(f"  - {url}")
    print()


if __name__ == "__main__":
    main()

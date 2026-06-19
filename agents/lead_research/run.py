"""
CLI for the lead_research agent.

    python -m agents.lead_research.run --company "Linkup"
    python -m agents.lead_research.run --discover "seed-stage devtools startups that raised funding recently"

Needs LINKUP_API_KEY and an LLM key (ANTHROPIC_API_KEY by default) in your .env.
"""

from __future__ import annotations

import argparse
import sys

from dotenv import load_dotenv

from .agent import LeadResult, run_lead_research

load_dotenv()


def _rule(char: str = "─", n: int = 70) -> str:
    return char * n


def _print_result(r: LeadResult) -> None:
    print(f"\n{_rule('=')}")
    print(f"COMPANY: {r.company}")
    print(_rule("="))

    if r.overview:
        print("\nOVERVIEW (from Linkup)")
        print(_rule())
        print(r.overview[:1200])

    if r.signal:
        print("\nRECENT SIGNAL (from Linkup)")
        print(_rule())
        print(r.signal[:800])

    if r.people:
        print("\nDECISION-MAKERS (from Linkup)")
        print(_rule())
        for p in r.people:
            title = f" — {p.title}" if p.title else ""
            url = f"  [{p.url}]" if p.url else ""
            star = " *" if r.top_person and p.name == r.top_person.name else ""
            print(f"  - {p.name}{title}{url}{star}")
        print("  (* = researched in depth and used for the note)")
    else:
        print("\nDECISION-MAKERS: none found.")

    print("\nOUTREACH NOTE (LLM, grounded in the above)")
    print(_rule())
    print(r.outreach_note or "(no note drafted)")

    if r.sources:
        print("\nSOURCES")
        print(_rule())
        for u in r.sources:
            print(f"  - {u}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="lead_research",
        description="Linkup-powered lead research -> personalized outreach note.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--company", help="A target company name (skips discovery).")
    group.add_argument(
        "--discover",
        help="A discovery query, e.g. 'seed-stage devtools startups that raised recently'.",
    )
    parser.add_argument(
        "--roles",
        default=None,
        help="Decision-maker roles to look for (default: founders/CEO/CTO/VP Eng/Head of Growth).",
    )
    parser.add_argument(
        "--sender", default="the Linkup team", help="Who the note is from."
    )
    parser.add_argument(
        "--offering",
        default="Linkup, a live-web search/research API for AI agents",
        help="What you're pitching.",
    )
    args = parser.parse_args(argv)

    kwargs = dict(sender=args.sender, offering=args.offering)
    if args.roles:
        kwargs["roles"] = args.roles
    if args.company:
        kwargs["company"] = args.company
    else:
        kwargs["discover"] = args.discover

    try:
        results = run_lead_research(**kwargs)
    except Exception as e:  # surface config/API errors cleanly at the CLI boundary
        print(f"error: {e}", file=sys.stderr)
        return 1

    if not results:
        print("No companies found for that seed.", file=sys.stderr)
        return 1

    for r in results:
        _print_result(r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

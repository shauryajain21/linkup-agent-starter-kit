"""
CLI for the seo_content agent.

    python -m agents.seo_content.run \
        --url https://linkup.so \
        --competitors https://exa.ai https://tavily.com \
        --keyword "web search API for AI agents"

Requires LINKUP_API_KEY and an LLM key (ANTHROPIC_API_KEY by default) in your
environment or a .env file. The /research step runs for minutes, so progress
lines are printed as each stage completes. With no destination connector or
creds, the article is written to ./output/ and the path is printed.
"""

from __future__ import annotations

import argparse
import sys

from dotenv import load_dotenv

load_dotenv()

from .agent import run_seo_content  # noqa: E402  (load_dotenv must run first)


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="python -m agents.seo_content.run",
        description="Fetch your site + competitors, research a keyword deeply, "
        "and write a cited SEO article (with a Notion / local-file destination).",
    )
    parser.add_argument("--url", required=True, help="Your website/page URL.")
    parser.add_argument(
        "--competitors",
        nargs="+",
        required=True,
        help="One or more competitor URLs (space-separated).",
    )
    parser.add_argument(
        "--keyword", required=True, help="Target keyword / topic for the article."
    )
    parser.add_argument(
        "--reasoning-depth",
        default="M",
        choices=["S", "M", "L", "XL"],
        help="/research reasoning depth. M is the balanced default; L/XL go deeper "
        "but slower.",
    )
    parser.add_argument(
        "--provider",
        default="notion",
        help="Destination connector provider (falls back to a local file).",
    )
    args = parser.parse_args()

    def progress(msg: str) -> None:
        print(msg, flush=True)

    print(f"SEO content agent | keyword: {args.keyword!r}")
    print(f"  our site:    {args.url}")
    print(f"  competitors: {', '.join(args.competitors)}\n")

    result = run_seo_content(
        our_url=args.url,
        competitor_urls=args.competitors,
        keyword=args.keyword,
        reasoning_depth=args.reasoning_depth,
        provider=args.provider,
        on_progress=progress,
    )

    print("\n" + "=" * 70)
    print(f"TITLE: {result.title}")
    print(f"META:  {result.meta_description}")
    print(f"SOURCES CITED: {len(result.research_sources)}")
    print(f"PUBLISHED TO:  {result.published_to}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())

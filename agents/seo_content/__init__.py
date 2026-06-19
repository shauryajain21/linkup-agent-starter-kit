"""
seo_content — a reference agent built on the */fetch + /research* pattern.

Given your site, a few competitor sites, and a target keyword, the agent:
  1. /fetch your page and each competitor page to clean markdown (in parallel).
  2. LLM reads the markdown and names the content gap / best angle.
  3. /research the keyword deeply -> a cited brief of facts, stats, FAQs, sources.
  4. LLM writes a full article grounded in that research.
  5. Publishes the draft to a destination connector (Notion), with a local-file fallback.

    from agents.seo_content import run_seo_content
    result = run_seo_content(
        our_url="https://linkup.so",
        competitor_urls=["https://exa.ai", "https://tavily.com"],
        keyword="web search API for AI agents",
    )

Why this pattern: /fetch is the right tool when you ALREADY have the URLs (your
own and your competitors') — it is a fast, deterministic URL->markdown call.
/research is the right tool for the open-ended "what should this article say?"
question, where a single search can't resolve it and you want a cited synthesis.
"""

from .agent import (
    ArticleResult,
    fetch_sources,
    find_content_gap,
    publish,
    research_topic,
    run_seo_content,
    write_article,
)

__all__ = [
    "ArticleResult",
    "run_seo_content",
    "fetch_sources",
    "find_content_gap",
    "research_topic",
    "write_article",
    "publish",
]

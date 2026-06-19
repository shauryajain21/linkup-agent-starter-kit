"""
seo_content agent — composable functions for the /fetch + /research pattern.

Pipeline (each function is independently usable; run_seo_content wires them up):

    fetch_sources    -> /fetch your URL + competitors to markdown (parallel)
    find_content_gap -> LLM over that markdown: what do they cover that you don't?
    research_topic   -> /research the keyword deeply (the heavy, cited step)
    write_article    -> LLM writes the full draft, grounded in the research
    publish          -> push to a destination connector, with a local-file fallback

The split mirrors the kit's mental model: Linkup is the engine (every fact about
the live web — competitor pages, the research brief — comes from it), and the LLM
only reasons over and formats what Linkup returned.
"""

from __future__ import annotations

import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from linkup_engine import Linkup, get_llm, prompts


@dataclass
class ArticleResult:
    """Everything the run produced, so callers can inspect or re-publish."""

    keyword: str
    our_url: str
    competitor_urls: list[str]
    content_gap: str
    research_brief: str
    research_sources: list[dict] = field(default_factory=list)
    title: str = ""
    meta_description: str = ""
    article_markdown: str = ""
    published_to: str = ""  # where it landed (Notion URL/id, or local file path)


# --------------------------------------------------------------------------
# 1. /fetch — your site + competitors -> clean markdown, in parallel
# --------------------------------------------------------------------------


def fetch_sources(
    our_url: str,
    competitor_urls: list[str],
    lk: Linkup | None = None,
    render_js: bool = True,
    max_chars: int = 12_000,
) -> dict[str, str]:
    """Fetch every URL to markdown concurrently and return {url: markdown}.

    We use /fetch (not /search) because we already KNOW the exact URLs — fetch is
    a fast (~1s), deterministic URL->markdown call with no search step to pay for.

    These fetches are independent, so we fan them out across a thread pool while
    reusing ONE Linkup client (its requests.Session pools connections). render_js
    defaults to True because most marketing/landing pages are client-rendered.

    Markdown is truncated to max_chars per page: we only need enough for the LLM
    to judge topical coverage, not the entire site, and this keeps the prompt cheap.
    """
    lk = lk or Linkup()
    urls = [our_url, *competitor_urls]

    def _one(url: str) -> tuple[str, str]:
        try:
            md = lk.fetch_markdown(url, render_js=render_js)
        except Exception as e:  # one dead competitor URL shouldn't kill the run
            md = f"[fetch failed for {url}: {e}]"
        return url, (md or "")[:max_chars]

    results: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=min(8, len(urls))) as pool:
        futures = [pool.submit(_one, u) for u in urls]
        for fut in as_completed(futures):
            url, md = fut.result()
            results[url] = md
    return results


# --------------------------------------------------------------------------
# 2. LLM — find the content gap / angle over the fetched markdown
# --------------------------------------------------------------------------

_GAP_SYSTEM = (
    "You are an SEO content strategist. You compare a company's page against its "
    "competitors' pages and identify, specifically and concretely, the topics, "
    "questions, and sub-keywords the competitors cover that the company does not. "
    "You reason ONLY from the page content provided — never invent facts. Be terse."
)


def find_content_gap(
    our_url: str,
    competitor_urls: list[str],
    fetched: dict[str, str],
    keyword: str,
    llm=None,
) -> str:
    """Have the LLM read the fetched markdown and name the gap and best angle.

    This is pure reasoning over Linkup output: the only world-facts in play are the
    page contents /fetch returned. We anchor the analysis to the target keyword so
    the gap is relevant to what we're trying to rank for.
    """
    llm = llm or get_llm()

    def _block(url: str) -> str:
        return f"### PAGE: {url}\n{fetched.get(url, '[no content]')}\n"

    our_block = _block(our_url)
    competitor_blocks = "\n".join(_block(u) for u in competitor_urls)

    user = (
        f"Target keyword: {keyword}\n\n"
        f"OUR PAGE:\n{our_block}\n"
        f"COMPETITOR PAGES:\n{competitor_blocks}\n\n"
        "Output, in under 200 words:\n"
        "1. The single best angle for us to win on this keyword.\n"
        "2. 3-6 concrete topics/questions competitors cover that we don't.\n"
        "3. What to emphasize given our existing positioning."
    )
    return llm.complete(system=_GAP_SYSTEM, user=user, max_tokens=600).strip()


# --------------------------------------------------------------------------
# 3. /research — deep, cited research on the SEO topic (the heavy step)
# --------------------------------------------------------------------------


def research_topic(
    keyword: str,
    lk: Linkup | None = None,
    reasoning_depth: str = "M",
    on_progress: Callable[[str], None] | None = None,
) -> tuple[str, list[dict]]:
    """Run autonomous /research on the keyword; return (brief_markdown, sources).

    Why /research and not /search here: writing a strong article needs more than a
    single query can resolve — current stats with dates, the questions readers ask,
    common misconceptions, and credible sources, synthesized into one cited brief.
    That is exactly what the research agent does (it runs for minutes and returns a
    cited report), whereas /search is a single agentic pass best for point lookups.

    mode="research" gives the broad, multi-topic report we want for an article.
    reasoning_depth defaults to "M" as a sensible speed/quality balance; "L"/"XL"
    dig deeper across more sources but take longer (and cost more).

    We access the result dict defensively (.get) because the sourcedAnswer envelope
    can vary. For a real (non-script) app, prefer lk.start_research() + polling with
    lk.get_research(id) so you don't hold a thread for minutes — see run.py notes.
    """
    lk = lk or Linkup()
    query = prompts.fill(prompts.SEO_TOPIC_RESEARCH, keyword=keyword)

    if on_progress:
        on_progress(f"Starting /research (mode=research, depth={reasoning_depth}). "
                    "This is the slow step (minutes).")

    result = lk.research(
        query,
        mode="research",
        reasoning_depth=reasoning_depth,
        output_type="sourcedAnswer",
    )

    # sourcedAnswer typically nests under "result"/"data"; fall back across shapes.
    payload = result.get("result") or result.get("data") or result
    brief = (
        payload.get("answer")
        or payload.get("content")
        or payload.get("markdown")
        or ""
    )
    sources = payload.get("sources") or result.get("sources") or []
    if on_progress:
        on_progress(f"/research complete: {len(brief)} chars, {len(sources)} sources.")
    return brief, sources


# --------------------------------------------------------------------------
# 4. LLM — write the full article, grounded in the research
# --------------------------------------------------------------------------

_WRITER_SYSTEM = (
    "You are an expert SEO content writer. You write accurate, genuinely useful "
    "long-form articles that read like a human expert wrote them — not keyword "
    "stuffing. You ground EVERY factual claim in the provided research brief and "
    "cite its sources inline as markdown links. You never invent statistics or "
    "sources. You naturally work in the target keyword without over-optimizing."
)


def _sources_block(sources: list[dict]) -> str:
    lines = []
    for s in sources:
        name = s.get("name") or s.get("title") or s.get("url") or "source"
        url = s.get("url") or ""
        if url:
            lines.append(f"- [{name}]({url})")
    return "\n".join(lines) if lines else "(no structured sources returned)"


def write_article(
    keyword: str,
    content_gap: str,
    research_brief: str,
    research_sources: list[dict],
    llm=None,
) -> tuple[str, str, str]:
    """Write the article. Returns (title, meta_description, article_markdown).

    The LLM gets three inputs, all grounded: the keyword, the content-gap angle
    (from step 2), and the cited research brief (from step 3). We ask for the SEO
    furniture (title + meta) up front in a parseable format, then strip it so the
    body is clean markdown ready to publish.
    """
    llm = llm or get_llm()

    user = (
        f"Target keyword: {keyword}\n\n"
        f"STRATEGIC ANGLE / CONTENT GAP TO CLOSE:\n{content_gap}\n\n"
        f"CITED RESEARCH BRIEF (ground all facts in this; cite its sources):\n"
        f"{research_brief}\n\n"
        f"AVAILABLE SOURCES (cite as inline markdown links):\n"
        f"{_sources_block(research_sources)}\n\n"
        "Write a complete, publication-ready article. Requirements:\n"
        "- Start with exactly two lines:\n"
        "  TITLE: <an SEO title, <=60 chars, includes the keyword naturally>\n"
        "  META: <a meta description, <=155 chars>\n"
        "- Then the article body in markdown: an H1, a strong intro, well-organized "
        "H2/H3 sections that close the content gap, and a short conclusion.\n"
        "- Cite statistics and claims inline as [text](url) using the sources above.\n"
        "- Be specific and useful. No fluff, no invented numbers."
    )

    # Article-length output: raise max_tokens well above the 1024 default.
    raw = llm.complete(system=_WRITER_SYSTEM, user=user, max_tokens=4096).strip()

    title, meta, body = _split_article(raw, fallback_title=keyword)
    return title, meta, body


def _split_article(raw: str, fallback_title: str) -> tuple[str, str, str]:
    """Pull the TITLE:/META: header lines off the front; return the clean body."""
    title, meta = "", ""
    lines = raw.splitlines()
    body_start = 0
    for i, line in enumerate(lines[:6]):  # header should be in the first few lines
        m_title = re.match(r"\s*TITLE:\s*(.+)", line, re.IGNORECASE)
        m_meta = re.match(r"\s*META:\s*(.+)", line, re.IGNORECASE)
        if m_title:
            title = m_title.group(1).strip()
            body_start = i + 1
        elif m_meta:
            meta = m_meta.group(1).strip()
            body_start = i + 1
    body = "\n".join(lines[body_start:]).strip()
    return (title or fallback_title.title()), meta, (body or raw)


# --------------------------------------------------------------------------
# 5. publish — destination connector, with an explicit local-file fallback
# --------------------------------------------------------------------------


def publish(
    title: str,
    article_markdown: str,
    keyword: str = "",
    meta_description: str = "",
    provider: str = "notion",
) -> str:
    """Publish the draft and return where it landed (a URL/id, or a file path).

    We try the destination connector first (another part of the kit owns it; we
    code against its documented interface and do NOT reimplement it). If the
    connector is unavailable — module missing, or no credentials configured — we
    fall back to writing the article to ./output/ and return that path, so the
    whole pipeline still runs end to end without any destination creds.
    """
    try:
        from connectors.destinations import get_destination  # provided elsewhere

        dest = get_destination(provider=provider)
        page = dest.create_page(
            title=title,
            markdown_body=article_markdown,
            keyword=keyword,
            meta_description=meta_description,
        )
        where = page.get("url") or page.get("id") or str(page)
        print(f"[publish] Pushed draft to {provider}: {where}")
        return where
    except Exception as e:
        # Explicit, visible fallback — never silently swallow a publish failure.
        print(f"[publish] Destination connector unavailable ({e}). "
              f"Falling back to a local file.")
        return _write_local(title, article_markdown, keyword)


def _write_local(title: str, article_markdown: str, keyword: str) -> str:
    out_dir = os.path.join(os.getcwd(), "output")
    os.makedirs(out_dir, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", (keyword or title).lower()).strip("-") or "article"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = os.path.join(out_dir, f"{slug}-{stamp}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n{article_markdown}\n")
    print(f"[publish] Wrote article to {path}")
    return path


# --------------------------------------------------------------------------
# Orchestrator
# --------------------------------------------------------------------------


def run_seo_content(
    our_url: str,
    competitor_urls: list[str],
    keyword: str,
    reasoning_depth: str = "M",
    provider: str = "notion",
    on_progress: Callable[[str], None] | None = None,
) -> ArticleResult:
    """Run the full /fetch + /research SEO pipeline and return an ArticleResult.

    on_progress (optional) receives human-readable status lines — useful because
    the /research step takes minutes. run.py passes a printer.
    """
    say = on_progress or (lambda _msg: None)

    # Reuse a single Linkup client across fetch + research (pools connections).
    lk = Linkup()
    llm = get_llm()

    say(f"[1/5] Fetching {1 + len(competitor_urls)} pages in parallel...")
    fetched = fetch_sources(our_url, competitor_urls, lk=lk)

    say("[2/5] Analyzing content gap with the LLM...")
    content_gap = find_content_gap(our_url, competitor_urls, fetched, keyword, llm=llm)

    say("[3/5] Researching the topic (deep, cited — this takes minutes)...")
    research_brief, research_sources = research_topic(
        keyword, lk=lk, reasoning_depth=reasoning_depth, on_progress=say
    )

    say("[4/5] Writing the article...")
    title, meta, article_md = write_article(
        keyword, content_gap, research_brief, research_sources, llm=llm
    )

    say(f"[5/5] Publishing (provider={provider}, local-file fallback)...")
    published_to = publish(
        title, article_md, keyword=keyword, meta_description=meta, provider=provider
    )

    return ArticleResult(
        keyword=keyword,
        our_url=our_url,
        competitor_urls=competitor_urls,
        content_gap=content_gap,
        research_brief=research_brief,
        research_sources=research_sources,
        title=title,
        meta_description=meta,
        article_markdown=article_md,
        published_to=published_to,
    )

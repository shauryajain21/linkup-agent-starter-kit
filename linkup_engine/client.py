"""
Linkup client — a thin, transparent wrapper over the four Linkup endpoints.

This is deliberately written against the raw REST API (not hidden behind an SDK)
so you can see *exactly* what Linkup does. Every method maps 1:1 to an endpoint
documented at https://docs.linkup.so.

    from linkup_engine import Linkup
    lk = Linkup()                      # reads LINKUP_API_KEY from the environment

    lk.search("who founded Linkup?", depth="standard")
    lk.fetch("https://linkup.so", render_js=True)
    lk.research("competitive landscape for web-search APIs", mode="research")

The four endpoints, at a glance:
    search    synchronous web search          <1s – ~30s   fast | standard | deep
    fetch     URL -> clean markdown           ~1s
    research  autonomous multi-step research  2 – 20 min    answer | investigate | research
    tasks     async batch of any of the above

Latency / capability cheat-sheet for `search`:
    fast      sub-second, keyword-only, no LLM, no scraping (beta)
    standard  single-iteration agentic, ~1-3s, can scrape ONE url named in the query
    deep      up to 10 iterations, ~5-30s, can chain search-then-scrape across pages
"""

from __future__ import annotations

import os
import time
from typing import Any, Literal

import requests

BASE_URL = "https://api.linkup.so/v1"

Depth = Literal["fast", "standard", "deep"]
OutputType = Literal["searchResults", "sourcedAnswer", "structured"]
ResearchMode = Literal["auto", "answer", "investigate", "research"]
ReasoningDepth = Literal["S", "M", "L", "XL"]


class LinkupError(RuntimeError):
    """Raised when the Linkup API returns a non-2xx response."""


class Linkup:
    """A small, dependency-light Linkup client. The engine every agent runs on."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = BASE_URL,
        timeout: int = 60,
        session: requests.Session | None = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("LINKUP_API_KEY")
        if not self.api_key:
            raise LinkupError(
                "No Linkup API key. Set LINKUP_API_KEY or pass api_key=. "
                "Get one at https://app.linkup.so."
            )
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = session or requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
        )

    # -- low-level ---------------------------------------------------------

    def _post(self, path: str, payload: dict[str, Any]) -> Any:
        # Strip None values so we never override server-side defaults by accident.
        body = {k: v for k, v in payload.items() if v is not None}
        resp = self._session.post(
            f"{self.base_url}{path}", json=body, timeout=self.timeout
        )
        if not resp.ok:
            raise LinkupError(f"POST {path} -> {resp.status_code}: {resp.text}")
        return resp.json()

    def _get(self, path: str) -> Any:
        resp = self._session.get(f"{self.base_url}{path}", timeout=self.timeout)
        if not resp.ok:
            raise LinkupError(f"GET {path} -> {resp.status_code}: {resp.text}")
        return resp.json()

    # -- /search -----------------------------------------------------------

    def search(
        self,
        query: str,
        depth: Depth = "standard",
        output_type: OutputType = "searchResults",
        structured_output_schema: dict | None = None,
        include_images: bool = False,
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        max_results: int | None = None,
        include_sources: bool = False,
    ) -> Any:
        """Synchronous web search.

        - depth="standard" is the everyday default. Use "deep" when the next step
          depends on the previous step's output (search -> scrape -> search).
        - output_type="searchResults" is best for LLM grounding; "sourcedAnswer"
          for end-user display; "structured" (with a schema) for pipelines.
        - Put a URL directly in the query to make Linkup scrape that page.
        """
        return self._post(
            "/search",
            {
                "q": query,
                "depth": depth,
                "outputType": output_type,
                "structuredOutputSchema": structured_output_schema,
                "includeImages": include_images,
                "includeDomains": include_domains,
                "excludeDomains": exclude_domains,
                "fromDate": from_date,
                "toDate": to_date,
                "maxResults": max_results,
                "includeSources": include_sources,
            },
        )

    # -- /fetch ------------------------------------------------------------

    def fetch(
        self,
        url: str,
        render_js: bool = True,
        extract_images: bool = False,
        include_raw_html: bool = False,
    ) -> Any:
        """URL -> clean markdown.

        render_js defaults to True here (many modern sites are client-rendered).
        Flip it to False only once you've confirmed a site renders server-side.
        HTML pages only — PDFs/ZIPs and pages >20MB return 400.
        """
        return self._post(
            "/fetch",
            {
                "url": url,
                "renderJs": render_js,
                "extractImages": extract_images,
                "includeRawHtml": include_raw_html,
            },
        )

    # -- /research ---------------------------------------------------------

    def start_research(
        self,
        query: str,
        output_type: Literal["sourcedAnswer", "structured"] = "sourcedAnswer",
        mode: ResearchMode = "auto",
        reasoning_depth: ReasoningDepth = "L",
        structured_output_schema: dict | None = None,
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> str:
        """Kick off an async research run. Returns the research id to poll."""
        data = self._post(
            "/research",
            {
                "q": query,
                "outputType": output_type,
                "mode": mode,
                "reasoningDepth": reasoning_depth,
                "structuredOutputSchema": structured_output_schema,
                "includeDomains": include_domains,
                "excludeDomains": exclude_domains,
                "fromDate": from_date,
                "toDate": to_date,
            },
        )
        return data["id"]

    def get_research(self, research_id: str) -> Any:
        """Poll a research run once. status is one of queued/running/completed/failed."""
        return self._get(f"/research/{research_id}")

    def research(
        self,
        query: str,
        mode: ResearchMode = "auto",
        reasoning_depth: ReasoningDepth = "L",
        output_type: Literal["sourcedAnswer", "structured"] = "sourcedAnswer",
        structured_output_schema: dict | None = None,
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        poll_interval: float = 10.0,
        max_wait: float = 25 * 60,
    ) -> Any:
        """Blocking convenience wrapper: start research and poll until done.

        For real apps prefer start_research()/get_research() so you don't hold a
        thread for up to 20 minutes — kick it off, store the id, poll later.
        """
        rid = self.start_research(
            query,
            output_type=output_type,
            mode=mode,
            reasoning_depth=reasoning_depth,
            structured_output_schema=structured_output_schema,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
            from_date=from_date,
            to_date=to_date,
        )
        deadline = time.monotonic() + max_wait
        while time.monotonic() < deadline:
            result = self.get_research(rid)
            status = result.get("status")
            if status == "completed":
                return result
            if status == "failed":
                raise LinkupError(f"Research {rid} failed: {result}")
            time.sleep(poll_interval)
        raise LinkupError(f"Research {rid} did not finish within {max_wait}s")

    # -- ergonomic helpers -------------------------------------------------
    # The raw endpoints return slightly different envelopes per output type.
    # These helpers normalize the common cases so agent code stays clean.

    def search_results(self, query: str, **kwargs) -> list[dict]:
        """search() with output_type='searchResults', returning a flat list of
        {name, url, content} dicts (the best shape for LLM grounding)."""
        kwargs.setdefault("depth", "standard")
        data = self.search(query, output_type="searchResults", **kwargs)
        if isinstance(data, dict):
            return data.get("results", []) or []
        return data or []

    def sourced_answer(self, query: str, **kwargs) -> dict:
        """search() with output_type='sourcedAnswer'. Returns {answer, sources}."""
        kwargs.setdefault("depth", "standard")
        return self.search(query, output_type="sourcedAnswer", **kwargs)

    def search_structured(self, query: str, schema: dict, **kwargs) -> Any:
        """search() with a structured output schema. Returns JSON matching it."""
        kwargs.setdefault("depth", "standard")
        return self.search(
            query,
            output_type="structured",
            structured_output_schema=schema,
            **kwargs,
        )

    def fetch_markdown(self, url: str, render_js: bool = True) -> str:
        """fetch() returning just the page markdown as a string."""
        data = self.fetch(url, render_js=render_js)
        if isinstance(data, dict):
            return data.get("markdown") or data.get("content") or ""
        return str(data or "")

    # -- /tasks ------------------------------------------------------------

    def tasks(self, tasks: list[dict[str, Any]]) -> Any:
        """Submit a batch (1-100) of search/fetch/research/extract tasks.

        Each task is {"type": "search"|"fetch"|"research"|"extract", "input": {...}}
        where `input` mirrors the corresponding endpoint's request body.
        """
        if not 1 <= len(tasks) <= 100:
            raise LinkupError("tasks() accepts between 1 and 100 tasks per call")
        return self._post("/tasks", {"tasks": tasks})

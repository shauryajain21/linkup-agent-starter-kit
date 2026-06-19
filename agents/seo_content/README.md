# seo_content — `/fetch` + `/research`

A reference agent that turns "here's my page, my competitors, and a keyword" into a
full, **cited** SEO article draft — pushed to Notion (or a local file).

It shows the `/fetch` + `/research` pattern: use the fast, deterministic endpoint
when you already have URLs, and the heavy autonomous one when the question is open.

## The flow (which endpoint at each step, and why)

1. **Fetch your site + competitors** — `lk.fetch_markdown(url)`, run in **parallel**
   (`ThreadPoolExecutor`, one reused `Linkup()`).
   *Why `/fetch`, not `/search`:* we already know the exact URLs. `/fetch` is a
   ~1s URL→markdown call with no search step to pay for. `render_js=True` because
   most marketing pages are client-rendered.
2. **Find the content gap** — the LLM reads only the fetched markdown and names the
   best angle + the topics competitors cover that you don't. Pure reasoning over
   Linkup output; no facts invented.
3. **Research the topic** — `lk.research(keyword, mode="research", reasoning_depth="M")`.
   *Why `/research`, not `/search`:* a strong article needs current stats (with
   dates), the questions readers ask, misconceptions, and credible sources, all
   synthesized into one **cited** brief — more than a single query resolves.
   `mode="research"` gives the broad multi-topic report; `reasoning_depth="M"` is a
   balanced default (`L`/`XL` dig deeper across more sources but are slower/costlier).
4. **Write the article** — the LLM writes title, meta description, and body, grounding
   every claim in the research brief and citing its sources inline. `max_tokens` is
   raised to `4096` for article length.
5. **Publish** — `connectors.destinations.get_destination("notion").create_page(...)`.
   If the connector or its creds are missing, it falls back to writing the article to
   `./output/<slug>-<timestamp>.md` and prints the path, so the agent runs end to end
   with no destination setup.

## Run it

```bash
pip install -r requirements.txt
cp .env.example .env   # set LINKUP_API_KEY + ANTHROPIC_API_KEY (and Notion creds if you have them)

python -m agents.seo_content.run \
    --url https://linkup.so \
    --competitors https://exa.ai https://tavily.com \
    --keyword "web search API for AI agents"
```

Optional: `--reasoning-depth {S,M,L,XL}` (default `M`), `--provider notion`.

## A note on research latency / async

`/research` runs for **minutes** — the CLI prints progress lines as each stage
completes. The agent uses the blocking `lk.research(...)` helper, which is fine for
a script/demo. In a real service, kick it off with `lk.start_research(query, ...)`,
store the returned `id`, and poll `lk.get_research(id)` (status
`queued`/`running`/`completed`/`failed`) from a worker — so you never hold a request
thread for the full duration.

## Extension ideas

- **Schedule it weekly** via Linkup `/tasks` (batch research multiple keywords) plus a
  cron, so the content pipeline refreshes drafts automatically.
- **More destinations**: add a WordPress or Webflow provider behind the same
  `connectors.destinations` interface — the agent code doesn't change.
- **Auto internal-linking**: `/fetch` your sitemap, then have the LLM insert relevant
  internal links into the draft before publishing.

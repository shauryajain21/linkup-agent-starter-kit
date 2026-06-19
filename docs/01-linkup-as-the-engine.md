# Linkup as the engine

## Why an LLM alone is not enough

An LLM is a reasoning engine frozen at its training cutoff. Ask it about today's
news, a company's current CFO, a price that changed this morning, or a page that
was published an hour ago, and it will do one of two things: tell you it doesn't
know, or — worse — confidently make something up. Neither is acceptable in an
agent that takes real actions on behalf of a user.

The uncomfortable truth about agents is simple:

> **An agent is only as good as the facts it acts on.**

A perfectly-reasoned outreach email built on a hallucinated funding round is a
liability. A meeting brief that cites an executive who left the company last
quarter erodes trust instantly. The reasoning was fine; the *facts* were stale or
invented.

Linkup exists to fix exactly this. It is the agent's connection to the **live
web**: real-time search, clean page extraction, and autonomous multi-step
research — all returning **current, sourced** reality with URLs you can carry
through to the final output.

## The mental model

Every agent in this kit is the same five-stage pipeline. Linkup is the engine in
the middle; the LLM is the reasoning/formatting layer wrapped around it.

```
        ┌──────────────────────────── your agent ────────────────────────────┐
        │                                                                     │
 trigger ─▶  LLM plans  ─▶  LINKUP (search · fetch · research)  ─▶  LLM writes  ─▶  destination
 (cron,        decide        ▲   the engine: fresh, grounded web facts          phrase,        (Notion, CRM,
  webhook,     what to       │                                                  format,         Slack, email,
  CLI, API)    look up       └──────── everything factual is grounded here ─────┘  cite           DB, webhook)
```

Read it left to right:

1. **Trigger** — something kicks the agent off: a schedule, an inbound webhook, a
   CLI invocation, a new calendar event.
2. **LLM plans** — the model decides *what to find out*. It does not answer from
   memory; it figures out the queries.
3. **Linkup** — the engine fetches the facts. `search` to find/answer, `fetch` to
   turn a known URL into clean markdown, `research` for questions one query can't
   resolve. This is the only place world-facts enter the system.
4. **LLM writes** — the model now reasons and phrases, but *only over what Linkup
   returned*. Its job is synthesis and formatting, never recall.
5. **Destination** — the result lands somewhere useful via a connector: a CRM
   note, a Slack message, a Notion page, an email.

## The one rule: ground, then reason

Everything in this kit follows a single discipline:

> **Ground, then reason.** Any fact about the world flows through Linkup first.
> The LLM only ever reasons over facts Linkup returned — it never recalls them.

Concretely, that means:

- If a step needs a fact that isn't already in the prompt or a connected system,
  it comes from Linkup. You never ask the LLM "who is the CEO of X?" — you ask
  Linkup, then hand the answer to the LLM to use.
- Linkup output (especially `searchResults` and `/research` citations) carries
  `url`s. Carry them through to the final output so every claim is traceable.
- The prompts that drive the LLM explicitly say "use only the supplied findings;
  if it isn't there, say so." See the system prompts in the reference agents.

## Where each piece sits

| Layer | What it is | What it is NOT | In this repo |
|-------|-----------|----------------|--------------|
| **Linkup** | The web-facts engine: live search, page fetch, deep research | Not your reasoning layer; not your private database | `linkup_engine/client.py` |
| **LLM** | The reasoning/formatting layer: plans queries, synthesizes findings, writes output | Not a source of world-facts; not a knowledge base | `linkup_engine/llm.py` (Claude by default, swappable) |
| **Connectors** | The edges: where context is read (CRM, calendar) and results are written (Slack, email, Notion) | Not the web; they hold *your* systems, not public reality | `connectors/` |

A useful way to draw the boundary: **connectors know your private world (your
deals, your calendar, your docs); Linkup knows the public world (the live web);
the LLM stitches the two together into something useful.** Keep those three jobs
separate and your agents stay simple, swappable, and trustworthy.

## What this buys you

- **No stale facts.** The web is the source of truth, queried at run time.
- **No hallucinated specifics.** The LLM phrases; it does not invent.
- **Citations for free.** URLs flow from Linkup through to the output.
- **Swappable everything.** The LLM and the connectors are pluggable; Linkup
  stays the constant engine underneath.

Next: [the four endpoints](./02-the-four-endpoints.md) that make up the entire
Linkup API surface.

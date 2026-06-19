# Providers — the menu around Linkup

Linkup is the engine: the agent's connection to the live web. Everything on this
page sits **around** Linkup — the LLM that reasons over its output, and the
connectors that feed in context and push out results. None of it is locked to one
vendor. This is a menu; pick per use case.

```
        context in                    THE ENGINE                     results out
   ┌──────────────────┐        ┌────────────────────────┐     ┌──────────────────┐
   │ CRM · Calendar   │ ─────▶ │   LINKUP  search ·     │ ──▶ │ Notion · Slack   │
   │ (your private    │        │   fetch · research ·   │     │ Email · CRM · DB │
   │  world)          │        │   tasks (live web)     │     │ (destinations)   │
   └──────────────────┘        └───────────┬────────────┘     └──────────────────┘
                                           ▼
                                ┌────────────────────────┐
                                │  LLM reasoning layer    │  (Claude by default)
                                └────────────────────────┘
```

---

## 1. LLMs / reasoning layer

The LLM plans queries and synthesizes Linkup's findings into output. It is **not**
a source of world-facts — that's Linkup's job. The engine ships with a one-method
interface (`linkup_engine/llm.py`) so any of these drops in behind `get_llm()`.

Default is **Anthropic Claude** — strong at tool use and synthesis, which is
exactly what the reasoning layer does.

| Provider | Models (use-case fit) | SDK | Env var |
|----------|----------------------|-----|---------|
| **Anthropic Claude** *(default)* | `claude-opus-4-8` (hardest reasoning/synthesis), `claude-sonnet-4-6` (fast, cheap, the everyday default), `claude-haiku-4-5` (cheapest/fastest, simple extraction/classification) | `anthropic` | `ANTHROPIC_API_KEY` |
| **OpenAI** | GPT-4.1 (general), o-series (hard reasoning) | `openai` | `OPENAI_API_KEY` |
| **Google Gemini** | Gemini 1.5/2.x Pro (long context), Flash (cheap/fast) | `google-genai` | `GOOGLE_API_KEY` |
| **Mistral** | Large (general), small/codestral (cheap/code) | `mistralai` | `MISTRAL_API_KEY` |
| **Cohere** | Command R/R+ (RAG-tuned, grounded generation) | `cohere` | `COHERE_API_KEY` |
| **Meta Llama** | Llama 3.x via a host (open weights) | via Groq/Together/Fireworks/Bedrock | host's key |
| **AWS Bedrock** | Claude, Llama, Mistral, etc. (enterprise/VPC) | `boto3` | AWS creds + `AWS_REGION` |
| **Azure OpenAI** | GPT models (enterprise/compliance) | `openai` (Azure mode) | `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT` |
| **Google Vertex AI** | Gemini, partner models (GCP-native) | `google-cloud-aiplatform` | GCP creds + `GOOGLE_CLOUD_PROJECT` |
| **Groq** | Llama/Mixtral (lowest latency inference) | `groq` | `GROQ_API_KEY` |
| **Together / Fireworks** | Open models (cheap hosted OSS) | `together` / `fireworks-ai` | provider key |
| **Local: Ollama** | Any local model (offline, no data egress) | `ollama` / OpenAI-compatible | none (localhost) |
| **Local: vLLM** | Self-hosted OSS at scale (your GPUs) | OpenAI-compatible HTTP | none (your endpoint) |

**Adding one** is ~10 lines: write a class with a `complete(system, user,
max_tokens)` method and register it in `_PROVIDERS` in `linkup_engine/llm.py`.

```python
# linkup_engine/llm.py
class GeminiLLM:
    def __init__(self, model="gemini-1.5-pro", api_key=None):
        from google import genai
        self.client = genai.Client(api_key=api_key or os.environ["GOOGLE_API_KEY"])
        self.model = model

    def complete(self, system: str, user: str, max_tokens: int = 1024) -> str:
        resp = self.client.models.generate_content(
            model=self.model,
            contents=user,
            config={"system_instruction": system, "max_output_tokens": max_tokens},
        )
        return resp.text or ""

_PROVIDERS["gemini"] = GeminiLLM        # now: get_llm("gemini")
```

Many local/hosted options (Ollama, vLLM, Groq, Together, Fireworks) are
OpenAI-compatible — point the existing `OpenAILLM` at their `base_url` instead of
writing a new class.

---

## 2. CRMs

Read contacts and write notes. In the kit, a CRM exposes `find_contact(email)`,
`last_touch(email)`, `create_note(email, body)` (see `connectors/crm/`).

| CRM | Fit | SDK / API | Env var |
|-----|-----|-----------|---------|
| **HubSpot** *(default stub)* | SMB/mid-market sales+marketing | `hubspot-api-client` / REST | `HUBSPOT_ACCESS_TOKEN` |
| **Salesforce** | Enterprise | `simple-salesforce` / REST | `SALESFORCE_ACCESS_TOKEN` |
| **Attio** | Modern, API-first CRM | REST | `ATTIO_API_KEY` |
| **Pipedrive** | Sales-pipeline focused | REST | `PIPEDRIVE_API_TOKEN` |
| **Close** | High-velocity inside sales | REST | `CLOSE_API_KEY` |
| **Zoho CRM** | SMB, cost-sensitive | REST (OAuth) | `ZOHO_ACCESS_TOKEN` |
| **MS Dynamics 365** | Microsoft-stack enterprise | Dataverse Web API | `DYNAMICS_ACCESS_TOKEN` |
| **Affinity** | VC / relationship intelligence | REST | `AFFINITY_API_KEY` |

---

## 3. Email

Send the agent's output as email.

| Provider | Fit | SDK / API | Env var |
|----------|-----|-----------|---------|
| **Resend** | Developer-first transactional | `resend` | `RESEND_API_KEY` |
| **SendGrid** | High-volume transactional | `sendgrid` | `SENDGRID_API_KEY` |
| **Postmark** | Deliverability-focused transactional | REST | `POSTMARK_SERVER_TOKEN` |
| **Gmail API** | Send as a Google user | `google-api-python-client` | OAuth creds JSON |
| **Microsoft Graph / Outlook** | Send as an M365 user | `msgraph-sdk` / REST | OAuth (Graph) |
| **Mailgun** | Email API + routing | REST | `MAILGUN_API_KEY` |
| **Amazon SES** | Cheap, AWS-native bulk | `boto3` | AWS creds |

---

## 4. Calendar

Read events to know who/when (the trigger for the meeting-prep pattern).

| Provider | Fit | SDK / API | Env var |
|----------|-----|-----------|---------|
| **Google Calendar** *(default)* | Google Workspace | `google-api-python-client` | `GOOGLE_CALENDAR_CREDENTIALS_JSON` |
| **Microsoft Graph** | M365 / Outlook calendar | `msgraph-sdk` | OAuth (Graph) |
| **Cal.com** | Open-source scheduling | REST | `CALCOM_API_KEY` |
| **Calendly** | Hosted scheduling | REST | `CALENDLY_API_KEY` |

---

## 5. Destinations / sinks

Where the agent writes its result.

| Destination | Fit | SDK / API | Env var |
|-------------|-----|-----------|---------|
| **Notion** *(default)* | Docs, wikis, drafts | `notion-client` | `NOTION_API_KEY` |
| **Slack** | Team notifications, briefs | `slack_sdk` | `SLACK_BOT_TOKEN` |
| **Linear** | Engineering issues/tasks | GraphQL | `LINEAR_API_KEY` |
| **Jira** | Enterprise issue tracking | `jira` / REST | `JIRA_API_TOKEN` |
| **Airtable** | Structured records | `pyairtable` | `AIRTABLE_API_KEY` |
| **Google Docs / Sheets** | Long-form / tabular output | `google-api-python-client` | OAuth creds |
| **Confluence** | Enterprise wiki | REST | `CONFLUENCE_API_TOKEN` |
| **WordPress** | Publish articles (SEO pattern) | REST | app password |
| **Webflow** | CMS-driven sites | REST | `WEBFLOW_API_TOKEN` |
| **Discord** | Community notifications | webhook / `discord.py` | webhook URL / bot token |
| **Postgres / Supabase** | Persist results in your DB | `psycopg` / `supabase` | `DATABASE_URL` / Supabase keys |
| **Generic webhook** | Anything else | `requests.post` | webhook URL |

---

## 6. Vector DBs / memory (optional)

| Store | Fit | SDK | Env var |
|-------|-----|-----|---------|
| **Pinecone** | Managed vector search | `pinecone` | `PINECONE_API_KEY` |
| **Weaviate** | Open-source + hybrid search | `weaviate-client` | `WEAVIATE_API_KEY` |
| **pgvector** | Vectors inside Postgres | `psycopg` + `pgvector` | `DATABASE_URL` |
| **Chroma** | Lightweight local/embedded | `chromadb` | none (local) |
| **Qdrant** | High-performance, self-host or cloud | `qdrant-client` | `QDRANT_API_KEY` |

**Important framing.** Linkup is the live web — it usually **replaces** the need
to pre-crawl and index the public internet into a vector DB. Use a vector store
for **your own private corpus** (internal docs, past tickets, product data) and
use **Linkup for the live web**. They're complementary: vector DB = your memory,
Linkup = the world's current facts.

---

## 7. Agent frameworks

The engine is plain Python and works standalone, but it also slots into the major
frameworks — Linkup ships as a **tool** inside them.

| Framework | Fit | How Linkup fits |
|-----------|-----|-----------------|
| **LangChain** | Most-used orchestration | Wrap a `Linkup` call as a `Tool`; bind to an agent |
| **LlamaIndex** | RAG + data agents | Linkup as a retrieval/tool source for live data |
| **CrewAI** | Multi-agent crews | Give a crew member a Linkup search/fetch tool |
| **AutoGen** | Conversational multi-agent | Register Linkup as a function/tool |
| **Vercel AI SDK** | TypeScript/JS apps | Linkup as a tool in `streamText`/`generateText` |
| **Agno** | Lightweight agent framework | Linkup as a tool |
| **Composio** | Managed tool catalog | Linkup available as a hosted tool |

Linkup also ships first-class integrations beyond Python SDKs:

- **MCP server** — expose Linkup to any MCP-capable client (Claude, Cursor, etc.)
  as native search/fetch/research tools.
- **Skills install** — `npx skills add LinkupPlatform/skills` to give a coding
  agent the Linkup query-construction know-how this kit's `CLAUDE.md` encodes.

---

## 8. Orchestration / scheduling

Trigger agents on a schedule or in response to events; pair with `/tasks` for
batch.

| Tool | Fit |
|------|-----|
| **cron** | Simplest recurring trigger on a box you control |
| **GitHub Actions** | Free scheduled jobs in CI; great for nightly batches |
| **Modal** | Serverless Python with cron + autoscale |
| **Temporal** | Durable, long-running workflows (pairs well with async `/research`) |
| **Airflow** | DAG-based data pipelines |
| **Prefect** | Pythonic dataflow orchestration |
| **Inngest** | Event-driven, durable steps |
| **Trigger.dev** | Event/cron jobs for TS/JS stacks |

Batch pattern: collect work into a single `/tasks` call (1-100 mixed
search/fetch/research/extract) and let the scheduler fire it. See
[05-patterns.md](./05-patterns.md#bulk-and-scheduled-runs-via-tasks).

---

## How to choose

Start from the **default stack** — Claude (Sonnet) as the reasoning layer, your
existing CRM and calendar as the context edges, and Slack or Notion as the sink —
and swap only where you have a real constraint: pick the LLM by reasoning
difficulty and budget (Haiku for cheap extraction, Sonnet for the everyday work,
Opus for the hardest synthesis; Bedrock/Azure/Vertex when compliance or VPC
dictates it; Ollama/vLLM when data can't leave your network); pick connectors to
match the systems your team already lives in; add a vector DB only for your own
private corpus; and add an orchestrator only when you need scheduled or
event-driven runs. Throughout, **Linkup stays the constant in the middle** — the
one engine that turns the live web into grounded, sourced facts your agent can act
on.

# Architecture (as built)

A technical description of the system **as it was actually built** across
milestones 1–5. For the gentler 20-minute orientation, see
[`architecture/overview.md`](architecture/overview.md); for *why* each decision
was made, see [`design-decisions.md`](design-decisions.md).

---

## System at a glance

A local, single-machine pipeline that turns public news sources into an AI/ML
newsletter:

```
News sources ──> Fetchers ──> SQLite + Markdown ──> Filter ──> Summarize ──> Write
(HN, RSS,        (async,       (storage +           (LLM)      (LLM)         (LLM)
 GitHub)          concurrent)   MCP server)                                  └─> newsletter.md
```

Every stage hands off through a **file or the database**, so each stage can run
and be debugged independently.

---

## Design principles in force

- **SOLID** — applied in M2 and proven, not just claimed:
  - *SRP:* fetchers fetch, `ArticleTransformer` converts, `*Storage` persists.
  - *OCP:* `BaseFetcher` ABC — GitHub Trending was added as **1 new file, 0 edits**
    to existing code.
  - *LSP/ISP:* all fetchers are substitutable behind one interface.
  - *DIP:* the orchestrator depends on an `ArticleStorage` interface; concretes
    are injected at the `main.py` composition root (swapping in `JSONStorage`
    was a **1-line** change).
- **Design patterns actually used:**
  - *Template Method* — `BaseAgent.execute()` owns `load -> process -> save`;
    each agent fills in the three steps.
  - *Factory* — `FetcherFactory` builds the right fetcher.
  - *Strategy* — `RateLimitStrategy` (Semaphore / TokenBucket), injected.
- **Async-first I/O** — concurrent fetching via `asyncio.gather`, semaphore-capped.

> Note: there is **no** Observer pattern — the pipeline is a straight sequential
> orchestration (`complete_pipeline.py`), not an event/subscriber system.

---

## Components

### 1. Fetchers (M1–M2) — `src/fetchers/`
- Sources: **HackerNews** (API), **RSS** (`feedparser`), **GitHub Trending** (scraped, no public API).
- Async + concurrent; semaphore caps concurrency (politeness / anti-ban).
- Per-item `try/except` so one bad article doesn't sink the batch.
- All sources converge on one `Article` model (`src/models/article.py`) via
  per-shape transformers.

### 2. Storage (M1, M4) — `src/storage/`, `src/database/`
- `MarkdownStorage` and `JSONStorage` behind the `ArticleStorage` interface (DIP).
- `DatabaseManager` (`aiosqlite`) — async SQLite with a `url UNIQUE` de-dup guard,
  parameterized queries, indexed `source` / `published_at`.

### 3. Agents (M3–M4) — `src/agents/`
- **`BaseAgent`** (Template Method): owns the `load -> process -> save` lifecycle,
  the LiteLLM call (`_call_llm`), the tool-call loop (`_call_llm_with_tools`),
  and the resilience controls:
  - *E6* per-minute throttle (min-interval pacing),
  - *E9* per-run call budget + `DailyQuotaExceeded` (stop, don't retry, on the daily cap),
  - transient-5xx retry with backoff.
- **`NewsFilterAgent`** — LLM relevance classification, returns score + reasoning;
  distinguishes a real verdict (`status: judged`) from a failed call (`status: error`).
- **`SummarizerAgent`** — groups kept articles by topic, LLM-summarizes each;
  per-topic try/except so one failure can't discard completed summaries.
- **`WriterAgent`** — turns the summary into a newsletter (final stage).

### 4. MCP integration (M4) — `src/mcp/`, `src/skills/`
- **Database MCP server** (`database_server.py`) exposes 3 tools over stdio:
  `query_articles`, `search_articles`, `get_sources`. Diagnostics go to **stderr**
  so they never corrupt the stdout JSON-RPC channel.
- **`SearchSkill`** — a reusable, higher-level wrapper over the MCP search tool
  (`skill.search("...")` hides connect/initialize/call/parse).

### 5. Evaluation (M5) — `src/evaluation/`, `data/evaluation/`
- **Golden dataset:** 10 hand-labeled cases (6 relevant, 4 not).
- **`FilterEvaluator`** runs the agent over the dataset and reports
  **accuracy / precision / recall / F1**, with per-case PASS/FAIL + reasoning.
- Resilient: stops cleanly on `DailyQuotaExceeded` and still writes a *partial*
  report (banner) instead of crashing.

---

## Data flow

```
External APIs / pages
        │  fetchers (async, concurrent)
        ▼
data/articles/all_articles.md  +  data/news_agent.db   (also queryable via MCP)
        │  NewsFilterAgent (LLM)
        ▼
data/context/filtered_articles.md
        │  SummarizerAgent (LLM, topic grouping)
        ▼
data/context/summary.md
        │  WriterAgent (LLM)
        ▼
data/output/newsletter.md
```

---

## Cross-cutting concerns

- **Encoding:** Windows console + file I/O is forced to UTF-8 (`BaseAgent` sets
  stdout once; file reads/writes pass `encoding="utf-8"`) — the recurring "E2"
  fix for emoji / non-Latin text.
- **Rate / quota handling:** per-minute throttle (recoverable) is separated from
  the per-day cap (not recoverable) — the agent throttles the former and *stops*
  for the latter, reporting honestly.
- **Provider-agnostic:** all LLM access is via LiteLLM; switching providers is a
  one-line `LITELLM_MODEL` change. Repo default: `gemini/gemini-2.5-flash-lite`.

---

## Measured results

- **Tests:** 41 collected; offline + deterministic for core logic (one known-flaky
  live-network timing test — see `challenges-and-strategies.md` D2).
- **Filter quality (M5 golden-dataset eval):** accuracy 90% (9/10), precision
  85.7%, recall 100%, F1 0.923. See `data/evaluation/evaluation_report.md`.

---

## Known limitations / future work

- `search_articles` and `get_sources` load up to 1000 rows and filter in Python
  rather than in SQL (`LIKE` / `DISTINCT`) — fine at current scale.
- The flaky D2 timing test should assert correctness rather than wall-clock.
- `SearchSkill` is wired into `SummarizerAgent` but not yet used for extra context.
- No scheduling / web UI / logging framework — intentionally out of scope.

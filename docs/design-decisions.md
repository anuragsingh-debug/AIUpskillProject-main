# Design Decisions — Milestone 2 (SOLID Refactoring)

**Branch:** `feature/milestone-2-solid`
**Goal:** take the working Milestone 1 news fetcher and restructure it to follow the 5 SOLID
principles + 3 design patterns — **without changing what the program does**.

The behaviour is identical (fetch HackerNews + RSS + GitHub Trending, save to markdown); only the
*structure* changed. Two "zero-edit" extensions prove the structure works:
a new **GitHub** source (proves OCP) and a new **JSON** storage (proves DIP).

---

## SOLID Principles

### 1. Single Responsibility Principle (SRP)

**Problem:** the M1 fetchers fetched data, transformed it into `Article` objects, *and* knew about
file output — three reasons to change in one class.

**Solution:**
- `src/transformers/article_transformer.py` — only turns raw data into `Article`s
  (`transform_hackernews`, `transform_rss`).
- `src/storage/markdown_storage.py` — only writes `Article`s to markdown.
- Fetchers now only fetch.

**Payoff:** if HackerNews changes its data shape, only `article_transformer.py` changes; if the
output format changes, only the storage class changes.

### 2. Open/Closed Principle (OCP) — headline proof #1

**Problem:** adding a new source in M1 meant editing existing fetcher code.

**Solution:** `src/fetchers/base_fetcher.py` defines a `BaseFetcher` ABC (the contract). All fetchers
inherit it. A brand-new source, `src/fetchers/github_trending_fetcher.py` (scraped with
BeautifulSoup, since GitHub has no API), was added **without editing any existing fetcher,
transformer, or storage file**.

**Proof:** adding GitHub = 1 new file + 1 registration line in the composition root. The 3 sources
run together: ~30 HN + 20 RSS + ~14 GitHub articles.

**Trade-off:** `GitHubTrendingFetcher` builds its `Article`s directly instead of going through
`ArticleTransformer`. Adding a `transform_github` method would have meant *editing* an existing file
and breaking the zero-edit OCP proof. SRP was bent slightly to keep OCP — a deliberate judgement call.

### 3. Liskov Substitution Principle (LSP)

**Problem:** fetchers must be truly interchangeable wherever a `BaseFetcher` is expected.

**Solution:** `tests/test_substitutability.py` loops over HN/RSS/GitHub through the base interface and
asserts each exposes `fetch_articles` / `get_source_name` / `fetch_and_save` and returns
`List[Article]`. The orchestrator relies on this — it calls every fetcher the same way, with no
`isinstance` branching.

### 4. Interface Segregation Principle (ISP)

**Problem:** not every source needs the same capabilities (auth, pagination), so a fat base
interface would force fetchers to implement methods they don't use.

**Solution:** `BaseFetcher` is kept minimal (3 methods all fetchers need). Optional capabilities live
in separate interfaces in `src/fetchers/interfaces.py` — `AuthenticatedFetcher` (`authenticate`) and
`PaginatedFetcher` (`fetch_page`). A future `TwitterFetcher` would be
`class TwitterFetcher(BaseFetcher, AuthenticatedFetcher)`; HackerNews never carries a useless
`authenticate()`.

### 5. Dependency Inversion Principle (DIP) — headline proof #2

**Problem:** high-level code depended on concrete classes (`MarkdownStorage`, the concrete fetchers).

**Solution:**
- `src/storage/base_storage.py` — `ArticleStorage` ABC; `MarkdownStorage` implements it.
- `FetchOrchestrator` takes an injected `List[BaseFetcher]` and an `ArticleStorage`; it no longer
  imports or constructs concrete fetchers.
- `src/main.py` is the **composition root** — the one place that builds concrete objects and wires
  them together.

**Proof:** `src/storage/json_storage.py` (`JSONStorage(ArticleStorage)`) was dropped in by changing
**one line** in `main.py` (`MarkdownStorage()` → `JSONStorage(...)`); output became JSON with the
orchestrator and fetchers untouched. Mirror of the OCP/GitHub proof, but for storage.

**Testing payoff:** `tests/test_orchestrator.py` injects `Mock`/`AsyncMock` fake fetchers, so the
orchestrator is tested offline and deterministically (no live HTTP). This replaced a flaky
live-network test.

---

## Design Patterns

### Template Method — `BaseFetcher.fetch_and_save`
Defines the algorithm skeleton (fetch → save) once; subclasses customise only the fetch step via
`fetch_articles()`. Every fetcher gets consistent save behaviour for free.

### Factory — `src/factories/fetcher_factory.py`
`FetcherFactory.create("hackernews", transformer, storage)` builds a fetcher from a string name, so
callers don't need to know concrete classes or argument order. `register()` adds new types without
editing the factory (OCP-friendly); `get_available_types()` lists what it can build. RSS is handled
as a special case because its constructor needs `feed_url`.

### Strategy — `src/strategies/rate_limit_strategy.py`
`RateLimitStrategy` is a swappable rate-limiting algorithm: `SemaphoreStrategy` (limit concurrency)
and `TokenBucketStrategy` (limit over time, allow bursts). The base class provides
`__aenter__`/`__aexit__`, so any strategy works as `async with strategy:`. `HackerNewsFetcher` takes
an injectable `rate_limiter` (defaults to `SemaphoreStrategy(10)`); GitHub deliberately has none
(single request, no need — an ISP-style decision).

---

## Metrics

| | Before (M1) | After (M2) |
|---|---|---|
| Responsibilities per fetcher | ~3 (fetch + transform + know output) | 1 (fetch) |
| Add a new source | edit existing code | 1 new file, 0 edits (GitHub proof) |
| Swap storage backend | rewrite call sites | 1 line (JSONStorage proof) |
| Orchestrator tests | live network, flaky | mocked, offline, deterministic |
| Tests | — | 23 passing, ruff clean |

---

## Trade-offs

- **More files / more abstraction.** Con: more to navigate. Pro: each piece is small, focused, and
  independently testable.
- **SRP bent for the GitHub fetcher** (builds its own Articles) to preserve the zero-edit OCP proof.
- **Dead code kept on purpose:** `src/utils/rate_limiter.py` (M1's limiter) is superseded by
  `SemaphoreStrategy` but retained as an M1 artifact.

---

## Lessons Learned

- **Copied tutorial code needs review + tests.** Several snippets carried real bugs we only caught by
  running `ruff` + `pytest`: missing `List`/`Article` imports (ISP interfaces, the Factory), an
  unreachable RSS branch in the Factory, and a Strategy version missing `async with` support that
  broke the HackerNews fetcher.
- **Mock against your real call path.** A tutorial test mocked `fetch_and_save`, but our concurrent
  orchestrator calls `fetch_articles` + `get_source_name`; awaiting a plain `Mock` raised `TypeError`
  until the right methods were faked.
- **Don't let a "simplifying" refactor kill a feature.** A simpler fetcher snippet would have made
  HackerNews sequential, dropping M1's `asyncio.gather` concurrency — tests flagged it.

---

*Milestone 2 — all 5 SOLID principles and 3 design patterns applied. 23 tests pass, ruff clean,
app fetches from 3 sources.*

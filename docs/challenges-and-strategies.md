# Challenges & Strategies — AI Upskilling Project

**Purpose:** a report-/presentation-ready record of the real problems hit while building the
AI news pipeline, the strategy used to overcome each, and the outcome. Every item below is grounded
in actual code in this repo — not generic theory.

**Scope so far:** Milestone 0 (Setup) → Milestone 1 (Async Fetcher) → Milestone 2 (SOLID Refactor).
Milestone 3 (First Agent) is the next phase.

---

## 1. Executive summary (one line per milestone)

| Milestone | Theme | Hardest challenge | Strategy that solved it |
|---|---|---|---|
| M0 | Setup & tooling | Provider lock-in + secret handling | LiteLLM model-string + `.env` + `verify_setup.py` |
| M1 | Async fetcher | Slow sequential API calls; risk of being blocked | `asyncio.gather` concurrency + semaphore rate limiting |
| M2 | SOLID + patterns | Code that couldn't grow without breaking | Abstractions (ABCs) + dependency injection + tests as guardrails |

**Headline results:** 3 live sources (HackerNews + RSS + GitHub Trending), **27 tests passing**,
`ruff` clean, **77% coverage**. Two "zero-edit" extensions prove the design (GitHub source = OCP,
JSON storage = DIP).

---

## 2. Challenges & strategies (detailed)

Each entry follows the same shape so it lifts straight into a report:
**Challenge → Why it mattered → Strategy → Outcome.**

### Category A — Concurrency & external APIs (Milestone 1)

**A1. Sequential fetching was too slow.**
- *Why it mattered:* HackerNews returns a list of IDs, then each story needs its own API call
  (~30 calls). Done one at a time this is slow and doesn't scale.
- *Strategy:* fire all per-story requests concurrently with `asyncio.gather` (see
  `src/fetchers/hackernews_fetcher.py::_fetch_stories`). HackerNews and RSS are also fetched in
  parallel at the orchestrator level.
- *Outcome:* fetch time dropped from "sum of all calls" to "slowest single call".

**A2. Firing 30 requests at once risks being rate-limited / blocked.**
- *Why it mattered:* hammering a public API with a burst can get the client throttled or banned.
- *Strategy:* a semaphore caps concurrency at 10 (`SemaphoreStrategy`, injected into the fetcher).
  Analogy used in code comments: an ATM with 2 machines and a guard letting people in 2 at a time.
- *Outcome:* concurrency without abuse; the limit is tunable per source.

**A3. Each source speaks a different "language".**
- *Why it mattered:* HackerNews is JSON, RSS is a feed format, GitHub Trending has **no public API**.
- *Strategy:* a transformer per shape (`transform_hackernews`, `transform_rss`); GitHub is scraped
  with BeautifulSoup. All three converge on one `Article` model.
- *Outcome:* downstream code only ever sees uniform `Article` objects.

**A4. Partial failures (one story errors or returns null).**
- *Why it mattered:* one bad network call shouldn't crash the whole fetch.
- *Strategy:* per-story `try/except` returning `None`, then filter `None`s out before transforming
  (`_fetch_story` / `_fetch_stories`).
- *Outcome:* resilient fetching — a single failure degrades gracefully instead of aborting.

### Category B — Designing for change (Milestone 2 / SOLID)

**B1. "God-class" fetchers did three jobs (fetch + transform + save).**
- *Why it mattered:* any change to data shape OR output format forced edits to the same class —
  fragile and hard to test.
- *Strategy (SRP):* extract `ArticleTransformer` (data → `Article`) and `MarkdownStorage` (write
  files). Fetchers now only fetch.
- *Outcome:* one reason to change per class.

**B2. Adding a new source meant editing existing, working code.**
- *Why it mattered:* every edit to shipped code is a regression risk.
- *Strategy (OCP):* a `BaseFetcher` ABC defines the contract; new sources subclass it. Proved by
  adding **GitHub Trending = 1 new file + 1 registration line, 0 edits** to existing fetchers.
- *Outcome:* the codebase is open to extension, closed to modification — demonstrably.

**B3. Tight coupling to concrete classes made testing need the real network/disk.**
- *Why it mattered:* tests that hit live HTTP are slow, flaky, and non-deterministic.
- *Strategy (DIP):* an `ArticleStorage` interface + constructor injection; `main.py` is the single
  composition root that wires concretes together. Tests inject `Mock`/`AsyncMock` fetchers.
- *Outcome:* the orchestrator is now tested offline and deterministically. Bonus proof: swapping in
  `JSONStorage` was a **one-line** change (DIP mirror of the OCP/GitHub proof).

### Category C — Quality traps we hit and caught (Milestone 2)

**C1. Copied tutorial code carried real bugs.**
- *Why it mattered:* example snippets aren't production-safe.
- *Strategy:* run `ruff` + `pytest` on everything. They caught missing `List`/`Article` imports,
  an unreachable RSS branch in the Factory, and a Strategy class missing `async with` support that
  broke the HackerNews fetcher.
- *Outcome:* "works on the slide" became "works in CI".

**C2. A mock test mocked the wrong method.**
- *Why it mattered:* a tutorial test mocked `fetch_and_save`, but the concurrent orchestrator calls
  `fetch_articles` + `get_source_name`. Awaiting a plain `Mock` raised `TypeError`.
- *Strategy:* mock the **real call path** with `AsyncMock` for the methods actually invoked.
- *Outcome:* tests exercise the true code path, not a fiction.

**C3. A "simplifying" refactor would have silently killed concurrency.**
- *Why it mattered:* a cleaner-looking fetcher snippet made HackerNews sequential again, dropping
  the `asyncio.gather` speed-up from M1.
- *Strategy:* keep behaviour-guarding tests; let them flag the regression.
- *Outcome:* a feature (concurrency) survived a structural refactor.

### Category D — Environment & known issues (cross-cutting)

**D1. `datetime` is not JSON-serializable.**
- *Why it mattered:* `JSONStorage` crashed dumping `Article.published_at`.
- *Strategy:* `json.dump(..., default=str)` to stringify non-JSON-native types.
- *Outcome:* JSON output works without changing the `Article` model.

**D2. Flaky timing-based integration test *(open issue)*.**
- *Why it mattered:* `tests/test_fetchers_integration.py::test_concurrent_fetching` asserts
  `elapsed < 10.0` against the **live** network. It passes alone (~4s) but fails under coverage
  instrumentation / slow networks — a non-deterministic failure.
- *Strategy (recommended):* assert *correctness* (articles returned) rather than wall-clock, or move
  it behind an `@pytest.mark.integration` marker excluded from the default run, or mock the network.
- *Outcome:* documented and slated for the next cleanup; the offline mocked orchestrator tests
  already cover the logic deterministically.

**D3. Windows / tooling friction.**
- *Why it mattered:* base Python lacked `pytest`; `gh` CLI isn't installed; paths have spaces.
- *Strategy:* run everything through the project `venv` (`./venv/Scripts/python.exe -m ...`); create
  PRs via the GitHub compare URL until `gh` is available.
- *Outcome:* reproducible local runs regardless of global Python state.

---

## 3. Condensed table (good for a single slide)

| # | Challenge | Strategy | Principle / Tool |
|---|---|---|---|
| A1 | Slow sequential API calls | Concurrent `asyncio.gather` | asyncio |
| A2 | Burst requests get blocked | Semaphore concurrency cap | Strategy pattern |
| A3 | Sources have different formats | One transformer per shape → one `Article` | SRP |
| A4 | One call fails → whole fetch dies | Per-item try/except, drop `None` | Resilience |
| B1 | Fetcher did 3 jobs | Split into transformer + storage | SRP |
| B2 | New source = edit old code | `BaseFetcher` ABC; GitHub added 0-edit | OCP |
| B3 | Tests needed live network | Storage interface + DI + mocks | DIP |
| C1 | Tutorial code had bugs | `ruff` + `pytest` gate | CI hygiene |
| C2 | Mocked the wrong method | Mock the real call path (`AsyncMock`) | Testing |
| C3 | Refactor dropped concurrency | Behaviour-guarding tests | Regression safety |
| D1 | `datetime` not JSON-safe | `json.dump(default=str)` | Serialization |
| D2 | Flaky timing test | Assert correctness, not wall-clock | Test design |

---

## 4. Presentation talking points (speaker notes)

Use these as slide bullets or narration:

1. **"We optimised for change, not just correctness."** The standout metric isn't speed — it's that
   adding a whole new data source took *one new file and zero edits* to existing code.
2. **"Tests turned theory into proof."** OCP and DIP aren't claims here; each is backed by a concrete
   zero-/one-line extension (GitHub source, JSON storage) and a passing test suite.
3. **"Async made it fast; rate limiting made it safe."** Concurrency and politeness to the API are a
   pair, solved together with `gather` + a semaphore.
4. **"We trust nothing we copied."** Linters and tests caught several bugs in tutorial snippets —
   the discipline mattered more than the code.
5. **"We document our open issues."** The flaky timing test is named, explained, and has a fix plan —
   honesty over a green-but-misleading dashboard.

---

## 5. Evidence / metrics (for an appendix slide)

- **Sources:** HackerNews (API) + RSS + GitHub Trending (scraped). ~30 + 20 + ~14 articles per run.
- **Tests:** 27 passing; offline + deterministic for core logic.
- **Lint:** `ruff` clean across `src/` and `tests/`.
- **Coverage:** 77% overall; new storage backends and patterns at 90–100%.
- **Design proof points:** GitHub source (OCP), JSON storage (DIP) — both added without touching the
  orchestrator or existing fetchers.

*Reproduce locally:*
```bash
./venv/Scripts/python.exe -m pytest -q                 # tests
./venv/Scripts/python.exe -m pytest --cov=src -q       # coverage
./venv/Scripts/python.exe -m ruff check src tests      # lint
```

---

*Living document — extend with Milestone 3 (agents, LiteLLM, tool use) challenges as they arise.*

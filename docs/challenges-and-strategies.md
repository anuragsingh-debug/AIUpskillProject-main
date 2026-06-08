# Challenges & Strategies — AI Upskilling Project

**Purpose:** a report-/presentation-ready record of the real problems hit while building the
AI news pipeline, the strategy used to overcome each, and the outcome. Every item below is grounded
in actual code in this repo — not generic theory.

**Scope so far:** Milestone 0 (Setup) → Milestone 1 (Async Fetcher) → Milestone 2 (SOLID Refactor) →
Milestone 3 (First Agent — *in progress*, Evening 11: LiteLLM verified + `BaseAgent` built;
Evening 12: `NewsFilterAgent` runs end-to-end; Evening 13: tools wired + autonomous tool call;
Evening 14: mocked tests + fetch→filter pipeline).

---

## 1. Executive summary (one line per milestone)

| Milestone | Theme | Hardest challenge | Strategy that solved it |
|---|---|---|---|
| M0 | Setup & tooling | Provider lock-in + secret handling | LiteLLM model-string + `.env` + `verify_setup.py` |
| M1 | Async fetcher | Slow sequential API calls; risk of being blocked | `asyncio.gather` concurrency + semaphore rate limiting |
| M2 | SOLID + patterns | Code that couldn't grow without breaking | Abstractions (ABCs) + dependency injection + tests as guardrails |
| M3 *(in progress)* | First AI agent | Wiring an LLM in cleanly + Windows/runtime gotchas | LiteLLM `completion()` + `BaseAgent` (Template Method) + UTF-8 console fix |

**Headline results:** 3 live sources (HackerNews + RSS + GitHub Trending), **40 tests passing**
(all offline/mocked), `ruff` clean. Two "zero-edit" extensions prove the design (GitHub source = OCP,
JSON storage = DIP); the agent's rate-limit (E6) and daily-quota (E9) handling is fully mocked-tested.

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

### Category E — First AI agent (Milestone 3, in progress)

**E1. Connecting to an LLM without locking into one provider.**
- *Why it mattered:* hard-coding a vendor SDK means rewriting code to switch models later.
- *Strategy:* LiteLLM's single `completion(model=..., messages=[...])` call; the model is read from
  `LITELLM_MODEL` in `.env` (currently `gemini/gemini-2.5-flash-lite`). Swapping providers = editing
  one env line. A throwaway `scripts/test_llm.py` proved the connection end-to-end before any agent
  code was written.
- *Outcome:* provider-agnostic LLM access confirmed working against Gemini.

**E2. Windows console crashed on emoji in LLM replies.**  *(the standout lesson of the day)*
- *Why it mattered:* the LLM call **succeeded**, but `print()` of the reply threw
  `UnicodeEncodeError` — Windows terminals default to the `cp1252` codec, which can't encode emoji
  (`😊`, and our own `🤖`/`✅` status prints). A working feature looked broken.
- *Strategy:* `sys.stdout.reconfigure(encoding="utf-8")`, baked into `BaseAgent` so every agent
  inherits safe printing.
- *Outcome:* no more encoding crashes; the fix lives in one place. **Key insight: distinguish "the
  LLM failed" from "printing the result failed" — they look identical in a traceback.**

**E3. "Tutorial code" had a wrong import.**
- *Why it mattered:* a copied snippet had `from litellm import LitelLM` — a name that doesn't exist —
  which also left `completion` undefined. (Same lesson as M2's C1: never trust copied code.)
- *Strategy:* run it; the `ImportError` was immediate. Fixed to `from litellm import completion`.
- *Outcome:* reinforced the "run + lint everything" discipline.

**E4. Running a script directly vs. as a module (import paths).**
- *Why it mattered:* `python tests/test_base_agent.py` failed with `ModuleNotFoundError: src` — a
  directly-run script only puts its own folder on the import path, so `from src...` isn't found.
- *Strategy:* run from the project root as a module: `./venv/Scripts/python.exe -m tests.test_base_agent`.
  The `-m` form puts the root on `sys.path`.
- *Outcome:* reliable way to run any in-repo script that imports `src`.

**E5. A scratch test that runs at import would poison the test suite.**
- *Why it mattered:* the quick `TestAgent` smoke file calls `asyncio.run(...)` at module level — if
  committed, `pytest` would fire a **live LLM call during test collection** and could hang/fail CI.
- *Strategy:* keep smoke scripts untracked; write proper *mocked* agent tests later (Evening 14).
- *Outcome:* the agent deliverable (`base_agent.py`) is committed; the scratch scripts are not.

**E6. Free-tier rate limit silently corrupted the agent's output.**  *(the standout lesson of M3 so far)*
- *Why it mattered:* the first full `NewsFilterAgent` run reported "7/43 relevant" and looked
  successful — but **32 of 43** articles had actually hit Gemini's free-tier limit (**10 requests/
  minute**; we fired 43 in a row). Each 429 (`RESOURCE_EXHAUSTED`) was caught by the `_judge_relevance`
  try/except and returned as `{"relevant": false, "relevance_score": 0}`. So **rate-limit failures
  masqueraded as editorial rejections** — only ~11 articles got a genuine LLM judgment, and good AI
  articles were thrown away for a traffic reason, not a content reason. The program "worked" while
  the data was wrong — the most dangerous kind of bug.
- *Strategy:* reuse the rate-limiting infrastructure already built in M1/M2
  (`src/utils/rate_limiter.py`, and `SemaphoreStrategy` / `TokenBucketStrategy` in
  `src/strategies/rate_limit_strategy.py`) to **space calls under 10/min** before they leave the
  agent — the same "ATM guard" idea that protects the fetchers, now protecting the LLM caller.
- *Outcome:* **DONE (2026-06-08).** `BaseAgent` now paces every LLM call under the per-minute cap
  via `_throttle()` — `requests_per_minute=8` by default → a minimum 7.5s gap between calls, enforced
  with `time.monotonic()` + `time.sleep()`. Because the agent's judging loop is *synchronous and
  serial*, a simple min-interval guard is the right tool here (the async `SemaphoreStrategy` caps
  *concurrency*, which a serial loop doesn't have); same "throttle before the wall" idea as the M1/M2
  fetchers, applied to the LLM caller. Covered by mocked tests (`test_throttle_*`). **Key insight: a
  single `relevance_threshold` filter is only as trustworthy as the calls behind it; throttle *before*
  you hit the wall, don't absorb 429s after — and match the limiter to the call path (rate vs
  concurrency, sync vs async).**

**E7. A swallowed error was indistinguishable from a real negative.**
- *Why it mattered:* the `except` fallback in `_judge_relevance` returned the *same shape* as a
  genuine "not relevant" verdict (`relevant: false, score: 0`). Downstream counting then treated a
  failed call exactly like an editorial "no" — the failure was invisible in the result.
- *Strategy:* distinguish *failure* from *judgment* — mark errored articles as `error`/`unknown` and
  exclude them from the kept/binned tally (or retry), so an outage can never inflate the "rejected"
  count. (Same family as E2's lesson: "the LLM failed" ≠ "the result is negative".)
- *Outcome:* **DONE (2026-06-08).** `_judge_relevance` now returns `status: "judged"` on a real LLM
  answer, or `status: "error"` (with `error_type` = `rate_limit` vs `error`, and `relevance_score:
  None`) on any failure — no more fake `score: 0`. `_process` routes errored articles into a separate
  `errored` bucket and skips them (never a verdict); `_save_result` reports `Could Not Judge: N`, a
  filter rate computed *over judged articles only*, and lists the un-judged ones so they're visible
  for a re-run, not silently lost. `ruff` clean; existing tests pass. **Known gap:** the working-tree
  test file was replaced with 2 live tests, so this error path is not yet covered by a mocked test —
  restoring the mocked suite + a `status: "error"` regression test is the next test task.

**E8. Four copy-paste bugs while wiring tools into the agent (Evening 13).**
- *Why it mattered:* tutorial snippets for the tools / `EnhancedFilterAgent` / its test carried real
  defects that each blocked the run. (Same recurring theme as M2's C1 and M3's E3 — never trust
  copied code.)
- *Strategy:* run early, read the actual error. Caught and fixed: (1) missing `import json` +
  `from typing import Dict` → `NameError` at *import*; (2) an `if __name__ == "__main__"` block
  indented *inside* the test function → the file ran but did nothing; (3) a wrong input path; and
  (4) the most instructive — `EnhancedFilterAgent` → `NewsFilterAgent` → `BaseAgent` is a 3-level
  chain, and the **middle class didn't forward the new `tools=` argument**, so `super().__init__(
  tools=...)` raised `TypeError`. Fixed by giving `NewsFilterAgent.__init__` a `tools=None` param it
  passes up.
- *Outcome:* tools work; the LLM **autonomously called `web_search`** mid-judgment to verify a claim.
  **Key insight: when you add an argument to a base class, every class *in between* must forward it.**

**E9. The free tier has TWO stacked limits — per-minute AND per-day.**  *(updates E6)*
- *Why it mattered:* after fixing the per-minute burst, a 5-article pipeline run *still* failed on
  articles 2–5 — the error had changed to `GenerateRequestsPerDayPerProjectPerModel-FreeTier,
  limit: 20`. We had exhausted the **daily** 20-request cap across the day's test runs.
- *Strategy:* recognise that a rate limiter (spacing requests) solves only the **per-minute** (10)
  cap; the **per-day** (20) cap can't be coded around — it needs waiting for reset (~midnight PT),
  a paid tier, or a different model. Plan dev around mocked tests so progress never depends on quota.
- *Outcome:* **DONE (2026-06-08).** The code now handles the daily wall *gracefully* even though the
  quota itself can't be removed: (1) a distinct `DailyQuotaExceeded` exception is raised when a 429
  names the per-day quota (`_is_daily_quota_error`), so the agent **stops the whole run** and marks the
  current + all remaining articles `error_type: "daily_quota"` (honest, E7) instead of firing 30 more
  doomed calls; (2) an optional `max_calls_per_run` budget lets a run self-limit (e.g. 15) to stay
  under the ~20/day cap on purpose. Covered by mocked tests (`test_daily_quota_*`, `test_max_calls_*`).
  **Key insight: "rate limited" can mean two different walls — read which quota id the 429 names; the
  per-minute one you throttle, the per-day one you stop for.**

**E10. Scratch smoke scripts poisoned the whole `pytest` run; mocking fixed dev-time fragility.**
- *Why it mattered:* `pytest` auto-discovers every `test_*.py`, so the untracked live-LLM smoke
  scripts got collected — and `scripts/test_llm.py` (with the intentionally-broken `LitelLM` import)
  aborted the *entire* suite at collection time. Separately, the tutorial's agent test ran the
  **real** agent → live LLM calls during testing (slow, costs quota, non-deterministic).
- *Strategy:* (a) add `pytest.ini` with `testpaths = tests` + `--ignore` for the 4 smoke files so
  `pytest` "just works"; (b) write the real agent tests **mocked** — patch `_call_llm` with a
  deterministic fake (and learn to key the fake on text unique to the article, `"GPT-5"`, not text
  that also appears in the prompt's few-shot examples, `"JavaScript"`).
- *Outcome:* `pytest` → **27 + 6 passing**, fully offline; the suite never fires a live LLM call.
  **Key insight: tests should exercise *your* logic deterministically — mocking means development
  continues even when the LLM quota is exhausted.**

### Design pattern reused in M3

**Template Method — `BaseAgent.execute()`.** Same pattern as M2's `BaseFetcher`: the base class owns
the fixed workflow (**load → process → save**); subclasses implement only the three varying steps
(`_load_context`, `_process`, `_save_result`). Proves the SOLID groundwork from M2 pays off directly
in M3 — the agent layer didn't have to reinvent structure.

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
| E1 | Don't lock into one LLM vendor | LiteLLM `completion()` + `.env` model | Provider-agnostic |
| E2 | Windows crash on emoji in replies | `sys.stdout.reconfigure(utf-8)` in BaseAgent | Encoding |
| E3 | Copied import name was wrong | Run it; fix `import completion` | Code hygiene |
| E4 | `from src...` fails in a script | Run as module: `python -m ...` from root | Import paths |
| E5 | Scratch test runs at import | Keep untracked; mock real tests later | Test design |
| E6 | Free-tier 429s silently dropped articles | Per-minute `_throttle()` (min-interval) in `BaseAgent` ✅ | Rate limiting |
| E7 | Swallowed error looked like a real "no" | `status:"error"` + separate `errored` bucket, never score 0 ✅ | Error handling |
| E8 | 4 copy-paste bugs wiring tools (incl. middle class not forwarding `tools=`) | Run early, read errors; forward args through the inheritance chain (now also `**kwargs`) | Inheritance |
| E9 | Free tier has per-minute AND per-day caps | `DailyQuotaExceeded` → stop run + optional `max_calls_per_run` budget ✅ | Quotas |
| E10 | Scratch smoke files broke `pytest` collection | `pytest.ini` (`testpaths`+`--ignore`); mock `_call_llm` | Test design |

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
6. **"The M2 design paid off immediately in M3."** The AI agent layer reused the exact Template
   Method pattern from the fetchers — `BaseAgent` owns the workflow, agents fill in the steps. Clean
   architecture wasn't busywork; it made adding AI straightforward.
7. **"A traceback isn't always what it looks like."** Our first agent run 'failed' on Windows — but
   the LLM call had actually succeeded; only *printing* the emoji reply crashed (`cp1252`). Reading
   the traceback carefully (not just the last line) is a real debugging skill.

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

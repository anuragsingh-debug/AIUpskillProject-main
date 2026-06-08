# Work Log — AI Upskilling Project

**Purpose:** a running, dated record of every meaningful step and action taken on this project, so it
can be summarised in the final report/presentation at project completion. Newest entries at the
bottom of each milestone. Commit hashes link each action to the git history.

> Companion docs: `docs/design-decisions.md` (why the architecture looks like it does) and
> `docs/challenges-and-strategies.md` (problems hit + how they were solved).

---

## Milestone 0 — Setup & tooling  (2026-05-31)

| Date | Commit | Action |
|---|---|---|
| 2026-05-31 | 69d1231 / 2df554d | Initial commit — AI Upskilling project structure scaffolded. |
| 2026-05-31 | 320b3cf | Merged remote `main`. |
| 2026-05-31 | ed5bd36 | Added sanitized `.env.example` template (Milestone 0). |
| 2026-05-31 | 415884f | Switched to using `.env` directly; removed the example template. |

**Outcome:** environment ready — LiteLLM model string + provider key in `.env`, `verify_setup.py`
confirms LLM access, Python `venv` created.

---

## Milestone 1 — Async News Fetcher  (2026-06-01)

| Date | Commit | Action |
|---|---|---|
| 2026-06-01 | 2c2cd43 | Built async news fetcher: HackerNews (API) + RSS support, `asyncio.gather` concurrency, semaphore rate limiting, `Article` model, markdown output. |

**Outcome:** working fetcher pulling from 2 live sources concurrently.

---

## Milestone 2 — SOLID Refactor + Design Patterns  (2026-06-03 → 2026-06-04)

Branch: `feature/milestone-2-solid`.

| Date | Commit | Action |
|---|---|---|
| 2026-06-03 | 86293fb | Applied SRP, OCP, LSP (+ partial DIP): extracted `ArticleTransformer` & `MarkdownStorage`, added `BaseFetcher` ABC, added GitHub Trending source with zero edits to existing code (OCP proof). |
| 2026-06-04 | f93b1e8 | Applied ISP + completed DIP: `ArticleStorage` interface, injected fetchers, `main.py` as composition root, mock-based orchestrator tests. |
| 2026-06-04 | 5bba0a3 | Added Factory + Strategy patterns (Evening 10): `FetcherFactory`, `RateLimitStrategy` (Semaphore / TokenBucket). |
| 2026-06-04 | c5e74cb | Added `docs/design-decisions.md` — SOLID + patterns rationale. |

**Outcome of the milestone work:** all 5 SOLID principles + 3 patterns (Factory, Strategy, Template
Method) applied; 3 live sources; two zero-/one-edit extension proofs (GitHub = OCP, JSON = DIP).

### Session 2026-06-04 — "finish M2 loose ends" + reports material

Detailed log of this working session:

1. **Resumed & assessed state.** Confirmed M2 fully committed, tree clean. Ran the suite via the
   project venv (`./venv/Scripts/python.exe -m pytest`) → **23 passing**. Ran `ruff` → clean.
2. **Reviewed the diff vs `main`** (24 files, +1077/-373) and ran coverage → **70%**. Found
   `src/storage/json_storage.py` at **0%** (new M2 file, untested) and `src/fetchers/interfaces.py`
   / `src/main.py` uncovered (abstract / entrypoint, expected).
3. **Closed the coverage gap.** Added `tests/test_json_storage.py` (4 tests: DIP `isinstance`
   contract, JSON round-trip, `.md`→`.json` filename coercion, multi-article). `json_storage.py`
   **0% → 100%**, total **70% → 77%**.
4. **Found a flaky test (open issue).** `tests/test_fetchers_integration.py::test_concurrent_fetching`
   asserts `elapsed < 10.0` against the **live** network; passes alone (~4s) but fails under coverage
   instrumentation. Documented with a fix plan (assert correctness, not wall-clock / mark as
   integration / mock). Not yet fixed.
5. **Wrote reports material.** Created `docs/challenges-and-strategies.md` — challenge→strategy→
   outcome for M0–M2, a single-slide table, speaker talking points, and a metrics appendix.
6. **Fixed a stale metric.** Updated `docs/design-decisions.md` test count 23 → 27.
7. **Committed & pushed** (commit `c0efb1a`). First attempt's message had stray `@` chars (PowerShell
   here-string ran in bash); amended to a clean message via `-F` file.
8. **Saved project memory** so future sessions know the venv test commands and milestone status.
9. **Created this work log.**

**State at end of session:** 27 tests (26 pass + 1 known-flaky deselected), ruff clean, 77% coverage,
branch pushed. **Remaining M2 loose end:** open the PR —
`https://github.com/anuragsingh-debug/AIUpskillProject-main/compare/main...feature/milestone-2-solid`
(`gh` CLI not installed).

---

## Milestone 3 — First Agent with Tools  (in progress, started 2026-06-04)

Branch: `feature/milestone-3-agent` (branched off the M2 tip so it has the SOLID code M3 builds on).

Planned (per `docs/milestones/milestone-3-first-agent.md`): LiteLLM smoke test, `BaseAgent`
(Template Method), `NewsFilterAgent` (relevance filtering via LLM), tool use (calculator + web
search), end-to-end fetch→filter pipeline, tests, PR.

### Evening 11, Step 1 — LiteLLM smoke test  (2026-06-04) ✅

Wrote a throwaway `scripts/test_llm.py` that calls `completion()` once to prove LiteLLM →
Gemini works end-to-end. Hit and fixed three issues:

1. **Wrong import** — `from litellm import LitelLM` (doesn't exist) → crashed with `ImportError`,
   and also left `completion` undefined. Fixed to `from litellm import completion`.
2. **Windows encoding crash** — the LLM call *succeeded*, but `print()` of the reply (which
   contained an emoji) crashed with `UnicodeEncodeError` because Windows terminals default to
   `cp1252`. Fixed by `sys.stdout.reconfigure(encoding="utf-8")`. **Takeaway:** the real agent
   code will need this too, since it prints LLM output constantly on Windows.
3. **Harmless noise** — litellm 1.55.0 emits `Pydantic serializer warnings`; cosmetic, ignored.

Result: prints `Hello! 👋` + `✅ LiteLLM working!`. LLM connection confirmed; the Gemini key is
valid. (`scripts/test_llm.py` is scratch, not a graded deliverable.)

### Evening 11, Step 2 — `BaseAgent` (Template Method)  (2026-06-04) ✅

Wrote `src/agents/base_agent.py`: an abstract base (`ABC`) where `execute()` owns the fixed
workflow (load → process → save) and subclasses implement the three `@abstractmethod` steps
(`_load_context`, `_process`, `_save_result`). A shared `_call_llm()` wraps `completion()` so no
agent re-writes LLM plumbing. Same Template Method idea as `BaseFetcher` from M2.

Verified with a throwaway `TestAgent` (in scratch `tests/test_base_agent.py`): ran
load → real LLM call → save end-to-end. Two gotchas hit:
- **Run command:** `python test_base_agent.py` fails (file is in `tests/`, and a directly-run
  script can't resolve `from src...`). Correct: `./venv/Scripts/python.exe -m tests.test_base_agent`
  from the root (the `-m` form puts the root on the import path).
- **Emoji crash again:** `base_agent.py` prints `🤖`/`✅`, so it needed the same
  `sys.stdout.reconfigure(encoding="utf-8")` fix — now baked into the base class, so every agent
  inherits safe printing.

Committed `base_agent.py` only; the scratch smoke scripts (`scripts/test_llm.py`,
`tests/test_base_agent.py`) are intentionally **not** committed — `test_base_agent.py` runs
`asyncio.run(...)` at import, which would trigger a live LLM call during pytest collection.

### Evening 12 — `NewsFilterAgent` (LLM relevance filtering)  (2026-06-05) ✅ (works; one open issue)

Wrote `src/agents/news_filter_agent.py` — the first concrete `BaseAgent`. It fills the three
Template-Method blanks: `_load_context` (parse `data/articles/all_articles.md` → article dicts),
`_process` (ask the LLM to judge each article and keep those scoring ≥ `relevance_threshold = 6`),
`_save_result` (write kept articles + score/reasoning/topics to `data/context/filtered_articles.md`).
The LLM is prompted to return **structured JSON** (`relevant`, `relevance_score`, `reasoning`,
`key_topics`), with fence-stripping (` ```json `) and a try/except fallback on parse failure.

Run via `./venv/Scripts/python.exe -m tests.test_filter_agent` (scratch test, untracked). Issues hit:

1. **UTF-8 on file read AND write (Windows cp1252 again).** `Path(input_path).read_text()` crashed
   with `UnicodeDecodeError: 'charmap' codec can't decode byte 0x8f` — the markdown has non-cp1252
   characters. Same root cause as the Evening 11 stdout fix, but on the **file** boundary this time.
   Fixed both sides: `read_text(encoding="utf-8")` and `open(output_path, "w", encoding="utf-8")`.
   **Takeaway:** on Windows, every file boundary needs explicit `encoding="utf-8"` — read *and* write.
2. **Rate limit silently corrupted the result *(open issue → next fix).*** Run reported "7/43
   relevant", but **32 of 43** articles got `score: 0` from the `except` fallback — all were Gemini
   **free-tier 429s** (`RESOURCE_EXHAUSTED`, quota = **10 requests/minute**; we fired 43 back-to-back).
   The code mislabels a *failed* call as "not relevant, score 0", so rate-limit errors masquerade as
   editorial rejections — only ~11 articles got a genuine judgment. **Decided next step:** reuse the
   M1/M2 rate limiter (`src/utils/rate_limiter.py` / `SemaphoreStrategy` + `TokenBucketStrategy` in
   `src/strategies/rate_limit_strategy.py`) to space calls under 10/min, and stop treating an error
   as a negative judgment (mark as `error`/skip, don't count as "not relevant").

**State at end of session:** agent runs end-to-end and writes filtered output; result is not yet
trustworthy until rate limiting + honest error handling land. `news_filter_agent.py` written
(not yet committed). _Next: add rate limiting (reuse M1/M2) + fix the silent-failure mislabel._

### Evening 13 — Tool use (calculator + web_search) wired into the agent  (2026-06-05) ✅

Built the agent's first **tools** and the function-calling loop:
- `src/tools/calculator.py` — exact math (`calculator()` + `CALCULATOR_SCHEMA`). Verified
  `23476 * 891 = 20917116` exactly (proves *why* a tool is needed — the LLM only predicts digits).
- `src/tools/web_search.py` — a **mock** search (`web_search()` + `WEB_SEARCH_SCHEMA`) returning fake
  results; the schema is real so swapping in a live API later is a 4-line change.
- `src/agents/base_agent.py` — added the **tool-call loop** `_call_llm_with_tools()` +
  `register_tool_function()` + a `tools=` constructor arg. The loop sends tool schemas, runs any
  requested tool locally, feeds the result back as a `role:"tool"` message, and repeats (cap 10
  rounds) until the model returns plain text.
- `src/agents/enhanced_filter_agent.py` — `EnhancedFilterAgent(NewsFilterAgent)` registers both
  tools and judges via `_call_llm_with_tools`.

Proven twice: a focused single-question demo (LLM **chose** to call `calculator` on `23476*891`),
and the enhanced agent on a 3-article sample where the LLM **autonomously called `web_search`** to
verify a "40% cost reduction" claim mid-judgment. **4 copy-paste bugs found & fixed** along the way
(see C&S E8): missing `import json`/`Dict`; an `if __name__` block indented *inside* the test
function (ran nothing); a wrong input path; and — most instructive — the **middle class
`NewsFilterAgent.__init__` didn't forward the new `tools=` arg** up to `BaseAgent` (`TypeError`),
a multi-level-inheritance lesson.

### Evening 14 — Tests + end-to-end pipeline  (2026-06-05) ✅ (code done; full live run quota-blocked)

1. **pytest hygiene.** Plain `pytest` was breaking at *collection* because it auto-discovers every
   `test_*.py`, including the untracked scratch smoke scripts (`scripts/test_llm.py` has the
   intentionally-broken `LitelLM` import). Added **`pytest.ini`** (`testpaths = tests` + `--ignore`
   the 4 live-LLM smoke files) so `pytest` "just works" → **27 passing**, no flags.
2. **Mocked agent tests** — `tests/test_news_filter_agent.py` (6 tests, fully offline). Patches
   `_call_llm` with a deterministic fake (keyed on `"GPT-5"`, unique to the test article — an earlier
   `"JavaScript"` key matched the prompt's few-shot *example* and broke the test, a real lesson in
   "know what's in the prompt before mocking on it"). Covers: tools, markdown parsing, full
   keep-AI/bin-non-AI flow, and graceful degradation when the LLM **raises** (guards E6/E7).
3. **Pipeline** — `src/pipeline.py` (fetch → filter). Fixed the tutorial's `FetchOrchestrator()`
   bug (real one needs injected `fetchers, transformer, storage` — built the composition root like
   `orchestrator.main()`). Kept the fetch small (HackerNews `limit=5`) to stay under the LLM quota.
   Integration **ran end-to-end** (fetched 5 → filtered → saved 1/5).
4. **New quota discovery (updates E6).** The full run revealed a **second, DAILY** cap:
   `GenerateRequestsPerDayPerProjectPerModel-FreeTier, limit: 20`. We'd exhausted today's 20 across
   all runs, so articles 2–5 failed instantly. A rate limiter fixes the *per-minute* (10) cap but
   **cannot** beat the *per-day* (20) cap — that needs waiting for reset or a paid tier/other model.

**State at end of session:** E13 + E14 code complete and committed-worthy (`tools/`,
`enhanced_filter_agent.py`, `pipeline.py`, `pytest.ini`, `tests/test_news_filter_agent.py`).
27 + 6 tests pass offline. Full *live* filter run is blocked only by the daily free quota (resets
~midnight PT), not by any code issue — a vindication of mocked tests (dev never stalls on quota).
_Next: rate-limiter fix (per-minute) + honest error handling (E7); then E15 polish + PR._

---

## Session — 2026-06-08 (M3 wrap-up: E6 + E7 + E9 fixed, PR-ready)

Goal: close the three open M3 quality issues, lock them in with offline tests, and get M3 ready to
merge before starting M4.

1. **E7 — honest error handling (`news_filter_agent.py`).** The `except` in `_judge_relevance` used
   to return `relevance_score: 0` for *any* failure — indistinguishable from a real "not AI" verdict,
   so 32/43 rate-limited articles had been silently binned. Now it returns `status: "judged"` on a
   real answer, or `status: "error"` (`error_type` = `rate_limit`/`error`, `relevance_score: None`)
   on failure. `_process` routes errors into a separate `errored` bucket (never a verdict);
   `_save_result` reports `Could Not Judge: N`, a filter rate computed over judged-only, and lists the
   un-judged articles for a re-run.
2. **E6 — per-minute throttle (`base_agent.py`).** Added `_throttle()` (min-interval via
   `time.monotonic()`/`time.sleep()`), `requests_per_minute=8` default (≈7.5s gap). Applied in both
   `_call_llm` and `_call_llm_with_tools`. A serial loop has no concurrency, so a rate (not semaphore)
   guard is the correct fit.
3. **E9 — daily-cap handling.** New `DailyQuotaExceeded` exception raised when a 429 names the per-day
   quota (`_is_daily_quota_error`); `_process` catches it, **stops the run**, and marks the current +
   all remaining articles `daily_quota` (fail-fast, honest). Added an optional `max_calls_per_run`
   budget so a run can self-limit under the ~20/day cap.
4. **Inheritance fix (E8 redux).** `NewsFilterAgent` and `EnhancedFilterAgent` now forward `**kwargs`
   up to `BaseAgent`, so the new options pass through the 3-level chain. Also fixed
   `EnhancedFilterAgent._judge_relevance`, which still returned the old `score: 0` shape with **no
   `status`** — it would have `KeyError`'d the inherited `_process`.
5. **Tests restored + extended.** The working-tree `test_news_filter_agent.py` had been replaced with
   2 *live* tests; restored the mocked suite and added coverage for throttle, error-bucketing, daily
   quota fail-fast, the per-run budget, and the quota classifier. **40 tests pass, fully offline.**
6. **Housekeeping.** Cleaned a stray unused `List` import in `web_search.py`; added `ruff.toml` to
   exclude the scratch smoke scripts from lint (mirroring `pytest.ini`). `ruff check src tests` clean.

**State at end of session:** E6/E7/E9 all DONE and covered by mocked tests. `src/mcp/` (early M4)
left untracked and out of this commit. M3 committed + pushed; PR opened via compare URL (no `gh`).
_Next: Milestone 4 (MCP-Powered Pipeline) on `feature/milestone-4-mcp` off the M3 tip._

---

*Living document — update at the end of each working session so the final report has a complete
trail.*

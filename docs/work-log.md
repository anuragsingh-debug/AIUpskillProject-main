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

## Milestone 3 — First Agent with Tools  (not started)

Planned (per `docs/milestones/milestone-3-first-agent.md`): LiteLLM smoke test, `BaseAgent`
(Template Method), `NewsFilterAgent` (relevance filtering via LLM), tool use (calculator + web
search), end-to-end fetch→filter pipeline, tests, PR.

_Append actions here as M3 proceeds._

---

*Living document — update at the end of each working session so the final report has a complete
trail.*

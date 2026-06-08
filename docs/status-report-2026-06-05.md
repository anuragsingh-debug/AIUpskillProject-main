# 📊 AI Upskilling Project — Status Update

**Prepared for:** Project Coordinator
**Date:** 5 June 2026
**Engineer:** Anurag Kumar Singh
**Project:** AI News Pipeline (milestone-based upskilling)

---

## 🎯 One-line status

> **On track.** Milestones 0–2 complete and tested; Milestone 3 (first AI agent) in progress and
> running end-to-end. No blockers — one known issue identified with a fix already planned.

---

## ✅ Progress by milestone

| Milestone | Theme | Status | Evidence |
|---|---|---|---|
| **M0** | Setup & tooling | ✅ Done | LLM access verified, `.env` + venv ready |
| **M1** | Async news fetcher | ✅ Done | 3 live sources, concurrent fetching |
| **M2** | SOLID refactor + design patterns | ✅ Done | **27 tests passing, 77% coverage, lint clean** |
| **M3** | First AI agent (LLM filtering) | 🔄 In progress | Agent runs end-to-end; 1 known issue being fixed |
| M4 | MCP pipeline | ⬜ Not started | — |
| M5 | Evaluation | ⬜ Not started | — |

**What's built and working today:** a pipeline that pulls AI news from **HackerNews + RSS + GitHub
Trending** concurrently, normalises them into one clean data model, and (M3) uses an **LLM to judge
each article's AI-relevance** and filter automatically.

---

## 🧗 ALL challenges faced & how we solved them (every milestone)

> Complete list — every challenge encountered, the strategy used, and the outcome.

### Milestone 0 — Setup & tooling
| # | Challenge | Strategy / Solution |
|---|---|---|
| 1 | **Provider lock-in & secret handling** — don't hard-code one LLM vendor or leak API keys | LiteLLM model-string + secrets in `.env` + a `verify_setup.py` that confirms LLM access before any real work |

### Milestone 1 — Async news fetcher
| # | Challenge | Strategy / Solution |
|---|---|---|
| A1 | **Sequential API calls were too slow** (HackerNews needs ~30 separate calls) | Fire all requests concurrently with `asyncio.gather` — fetch time drops from "sum of all calls" to "slowest single call" |
| A2 | **Bursting 30+ requests risks being rate-limited / blocked** | Semaphore caps concurrency at 10 ("ATM guard — only N at a time"); tunable per source |
| A3 | **Each source speaks a different format** (HackerNews = JSON, RSS = feed, GitHub = no public API) | One transformer per shape + BeautifulSoup scrape for GitHub; all converge on one `Article` model |
| A4 | **One bad call could crash the whole fetch** (a story errors or returns null) | Per-story `try/except` returning `None`, then filter the `None`s out — graceful degradation |

### Milestone 2 — SOLID refactor + design patterns
| # | Challenge | Strategy / Solution |
|---|---|---|
| B1 | **"God-class" fetchers did 3 jobs** (fetch + transform + save) | Split responsibilities → `ArticleTransformer` + `MarkdownStorage`; fetchers only fetch (SRP) |
| B2 | **Adding a new source meant editing working code** (regression risk) | `BaseFetcher` ABC contract; proved by **adding GitHub Trending = 1 new file + 1 line, 0 edits** (OCP) |
| B3 | **Tests needed the live network — slow & flaky** | `ArticleStorage` interface + dependency injection + mocks; bonus: swapping in `JSONStorage` was a **1-line** change (DIP) |
| C1 | **Copied tutorial code carried real bugs** | `ruff` + `pytest` caught missing `List`/`Article` imports, an unreachable RSS branch, and a Strategy class missing `async with` |
| C2 | **A mock test mocked the wrong method** (awaiting a plain `Mock` raised `TypeError`) | Mock the **real call path** with `AsyncMock` for the methods actually invoked |
| C3 | **A "simplifying" refactor would silently kill concurrency** | Behaviour-guarding tests flagged the regression before it shipped |
| D1 | **`datetime` is not JSON-serializable** (`JSONStorage` crashed) | `json.dump(..., default=str)` to stringify non-JSON-native types |
| D2 | **Flaky timing-based integration test** *(open issue)* — asserts wall-clock vs the live network | Plan: assert *correctness* not wall-clock, or mark as `@integration` and exclude from default run |
| D3 | **Windows / tooling friction** — base Python lacked `pytest`, `gh` CLI not installed, paths have spaces | Run everything through the project `venv` (`./venv/Scripts/python.exe -m ...`); create PRs via GitHub compare URL |

### Milestone 3 — First AI agent *(in progress)*
| # | Challenge | Strategy / Solution |
|---|---|---|
| E1 | **Connect to an LLM without locking into one provider** | LiteLLM's single `completion()` call; model read from `.env` — switching providers = editing one line |
| E2 | **Windows console crashed on emoji in LLM replies** (`UnicodeEncodeError`, cp1252) — the call *succeeded*, only printing failed | `sys.stdout.reconfigure(encoding="utf-8")`, baked into `BaseAgent` so every agent inherits safe printing |
| E3 | **Copied tutorial code had a wrong import** (`from litellm import LitelLM` doesn't exist) | Ran it → immediate `ImportError`; fixed to `from litellm import completion` |
| E4 | **Running a script directly vs as a module** (`from src...` → `ModuleNotFoundError`) | Run from project root as a module: `./venv/Scripts/python.exe -m tests.test_...` |
| E5 | **A scratch test that runs at import would poison the suite** (live LLM call during pytest collection) | Keep smoke scripts untracked; write proper *mocked* tests later (Evening 14) |
| E6 | **Free-tier rate limit silently corrupted output** — 10 req/min cap; 43 in a row → 32 articles got `score:0` from the error fallback, mislabelled as "not relevant" *(open, fix in progress)* | Reuse the **M1/M2 rate-limiter** (`rate_limiter.py` / `SemaphoreStrategy`) to throttle calls under the limit |
| E7 | **A swallowed error was indistinguishable from a real "no"** — a failed call returned the same shape as a genuine rejection | Mark errored articles as `error`/skip and exclude from the tally — never let an outage inflate "rejected" *(planned with E6)* |
| E8 | **UTF-8 needed on the file boundary too** (`read_text()`/`open()` crashed on cp1252 with real-world text) | Add explicit `encoding="utf-8"` to **both** the file read and write — same root cause as E2, new location |

**Pattern reused in M3:** the **Template Method** pattern from M2's `BaseFetcher` carried straight
over to `BaseAgent` — the base owns the workflow (load → process → save), agents fill the steps.
Clean architecture from M2 paid off immediately.

---

## ⚠️ Current known issue (being addressed — full transparency)

While running the new filter agent, I found the **free-tier LLM allows only 10 requests/minute**.
Firing 43 articles in a row caused 32 of them to silently fail and get mislabelled as "not relevant."

- **Impact:** the filtered output isn't trustworthy *yet*.
- **Root cause identified:** rate-limit errors were being treated the same as a genuine "no."
- **Fix already decided (in progress):** reuse the **rate-limiter we built back in M1/M2** to stay
  under the limit, and count failed calls honestly instead of as rejections.
- **No external blocker** — this is ours to fix and the path is clear.

*(Logged in `docs/challenges-and-strategies.md` as items E6/E7 — we document open issues rather than
hide them.)*

---

## 🔜 Next steps

1. Add rate-limiting to the agent + honest error handling (this week).
2. Tool use for the agent (calculator + web search).
3. End-to-end fetch → filter pipeline + tests, then raise the M3 PR.

---

**Summary for leadership:** *Solid, steady progress — 3 of 6 milestones fully delivered with a
tested, well-architected codebase; the 4th is running and one known issue is already being resolved.
No blockers, nothing waiting on anyone else.*

---

*Companion docs (deeper detail): `docs/work-log.md` (dated step-by-step trail),
`docs/challenges-and-strategies.md` (challenge → strategy → outcome), `docs/design-decisions.md`
(architecture rationale).*

# Final Project Report — AI News Pipeline

**Program:** AI Agent Onboarding / Upskilling (5 weeks, 6 milestones)
**Author:** Anurag Kumar Singh
**Date:** 2026-06-09
**Repository:** `anuragsingh-debug/AIUpskillProject-main`

> Companion docs: [`work-log.md`](work-log.md) (dated trail of every step),
> [`design-decisions.md`](design-decisions.md) (SOLID + patterns rationale),
> [`challenges-and-strategies.md`](challenges-and-strategies.md) (problem → strategy → outcome),
> [`architecture.md`](architecture.md) (as-built), [`deployment.md`](deployment.md) (run/deploy).

---

## 1. Executive summary

This project builds a **production-style, multi-agent AI system** that fetches technology news from
multiple live sources, uses an LLM agent to filter for AI/ML relevance, summarizes the survivors by
topic, and writes a polished newsletter — with a **Model Context Protocol (MCP)** database server in
the middle and an **evaluation framework** measuring the filter's quality against a hand-labeled
golden dataset.

It was built incrementally across six milestones, each on its own feature branch, with the
discipline of **tests as guardrails** and an honest, dated work-log throughout.

**Headline outcomes**
- **End-to-end pipeline working:** Fetch → Database (MCP) → Filter → Summarize → Write → Evaluate.
- **3 live sources** (HackerNews API, RSS, GitHub Trending scrape) converging on one `Article` model.
- **4 AI agents** on a shared `BaseAgent` (Template Method): filter, enhanced-filter (tool-using),
  summarizer, writer.
- **MCP database server** exposing 3 tools (query / search / get_sources) over SQLite.
- **40+ tests, fully mocked/offline**, `ruff` clean; core logic deterministic and quota-independent.
- **Filter quality:** baseline **90% accuracy / F1 0.923** (10 cases) → **100% / F1 1.000** (20
  cases) after a disciplined, anti-overfitting prompt-tuning pass.
- **Two "zero-edit" extension proofs** validate the architecture: a new source (OCP) and a new
  storage backend (DIP), each added without touching existing code.
- A **browser-based simulation UI** (`demo/`) replays the whole pipeline for demos — no LLM calls.

---

## 2. The system at a glance

```
   News sources                MCP layer            AI agents (LiteLLM)         Output
 ┌──────────────┐          ┌──────────────┐     ┌───────────────────┐
 │ HackerNews   │          │  Database    │     │ NewsFilterAgent    │
 │ RSS feeds    │  fetch   │  MCP server  │     │ SummarizerAgent    │   📄 newsletter.md
 │ GitHub Trend │ ───────► │  (SQLite,    │ ──► │ WriterAgent        │ ► 📊 evaluation_report.md
 └──────────────┘          │   3 tools)   │     │ (+ SearchSkill,    │
                           └──────────────┘     │   tools)           │
                                                └───────────────────┘
        Fetch  ──►  Database  ──►  Filter  ──►  Summarize  ──►  Write  ──►  Evaluate
```

**Stack:** Python 3.11+ · `asyncio` / `aiohttp` · **LiteLLM** (provider-agnostic LLM access,
currently `gemini/gemini-2.5-flash-lite`) · **MCP** (`mcp` + `aiosqlite`) · **SQLite** · `pytest` ·
`ruff`.

---

## 3. The milestone journey

| Milestone | Theme | What was delivered |
|---|---|---|
| **M0** | Setup & tooling | `.env` + LiteLLM model string + `verify_setup.py`; venv; provider-agnostic from day one. |
| **M1** | Async fetcher | Concurrent fetch (HackerNews + RSS) via `asyncio.gather` + semaphore rate limiting; `Article` model; markdown output. |
| **M2** | SOLID + patterns | Full SRP/OCP/LSP/ISP/DIP refactor; Template Method, Factory, Strategy; GitHub source added (OCP proof), JSON storage added (DIP proof). |
| **M3** | First AI agent | `BaseAgent` (Template Method) + `NewsFilterAgent` (LLM relevance scoring); tool use (calculator + web_search) with an autonomous tool-call loop; rate-limit, daily-quota, and honest-error handling. |
| **M4** | MCP + multi-agent | MCP database server (3 tools) + `SearchSkill`; Summarizer → Writer agents; `complete_pipeline.py` (Fetch→DB→Filter→Summarize→Write) with retry + per-item resilience. |
| **M5** | Evaluation + docs | `FilterEvaluator` + golden dataset; README/architecture/deployment docs; prompt-tuning pass (90%→100%); this report + a demo UI. |

A dated, commit-linked account of every working session lives in [`work-log.md`](work-log.md).

---

## 4. Architecture & key design decisions

The architecture is the M2 SOLID groundwork paying compound interest in every later milestone.

- **Template Method everywhere.** `BaseFetcher.fetch_and_save` (M2) and `BaseAgent.execute`
  (load → process → save, M3) both fix the workflow once and let subclasses fill the varying steps.
  Adding the summarizer and writer agents in M4 was "fill in three methods," not "design a new class."
- **Open/Closed, proven.** Adding **GitHub Trending** (a scraped source, no public API) was **1 new
  file + 1 registration line, zero edits** to existing fetchers/transformer/storage.
- **Dependency Inversion, proven.** Swapping `MarkdownStorage` → `JSONStorage` was a **one-line**
  change in the composition root (`main.py`), with the orchestrator untouched. The same DI makes the
  orchestrator testable with mock fetchers — no live network in tests.
- **Provider-agnostic LLM access.** Every model call goes through LiteLLM's single `completion()`;
  the model is one env var (`LITELLM_MODEL`). Switching Gemini ↔ Claude ↔ OpenAI is an `.env` edit,
  not a code change.
- **MCP as a clean tool boundary.** The database is exposed as an MCP server (stdio transport, JSON-RPC
  on stdout, diagnostics on stderr), with `SearchSkill` as a reusable high-level wrapper — so an agent
  asks for "search articles" without knowing SQLite exists.

Full rationale, trade-offs (e.g. SRP deliberately bent for the GitHub fetcher to preserve the
zero-edit OCP proof) and a before/after metrics table are in [`design-decisions.md`](design-decisions.md).

---

## 5. Challenges & how they were solved (highlights)

The full catalogue (A1–E10, each *challenge → why it mattered → strategy → outcome*) is in
[`challenges-and-strategies.md`](challenges-and-strategies.md). The most instructive:

- **A traceback that lied (E2).** The first agent run "crashed" on Windows — but the LLM call had
  *succeeded*; only `print()` of the emoji reply threw `UnicodeEncodeError` (cp1252). Fix:
  `sys.stdout.reconfigure(encoding="utf-8")` baked into `BaseAgent`. **Lesson: distinguish "the LLM
  failed" from "printing the result failed."**
- **A silent data-corruption bug (E6/E7).** A full filter run reported "7/43 relevant" and *looked*
  fine — but 32/43 were free-tier **429s** that the `except` mislabeled as "not relevant, score 0."
  Rate-limit failures masqueraded as editorial rejections. Fix: a per-minute `_throttle()` (min-interval
  guard) **before** the wall, plus honest error handling — failed calls return `status:"error"` and go
  to a separate bucket, never a fake score 0. **Lesson: a filter is only as trustworthy as the calls
  behind it; an error is not a verdict.**
- **Two stacked quotas (E9).** After fixing the per-minute (10/min) cap, runs *still* failed on a
  **per-day** (~20/day) cap. A rate limiter can't beat a daily cap. Fix: a distinct `DailyQuotaExceeded`
  that **stops the run** and marks the rest un-judged (fail-fast, honest), plus an optional
  `max_calls_per_run` budget. **Lesson: read *which* quota the 429 names — throttle the per-minute,
  stop for the per-day.**
- **Never trust copied code (C1/E3/E8).** Tutorial snippets carried real bugs — a non-existent
  `LitelLM` import, missing imports, and a middle inheritance class that didn't forward a new `tools=`
  arg (`TypeError`). `ruff` + `pytest` + "run it early" caught them all.

---

## 6. Evaluation — the Milestone-5 centerpiece

**Goal:** measure the filter agent's quality objectively, not by vibes.

**Method.** `FilterEvaluator` runs `NewsFilterAgent` over a hand-labeled `golden_dataset.json` and
reports **accuracy / precision / recall / F1** with per-case PASS/FAIL. It's resilient: it stops
cleanly on `DailyQuotaExceeded` and still writes a (clearly-flagged) partial report.

**Baseline (10 cases).** Accuracy **90% (9/10)**, precision 85.7%, recall 100%, **F1 0.923**. The one
miss was a **false positive**: *Docker 25 Released* judged AI-relevant at exactly the threshold (score
6), reasoning "Docker is used to deploy AI." Root cause: the prompt said what *is* relevant but never
what is *not*, so infrastructure "used with AI" was over-included.

**The honest fix (anti-overfitting).** The cheap path — hard-coding "Docker → not relevant" — would be
*teaching to the test*. Instead:
1. The prompt gained a **general decision rule** ("the article must be *about* AI/ML, not merely
   infrastructure/tooling AI is built with") + a scoring guide + **neutral examples not drawn from the
   golden set**.
2. The golden set was **expanded 10 → 20**, adding 5 clear AI cases and **5 held-out "used-with-AI"
   traps** (Kubernetes, gaming GPU, AWS S3, Rust, Kafka) to test *generalisation*.

**Result (verified, Gemini, 20 cases).** Accuracy **100%**, precision **100%**, recall **100%**, **F1
1.000**. Docker flipped to *Not Relevant, score 2*; **all 5 unseen traps were correctly rejected** —
proof the rule generalised rather than memorised. Scores also became better calibrated (Docker 6→2,
PostgreSQL 5→2).

| Metric | Before (10, old prompt) | After (20, new prompt) |
|---|---|---|
| Accuracy | 90.0% | **100%** |
| Precision | 85.7% | **100%** |
| Recall | 100% | **100%** |
| F1 | 0.923 | **1.000** |

> **Honest framing:** 100% is over 20 cases, and Gemini has slight run-to-run variance. The defensible
> claim is *"the over-inclusion failure mode was fixed by a general rule that held across 10 unseen
> trap cases on a larger, harder test set"* — not "perfect forever." See §9.

---

## 7. Testing & quality

- **40+ tests, fully mocked/offline.** Agent tests patch `_call_llm` with a deterministic fake, so the
  suite never fires a live LLM call — development continues even when the daily quota is exhausted.
- **Design proven, not claimed.** Dedicated tests back LSP (substitutability), DIP (mock-injected
  orchestrator), and the throttle / error-bucket / daily-quota behaviour (E6/E7/E9).
- **Lint:** `ruff` clean across `src/` and `tests/`.
- **Coverage:** ~77% overall; new storage backends and patterns at 90–100%.

```bash
./venv/Scripts/python.exe -m pytest -q                 # tests
./venv/Scripts/python.exe -m pytest --cov=src -q       # coverage
./venv/Scripts/python.exe -m ruff check src tests      # lint
```

---

## 8. The demo UI (`demo/`)

A self-contained **HTML/CSS/JS** simulation (open `demo/index.html` — no server, no install) that
replays the full pipeline: click **Start** to watch all six stages run with live progress, per-article
relevance judging (KEEP/BIN with scores + reasoning), topic summaries, a **paginated, downloadable
newsletter** (.md / .html / print-to-PDF), and the **evaluation metrics** with the 90%→100% before/after.

It makes **no LLM calls, uses no quota, imports nothing from `src/`**, and uses real data extracted
from the project's own outputs. A "Replay of verified run" badge marks that aggregate metrics are real
while a few per-case scores are illustrative.

---

## 9. Honest caveats & limitations

Surfacing these is a deliberate choice — honesty over a green-but-misleading dashboard.

- **The committed `evaluation_report.md` currently shows the 90% baseline.** The verified 100% run's
  report file was overwritten by a follow-up run that hit the exhausted daily quota; regenerating it
  (and bumping the numbers in README/architecture) is a ~5-minute follow-up pending the **midnight-PT
  daily-quota reset**. The 100% result is verified and recorded in the work-log + demo meanwhile.
- **Free-tier quota (E9).** Gemini's free tier caps full live runs (~20/day); this is a cost/tier
  limit, not a code limit. Per a senior's direction, multi-API-key rotation to dodge the quota was
  **explicitly not used** (it was prototyped and fully reverted).
- **Flaky timing test (D2).** `tests/test_fetchers_integration.py::test_concurrent_fetching` asserts a
  wall-clock bound against the live network; it passes alone but fails in-suite. Deselect it →
  **39 passed / 1 skipped**. Fix plan: assert correctness, not wall-clock (documented, not hidden).
- **Evaluation scale.** 20 golden cases is small; a larger, periodically-refreshed set would make the
  metric even more robust.

---

## 10. Skills demonstrated

- **Async Python** — `asyncio.gather` concurrency, semaphore/token-bucket rate limiting.
- **Clean architecture** — all 5 SOLID principles + Template Method / Factory / Strategy, with
  executable proofs (zero-edit OCP & DIP extensions).
- **AI engineering** — provider-agnostic LLM integration, prompt engineering (with a real
  anti-overfitting discipline), tool use / function-calling, multi-agent orchestration.
- **MCP** — building a working MCP server (3 tools) + a reusable skill over it.
- **Evaluation** — golden datasets, precision/recall/F1, and the maturity to distinguish a *real* gain
  from a memorised one.
- **Production discipline** — mocked/offline tests, lint, resilient error/quota handling, dated
  documentation, and front-end demoing.

---

## 11. Future work

1. **Finalize the eval refresh** (regenerate the 20-case report → 100%, sync README/architecture) once
   quota resets.
2. **More sources** (arXiv, Reddit, Twitter) — trivial under OCP (1 file each).
3. **Bigger / refreshed golden set** + a periodic re-evaluation to catch drift.
4. **Fix the D2 timing test** (assert correctness, not wall-clock).
5. **A live (non-simulated) web UI** backed by the real pipeline, behind a small FastAPI server.
6. **Caching** of LLM judgments to make full runs quota-cheap and repeatable.

---

## 12. Conclusion

The project delivers a complete, tested, multi-agent AI pipeline that fetches, filters, summarizes,
writes, and **measures itself** — built on a clean architecture whose extensibility is proven, not
asserted. The evaluation work is the standout: a real failure mode was diagnosed and fixed with a
*general* rule that demonstrably generalises, taking the filter from 90% to a verified 100% F1 1.000
on a larger, harder test set — while staying honest about what that number does and doesn't claim.

Most importantly, the recurring lessons — *trust nothing you copied, an error is not a verdict, read
which wall you hit, and document your open issues* — are the habits of a production AI engineer, not
just a tutorial-follower.

---

*Generated as the Milestone-5 capstone deliverable. See the companion docs for full detail.*

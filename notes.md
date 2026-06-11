# AI News Pipeline — Topic Notes (Milestone + Evening wise)

> Complete topic checklist, in order (E1 → E26), pulled from `docs/work-log.md` and
> `docs/m1-m2-evenings-table.md`. Everything below is what you should be able to explain
> before showing this project to your senior.

---

## 🟤 Milestone 0 — Setup (2026-05-31)

| # | Topic | What you must be able to say |
|---|-------|------------------------------|
| 0 | Environment & tooling | Python `venv`, `.env` for secrets, LiteLLM model string + provider key, `verify_setup.py` confirms LLM access |

---

## 🔵 Milestone 1 — Async News Fetcher (E1–E5)

| Evening | Topic | One-line you must know |
|---|-------|------------------------|
| **E1** | First API fetch | HackerNews gives **story IDs first**, then 1 call per story (~30 calls) — basic working fetch |
| **E2** | **Async concurrency** | `async/await` + `asyncio.gather` → all requests fire at once; time = slowest call, not the sum |
| **E3** | **Rate limiting (semaphore)** | A semaphore caps how many requests run at once (max 10) so you don't get banned/throttled |
| **E4** | Multiple sources + model | Added RSS; **one translator per source**, all output the same `Article` model (dataclass) |
| **E5** | Resilience | `try/except` per call, drop the `None`s → one bad call doesn't crash the whole fetch |

**M1 outcome:** working fetcher pulling from live sources **concurrently and safely**.

---

## 🟡 Milestone 2 — SOLID + Design Patterns (E6–E10)

| Evening | Topic | One-line you must know |
|---|-------|------------------------|
| **E6** | **SRP** (Single Responsibility) | Split the do-everything fetcher → `ArticleTransformer` (clean) + `MarkdownStorage` (save) |
| **E7** | **OCP** (Open/Closed) + Template Method | `BaseFetcher` ABC; proof = added GitHub Trending in **1 new file, 0 edits** |
| **E8** | **DIP + ISP** (Dependency Inversion / Interface Segregation) | `ArticleStorage` interface, **dependency injection**, mocks for offline tests, `main.py` = composition root; JSON swap in 1 line |
| **E9** | Quality gate | `ruff` (lint) + `pytest` caught real bugs in copied tutorial code (missing imports, broken async) |
| **E10** | **Factory + Strategy patterns** | `FetcherFactory` creates the right fetcher; `RateLimitStrategy` (Semaphore / TokenBucket) is pluggable |

**M2 outcome:** all 5 SOLID principles + 3 patterns; 3 live sources; two zero-/one-edit extension proofs.

---

## 🟣 Milestone 3 — First Agent with Tools (E11–E14 + wrap-up)

| Evening | Topic | One-line you must know |
|---|-------|------------------------|
| **E11** | LLM smoke test + `BaseAgent` | LiteLLM→Gemini works; `BaseAgent` Template Method (`execute` = load→process→save, subclasses fill `@abstractmethod`s); UTF-8 stdout on Windows |
| **E12** | **LLM relevance filtering** | `NewsFilterAgent` asks LLM to score each article, keeps ≥ threshold; **structured JSON output** + fence-stripping; UTF-8 on file read/write; discovered 429 rate-limit (10 req/min) |
| **E13** | **Tool use / function-calling** | `calculator` (exact math) + `web_search` (mock) tools; the **tool-call loop** (send schema → run tool → feed result back); multi-level inheritance lesson (`**kwargs` forwarding) |
| **E14** | Tests + pipeline | `pytest.ini`, **mocked agent tests** (offline), `pipeline.py` fetch→filter end-to-end; discovered **daily quota cap (20/day)** |
| **wrap-up** | Honest errors + throttling | `status: judged/error` (don't bin rate-limit failures as "not relevant"); per-minute throttle (`requests_per_minute`); `DailyQuotaExceeded` fail-fast; `max_calls_per_run` budget |

---

## 🟠 Milestone 4 — MCP + Multi-Agent Pipeline (E15+)

| Step | Topic | One-line you must know |
|---|-------|------------------------|
| **E15** | **MCP basics** | Hello-world MCP server + stdio client; **JSON-RPC over stdout**, so diagnostics go to **stderr** |
| | Async SQLite | `DatabaseManager` with `aiosqlite`; `populate_db` loads markdown → SQLite |
| | **Database MCP server** | 3 tools exposed; fixed `Tool(inputSchema=)` field; launch via `sys.executable -m` so imports resolve |
| | Reusable skill | `SearchSkill` wraps the MCP `search_articles` tool |
| | **Multi-agent chain** | `SummarizerAgent` → `WriterAgent`; `complete_pipeline.py` (fetch→db→filter→summarize→write); 5xx retry + per-topic try/except so one failure doesn't discard finished summaries |

**M4 outcome:** MCP database server (3 tools), reusable skill, and the full Filter→Summarize→Write pipeline working.

---

## 🔴 Milestone 5 — Evaluation + Docs (E24, E26)

| Evening | Topic | One-line you must know |
|---|-------|------------------------|
| | **Evaluation metrics** | `FilterEvaluator` vs hand-labeled `golden_dataset.json`; **accuracy / precision / recall / F1**, per-case PASS/FAIL; resilient partial report |
| | First results | **90% accuracy, precision 85.7%, recall 100%, F1 0.923** — 1 false positive (Docker), no relevant article dropped |
| **E24** | Documentation | Accurate `README`, `docs/architecture.md` (as-built), `docs/deployment.md` |
| **E26** | **Prompt tuning + generalization** | Fixed the **over-inclusion trap** with a general decision rule ("article must be ABOUT AI, not infra AI is built with"); avoided **overfitting** by expanding golden set 10→20 with **5 held-out trap cases** → 100%/F1 1.000 that *generalises* |

---

## 🎯 The "must-defend" headline concepts (if senior asks "what did you actually learn?")

1. **Async concurrency** — `asyncio.gather` vs sequential
2. **All 5 SOLID principles** + Factory / Strategy / Template Method patterns
3. **Dependency injection + mocking** → tests run offline
4. **LLM agents** — Template Method base, structured JSON output, **function-calling/tool use**
5. **Rate limits** — per-minute vs per-day, honest error handling (don't mask failures as verdicts)
6. **MCP** — server/client, JSON-RPC stdout discipline
7. **Multi-agent pipeline** — filter → summarize → write
8. **Evaluation** — precision/recall/F1, and **overfitting vs generalization** (the E26 story is the strongest "I understand ML rigor" point)

---

## 📌 Quick wins to say out loud

- **M1:** Async made it fast; the rate-limit guard made it safe.
- **M2:** We optimised for change — a whole new data source took **1 file and 0 edits**.
- **M3:** The agent *chose* to call a tool (calculator / web_search) on its own — real function-calling.
- **M4:** MCP let the agent talk to a database through standard tools.
- **M5:** Fixed a real failure mode with a **general rule**, proven on **10 unseen traps** — not by memorising the test.

---

## 🗂️ Companion diagrams (in `docs/diagrams/`)

- `project-tree-branches.png` — branching file tree **with concept per file**
- `project-tree.png` — top-down file tree
- `system-design.png` — architecture / data-flow

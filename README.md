# AI Upskill Project

**Blend's AI engineering onboarding curriculum.** A 5-week self-paced project
that takes engineers from async Python through agents, MCP, and evaluation
by building a small AI-powered news pipeline end-to-end.

- **Time commitment:** 1–2 hours per evening, ~5 weeks (38–54 hours total)
- **Format:** Self-paced. Each milestone ends with a PR checkpoint reviewed by two peers.
- **Outcome:** A working multi-agent news pipeline with tests, evaluation, and docs.

---

## Where to start

1. Read [`docs/architecture/overview.md`](docs/architecture/overview.md) for the 20-min big-picture orientation.
2. Open [`docs/milestones/milestone-0-setup.md`](docs/milestones/milestone-0-setup.md) and follow it. It will get you to a working dev environment in one evening.
3. From there, milestones link to the next one in sequence.

---

## The 5-week arc

| Week | Milestone | What you build | Hours |
|------|-----------|----------------|-------|
| 0 (Evening 1) | [M0 — Setup](docs/milestones/milestone-0-setup.md) | Dev environment, API key, verify script passes | 1–2 |
| 1 | [M1 — Async News Fetcher](docs/milestones/milestone-1-async-fetcher.md) | Hacker News + RSS fetchers, orchestrator, rate limiting, tests | 6–8 |
| 2 | [M2 — SOLID Refactoring](docs/milestones/milestone-2-solid-refactoring.md) | All five SOLID principles applied; add GitHub Trending with zero edits to existing code | 8–10 |
| 3 | [M3 — First Agent](docs/milestones/milestone-3-first-agent.md) | `NewsFilterAgent` via LiteLLM, prompt engineering, function calling | 8–10 |
| 4 | [M4 — MCP Pipeline](docs/milestones/milestone-4-mcp-pipeline.md) | Database MCP server, three-agent pipeline (Filter → Summarize → Write) | 10–14 |
| 5 | [M5 — Evaluation](docs/milestones/milestone-5-evaluation.md) | Golden dataset, accuracy/precision/recall/F1, project docs | 4–6 |

Full curriculum overview lives in [`docs/curriculum/overview.md`](docs/curriculum/overview.md).

---

## Tech stack

- **Python 3.11+** with async/await throughout
- **`aiohttp`** for concurrent HTTP, **`feedparser`** for RSS
- **LiteLLM** as the LLM provider abstraction — this repo is currently configured with `gemini/gemini-2.5-flash-lite` (free tier), and you can swap to Claude, OpenAI, or any [LiteLLM-supported provider](https://docs.litellm.ai/docs/providers) by changing the `LITELLM_MODEL` env var (no code changes)
- **MCP (Model Context Protocol)** for tool integration in Milestone 4
- **SQLite** for the database server in Milestone 4
- **pytest + pytest-asyncio** for tests
- **ruff** for formatting and linting

---

## Quickstart

```bash
git clone https://github.com/BLEND360/AIUpskillProject.git
cd AIUpskillProject

python3.11 -m venv venv
source venv/bin/activate          # macOS/Linux
# venv\Scripts\activate            # Windows

pip install --upgrade pip
pip install -r requirements.txt

# create a .env file in the project root with your model + provider key, e.g.:
#   LITELLM_MODEL=gemini/gemini-2.5-flash-lite
#   GEMINI_API_KEY=your-key-here
python scripts/verify_setup.py    # should print all ✅
```

Then open [`docs/milestones/milestone-0-setup.md`](docs/milestones/milestone-0-setup.md).

---

## Running the built pipeline

Run from the **project root**, as modules (`-m`) so the `src` imports resolve.
On Windows use `./venv/Scripts/python.exe`; on macOS/Linux use `python`.

```bash
# Full pipeline: fetch -> db -> filter -> summarize -> write
python -m src.complete_pipeline
#   -> data/output/newsletter.md   (final newsletter)
#   -> data/context/               (intermediate filter + summary)
#   -> data/news_agent.db          (article database)

# Individual pieces
python -m src.main                   # fetch articles only
python -m scripts.populate_db        # load fetched markdown into SQLite
python -m tests.test_db_server       # exercise the database MCP server
python -m src.evaluation.evaluator   # score the filter agent vs the golden dataset
```

> ⚠️ The agents make live LLM calls. On the Gemini free tier (the default here)
> the ~20-requests/day cap can truncate a full pipeline run — the agents fail
> gracefully and report what completed rather than crashing.

## Evaluation results

`NewsFilterAgent` scored against the 10-case hand-labeled golden dataset
(`data/evaluation/golden_dataset.json`), full report in
[`data/evaluation/evaluation_report.md`](data/evaluation/evaluation_report.md):

| Metric | Score |
|--------|-------|
| Accuracy | 90.0% (9/10) |
| Precision | 85.7% |
| Recall | 100.0% |
| F1 | 0.923 |

The single miss is a false positive (a Docker release judged AI-relevant) —
recall is perfect, so no genuinely relevant article was dropped.

---

## Repository layout

```
AIUpskillProject/
├── README.md                  ← you are here
├── requirements.txt
├── .env.example
├── scripts/
│   └── verify_setup.py        # M0 Task 5 runs this
├── src/                       # built milestone by milestone
│   ├── models/
│   ├── fetchers/
│   ├── transformers/
│   ├── storage/
│   ├── agents/
│   ├── mcp/                    # database_server, hello_server, simple_client
│   ├── skills/
│   ├── evaluation/
│   └── orchestrator.py / complete_pipeline.py
├── tests/
├── data/                      # created at runtime
└── docs/
    ├── architecture/overview.md
    ├── milestones/            # M0 → M5
    └── curriculum/            # high-level curriculum docs
```

---

## How checkpoints work

Each milestone ends with a PR you open against your fork of this repo. Two
reviewers approve before you move on. PR templates and review criteria live
inside the relevant milestone doc.

---

## Questions

Ask in Slack: `#ai-upskill-cohort-[X]`

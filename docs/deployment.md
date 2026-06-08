# Deployment / Run Guide

This project is designed to **run locally** — it's a learning project, not a
cloud service. No server or container is required.

---

## Requirements

- Windows, macOS, or Linux
- Python 3.11+
- ~1 GB disk, ~2 GB RAM
- One LLM provider API key (this repo defaults to Gemini free tier)

## Setup

See the [README Quickstart](../README.md#quickstart). In short:

```bash
python -m venv venv
# Windows:        venv\Scripts\activate     (or call ./venv/Scripts/python.exe directly)
# macOS/Linux:    source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` in the project root:

```
LITELLM_MODEL=gemini/gemini-2.5-flash-lite
GEMINI_API_KEY=your-key-here
```

Verify: `python scripts/verify_setup.py` (should print all ✅).

## Running

Always run from the **project root as a module** (`-m`) so `from src...` imports
resolve. On Windows, substitute `./venv/Scripts/python.exe` for `python`.

```bash
python -m src.complete_pipeline       # full fetch -> ... -> newsletter
python -m src.main                    # fetch only
python -m src.evaluation.evaluator    # filter-agent evaluation
```

Outputs land in `data/output/newsletter.md`, `data/context/`, and
`data/news_agent.db`.

> Running a bare script (`python src/complete_pipeline.py`) will fail with
> `ModuleNotFoundError: src` — that's why the `-m` form is required.

## Scheduling (optional)

**macOS/Linux (cron)** — daily at 9 AM:

```cron
0 9 * * * cd /path/to/project && /path/to/venv/bin/python -m src.complete_pipeline
```

**Windows (Task Scheduler):** Create Basic Task → Daily 9 AM → Start a program:
- Program: `C:\path\to\project\venv\Scripts\python.exe`
- Arguments: `-m src.complete_pipeline`
- Start in: `C:\path\to\project`

## Docker (optional)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
# -m form so src imports resolve inside the container
CMD ["python", "-m", "src.complete_pipeline"]
```

```bash
docker build -t aiupskillproject .
# pass the key at runtime; mount data/ to keep outputs
docker run --rm -e LITELLM_MODEL=gemini/gemini-2.5-flash-lite \
  -e GEMINI_API_KEY=your-key -v "$(pwd)/data:/app/data" aiupskillproject
```

## Configuration

| Variable | Required | Notes |
|----------|----------|-------|
| `LITELLM_MODEL` | yes | LiteLLM model string, e.g. `gemini/gemini-2.5-flash-lite` |
| `GEMINI_API_KEY` (or `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`) | yes | Must match the provider in `LITELLM_MODEL` |
| `ENVIRONMENT` | no | `development` / `production` |
| `LOG_LEVEL` | no | Currently informational; no logging framework is wired up yet |

`.env` is gitignored — never commit your keys.

## Inspecting state

```bash
# how many articles are in the database
sqlite3 data/news_agent.db "SELECT COUNT(*) FROM articles;"

# read the latest outputs
cat data/output/newsletter.md
cat data/evaluation/evaluation_report.md
```

## Troubleshooting

- **`ModuleNotFoundError: src`** — you ran a bare script; use the `-m` form from the root.
- **`UnicodeEncodeError` (cp1252)** — an entry point printing/writing emoji without
  UTF-8; entry scripts call `sys.stdout.reconfigure(encoding="utf-8")` and file I/O
  passes `encoding="utf-8"`.
- **Daily quota / 429 `PerDay`** — the free tier caps ~20 requests/day; the agents
  stop cleanly and report partial results. Wait for reset (~midnight PT), switch to
  a paid tier, or point `LITELLM_MODEL` at another provider.
- **`ModuleNotFoundError: aiosqlite` / `mcp`** — dependencies not installed in the
  active venv; re-run `pip install -r requirements.txt`.

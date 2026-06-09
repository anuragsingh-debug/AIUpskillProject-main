# Pipeline Simulation (demo UI)

A self-contained **HTML/CSS/JS** visualisation of the AI news pipeline
(**Fetch → Database → Filter → Summarize → Write**). Built for the project
demo / final report.

## What it does
- Click **▶ Start Pipeline** and watch all 5 stages run with live progress bars.
- The **Filter** stage shows each article being judged by the AI agent — a live
  relevance score (0–10), with **KEEP** (≥6, green) or **BIN** (<6, red) and the
  agent's reasoning + topic tags.
- The **Write** stage produces a multi-page **Newsletter** you can page through,
  **download** as `.md` or `.html`, or **Print / Save as PDF**.

## How to run
Just **double-click `index.html`** (opens in any browser). No server, no install.

## Important: this is a SIMULATION
- ❌ Makes **no LLM calls** and **uses no API quota**.
- ❌ Imports nothing from `src/` and changes **no** production code or tests.
- ✅ Uses **real data** extracted from the project's own output files
  (`data/articles/`, `data/context/`) — see `data.js`.

The live counts are for the 12-article sample in `data.js`. The real production
run processed **43 → 7 articles (16.3%)**; the filter agent's quality is measured
separately in `data/evaluation/evaluation_report.md`.

## Files
| File | Purpose |
|---|---|
| `index.html` | layout / structure |
| `styles.css` | styling (dark dashboard + print styles) |
| `app.js` | animation engine, judging feed, pagination, downloads |
| `data.js` | real article + summary data (no secrets) |

# Pipeline Demo UI

A visualisation of the AI news pipeline
(**Fetch → Database → Filter → Summarize → Write → Evaluate**) with **two modes**.

## Two modes

### 1. Replay (offline, default) — runs anywhere
- Double-click `index.html`, or open the live site, and click **▶ Start Pipeline**.
- Replays the pipeline using **real data** from the project's own outputs (`data.js`).
- Makes **no LLM calls**, uses **no quota**, imports nothing from `src/`.
- Perfect for sharing a public link (GitHub Pages).

### 2. Live (real LLM) — real-time, needs the local server
- Start the backend from the repo root:
  ```bash
  ./venv/Scripts/python.exe -m server
  ```
- Open **http://localhost:8000/**, set **Mode → "Live (real LLM)"**, click **Run**.
- This runs the **real** `src/` agents: it fetches live news (HackerNews + RSS) and
  the real `NewsFilterAgent` judges each article via the LLM — streamed to the page
  over Server-Sent Events. **Not a replay.**
- ⚠️ Uses **real Gemini quota** (~6–10 calls per run; free tier ≈ 20/day). If the
  daily cap is hit it stops gracefully (the E9 behaviour). On GitHub Pages (no
  backend) Live mode shows a friendly "needs local server" message.

## Output
Both modes produce a multi-page **Newsletter** you can page through and download as
**PDF** (bundled `vendor/html2pdf.bundle.min.js`), `.md`, `.html`, or Print.

## Files
| File | Purpose |
|---|---|
| `index.html` | layout / structure (mode toggle, controls) |
| `styles.css` | styling (dark dashboard + print styles) |
| `app.js` | engine: replay animation, live SSE client, judging feed, pagination, downloads |
| `data.js` | real article + summary + eval data for Replay (no secrets) |
| `vendor/html2pdf.bundle.min.js` | client-side PDF generation |
| `../server.py` | aiohttp backend for Live mode (runs the real pipeline) |

Nothing here contains secrets; the `.env` API key is never used by the static site
(only by `server.py`, locally).

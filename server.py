"""Live demo backend — runs the REAL pipeline and streams progress over SSE.

Run from the repo root:
    ./venv/Scripts/python.exe -m server
Then open  http://localhost:8000/  and pick "Live (real LLM)" in the top bar.

This makes REAL fetches and REAL LLM calls (it uses your Gemini quota). It reuses
the actual agents/fetchers in `src/` — nothing is faked. For a zero-quota,
always-on demo, use the static replay (`demo/index.html` or the GitHub Pages site).

It does NOT modify the real pipeline code and does NOT write to `data/` — it calls
the fetchers/agents directly and streams results to the browser.
"""

import asyncio
import json
import sys
from pathlib import Path

from aiohttp import web

from src.transformers.article_transformer import ArticleTransformer
from src.storage.markdown_storage import MarkdownStorage
from src.fetchers.hackernews_fetcher import HackerNewsFetcher
from src.fetchers.rss_fetcher import RSSFetcher
from src.agents.news_filter_agent import NewsFilterAgent
from src.agents.base_agent import DailyQuotaExceeded

DEMO_DIR = Path(__file__).parent / "demo"
MAX_ARTICLES = 6   # keep small — each one is a real LLM call (free tier ~20/day)
THRESHOLD = 6


async def run_pipeline(request: web.Request) -> web.StreamResponse:
    """Server-Sent Events stream of a real pipeline run."""
    resp = web.StreamResponse(
        status=200,
        headers={
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
    await resp.prepare(request)

    async def emit(**event):
        await resp.write(f"data: {json.dumps(event)}\n\n".encode("utf-8"))

    try:
        await emit(type="log", cls="c-info",
                   msg="LIVE - real fetch + real LLM (uses Gemini quota)")

        # ---- Stage 1: Fetch (no LLM) ----
        await emit(type="stage", stage="fetch", state="running")
        transformer = ArticleTransformer()
        storage = MarkdownStorage()
        fetchers = [
            HackerNewsFetcher(transformer, storage),
            RSSFetcher("https://hnrss.org/frontpage", transformer, storage),
        ]
        articles = []
        for f in fetchers:
            try:
                got = await f.fetch_articles()
                articles.extend(got)
                await emit(type="log", cls="c-dim",
                           msg=f"   - {f.get_source_name()}: {len(got)} articles")
            except Exception as ex:  # one source failing must not kill the run
                await emit(type="log", cls="c-bad",
                           msg=f"   {f.get_source_name()} failed: {ex}")
        articles = articles[:MAX_ARTICLES]
        for i in range(len(articles)):
            await emit(type="kpi", key="fetched", val=i + 1)
        await emit(type="stage", stage="fetch", state="done")
        await emit(type="log", cls="c-ok", msg=f"Fetched {len(articles)} real articles")

        if not articles:
            await emit(type="fatal", msg="No articles fetched (network?). Try again.")
            await emit(type="done")
            return resp

        # ---- Stage 2: Database (light) ----
        await emit(type="stage", stage="db", state="running")
        await emit(type="stage", stage="db", state="done")

        # ---- Stage 3: Filter (REAL LLM, one call per article) ----
        await emit(type="stage", stage="filter", state="running")
        agent = NewsFilterAgent()
        kept, binned = [], 0
        for a in articles:
            await emit(type="article-start", title=a.title, source=a.source,
                       points=getattr(a, "score", 0) or 0)
            try:
                # _judge_relevance is sync (blocking LLM call) -> run off the loop
                judgment = await asyncio.to_thread(
                    agent._judge_relevance, {"title": a.title, "summary": a.summary or ""}
                )
            except DailyQuotaExceeded as ex:
                await emit(type="article-verdict", title=a.title, score=0, keep=False,
                           error=True, reasoning="daily quota", topics=[])
                await emit(type="stage", stage="filter", state="done")
                await emit(type="fatal",
                           msg=f"Gemini daily quota exhausted - try after midnight PT, "
                               f"or use Replay mode. ({ex})")
                await emit(type="done")
                return resp

            if judgment["status"] == "error":
                await emit(type="article-verdict", title=a.title, score=0, keep=False,
                           error=True,
                           reasoning=f"could not judge ({judgment['error_type']})", topics=[])
                await emit(type="log", cls="c-bad",
                           msg=f"   ! {a.title[:48]} - {judgment['error_type']}")
                continue

            score = judgment["relevance_score"]
            keep = bool(judgment["relevant"]) and score >= THRESHOLD
            await emit(type="article-verdict", title=a.title, score=score, keep=keep,
                       error=False, reasoning=judgment.get("reasoning", ""),
                       topics=judgment.get("key_topics", []))
            if keep:
                kept.append({"title": a.title, "reasoning": judgment.get("reasoning", ""),
                             "topics": judgment.get("key_topics", [])})
                await emit(type="kpi", key="kept", val=len(kept))
                await emit(type="log", cls="c-ok", msg=f"   keep [{score}/10] {a.title[:48]}")
            else:
                binned += 1
                await emit(type="kpi", key="binned", val=binned)
                await emit(type="log", cls="c-bad", msg=f"   bin  [{score}/10] {a.title[:48]}")
        await emit(type="stage", stage="filter", state="done")

        # ---- Stage 4: Summarize (REAL LLM, grouped by first topic) ----
        await emit(type="stage", stage="summarize", state="running")
        groups: dict[str, list] = {}
        for k in kept:
            topic = k["topics"][0] if k["topics"] else "Other"
            groups.setdefault(topic, []).append(k)
        n_topics = 0
        for topic, items in groups.items():
            arts = "\n".join(f"- {it['title']}: {it['reasoning']}" for it in items)
            prompt = (f"Summarize these {topic} articles into 2-3 sentences for a daily "
                      f"digest:\n\n{arts}\n\nBe concise and informative.")
            try:
                text = (await asyncio.to_thread(agent._call_llm, prompt)).strip()
            except DailyQuotaExceeded:
                await emit(type="log", cls="c-bad", msg="Daily quota hit during summarize.")
                break
            except Exception as ex:
                text = f"(summary unavailable: {ex})"
            n_topics += 1
            await emit(type="summary", topic=topic, count=len(items), text=text)
            await emit(type="kpi", key="topics", val=n_topics)
        await emit(type="stage", stage="summarize", state="done")

        # ---- Stage 5: Write ----
        await emit(type="stage", stage="write", state="running")
        await emit(type="newsletter")
        await emit(type="stage", stage="write", state="done")
        await emit(type="log", cls="c-ok", msg="Newsletter generated (live)")

        # ---- Stage 6: Evaluate (show the VERIFIED numbers; a live eval = +20 calls) ----
        await emit(type="stage", stage="evaluate", state="running")
        await emit(type="eval-verified")
        await emit(type="stage", stage="evaluate", state="done")

        await emit(type="done")
    except Exception as ex:  # never leave the stream hanging
        try:
            await emit(type="fatal", msg=f"server error: {ex}")
        except Exception:
            pass
    return resp


async def index(_request):
    return web.FileResponse(DEMO_DIR / "index.html")


def make_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/api/run", run_pipeline)
    app.router.add_get("/", index)
    app.router.add_static("/", DEMO_DIR, show_index=False)
    return app


if __name__ == "__main__":
    if sys.platform.startswith("win"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")  # agents print emoji
        except Exception:
            pass
    print("Live demo running:  http://localhost:8000   (Ctrl+C to stop)")
    web.run_app(make_app(), host="127.0.0.1", port=8000, print=None)

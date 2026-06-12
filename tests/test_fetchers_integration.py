# tests/test_fetchers_integration.py
import pytest
from src.fetchers.hackernews_fetcher import HackerNewsFetcher
from src.fetchers.rss_fetcher import RSSFetcher
from src.transformers.article_transformer import ArticleTransformer
from src.storage.markdown_storage import MarkdownStorage


def make_deps():
    """Shared dependencies injected into every fetcher."""
    return ArticleTransformer(), MarkdownStorage()


@pytest.mark.asyncio
async def test_both_fetchers():
    """Test both fetchers work."""
    transformer, storage = make_deps()

    # HackerNews
    hn = HackerNewsFetcher(transformer, storage, limit=5)
    hn_articles = await hn.fetch_articles()
    assert len(hn_articles) > 0

    # RSS
    rss = RSSFetcher("https://hnrss.org/frontpage", transformer, storage)
    rss_articles = await rss.fetch_articles()
    assert len(rss_articles) > 0

    print(f"HN: {len(hn_articles)} articles")
    print(f"RSS: {len(rss_articles)} articles")


@pytest.mark.asyncio
async def test_concurrent_fetching():
    """Both sources can be fetched together under asyncio.gather and return data.

    This is a SMOKE test (does concurrent invocation work end to end), NOT a
    speed test. We deliberately make NO wall-clock assertion: fetching over the
    live network has huge variance — in repeated runs the same fetch took 1.4s,
    6s, and 18s — so any "concurrent must be faster than X" check flakes on
    network jitter, not on real behaviour. The actual concurrency GUARANTEE (the
    RSS fetch not blocking the event loop) is proven deterministically in
    test_rss_fetch_does_not_block_event_loop below.
    """
    import asyncio

    transformer, storage = make_deps()
    hn = HackerNewsFetcher(transformer, storage, limit=5)
    rss = RSSFetcher("https://hnrss.org/frontpage", transformer, storage)

    # Fire both at the same time; both must come back with data.
    hn_articles, rss_articles = await asyncio.gather(
        hn.fetch_articles(), rss.fetch_articles()
    )

    print(f"Fetched {len(hn_articles)} HN + {len(rss_articles)} RSS concurrently")
    assert len(hn_articles) > 0 and len(rss_articles) > 0


@pytest.mark.asyncio
async def test_rss_fetch_does_not_block_event_loop(monkeypatch):
    """RSS fetch must offload the blocking feedparser.parse so the loop keeps running.

    feedparser.parse() does blocking network I/O. If the fetcher calls it
    directly on the event-loop thread, it freezes EVERY other concurrent task
    until it returns — which is the bug that made HN+RSS run serially instead of
    overlapping. This test proves the fix deterministically, with no network:

      1. Replace feedparser.parse with a stub that BLOCKS (time.sleep) for a
         known duration, returning an empty feed.
      2. Run a "heartbeat" coroutine alongside the fetch. The heartbeat can only
         tick if the event loop is free to schedule it.
      3. If the fetcher offloads the blocking call (asyncio.to_thread), the
         heartbeat ticks many times during the parse. If it blocks the loop, the
         heartbeat is frozen and ticks ~0 times.
    """
    import asyncio
    import time

    BLOCK_SECONDS = 0.5  # how long the fake "network" blocks

    class _FakeFeed:
        entries = []  # transform_rss([]) -> [] ; keeps the fetcher path intact

    def blocking_parse(_url):
        time.sleep(BLOCK_SECONDS)  # simulate a slow, BLOCKING fetch+parse
        return _FakeFeed()

    # Patch the parse used inside the RSS fetcher module.
    monkeypatch.setattr(
        "src.fetchers.rss_fetcher.feedparser.parse", blocking_parse
    )

    transformer, storage = make_deps()
    rss = RSSFetcher("http://example.invalid/feed", transformer, storage)

    ticks = 0

    async def heartbeat():
        nonlocal ticks
        while True:
            await asyncio.sleep(0.02)  # ~25 chances to tick during a 0.5s block
            ticks += 1

    hb = asyncio.create_task(heartbeat())
    await rss.fetch_articles()  # blocks 0.5s INSIDE a worker thread if fixed
    hb.cancel()

    print(f"Heartbeat ticked {ticks} times during the blocking parse")
    # If the loop stayed free, we expect ~20+ ticks; a blocked loop gives ~0.
    # Assert a conservative floor so the test is robust to scheduling slack.
    assert ticks >= 5

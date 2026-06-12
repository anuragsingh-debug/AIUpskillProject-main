# src/fetchers/rss_fetcher.py

import asyncio
from src.fetchers.base_fetcher import BaseFetcher
import feedparser
from typing import List
from src.models.article import Article


class RSSFetcher(BaseFetcher):
    """Fetch from RSS feed."""

    def __init__(self, feed_url: str, transformer, storage):
        super().__init__(transformer, storage)
        self.feed_url = feed_url

    async def fetch_articles(self) -> List[Article]:
        """Fetch from RSS feed.

        feedparser.parse() does a BLOCKING network request + parse. Calling it
        directly inside this `async def` would freeze the whole event loop until
        it returns — so a sibling task (e.g. the aiohttp HackerNews fetch running
        under the same asyncio.gather) cannot make progress meanwhile, defeating
        the point of fetching concurrently. asyncio.to_thread offloads the
        blocking call to a worker thread and `await`s it, which yields control
        back to the loop so the two sources genuinely overlap.
        """
        feed = await asyncio.to_thread(feedparser.parse, self.feed_url)
        return self.transformer.transform_rss(feed.entries)

    def get_source_name(self) -> str:
        """Return source name."""
        return "rss"

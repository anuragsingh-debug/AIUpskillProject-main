"""Fetch top stories from HackerNews."""

import asyncio
import aiohttp
from typing import List
from src.models.article import Article
from src.fetchers.base_fetcher import BaseFetcher
from src.strategies.rate_limit_strategy import RateLimitStrategy, SemaphoreStrategy


class HackerNewsFetcher(BaseFetcher):
    """
    Fetches top stories from the HackerNews API.

    Inherits from BaseFetcher: implements only the source-specific parts
    (how to fetch raw data + the source name). Turning raw dicts into Article
    objects is delegated to the injected transformer (SRP).

    API Docs: https://github.com/HackerNews/API
    """

    BASE_URL = "https://hacker-news.firebaseio.com/v0"

    def __init__(
        self,
        transformer,
        storage,
        limit: int = 30,
        rate_limiter: RateLimitStrategy = None,
    ):
        # Parent keeps the transformer ("chef") and storage ("cashier").
        super().__init__(transformer, storage)
        self.limit = limit
        # Rate-limiting algorithm is injectable (Strategy pattern). Default caps
        # concurrent item requests at 10 so we don't hammer the API.
        self.rate_limiter = rate_limiter or SemaphoreStrategy(max_concurrent=10)

    def get_source_name(self) -> str:
        """Return the source name (used for the output filename)."""
        return "hackernews"

    async def fetch_articles(self) -> List[Article]:
        """Fetch raw stories from HackerNews, then hand them to the transformer."""
        # Step 1: get the list of top story IDs.
        story_ids = await self._fetch_top_story_ids()

        # Step 2: fetch the first `limit` stories concurrently (the async speed-up).
        raw_stories = await self._fetch_stories(story_ids[: self.limit])

        # Step 3: this fetcher does NOT build Articles itself (SRP) — transformer does.
        return self.transformer.transform_hackernews(raw_stories)

    async def _fetch_top_story_ids(self) -> List[int]:
        """Fetch the list of top story IDs (one network call)."""
        url = f"{self.BASE_URL}/topstories.json"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.json()

    async def _fetch_stories(self, story_ids: List[int]) -> List[dict]:
        """Fetch many story dicts at once, dropping any that failed (None)."""
        tasks = [self._fetch_story(story_id) for story_id in story_ids]
        stories = await asyncio.gather(*tasks)
        return [s for s in stories if s is not None]

    async def _fetch_story(self, story_id: int) -> dict:
        """Fetch one raw story dict by its ID (rate-limited)."""
        url = f"{self.BASE_URL}/item/{story_id}.json"
        try:
            # Grab a slot first; if 10 are already running, wait here for a free one.
            async with self.rate_limiter:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        return await response.json()
        except Exception as e:
            print(f"Failed to fetch story {story_id}: {e}")
            return None

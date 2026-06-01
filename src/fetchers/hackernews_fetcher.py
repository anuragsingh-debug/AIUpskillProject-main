"""Fetch top stories from HackerNews."""

import asyncio
import aiohttp
from typing import List
from datetime import datetime
from src.models.article import Article
from src.storage.markdown_storage import MarkdownStorage
from src.utils.rate_limiter import RateLimiter


class HackerNewsFetcher:
    """
    Fetches top stories from HackerNews API.

    API Docs: https://github.com/HackerNews/API
    """

    BASE_URL = "https://hacker-news.firebaseio.com/v0"

    # Constructor: runs once when you do HackerNewsFetcher(). Sets up storage.
    def __init__(self):
        self.storage = MarkdownStorage()
        # Guard: at most 10 stories fetched at the same time (see rate_limiter.py).
        self.rate_limiter = RateLimiter(max_concurrent=10)

    # This is the PUBLIC method — the outside world calls only this one.
    async def fetch(self, limit: int = 30) -> List[Article]:
        """
        Fetch top stories from HackerNews.

        Args:
            limit: Number of stories to fetch (default 30)

        Returns:
            List of Article objects
        """
        print(f"📰 Fetching {limit} stories from HackerNews...")

        # Step 1: Get the big list of top story IDs (just numbers, no details yet).
        story_ids = await self._fetch_top_story_ids()

        # Step 2: Take only the first `limit` IDs, then fetch their details all at once.
        articles = await self._fetch_stories(story_ids[:limit])

        print(f"✅ Fetched {len(articles)} HackerNews stories")
        return articles

    # Fetch AND save in one call: get the articles, then write them to a .md file.
    async def fetch_and_save(self, limit: int = 30) -> List[Article]:
        """Fetch articles and save them to a markdown file."""
        articles = await self.fetch(limit)

        # Only write a file if we actually got something (skip empty list).
        if articles:
            self.storage.save(articles, "hackernews_articles.md")

        return articles

    # Helper 1: get the list of top story IDs (one network call).
    async def _fetch_top_story_ids(self) -> List[int]:
        """Fetch list of top story IDs."""
        # Build the URL. self. is needed because BASE_URL lives on the class.
        url = f"{self.BASE_URL}/topstories.json"

        # Open a session (like a browser tab) and auto-close it when done.
        async with aiohttp.ClientSession() as session:
            # Send GET request; await = pause while data travels over network.
            async with session.get(url) as response:
                # Turn the JSON body into a Python list of ints, e.g. [38901, 38902, ...].
                story_ids = await response.json()
                return story_ids

    # Helper 2: fetch MANY stories at the same time (the async magic ⚡).
    async def _fetch_stories(self, story_ids: List[int]) -> List[Article]:
        """
        Fetch multiple stories concurrently.

        This is where async shines - fetch all at once!
        """
        # Make a "to-do" list of coroutines — nothing runs yet, just prepared.
        tasks = [self._fetch_story(story_id) for story_id in story_ids]

        # gather() fires ALL of them together and waits for every one to finish.
        stories = await asyncio.gather(*tasks)

        # Some fetches return None (e.g. Ask HN posts). Keep only real articles.
        return [s for s in stories if s is not None]

    # Helper 3: fetch ONE story by its ID and turn it into an Article.
    async def _fetch_story(self, story_id: int) -> Article:
        """Fetch single story by ID."""
        # Each story has its own URL: .../item/<id>.json
        url = f"{self.BASE_URL}/item/{story_id}.json"

        # try/except so one broken story doesn't crash the whole batch.
        try:
            # Grab a token first — if 10 are already running, WAIT here for a free slot.
            async with self.rate_limiter:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        data = await response.json()  # data is a dict for this story

                        # Skip stories with no link (Ask HN, polls, etc.).
                        if not data.get("url"):
                            return None

                        # Build an Article. .get(key, default) avoids crashes if a key is missing.
                        return Article(
                            title=data.get("title", "No Title"),
                            url=data["url"],
                            # HN gives time as a Unix timestamp (seconds) -> convert to datetime.
                            published_at=datetime.fromtimestamp(data.get("time", 0)),
                            source="hackernews",
                            summary=data.get("text", "")[
                                :200
                            ],  # keep first 200 chars only
                            score=data.get("score", 0),
                        )
        except Exception as e:
            # Log the problem and return None; _fetch_stories will filter it out.
            print(f"⚠️  Failed to fetch story {story_id}: {e}")
            return None


# Test it
async def test_fetch():
    """Quick test of fetcher — now fetches AND saves to markdown."""
    fetcher = HackerNewsFetcher()
    articles = await fetcher.fetch_and_save(limit=10)

    print("\n📊 Results:")
    for article in articles:
        print(f"  - {article.title[:50]}...")

    return articles


if __name__ == "__main__":
    asyncio.run(test_fetch())

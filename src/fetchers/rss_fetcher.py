"""Fetch articles from RSS feeds."""

import asyncio
import feedparser
from typing import List
from datetime import datetime
from dateutil import parser as date_parser
from src.models.article import Article
from src.storage.markdown_storage import MarkdownStorage


class RSSFetcher:
    """
    Fetches articles from RSS feeds.

    Uses feedparser library for RSS parsing.
    """

    # Constructor: runs once when you do RSSFetcher(url).
    # Each RSS feed has its OWN url, so we take it as a parameter and store it.
    # We also keep a storage object here so this fetcher can save its results later.
    def __init__(self, feed_url: str):
        """
        Initialize RSS fetcher.

        Args:
            feed_url: URL of RSS feed
        """
        self.feed_url = feed_url
        self.storage = MarkdownStorage()

    # The PUBLIC method — outside world calls this to get articles.
    # feedparser is SYNC (blocking), so we run it in a thread via run_in_executor
    # to keep our async program from freezing, then turn each entry into an Article.
    async def fetch(self) -> List[Article]:
        """
        Fetch articles from RSS feed.

        Returns:
            List of Article objects
        """
        print(f"📰 Fetching from RSS: {self.feed_url}")

        # feedparser is sync, run in executor
        loop = asyncio.get_event_loop()
        feed = await loop.run_in_executor(
            None,  # Default executor
            feedparser.parse,
            self.feed_url,
        )

        # Parse entries
        articles = []
        for entry in feed.entries:
            article = self._parse_entry(entry)
            if article:
                articles.append(article)

        print(f"✅ Fetched {len(articles)} RSS articles")
        return articles

    # Helper (the _ means "private, internal use only").
    # Takes ONE raw RSS entry and converts it into a clean Article object.
    # Handles missing fields, messy date strings, and strips HTML from the summary.
    def _parse_entry(self, entry) -> Article:
        """Parse RSS entry to Article."""
        try:
            # Get title
            title = entry.get("title", "No Title")

            # Get URL
            url = entry.get("link", "")
            if not url:
                return None

            # Parse date
            published_str = entry.get("published", entry.get("updated", ""))
            if published_str:
                try:
                    published_at = date_parser.parse(published_str)
                except Exception:
                    published_at = datetime.now()
            else:
                published_at = datetime.now()

            # Get summary
            summary = entry.get("summary", entry.get("description", ""))
            # Clean HTML tags (basic)
            import re

            summary = re.sub("<.*?>", "", summary)[:200]

            return Article(
                title=title,
                url=url,
                published_at=published_at,
                source="rss",
                summary=summary,
            )
        except Exception as e:
            print(f"⚠️  Failed to parse entry: {e}")
            return None

    # Convenience method: fetch AND write to a markdown file in one call.
    # It builds a filename from the feed's domain (e.g. rss_hnrss.org_articles.md)
    # and only saves if we actually got some articles back.
    async def fetch_and_save(self) -> List[Article]:
        """Fetch and save articles."""
        articles = await self.fetch()

        if articles:
            # Extract feed name from URL
            feed_name = self.feed_url.split("//")[-1].split("/")[0]
            filename = f"rss_{feed_name}_articles.md"
            self.storage.save(articles, filename)

        return articles


# Test it
async def test_rss():
    """Test RSS fetcher."""
    # HackerNews RSS feed
    fetcher = RSSFetcher("https://hnrss.org/frontpage")
    articles = await fetcher.fetch_and_save()

    print(f"\n📊 Fetched {len(articles)} articles")
    for article in articles[:3]:
        print(f"  - {article.title[:50]}...")


if __name__ == "__main__":
    asyncio.run(test_rss())

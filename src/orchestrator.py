"""Orchestrate multiple news fetchers."""

import asyncio
from typing import List
from src.models.article import Article
from src.fetchers.hackernews_fetcher import HackerNewsFetcher
from src.fetchers.rss_fetcher import RSSFetcher
from src.fetchers.github_trending_fetcher import GitHubTrendingFetcher


class FetchOrchestrator:
    """
    Orchestrates fetching from multiple sources.

    Dependencies (transformer, storage) are INJECTED via the constructor
    (Dependency Inversion) — the orchestrator no longer builds them itself.
    """

    def __init__(self, transformer, storage):
        # Injected dependencies, shared by every fetcher.
        self.transformer = transformer
        self.storage = storage

        # Build the list of fetchers. Adding a new source = one line here.
        self.fetchers = [
            HackerNewsFetcher(transformer, storage),
            RSSFetcher("https://hnrss.org/frontpage", transformer, storage),
            GitHubTrendingFetcher(transformer, storage),
        ]

    async def fetch_all(self) -> List[Article]:
        """Fetch from all sources concurrently and save the combined result."""
        print("\nStarting fetch from all sources...")
        print(f"   Sources: {len(self.fetchers)}")

        # All fetchers share the same interface (fetch_articles), so no isinstance
        # checks are needed — that is the Open/Closed + Liskov payoff.
        tasks = [fetcher.fetch_articles() for fetcher in self.fetchers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Combine articles; ask each fetcher its own name via get_source_name().
        all_articles = []
        for fetcher, result in zip(self.fetchers, results):
            name = fetcher.get_source_name()
            if isinstance(result, Exception):
                print(f"   {name} failed: {result}")
            else:
                print(f"   {name}: {len(result)} articles")
                all_articles.extend(result)

        # Save combined results
        if all_articles:
            self.storage.save(all_articles, "all_articles.md")

        print(f"\nTotal: {len(all_articles)} articles from {len(self.fetchers)} sources")
        return all_articles


# Manual run: python -m src.orchestrator
async def main():
    from src.transformers.article_transformer import ArticleTransformer
    from src.storage.markdown_storage import MarkdownStorage

    orchestrator = FetchOrchestrator(ArticleTransformer(), MarkdownStorage())
    articles = await orchestrator.fetch_all()

    print("\nSample articles:")
    for article in articles[:5]:
        print(f"  [{article.source}] {article.title[:60]}...")


if __name__ == "__main__":
    asyncio.run(main())

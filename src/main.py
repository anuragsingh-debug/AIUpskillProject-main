"""Main entry point for news fetcher."""

import asyncio
import sys
from src.orchestrator import FetchOrchestrator
from src.transformers.article_transformer import ArticleTransformer
from src.storage.markdown_storage import MarkdownStorage
from src.fetchers.hackernews_fetcher import HackerNewsFetcher
from src.fetchers.rss_fetcher import RSSFetcher
from src.fetchers.github_trending_fetcher import GitHubTrendingFetcher


async def main():
    """Main function."""
    print("=" * 60)
    print("  AI Agent Onboarding - News Fetcher")
    print("  Milestone 1: Async News Fetcher")
    print("=" * 60)

    try:
        # Composition root: build every concrete dependency HERE, then inject.
        # This is the only place that knows which fetchers/storage we use.
        transformer = ArticleTransformer()
        storage = MarkdownStorage()
        fetchers = [
            HackerNewsFetcher(transformer, storage),
            RSSFetcher("https://hnrss.org/frontpage", transformer, storage),
            GitHubTrendingFetcher(transformer, storage),
        ]
        # Inject everything by name (keyword args) so the order never matters.
        orchestrator = FetchOrchestrator(
            fetchers=fetchers,
            transformer=transformer,
            storage=storage,
        )
        articles = await orchestrator.fetch_all()

        print("\n" + "=" * 60)
        print(f"✅ Success! Fetched {len(articles)} articles total")
        print("📁 Saved to: data/articles/all_articles.md")
        print("=" * 60)

        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

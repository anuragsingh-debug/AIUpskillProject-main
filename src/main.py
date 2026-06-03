"""Main entry point for news fetcher."""

import asyncio
import sys
from src.orchestrator import FetchOrchestrator
from src.transformers.article_transformer import ArticleTransformer
from src.storage.markdown_storage import MarkdownStorage


async def main():
    """Main function."""
    print("=" * 60)
    print("  AI Agent Onboarding - News Fetcher")
    print("  Milestone 1: Async News Fetcher")
    print("=" * 60)

    try:
        # Build the shared dependencies here (composition root), then inject them.
        transformer = ArticleTransformer()
        storage = MarkdownStorage()
        orchestrator = FetchOrchestrator(transformer, storage)
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

"""Main entry point for news fetcher."""

import asyncio
import sys
from src.orchestrator import FetchOrchestrator


async def main():
    """Main function."""
    print("=" * 60)
    print("  AI Agent Onboarding - News Fetcher")
    print("  Milestone 1: Async News Fetcher")
    print("=" * 60)

    try:
        # Run orchestrator
        orchestrator = FetchOrchestrator()
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

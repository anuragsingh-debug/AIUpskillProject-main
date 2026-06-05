"""Complete pipeline: Fetch -> Filter (Milestone 1 + Milestone 3)."""

import asyncio
from pathlib import Path

from src.transformers.article_transformer import ArticleTransformer
from src.storage.markdown_storage import MarkdownStorage
from src.fetchers.hackernews_fetcher import HackerNewsFetcher
from src.orchestrator import FetchOrchestrator
from src.agents.news_filter_agent import NewsFilterAgent


async def run_pipeline():
    """
    Run the complete pipeline end-to-end.

    1. Fetch articles (Milestone 1)
    2. Filter with the AI agent (Milestone 3)
    """
    print("=" * 60)
    print("  Complete Pipeline: Fetch + Filter")
    print("=" * 60)

    # --- Composition root: build dependencies and INJECT them (DIP) ---
    transformer = ArticleTransformer()
    storage = MarkdownStorage()

    # Keep the fetch small (HackerNews, limit=5) so the filter step stays under
    # the free-tier LLM limit (10 req/min) until rate limiting (issue E6) lands.
    # Adding RSS / GitHub is one line each here, thanks to injected fetchers (OCP).
    fetchers = [HackerNewsFetcher(transformer, storage, limit=5)]
    orchestrator = FetchOrchestrator(fetchers, transformer, storage)

    # Step 1: Fetch articles
    print("\n📰 Step 1: Fetching articles...")
    articles = await orchestrator.fetch_all()
    fetch_output = Path("data/articles/all_articles.md")
    print(f"✅ Fetched {len(articles)} articles")
    print(f"   Saved to: {fetch_output}")

    # Step 2: Filter with the AI agent
    print("\n🤖 Step 2: Filtering with AI...")
    agent = NewsFilterAgent()
    filter_output = Path("data/context/filtered_articles.md")
    await agent.execute(
        input_path=str(fetch_output),
        output_path=str(filter_output),
    )

    print("\n" + "=" * 60)
    print("🎉 Pipeline complete!")
    print(f"   1. Fetched:  {fetch_output}")
    print(f"   2. Filtered: {filter_output}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_pipeline())

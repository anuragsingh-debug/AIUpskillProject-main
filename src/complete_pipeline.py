"""Complete multi-agent pipeline with MCP."""

import asyncio
from pathlib import Path
from src.orchestrator import FetchOrchestrator
from src.transformers.article_transformer import ArticleTransformer
from src.storage.markdown_storage import MarkdownStorage
from src.fetchers.hackernews_fetcher import HackerNewsFetcher
from src.fetchers.rss_fetcher import RSSFetcher
from src.fetchers.github_trending_fetcher import GitHubTrendingFetcher
from src.agents.news_filter_agent import NewsFilterAgent
from src.agents.summarizer_agent import SummarizerAgent
from src.agents.writer_agent import WriterAgent
from src.database.db_manager import DatabaseManager


async def run_complete_pipeline():
    """
    Run complete pipeline:
    1. Fetch articles (Milestone 1)
    2. Save to database
    3. Filter with AI (Milestone 3)
    4. Summarize (Milestone 4)
    5. Write newsletter (Milestone 4)
    """
    print("=" * 70)
    print("  Complete AI Agent Pipeline with MCP")
    print("=" * 70)

    # Step 1: Fetch
    print("\n📰 Step 1: Fetching articles from sources...")
    # Composition root: build the concrete dependencies HERE, then inject them
    # (Dependency Inversion). The orchestrator stays decoupled from concrete
    # fetchers/storage — same wiring as src/main.py.
    transformer = ArticleTransformer()
    storage = MarkdownStorage()
    fetchers = [
        HackerNewsFetcher(transformer, storage),
        RSSFetcher("https://hnrss.org/frontpage", transformer, storage),
        GitHubTrendingFetcher(transformer, storage),
    ]
    orchestrator = FetchOrchestrator(
        fetchers=fetchers,
        transformer=transformer,
        storage=storage,
    )
    articles = await orchestrator.fetch_all()
    fetch_output = Path("data/articles/all_articles.md")
    print(f"✅ Fetched {len(articles)} articles → {fetch_output}")

    # Step 2: Save to database
    print("\n💾 Step 2: Saving to database...")
    db = DatabaseManager()
    await db.initialize()
    # The articles table de-dups on a UNIQUE url, and the DB file PERSISTS across
    # runs — so the total row count is cumulative, not this run's count. Measure
    # before/after so we can report what THIS run actually added vs. what was
    # already stored (otherwise "Database has 47" after fetching 66 looks like 19
    # articles silently vanished, when they were really cross-run duplicates).
    count_before = len(await db.query_articles(limit=100000))
    for article in articles:
        await db.insert_article(
            {
                "title": article.title,
                "url": article.url,
                "source": article.source,
                "published_at": article.published_at.isoformat(),
                "summary": article.summary,
                "score": getattr(article, "score", 0),
            }
        )
    db_articles = await db.query_articles(limit=100000)
    inserted = len(db_articles) - count_before
    duplicates = len(articles) - inserted
    print(
        f"✅ Inserted {inserted} new article(s) this run "
        f"({duplicates} already in DB); database now holds {len(db_articles)} unique total"
    )

    # Step 3: Filter
    print("\n🤖 Step 3: Filtering with AI agent...")
    filter_agent = NewsFilterAgent()
    filter_output = Path("data/context/filtered_articles.md")
    await filter_agent.execute(
        input_path=str(fetch_output), output_path=str(filter_output)
    )
    print(f"✅ Filtered articles → {filter_output}")

    # Step 4: Summarize
    print("\n📝 Step 4: Summarizing with AI agent...")
    summarizer = SummarizerAgent()
    summary_output = Path("data/context/summary.md")
    await summarizer.execute(
        input_path=str(filter_output), output_path=str(summary_output)
    )
    print(f"✅ Summary → {summary_output}")

    # Step 5: Write
    print("\n✍️  Step 5: Writing newsletter...")
    writer = WriterAgent()
    newsletter_output = Path("data/output/newsletter.md")
    await writer.execute(
        input_path=str(summary_output), output_path=str(newsletter_output)
    )
    print(f"✅ Newsletter → {newsletter_output}")

    print("\n" + "=" * 70)
    print("🎉 Complete Pipeline Success!")
    print("=" * 70)
    print("\n📊 Pipeline Summary:")
    print(f"   1. Fetched: {len(articles)} articles")
    print(f"   2. Database: {len(db_articles)} total articles")
    print(f"   3. Filtered: {filter_output}")
    print(f"   4. Summarized: {summary_output}")
    print(f"   5. Newsletter: {newsletter_output}")
    print("\n📖 Read your newsletter:")
    print(f"   cat {newsletter_output}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_complete_pipeline())

"""Tests for HackerNews fetcher."""

import pytest
from src.fetchers.hackernews_fetcher import HackerNewsFetcher
from src.transformers.article_transformer import ArticleTransformer
from src.storage.markdown_storage import MarkdownStorage
from src.models.article import Article


def make_fetcher(limit):
    """Helper: build a fetcher with its injected dependencies (DI)."""
    return HackerNewsFetcher(ArticleTransformer(), MarkdownStorage(), limit=limit)


@pytest.mark.asyncio
async def test_fetch_returns_articles():
    """Test that fetch_articles returns a list of Article objects."""
    fetcher = make_fetcher(limit=5)
    articles = await fetcher.fetch_articles()

    # Should get some articles
    assert len(articles) > 0
    assert len(articles) <= 5

    # Each should be an Article
    for article in articles:
        assert isinstance(article, Article)
        assert article.title
        assert article.url
        assert article.source == "hackernews"


@pytest.mark.asyncio
async def test_fetch_concurrent():
    """Test that fetch is fast (concurrent, not one-by-one)."""
    import time

    fetcher = make_fetcher(limit=10)

    start = time.time()
    articles = await fetcher.fetch_articles()
    elapsed = time.time() - start

    # Should be faster than sequential (< 5 seconds) thanks to asyncio.gather
    assert elapsed < 5.0
    assert len(articles) > 0

    print(f"Fetched {len(articles)} articles in {elapsed:.2f}s")

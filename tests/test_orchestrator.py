# tests/test_orchestrator.py
"""
Orchestrator tests using MOCK fetchers (no real network).

This is the payoff of Dependency Inversion: because FetchOrchestrator takes its
fetchers/storage as constructor arguments, we can inject fakes here. The tests
are fast, offline, and deterministic — they never call HackerNews/RSS/GitHub.

NOTE: our orchestrator calls fetcher.fetch_articles() + get_source_name() (not
fetch_and_save), so those are the methods we fake on each mock fetcher.
"""
from datetime import datetime
from unittest.mock import Mock, AsyncMock

import pytest

from src.orchestrator import FetchOrchestrator
from src.models.article import Article


def make_article(title: str, source: str) -> Article:
    """Tiny helper to build a valid Article for tests."""
    return Article(
        title=title,
        url=f"https://example.com/{title}",
        published_at=datetime.now(),
        source=source,
        summary="test summary",
    )


def make_fake_fetcher(source_name: str, articles: list) -> Mock:
    """
    Build a stand-in fetcher that quacks like a BaseFetcher.

    The orchestrator only calls two things on each fetcher:
    fetch_articles() (async) and get_source_name(). We fake exactly those.
    """
    fetcher = Mock()
    fetcher.fetch_articles = AsyncMock(return_value=articles)
    fetcher.get_source_name = Mock(return_value=source_name)
    return fetcher


@pytest.mark.asyncio
async def test_orchestrator_combines_all_fetchers():
    """fetch_all() should gather articles from every injected fetcher."""
    fetcher_a = make_fake_fetcher("source_a", [make_article("A1", "source_a")])
    fetcher_b = make_fake_fetcher(
        "source_b",
        [make_article("B1", "source_b"), make_article("B2", "source_b")],
    )
    storage = Mock()  # fake storage; we just check it was asked to save

    orchestrator = FetchOrchestrator(
        fetchers=[fetcher_a, fetcher_b],
        transformer=Mock(),
        storage=storage,
    )

    articles = await orchestrator.fetch_all()

    # 1 from A + 2 from B = 3 combined
    assert len(articles) == 3
    # Each fake fetcher was actually used.
    fetcher_a.fetch_articles.assert_awaited_once()
    fetcher_b.fetch_articles.assert_awaited_once()
    # Combined result was handed to storage exactly once.
    storage.save.assert_called_once()


@pytest.mark.asyncio
async def test_orchestrator_handles_a_failing_fetcher():
    """If one fetcher raises, the others' articles still come through."""
    good = make_fake_fetcher("good", [make_article("G1", "good")])
    bad = make_fake_fetcher("bad", [])
    bad.fetch_articles = AsyncMock(side_effect=RuntimeError("network down"))

    orchestrator = FetchOrchestrator(
        fetchers=[good, bad],
        transformer=Mock(),
        storage=Mock(),
    )

    articles = await orchestrator.fetch_all()

    # The bad fetcher is swallowed (return_exceptions=True); the good one survives.
    assert len(articles) == 1
    assert articles[0].source == "good"


@pytest.mark.asyncio
async def test_orchestrator_with_no_articles_skips_save():
    """When every fetcher returns nothing, storage.save is not called."""
    empty = make_fake_fetcher("empty", [])
    storage = Mock()

    orchestrator = FetchOrchestrator(
        fetchers=[empty],
        transformer=Mock(),
        storage=storage,
    )

    articles = await orchestrator.fetch_all()

    assert articles == []
    storage.save.assert_not_called()

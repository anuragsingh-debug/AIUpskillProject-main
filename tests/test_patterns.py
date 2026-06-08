# tests/test_patterns.py
"""Tests for the design patterns added in Milestone 2 (Factory, Strategy)."""

import asyncio
import time
from unittest.mock import Mock

import pytest

from src.factories.fetcher_factory import FetcherFactory
from src.fetchers.base_fetcher import BaseFetcher
from src.fetchers.hackernews_fetcher import HackerNewsFetcher
from src.fetchers.rss_fetcher import RSSFetcher
from src.strategies.rate_limit_strategy import (
    RateLimitStrategy,
    SemaphoreStrategy,
    TokenBucketStrategy,
)


def test_factory_creates_known_fetcher():
    """create() returns the right concrete fetcher for a known name."""
    fetcher = FetcherFactory.create("hackernews", Mock(), Mock())
    assert isinstance(fetcher, HackerNewsFetcher)
    assert fetcher.get_source_name() == "hackernews"


def test_factory_creates_rss_with_feed_url():
    """RSS is a special case: it needs a feed_url passed via kwargs."""
    fetcher = FetcherFactory.create(
        "rss", Mock(), Mock(), feed_url="https://hnrss.org/frontpage"
    )
    assert isinstance(fetcher, RSSFetcher)
    assert fetcher.feed_url == "https://hnrss.org/frontpage"


def test_factory_rss_without_feed_url_raises():
    """Asking for RSS without a feed_url is a clear error."""
    with pytest.raises(ValueError, match="feed_url"):
        FetcherFactory.create("rss", Mock(), Mock())


def test_factory_unknown_type_raises():
    """Unknown names raise a helpful ValueError."""
    with pytest.raises(ValueError, match="Unknown fetcher type"):
        FetcherFactory.create("twitter", Mock(), Mock())


def test_factory_lists_available_types():
    """The factory can report what it knows how to build."""
    types = FetcherFactory.get_available_types()
    assert "hackernews" in types
    assert "rss" in types
    assert "github" in types


def test_factory_register_adds_new_type():
    """register() extends the factory without editing its code (OCP)."""

    class DummyFetcher(BaseFetcher):
        async def fetch_articles(self):
            return []

        def get_source_name(self):
            return "dummy"

    FetcherFactory.register("dummy", DummyFetcher)
    try:
        fetcher = FetcherFactory.create("dummy", Mock(), Mock())
        assert isinstance(fetcher, DummyFetcher)
    finally:
        # Keep the shared registry clean for other tests.
        FetcherFactory._fetchers.pop("dummy", None)


# --- Strategy pattern -------------------------------------------------------


def test_both_strategies_share_one_interface():
    """Both strategies are interchangeable RateLimitStrategy instances."""
    assert isinstance(SemaphoreStrategy(2), RateLimitStrategy)
    assert isinstance(TokenBucketStrategy(5, 1.0), RateLimitStrategy)


@pytest.mark.asyncio
async def test_semaphore_strategy_limits_concurrency():
    """With max_concurrent=2, four 0.1s tasks run in two waves (~0.2s)."""
    strategy = SemaphoreStrategy(max_concurrent=2)

    async def task():
        async with strategy:  # uses the strategy as an async context manager
            await asyncio.sleep(0.1)

    start = time.perf_counter()
    await asyncio.gather(*[task() for _ in range(4)])
    elapsed = time.perf_counter() - start

    # 4 tasks, 2 at a time, 0.1s each -> at least ~0.2s (never all-at-once 0.1s).
    assert elapsed >= 0.2


@pytest.mark.asyncio
async def test_token_bucket_strategy_allows_initial_burst():
    """A fresh bucket has full tokens, so the first `rate` calls don't block."""
    strategy = TokenBucketStrategy(rate=3, per=1.0)

    start = time.perf_counter()
    for _ in range(3):
        await strategy.acquire()
    elapsed = time.perf_counter() - start

    # The 3 starting tokens are spent instantly (no sleeping).
    assert elapsed < 0.05

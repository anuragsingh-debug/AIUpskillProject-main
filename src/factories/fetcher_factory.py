"""Factory for creating fetchers (Factory pattern)."""

from typing import Dict, List, Type

from src.fetchers.base_fetcher import BaseFetcher
from src.fetchers.hackernews_fetcher import HackerNewsFetcher
from src.fetchers.rss_fetcher import RSSFetcher
from src.fetchers.github_trending_fetcher import GitHubTrendingFetcher


class FetcherFactory:
    """
    Creates fetcher instances from a short string name.

    The caller doesn't need to know the concrete class or its argument order —
    it just asks for "hackernews" and gets a ready fetcher. New types can be
    added via register() without editing this class (Open/Closed friendly).
    """

    # Registry: name -> fetcher class. RSS is included so create("rss", ...) works.
    _fetchers: Dict[str, Type[BaseFetcher]] = {
        "hackernews": HackerNewsFetcher,
        "rss": RSSFetcher,
        "github": GitHubTrendingFetcher,
    }

    @classmethod
    def create(cls, source_type: str, transformer, storage, **kwargs) -> BaseFetcher:
        """
        Build a fetcher by name.

        Args:
            source_type: registered name, e.g. "hackernews" / "rss" / "github".
            transformer: ArticleTransformer to inject.
            storage: ArticleStorage to inject.
            **kwargs: extra args for specific fetchers (RSS needs feed_url).

        Raises:
            ValueError: if source_type is unknown, or RSS is missing feed_url.
        """
        if source_type not in cls._fetchers:
            available = ", ".join(cls._fetchers)
            raise ValueError(
                f"Unknown fetcher type: {source_type}. Available: {available}"
            )

        fetcher_class = cls._fetchers[source_type]

        # RSS has a different constructor: it needs the feed URL first.
        if source_type == "rss":
            feed_url = kwargs.get("feed_url")
            if not feed_url:
                raise ValueError("RSS fetcher requires a 'feed_url' argument")
            return fetcher_class(feed_url, transformer, storage)

        # Every other fetcher takes (transformer, storage).
        return fetcher_class(transformer, storage)

    @classmethod
    def register(cls, name: str, fetcher_class: Type[BaseFetcher]) -> None:
        """Add a new fetcher type at runtime (extend without editing the factory)."""
        cls._fetchers[name] = fetcher_class

    @classmethod
    def get_available_types(cls) -> List[str]:
        """List the names this factory can build."""
        return list(cls._fetchers)

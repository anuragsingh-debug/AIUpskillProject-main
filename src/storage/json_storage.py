"""Save articles to JSON files."""

import json
from typing import List
from pathlib import Path
from datetime import datetime
from dataclasses import asdict
from src.models.article import Article
from src.storage.base_storage import ArticleStorage


class JSONStorage(ArticleStorage):
    """
    Saves articles to JSON files.

    A second implementation of the ArticleStorage interface. Proves Dependency
    Inversion: this can be dropped in anywhere MarkdownStorage was used, without
    changing a single fetcher or the orchestrator.
    """

    def __init__(self, base_path: str = "data/articles"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save(self, articles: List[Article], filename: str = None) -> Path:
        """Write articles to a JSON file and return its path."""
        if filename is None:
            date_str = datetime.now().strftime("%Y-%m-%d")
            filename = f"articles_{date_str}.json"

        # Same contract as MarkdownStorage, but JSON wants a .json file.
        if filename.endswith(".md"):
            filename = filename[:-3] + ".json"

        filepath = self.base_path / filename

        # Turn each Article dataclass into a plain dict; datetime isn't JSON-safe,
        # so default=str converts published_at to a string.
        payload = [asdict(article) for article in articles]

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False, default=str)

        return filepath

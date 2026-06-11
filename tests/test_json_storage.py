# tests/test_json_storage.py
import json
import tempfile
from datetime import datetime

from src.models.article import Article
from src.storage.base_storage import ArticleStorage
from src.storage.json_storage import JSONStorage


def test_json_storage_is_article_storage():
    """JSONStorage must honour the ArticleStorage contract (DIP / LSP)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = JSONStorage(tmpdir)
        # It can be used anywhere an ArticleStorage is expected.
        assert isinstance(storage, ArticleStorage)


def test_json_storage_save():
    """Saving writes a valid JSON file containing the article's fields."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = JSONStorage(tmpdir)

        article = Article(
            title="Test",
            url="https://test.com",
            published_at=datetime.now(),
            source="test",
        )

        path = storage.save([article], "test.json")

        assert path.exists()
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert len(payload) == 1
        assert payload[0]["title"] == "Test"
        assert payload[0]["url"] == "https://test.com"


def test_json_storage_rewrites_md_extension():
    """A .md filename is coerced to .json so the contract stays drop-in."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = JSONStorage(tmpdir)

        article = Article("A", "https://a.com", datetime.now(), "test")
        path = storage.save([article], "articles.md")

        assert path.suffix == ".json"
        assert path.name == "articles.json"


def test_json_storage_multiple_articles():
    """Saving many articles serialises every one of them."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = JSONStorage(tmpdir)

        articles = [
            Article(f"Article {i}", f"https://test{i}.com", datetime.now(), "test")
            for i in range(5)
        ]

        path = storage.save(articles)
        payload = json.loads(path.read_text(encoding="utf-8"))

        titles = [item["title"] for item in payload]
        assert titles == [f"Article {i}" for i in range(5)]

# tests/test_orchestrator.py
import pytest
from src.orchestrator import FetchOrchestrator
from src.transformers.article_transformer import ArticleTransformer
from src.storage.markdown_storage import MarkdownStorage


@pytest.mark.asyncio
async def test_orchestrator_fetch_all():
    """Test orchestrator fetches from all sources."""
    # Inject the dependencies (Dependency Inversion).
    orchestrator = FetchOrchestrator(ArticleTransformer(), MarkdownStorage())
    articles = await orchestrator.fetch_all()

    # Should get some articles
    assert len(articles) > 0

    # Should have different sources
    sources = {a.source for a in articles}
    assert len(sources) > 1

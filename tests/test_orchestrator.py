# tests/test_orchestrator.py
import pytest
from src.orchestrator import FetchOrchestrator


@pytest.mark.asyncio
async def test_orchestrator_fetch_all():
    """Test orchestrator fetches from all sources."""
    orchestrator = FetchOrchestrator()
    articles = await orchestrator.fetch_all()

    # Should get some articles
    assert len(articles) > 0

    # Should have different sources
    sources = {a.source for a in articles}
    assert len(sources) > 1

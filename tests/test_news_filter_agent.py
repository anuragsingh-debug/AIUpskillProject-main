"""Tests for NewsFilterAgent and the agent tools.

These are MOCKED + offline by design: we never fire a real LLM call. The agent's
`_call_llm` is patched with a deterministic stand-in, so the tests are fast,
free, and repeatable (same discipline as the M2 mocked orchestrator tests —
"mock the real call path", and never let a test hit the live network/LLM).
"""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.agents.news_filter_agent import NewsFilterAgent
from src.tools.calculator import calculator
from src.tools.web_search import web_search


# A tiny articles file in exactly the markdown shape the parser expects.
SAMPLE_MD = """# Articles

## GPT-5 Released by OpenAI

**URL:** https://example.com/gpt5

OpenAI announces GPT-5 with major reasoning improvements.

---

## New JavaScript Framework Launched

**URL:** https://example.com/js

A React alternative for building web apps.
"""


@pytest.fixture(autouse=True)
def _set_model(monkeypatch):
    """Ensure BaseAgent.__init__ has a model so it doesn't raise.

    The value is irrelevant — every test mocks `_call_llm`, so no real LLM
    call is ever made with it.
    """
    monkeypatch.setenv("LITELLM_MODEL", "gemini/test-model")


def _fake_llm(prompt, system=None):
    """Deterministic stand-in for the LLM.

    Keys off "GPT-5" — which appears ONLY in the real AI article's title, not in
    the prompt's few-shot examples (those use "GPT-4" / "JavaScript"). So the AI
    article is judged relevant, the other not. Returns a JSON string like the
    real LLM does.
    """
    if "GPT-5" in prompt:
        return json.dumps({
            "relevant": True, "relevance_score": 9,
            "reasoning": "Discusses an LLM", "key_topics": ["LLM"],
        })
    return json.dumps({
        "relevant": False, "relevance_score": 2,
        "reasoning": "Web dev, not AI", "key_topics": [],
    })


# ---------------------------------------------------------------------------
# Tool tests (no LLM involved at all)
# ---------------------------------------------------------------------------

def test_calculator_tool():
    result = calculator("10 * 5 + 3")
    assert result["success"] is True
    assert result["result"] == 53


def test_calculator_handles_bad_input():
    result = calculator("not math")
    assert result["success"] is False


def test_web_search_tool_returns_results():
    result = web_search("AI news", num_results=3)
    assert result["success"] is True
    assert len(result["results"]) == 3


# ---------------------------------------------------------------------------
# Agent tests (LLM mocked)
# ---------------------------------------------------------------------------

def test_parse_markdown_extracts_articles():
    agent = NewsFilterAgent()
    articles = agent._parse_markdown(SAMPLE_MD)
    assert len(articles) == 2
    assert {a["title"] for a in articles} == {
        "GPT-5 Released by OpenAI",
        "New JavaScript Framework Launched",
    }


@pytest.mark.asyncio
async def test_agent_keeps_ai_and_bins_non_ai():
    """End-to-end execute(): AI article kept, JS article binned — all offline."""
    with tempfile.TemporaryDirectory() as tmp:
        input_file = Path(tmp) / "in.md"
        output_file = Path(tmp) / "out.md"
        input_file.write_text(SAMPLE_MD, encoding="utf-8")

        agent = NewsFilterAgent()
        with patch.object(agent, "_call_llm", side_effect=_fake_llm):
            result = await agent.execute(str(input_file), str(output_file))

        assert result["success"] is True
        assert output_file.exists()

        content = output_file.read_text(encoding="utf-8")
        assert "GPT-5" in content            # AI article kept
        assert "JavaScript" not in content   # non-AI article binned
        assert "**Total Output:** 1" in content


@pytest.mark.asyncio
async def test_failed_llm_call_does_not_keep_article():
    """If the LLM call raises, the article is not kept (graceful degradation)."""
    article_md = """## Some AI Article

**URL:** https://example.com/x

About neural networks.
"""
    with tempfile.TemporaryDirectory() as tmp:
        input_file = Path(tmp) / "in.md"
        output_file = Path(tmp) / "out.md"
        input_file.write_text(article_md, encoding="utf-8")

        agent = NewsFilterAgent()
        with patch.object(agent, "_call_llm", side_effect=RuntimeError("LLM down")):
            await agent.execute(str(input_file), str(output_file))

        content = output_file.read_text(encoding="utf-8")
        assert "**Total Output:** 0" in content

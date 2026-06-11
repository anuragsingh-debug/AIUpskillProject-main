"""Tests for NewsFilterAgent, the agent tools, and the rate-limit / error-handling
behaviour added for challenges E6 / E7 / E9.

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

from src.agents.base_agent import DailyQuotaExceeded
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
        return json.dumps(
            {
                "relevant": True,
                "relevance_score": 9,
                "reasoning": "Discusses an LLM",
                "key_topics": ["LLM"],
            }
        )
    return json.dumps(
        {
            "relevant": False,
            "relevance_score": 2,
            "reasoning": "Web dev, not AI",
            "key_topics": [],
        }
    )


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
# Parsing / happy-path agent tests (LLM mocked)
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
        assert "GPT-5" in content  # AI article kept
        assert "JavaScript" not in content  # non-AI article binned
        assert "**Total Output:** 1" in content


# ---------------------------------------------------------------------------
# Keyword pre-filter — skip obviously-non-AI articles BEFORE spending an LLM call
# ---------------------------------------------------------------------------


def test_looks_ai_relevant_matches_ai_and_skips_non_ai():
    """The cheap keyword check flags AI titles and ignores non-AI ones, with word
    boundaries so 'ai' inside 'training' does NOT count as a match."""
    agent = NewsFilterAgent()
    assert agent._looks_ai_relevant({"title": "GPT-5 Released by OpenAI", "summary": ""})
    assert agent._looks_ai_relevant({"title": "A new neural network", "summary": ""})
    assert not agent._looks_ai_relevant(
        {"title": "New JavaScript Framework", "summary": "A React alternative."}
    )
    # 'training' / 'email' must NOT trip the bare-'ai' pattern.
    assert not agent._looks_ai_relevant(
        {"title": "Email training for staff", "summary": "Office productivity tips."}
    )


@pytest.mark.asyncio
async def test_prefilter_skips_non_ai_without_an_llm_call():
    """With the pre-filter ON, a non-AI article is rejected up front and never
    reaches the LLM (so it is neither output nor errored)."""
    with tempfile.TemporaryDirectory() as tmp:
        input_file = Path(tmp) / "in.md"
        input_file.write_text(SAMPLE_MD, encoding="utf-8")

        agent = NewsFilterAgent()  # pre-filter ON by default
        with patch.object(agent, "_call_llm", side_effect=_fake_llm) as mock_llm:
            ctx = await agent._load_context(str(input_file))
            result = await agent._process(ctx)

        # GPT-5 (AI) judged and kept; JS article skipped before any LLM call.
        assert result["total_output"] == 1
        assert result["total_errored"] == 0
        # The non-AI article never reached the LLM: every prompt sent was about
        # the GPT-5 candidate, and none mentioned the JavaScript article.
        prompts = [call.args[0] for call in mock_llm.call_args_list]
        assert prompts  # the AI candidate WAS judged
        assert all("JavaScript" not in p for p in prompts)
        assert any("GPT-5" in p for p in prompts)


# ---------------------------------------------------------------------------
# E7 — honest error handling: a failed call is NOT a "not relevant" verdict
# ---------------------------------------------------------------------------


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


@pytest.mark.asyncio
async def test_error_is_set_aside_not_counted_as_rejection():
    """A failed judgement lands in the 'errored' bucket with score None — never
    a fake score 0 that looks like a real 'not relevant' verdict (E7)."""
    with tempfile.TemporaryDirectory() as tmp:
        input_file = Path(tmp) / "in.md"
        input_file.write_text(SAMPLE_MD, encoding="utf-8")

        agent = NewsFilterAgent()
        # Exercise the LLM error path for BOTH articles. The keyword pre-filter is
        # an orthogonal optimization (covered by its own test); turn it off here so
        # the non-AI article still reaches the LLM and lands in the errored bucket.
        agent.use_keyword_prefilter = False
        # Patch the *process* step's judge call so we can inspect its return dict.
        with patch.object(
            agent, "_call_llm", side_effect=RuntimeError("429 rate limit")
        ):
            ctx = await agent._load_context(str(input_file))
            result = await agent._process(ctx)

        # Both articles errored -> none kept, none rejected on merit.
        assert result["total_output"] == 0
        assert result["total_errored"] == 2
        assert all(a["error_type"] == "rate_limit" for a in result["errored_articles"])
        # Errored articles carry no misleading numeric score.
        assert all("relevance_score" not in a for a in result["errored_articles"])


# ---------------------------------------------------------------------------
# E9 — daily quota: stop the whole run, mark the rest un-judged (fail-fast)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_daily_quota_stops_run_and_marks_remaining():
    """When the per-day cap is hit, the run stops and every remaining article is
    marked 'daily_quota' — not silently rejected, and no further calls fired."""
    with tempfile.TemporaryDirectory() as tmp:
        input_file = Path(tmp) / "in.md"
        input_file.write_text(SAMPLE_MD, encoding="utf-8")

        agent = NewsFilterAgent()
        # Both articles must reach the LLM so the quota-stop marks them all; the
        # keyword pre-filter (tested separately) would otherwise skip the non-AI one.
        agent.use_keyword_prefilter = False
        with patch.object(
            agent,
            "_call_llm",
            side_effect=DailyQuotaExceeded("RequestsPerDay limit: 20"),
        ):
            ctx = await agent._load_context(str(input_file))
            result = await agent._process(ctx)

        assert result["stopped_early"] is True
        assert result["total_output"] == 0
        assert result["total_errored"] == 2
        assert all(a["error_type"] == "daily_quota" for a in result["errored_articles"])


def test_max_calls_per_run_budget_blocks_further_calls():
    """E9: the local per-run budget raises DailyQuotaExceeded once spent, so a
    run can deliberately stay under the free tier's ~20/day cap."""
    agent = NewsFilterAgent(max_calls_per_run=0)
    with pytest.raises(DailyQuotaExceeded):
        agent._check_budget()


def test_daily_quota_classifier():
    """The per-DAY 429 is recognised distinctly from a per-minute one."""
    assert NewsFilterAgent._is_daily_quota_error(
        Exception("GenerateRequestsPerDayPerProjectPerModel-FreeTier, limit: 20")
    )
    assert not NewsFilterAgent._is_daily_quota_error(Exception("429 per minute"))


# ---------------------------------------------------------------------------
# E6 — per-minute throttle paces calls without hitting the wall
# ---------------------------------------------------------------------------


def test_throttle_interval_from_requests_per_minute():
    agent = NewsFilterAgent(requests_per_minute=10)
    assert agent._min_interval == pytest.approx(6.0)


def test_throttle_sleeps_between_back_to_back_calls(monkeypatch):
    """The first call doesn't wait; a second, immediate call sleeps ~one interval.

    `time.sleep` is patched so the test is instant and deterministic.
    """
    slept = []
    monkeypatch.setattr("src.agents.base_agent.time.sleep", lambda s: slept.append(s))

    agent = NewsFilterAgent(requests_per_minute=8)  # interval = 7.5s
    agent._throttle()  # first call: nothing to wait for
    agent._throttle()  # immediately after: must pace
    assert slept and slept[-1] > 0


def test_throttle_disabled_when_rpm_zero(monkeypatch):
    slept = []
    monkeypatch.setattr("src.agents.base_agent.time.sleep", lambda s: slept.append(s))
    agent = NewsFilterAgent(requests_per_minute=0)
    agent._throttle()
    agent._throttle()
    assert slept == []

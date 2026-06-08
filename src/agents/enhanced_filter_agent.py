"""News filter agent with tool use."""

import json
from typing import Dict

from src.agents.base_agent import DailyQuotaExceeded
from src.agents.news_filter_agent import NewsFilterAgent
from src.tools.calculator import calculator, CALCULATOR_SCHEMA
from src.tools.web_search import web_search, WEB_SEARCH_SCHEMA


class EnhancedFilterAgent(NewsFilterAgent):
    """
    Filter agent that can use tools.

    Extends NewsFilterAgent with calculator and search.
    """

    def __init__(self, **kwargs):
        # Pass tools through to BaseAgent so they're sent on every LLM call, and
        # forward any other BaseAgent options (rate limit / budget / model).
        super().__init__(tools=[CALCULATOR_SCHEMA, WEB_SEARCH_SCHEMA], **kwargs)

        # Register the actual Python functions backing each tool schema.
        self.register_tool_function("calculator", calculator)
        self.register_tool_function("web_search", web_search)

    def _judge_relevance(self, article: Dict) -> Dict:
        """
        Judge relevance with tool access.

        LLM can now call calculator or search if needed.
        """
        prompt = f"""You are an AI/ML news analyst with access to tools.

Article:
Title: {article['title']}
Summary: {article['summary']}

Judge if this is AI/ML relevant. You can use:
- calculator: for any math calculations
- web_search: to verify claims or get context

Output JSON:
{{
  "relevant": true/false,
  "relevance_score": 1-10,
  "reasoning": "explanation (mention if you used tools)",
  "key_topics": ["topic1", "topic2"]
}}
"""

        try:
            # Use tool-enabled LLM call
            response = self._call_llm_with_tools(prompt)

            # Parse JSON (same as before)
            json_text = response
            if "```json" in response:
                json_text = response.split("```json")[1].split("```")[0]

            judgment = json.loads(json_text.strip())
            # Must match the parent contract: _process reads judgment['status'].
            judgment["status"] = "judged"
            return judgment

        except DailyQuotaExceeded:
            # E9: bubble up so _process stops the whole run (daily cap won't clear).
            raise
        except Exception as e:
            # E7: a failed call is NOT a "not relevant" verdict — mark it as an
            # error (score None) so _process sets it aside instead of binning it.
            msg = str(e)
            lower = msg.lower()
            is_rate_limit = (
                "429" in msg
                or "rate limit" in lower
                or "ratelimit" in lower
                or "quota" in lower
                or "resource_exhausted" in lower
            )
            print(f"      ⚠️  Could not judge: {e}")
            return {
                "status": "error",
                "error": msg,
                "error_type": "rate_limit" if is_rate_limit else "error",
                "relevant": None,
                "relevance_score": None,
                "reasoning": f"Could not judge: {e}",
                "key_topics": [],
            }

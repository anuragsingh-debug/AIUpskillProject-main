"""Scratch demo: prove the LLM actually CALLS our tools via the tool-call loop.

Single focused question (not the 43-article run) so it doesn't hit the
free-tier rate limit. Untracked smoke script — runs a live LLM call at import.
"""
from src.agents.base_agent import BaseAgent
from src.tools.calculator import calculator, CALCULATOR_SCHEMA
from src.tools.web_search import web_search, WEB_SEARCH_SCHEMA


class ToolDemoAgent(BaseAgent):
    """Minimal agent: only here to exercise _call_llm_with_tools."""

    def __init__(self):
        super().__init__(tools=[CALCULATOR_SCHEMA, WEB_SEARCH_SCHEMA])
        self.register_tool_function("calculator", calculator)
        self.register_tool_function("web_search", web_search)

    # The three abstract steps aren't used in this demo — no-op them.
    async def _load_context(self, input_path):
        return {}

    async def _process(self, context):
        return {}

    async def _save_result(self, result, output_path):
        pass


if __name__ == "__main__":
    agent = ToolDemoAgent()
    print("Asking a math question the LLM can't answer reliably alone...\n")
    answer = agent._call_llm_with_tools(
        "What is 23476 * 891? Use the calculator tool to be exact, "
        "then state the final number."
    )
    print(f"\n💬 Final answer from LLM:\n{answer}")

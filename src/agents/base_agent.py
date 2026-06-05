"""Base class for AI agents."""
import json
import os
import sys
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional

from litellm import completion

# LLM replies (and our own status prints) contain emoji/unicode, and Windows
# terminals default to cp1252 which can't encode them. Force UTF-8 once here so
# every agent that prints is safe.
sys.stdout.reconfigure(encoding="utf-8")


class BaseAgent(ABC):
    """
    Base class for all AI agents.

    Implements Template Method pattern:
    - execute() orchestrates the workflow
    - Subclasses implement specific steps
    """

    def __init__(
        self,
        model: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
    ):
        """
        Initialize agent.

        Args:
            model: LiteLLM model string. Defaults to LITELLM_MODEL from env.
            tools: Optional list of tool schemas (OpenAI / LiteLLM format) the
                LLM is allowed to call.
        """
        self.model = model or os.getenv("LITELLM_MODEL")
        if not self.model:
            raise ValueError(
                "No model configured. Set LITELLM_MODEL in .env "
                "or pass `model=` to the agent constructor."
            )
        # Tool schemas sent to the LLM (the "menu"), and the real Python
        # functions that back each schema name (the "kitchen").
        self.tools = tools or []
        self.tool_functions: Dict[str, Callable] = {}

    def register_tool_function(self, name: str, function: Callable) -> None:
        """Register the actual Python function backing a tool schema name."""
        self.tool_functions[name] = function

    async def execute(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """
        Execute agent workflow (Template Method).

        Steps:
        1. Load input context
        2. Process with LLM
        3. Save results

        Args:
            input_path: Path to input markdown file
            output_path: Path to save output

        Returns:
            Result metadata
        """
        print(f"\n🤖 {self.__class__.__name__} starting...")

        # Step 1: Load
        context = await self._load_context(input_path)

        # Step 2: Process
        result = await self._process(context)

        # Step 3: Save
        await self._save_result(result, output_path)

        print(f"✅ {self.__class__.__name__} complete")

        return {
            "input_path": input_path,
            "output_path": output_path,
            "success": True,
        }

    @abstractmethod
    async def _load_context(self, input_path: str) -> Dict[str, Any]:
        """Load input context. Subclasses implement how to read their input."""
        pass

    @abstractmethod
    async def _process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process context with LLM. Subclasses implement their specific logic."""
        pass

    @abstractmethod
    async def _save_result(self, result: Dict[str, Any], output_path: str):
        """Save processing result. Subclasses implement how to save their output."""
        pass

    def _call_llm(self, prompt: str, system: Optional[str] = None) -> str:
        """
        Call the configured LLM via LiteLLM.

        Helper method for subclasses.

        Args:
            prompt: User prompt.
            system: Optional system prompt.

        Returns:
            LLM response text.
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            response = completion(model=self.model, messages=messages)
            return response.choices[0].message.content
        except Exception as e:
            print(f"❌ LLM call failed: {e}")
            raise

    def _call_llm_with_tools(self, prompt: str, system: Optional[str] = None) -> str:
        """
        Call the LLM with tool support, looping until it returns plain text.

        Tool-call protocol (the "manager with a phone" loop):
          1. Send the prompt + the tool schemas.
          2. If the reply contains tool_calls, run each tool locally.
          3. Append the assistant turn + each tool result back into messages.
          4. Call the model again.
          5. Repeat until the model returns a normal text answer.

        Returns:
            The model's final text response.
        """
        messages: List[Dict] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        # Hard cap on rounds — protects against an infinite tool-call loop.
        for _ in range(10):
            response = completion(
                model=self.model,
                messages=messages,
                tools=self.tools or None,
            )
            msg = response.choices[0].message

            # No tool calls -> the model gave its final answer.
            if not getattr(msg, "tool_calls", None):
                return msg.content

            # Record the assistant turn (must come before the tool results).
            messages.append(msg.model_dump())

            # Execute each requested tool and feed its result back.
            for tool_call in msg.tool_calls:
                name = tool_call.function.name
                args = json.loads(tool_call.function.arguments or "{}")
                print(f"   🔧 Tool call: {name}({args})")

                if name not in self.tool_functions:
                    raise ValueError(f"Tool {name!r} not registered")

                result = self.tool_functions[name](**args)
                print(f"   📊 Tool result: {result}")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": name,
                    "content": json.dumps(result),
                })

        raise RuntimeError("Tool-call loop exceeded 10 rounds — model is stuck.")
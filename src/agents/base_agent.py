"""Base class for AI agents."""

import json
import os
import sys
import time
import warnings
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional

from litellm import completion

# LLM replies (and our own status prints) contain emoji/unicode, and Windows
# terminals default to cp1252 which can't encode them. Force UTF-8 once here so
# every agent that prints is safe.
sys.stdout.reconfigure(encoding="utf-8")

# litellm 1.55 + a local Ollama model emit a noisy Pydantic UserWarning on EVERY
# call ("Pydantic serializer warnings: ... Expected 5 fields but got 4"): Ollama's
# response Message simply has fewer fields than litellm's model declares. It is
# purely cosmetic — the returned `.content` is unaffected — but it prints multiple
# times per pipeline run and buries the real output. Silence just that one warning;
# all other warnings still surface.
warnings.filterwarnings(
    "ignore",
    message=r"Pydantic serializer warnings",
    category=UserWarning,
)


class DailyQuotaExceeded(Exception):
    """Raised when the provider's per-DAY request cap (or our own per-run call
    budget) is hit.

    This is deliberately distinct from an ordinary per-minute 429: a per-minute
    limit clears in seconds (so spacing calls fixes it — see E6), but the daily
    cap will not clear until the quota resets (~midnight PT). Callers should
    therefore STOP the run rather than retry or mark each article individually.
    """


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
        requests_per_minute: int = 8,
        max_calls_per_run: Optional[int] = None,
    ):
        """
        Initialize agent.

        Args:
            model: LiteLLM model string. Defaults to LITELLM_MODEL from env.
            tools: Optional list of tool schemas (OpenAI / LiteLLM format) the
                LLM is allowed to call.
            requests_per_minute: E6 per-minute throttle. The free tier allows
                ~10 LLM calls/min; we pace to 8 by default (a safety margin) by
                enforcing a minimum gap between calls. Set to 0 to disable.
            max_calls_per_run: E9 per-run budget. The free tier ALSO caps ~20
                calls/DAY, which no throttle can dodge. Setting e.g. 15 makes a
                run stop itself before burning the daily cap. None = no cap.
        """
        self.model = model or os.getenv("LITELLM_MODEL")
        if not self.model:
            raise ValueError(
                "No model configured. Set LITELLM_MODEL in .env "
                "or pass `model=` to the agent constructor."
            )
        # A local Ollama model ("ollama/..." or "ollama_chat/...") runs on THIS
        # machine: there is no provider, so there is no per-minute rate limit and
        # no per-DAY quota. The E6 throttle and E9 budget below exist ONLY to keep
        # us under a hosted free tier — applying them to a local model would just
        # make us sleep ~7.5s before every call for a limit that doesn't exist.
        # So when the model is local we neutralize both automatically. (Switching
        # `.env` back to gemini/... silently restores the hosted-tier behavior.)
        self._is_local = self.model.startswith(("ollama/", "ollama_chat/"))
        if self._is_local:
            requests_per_minute = 0      # no per-minute limit locally → no pacing
            max_calls_per_run = None     # no daily cap locally → no run budget

        # Tool schemas sent to the LLM (the "menu"), and the real Python
        # functions that back each schema name (the "kitchen").
        self.tools = tools or []
        self.tool_functions: Dict[str, Callable] = {}

        # E6 — per-minute throttle. The agent loop is serial, so a simple
        # "minimum gap between calls" is enough; no async semaphore needed in
        # this synchronous call path (cf. the M1/M2 fetcher's SemaphoreStrategy).
        self.requests_per_minute = requests_per_minute
        self._min_interval = 60.0 / requests_per_minute if requests_per_minute else 0.0
        self._last_call_at = 0.0

        # E9 — optional local cap to stay under the provider's daily quota.
        self.max_calls_per_run = max_calls_per_run
        self._calls_made = 0

        # Per-call options passed ONLY to a local Ollama model. On a CPU (no GPU
        # here) the two biggest, safest speedups are:
        #   • num_ctx — Ollama allocates a KV cache for the FULL context window
        #     regardless of how much we actually use. Its default for this model
        #     is 32768; our largest prompt (the batched filter) is ~5k tokens, so
        #     8192 covers every agent with headroom while shrinking that cache ~4x.
        #   • keep_alive — without it Ollama unloads the model between calls and
        #     pays the multi-second reload cost on the NEXT call. Pinning it
        #     resident for 30m keeps the whole pipeline warm.
        # These are no-ops for hosted models, so we only attach them when local.
        self._llm_options: Dict[str, Any] = {}
        if self._is_local:
            self._llm_options = {
                "num_ctx": 8192,
                "keep_alive": "30m",
                # temperature=0 makes judging DETERMINISTIC. Relevance filtering
                # is a yes/no classification, not creative writing — Ollama's
                # default 0.8 adds randomness that makes a small model give the
                # SAME article different scores on different runs (we saw "Rich
                # Sutton" score 8 then 7). Zero removes that noise: same input ->
                # same verdict, and measurably better recall on the golden set.
                "temperature": 0,
            }

    def register_tool_function(self, name: str, function: Callable) -> None:
        """Register the actual Python function backing a tool schema name."""
        self.tool_functions[name] = function

    def _throttle(self) -> None:
        """E6: sleep just long enough to keep LLM calls under the per-minute rate."""
        if self._min_interval <= 0:
            return
        gap = self._min_interval - (time.monotonic() - self._last_call_at)
        if gap > 0:
            print(
                f"   ⏳ Pacing LLM calls: waiting {gap:.1f}s (≤{self.requests_per_minute}/min)"
            )
            time.sleep(gap)
        self._last_call_at = time.monotonic()

    def _check_budget(self) -> None:
        """E9: stop before calling if this run's local LLM-call budget is spent."""
        if (
            self.max_calls_per_run is not None
            and self._calls_made >= self.max_calls_per_run
        ):
            raise DailyQuotaExceeded(
                f"Local per-run budget of {self.max_calls_per_run} LLM calls reached "
                f"(set to stay under the free tier's ~20/day cap)."
            )

    @staticmethod
    def _is_daily_quota_error(err: Exception) -> bool:
        """True when a 429 names the per-DAY quota (vs the recoverable per-minute one)."""
        msg = str(err).lower()
        return (
            "perday" in msg
            or "per day" in msg
            or "requests per day" in msg
            or "generaterequestsperdayperprojectpermodel" in msg
        )

    @staticmethod
    def _is_transient_error(err: Exception) -> bool:
        """True for transient provider-side failures worth a quick retry.

        These are server hiccups (HTTP 5xx / overloaded), NOT client problems
        like a bad request or a quota cap — retrying those would only waste
        calls. A 500 "internal error" from Gemini is the classic case.
        """
        msg = str(err).lower()
        name = err.__class__.__name__.lower()
        return (
            "internalservererror" in name
            or "serviceunavailable" in name
            or 'code": 500' in msg
            or 'code": 503' in msg
            or "internal error" in msg
            or "overloaded" in msg
            or "try again" in msg
        )

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

        self._check_budget()  # E9: respect the per-run cap before spending a call
        self._throttle()  # E6: pace under the per-minute limit

        # Retry transient server-side 5xx errors a couple of times with a short
        # backoff; a daily-quota 429 is never retried (it won't clear today).
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                response = completion(
                    model=self.model, messages=messages, **self._llm_options
                )
                self._calls_made += 1
                return response.choices[0].message.content
            except Exception as e:
                # E9: a per-DAY 429 won't clear on retry — re-raise as a distinct
                # type so callers stop the run instead of treating it per-article.
                if self._is_daily_quota_error(e):
                    raise DailyQuotaExceeded(str(e)) from e
                if self._is_transient_error(e) and attempt < max_attempts - 1:
                    wait = 2**attempt  # 1s, then 2s
                    print(
                        f"   ⚠️ Transient LLM error ({e.__class__.__name__}); "
                        f"retry {attempt + 1}/{max_attempts - 1} in {wait}s"
                    )
                    time.sleep(wait)
                    continue
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
            self._check_budget()  # E9: per-run cap
            self._throttle()  # E6: per-minute pacing
            try:
                response = completion(
                    model=self.model,
                    messages=messages,
                    tools=self.tools or None,
                    **self._llm_options,
                )
                self._calls_made += 1
            except Exception as e:
                if self._is_daily_quota_error(e):
                    raise DailyQuotaExceeded(str(e)) from e
                raise
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

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": name,
                        "content": json.dumps(result),
                    }
                )

        raise RuntimeError("Tool-call loop exceeded 10 rounds — model is stuck.")

"""Agent that filters AI-relevant articles."""

import json
from typing import Dict, Any, List
from pathlib import Path
from src.agents.base_agent import BaseAgent, DailyQuotaExceeded
import re


class NewsFilterAgent(BaseAgent):
    """
    Filters articles for AI/ML relevance.

    Reads articles from markdown, uses LLM to judge relevance,
    saves filtered articles.
    """

    def __init__(self, tools=None, **kwargs):
        # Forward `tools` AND any BaseAgent options (requests_per_minute,
        # max_calls_per_run, model, ...) up through this middle class — the E8
        # lesson: a class in the middle of an inheritance chain must pass through
        # every argument it doesn't itself consume.
        super().__init__(tools=tools, **kwargs)
        self.relevance_threshold = 6  # Out of 10

    async def _load_context(self, input_path: str) -> Dict[str, Any]:
        """
        Load articles from markdown file.

        Args:
            input_path: Path to markdown file with articles

        Returns:
            Dict with articles list
        """
        print(f"📖 Loading articles from {input_path}")

        # Read markdown file
        content = Path(input_path).read_text(encoding="utf-8")

        # Parse articles (simple parsing)
        articles = self._parse_markdown(content)

        print(f"   Found {len(articles)} articles")
        return {"articles": articles}

    def _parse_markdown(self, content: str) -> List[Dict]:
        """Parse markdown content to extract articles."""
        articles = []

        # Split by article separator
        sections = content.split("---")

        for section in sections:
            if "##" not in section:
                continue

            # Extract title (line starting with ##)
            title_match = re.search(r"## (.+)", section)
            if not title_match:
                continue

            title = title_match.group(1).strip()

            # Extract URL
            url_match = re.search(r"\*\*URL:\*\* (.+)", section)
            url = url_match.group(1).strip() if url_match else ""

            # Extract summary (last paragraph)
            lines = [
                ln
                for ln in section.split("\n")
                if ln.strip() and not ln.startswith("**")
            ]
            summary = lines[-1] if lines else ""

            articles.append({"title": title, "url": url, "summary": summary})

        return articles

    async def _process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter articles using LLM.

        Args:
            context: Dict with articles

        Returns:
            Dict with filtered articles and metadata
        """
        articles = context["articles"]
        print(f"🔍 Filtering {len(articles)} articles...")

        filtered = []
        errored = []

        stopped_early = False
        for i, article in enumerate(articles):
            print(f"   [{i+1}/{len(articles)}] {article['title'][:50]}...")

            # Ask LLM to judge relevance
            try:
                judgment = self._judge_relevance(article)
            except DailyQuotaExceeded as e:
                # E9: the daily cap won't clear until reset — stop now and mark
                # this article + every remaining one as un-judged (honest, E7),
                # instead of firing 30 more calls that would all 429.
                remaining = articles[i:]
                print(
                    f"   🛑 Daily quota hit — stopping. "
                    f"{len(remaining)} article(s) left un-judged."
                )
                for art in remaining:
                    errored.append(
                        {**art, "error": str(e), "error_type": "daily_quota"}
                    )
                stopped_early = True
                break

            # A failed call is NOT a verdict — we never got an answer, so it must
            # not masquerade as "not relevant". Set it aside in its own bucket.
            if judgment["status"] == "error":
                errored.append(
                    {
                        **article,
                        "error": judgment["error"],
                        "error_type": judgment["error_type"],
                    }
                )
                continue

            if (
                judgment["relevant"]
                and judgment["relevance_score"] >= self.relevance_threshold
            ):
                filtered.append(
                    {
                        **article,
                        "relevance_score": judgment["relevance_score"],
                        "reasoning": judgment["reasoning"],
                        "key_topics": judgment.get("key_topics", []),
                    }
                )
                print(f"      ✅ Relevant (score: {judgment['relevance_score']})")
            else:
                print(f"      ❌ Not relevant (score: {judgment['relevance_score']})")

        judged = len(articles) - len(errored)
        print(f"\n📊 Filtered: {len(filtered)}/{judged} judged articles relevant")
        if errored:
            print(
                f"⚠️  {len(errored)} article(s) could not be judged "
                f"(set aside, NOT counted as a verdict)"
            )

        return {
            "filtered_articles": filtered,
            "errored_articles": errored,
            "total_input": len(articles),
            "total_output": len(filtered),
            "total_errored": len(errored),
            "stopped_early": stopped_early,
        }

    def _judge_relevance(self, article: Dict) -> Dict:
        """
        Use LLM to judge article relevance.

        Args:
            article: Article dict with title, url, summary

        Returns:
            Dict with relevant, relevance_score, reasoning
        """
        prompt = f"""You are an expert AI/ML news analyst. Judge if this article is relevant to AI/ML.

Article:
Title: {article['title']}
Summary: {article['summary']}

Relevant topics include: Machine Learning, LLMs, Neural Networks, Computer Vision, NLP, AI Research, AI Applications, Deep Learning, Transformers, GPT, Stable Diffusion, AI Ethics, AI Safety

Output ONLY valid JSON with this exact format:
{{
  "relevant": true or false,
  "relevance_score": 1-10,
  "reasoning": "brief explanation",
  "key_topics": ["topic1", "topic2"]
}}

Examples:
- "GPT-4 Released" -> {{"relevant": true, "relevance_score": 10, "reasoning": "Major LLM release", "key_topics": ["LLM", "GPT"]}}
- "New JavaScript Framework" -> {{"relevant": false, "relevance_score": 1, "reasoning": "Web dev, not AI", "key_topics": []}}

Your JSON response:"""

        try:
            response = self._call_llm(prompt)

            # Extract JSON from response
            # LLM might wrap in ```json or similar
            json_text = response
            if "```json" in response:
                json_text = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_text = response.split("```")[1].split("```")[0]

            judgment = json.loads(json_text.strip())

            # Validate
            assert "relevant" in judgment
            assert "relevance_score" in judgment
            assert "reasoning" in judgment

            # The LLM actually answered — this is a real verdict we can trust.
            judgment["status"] = "judged"
            return judgment

        except DailyQuotaExceeded:
            # E9: do NOT swallow this as a per-article error — let it bubble up
            # to _process so the whole run stops (the daily cap won't recover).
            raise
        except Exception as e:
            # We never got a usable answer (rate limit / network / bad JSON).
            # This is NOT a verdict — do NOT record score 0, which would be
            # indistinguishable from a real "not AI" judgment. Mark it as an
            # error so _process can set it aside instead of silently binning it.
            msg = str(e)
            lower = msg.lower()
            is_rate_limit = (
                "429" in msg
                or "rate limit" in lower
                or "ratelimit" in lower
                or "quota" in lower
                or "resource_exhausted" in lower
            )
            error_type = "rate_limit" if is_rate_limit else "error"
            print(f"      ⚠️  Could not judge ({error_type}): {e}")
            return {
                "status": "error",
                "error": msg,
                "error_type": error_type,
                "relevant": None,
                "relevance_score": None,
                "reasoning": f"Could not judge: {e}",
                "key_topics": [],
            }

    async def _save_result(self, result: Dict[str, Any], output_path: str):
        """
        Save filtered articles to markdown.

        Args:
            result: Dict with filtered_articles
            output_path: Path to save markdown
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        articles = result["filtered_articles"]
        errored = result.get("errored_articles", [])
        total_input = result["total_input"]
        # Filter rate is meaningful only over articles we actually judged.
        judged = total_input - result.get("total_errored", 0)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("# Filtered AI/ML Articles\n\n")
            f.write(f"**Total Input:** {total_input}\n")
            f.write(f"**Total Output:** {result['total_output']}\n")
            f.write(f"**Could Not Judge:** {result.get('total_errored', 0)}\n")
            filter_rate = (result["total_output"] / judged * 100) if judged else 0.0
            f.write(f"**Filter Rate:** {filter_rate:.1f}% (of judged)\n\n")
            f.write("---\n\n")

            for article in articles:
                f.write(f"## {article['title']}\n\n")
                f.write(f"**URL:** {article['url']}\n")
                f.write(f"**Relevance Score:** {article['relevance_score']}/10\n")
                f.write(f"**Reasoning:** {article['reasoning']}\n")
                f.write(f"**Key Topics:** {', '.join(article['key_topics'])}\n\n")
                f.write(f"{article['summary']}\n\n")
                f.write("---\n\n")

            # Honest trail: articles we never actually judged (rate limit / error),
            # listed separately so they are not mistaken for "judged not relevant".
            if errored:
                f.write("## ⚠️ Could Not Be Judged\n\n")
                f.write(
                    "These were NOT judged (LLM error / rate limit) — neither kept "
                    "nor rejected on merit. Re-run them after the quota resets:\n\n"
                )
                for article in errored:
                    f.write(
                        f"- **{article['title']}** "
                        f"({article.get('error_type', 'error')}): "
                        f"{article.get('error', '')}\n"
                    )
                f.write("\n---\n\n")

        print(f"💾 Saved {len(articles)} filtered articles to {output_path}")
        if errored:
            print(f"   ⚠️  {len(errored)} could not be judged — listed in the report")

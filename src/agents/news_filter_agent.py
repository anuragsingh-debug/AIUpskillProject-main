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
        prompt = f"""You are an expert AI/ML news analyst. Decide whether this article is genuinely ABOUT artificial intelligence / machine learning.

Article:
Title: {article['title']}
Summary: {article['summary']}

DECISION RULE (read carefully):
An article is relevant ONLY if its MAIN SUBJECT is AI/ML itself — its research, models, techniques, algorithms, or a direct application of AI/ML to solve a problem. A topic is NOT relevant merely because AI is built with it, runs on it, or could use it. General software, programming languages, databases, containers, cloud services, DevOps/CI tools, networking, and consumer hardware are NOT AI/ML topics — even though AI systems are commonly built on top of them. When an article is only infrastructure or tooling that *could* support AI, it is NOT relevant.

Relevant AI/ML topics: Machine Learning, LLMs, Neural Networks, Computer Vision, NLP, AI Research, AI Applications, Deep Learning, Transformers, Generative AI, Reinforcement Learning, AI Ethics/Safety, model releases and benchmarks.

Scoring guide:
- 8-10: core AI/ML — model releases, research, novel architectures or techniques.
- 6-7: a clear real-world application of AI/ML, or AI governance/ethics.
- 4-5: AI mentioned only in passing or tangentially.
- 1-3: NOT about AI/ML — general software, infrastructure, hardware, or unrelated topics.
Set "relevant" to true ONLY when the score is 6 or higher.

Output ONLY valid JSON with this exact format:
{{
  "relevant": true or false,
  "relevance_score": 1-10,
  "reasoning": "brief explanation",
  "key_topics": ["topic1", "topic2"]
}}

Examples:
- "Researchers train a neural network to translate sign language in real time" -> {{"relevant": true, "relevance_score": 9, "reasoning": "Applied deep learning / computer vision", "key_topics": ["Neural Networks", "Computer Vision"]}}
- "Jenkins CI server adds new build pipeline plugins" -> {{"relevant": false, "relevance_score": 2, "reasoning": "DevOps tooling; may be used in ML ops but the article is not about AI", "key_topics": []}}
- "Local bakery wins national pastry award" -> {{"relevant": false, "relevance_score": 1, "reasoning": "Unrelated to AI", "key_topics": []}}

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

    def _judge_relevance_batch(self, articles: List[Dict]) -> List[Dict]:
        """
        Judge MANY articles in a SINGLE LLM call (one call, not one-per-article).

        --------------------------------------------------------------------
        REAL-WORLD PARALLEL: instead of handing the junior employee 20 articles
        ONE AT A TIME (20 trips to their desk = 20 LLM calls = 20 units of the
        daily quota), we hand over ALL 20 stapled together with the instruction
        "number your answers 1..20". ONE trip. ONE quota unit. Same junior, same
        grading rule — we only changed HOW MANY we ask per trip.
        --------------------------------------------------------------------

        The DECISION RULE / scoring / threshold here are IDENTICAL to
        `_judge_relevance` — nothing about how an article is judged changes. The
        only difference is batching, which is what lets the whole golden set fit
        inside one free-tier daily quota (the ~per-day cap a throttle can't dodge).

        Args:
            articles: list of dicts, each with at least `title` and `summary`.

        Returns:
            A list the SAME length and order as `articles`. Each item has the
            same shape `_judge_relevance` returns (relevant / relevance_score /
            reasoning / key_topics / status). If the batch reply can't be parsed
            into one verdict per article, raises so the caller stays honest
            rather than inventing verdicts.
        """
        # Number every article so the model can line its answers up 1:1 with ours.
        numbered = "\n\n".join(
            f"[{i + 1}]\nTitle: {a['title']}\nSummary: {a.get('summary', '')}"
            for i, a in enumerate(articles)
        )

        # Same decision rule + scoring guide as the single-article path — only the
        # output shape changes (a JSON ARRAY, one object per numbered article).
        prompt = f"""You are an expert AI/ML news analyst. For EACH numbered article below, decide whether it is genuinely ABOUT artificial intelligence / machine learning.

DECISION RULE (read carefully):
An article is relevant ONLY if its MAIN SUBJECT is AI/ML itself — its research, models, techniques, algorithms, or a direct application of AI/ML to solve a problem. A topic is NOT relevant merely because AI is built with it, runs on it, or could use it. General software, programming languages, databases, containers, cloud services, DevOps/CI tools, networking, and consumer hardware are NOT AI/ML topics — even though AI systems are commonly built on top of them. When an article is only infrastructure or tooling that *could* support AI, it is NOT relevant.

Relevant AI/ML topics: Machine Learning, LLMs, Neural Networks, Computer Vision, NLP, AI Research, AI Applications, Deep Learning, Transformers, Generative AI, Reinforcement Learning, AI Ethics/Safety, model releases and benchmarks.

Scoring guide:
- 8-10: core AI/ML — model releases, research, novel architectures or techniques.
- 6-7: a clear real-world application of AI/ML, or AI governance/ethics.
- 4-5: AI mentioned only in passing or tangentially.
- 1-3: NOT about AI/ML — general software, infrastructure, hardware, or unrelated topics.
Set "relevant" to true ONLY when the score is 6 or higher.

ARTICLES:
{numbered}

Output ONLY a valid JSON ARRAY with EXACTLY {len(articles)} objects, in the SAME ORDER as the articles above. Each object MUST have this format:
{{"relevant": true or false, "relevance_score": 1-10, "reasoning": "brief explanation", "key_topics": ["topic1", "topic2"]}}

Do not include the article number inside the objects and do not add any text outside the JSON array.

Your JSON array:"""

        # One LLM call for the whole batch. DailyQuotaExceeded (the per-day cap)
        # still bubbles straight up to the caller, exactly like the single path.
        response = self._call_llm(prompt)

        # The model may wrap the array in ```json fences — strip them if present.
        json_text = response
        if "```json" in response:
            json_text = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            json_text = response.split("```")[1].split("```")[0]

        # Be forgiving about leading/trailing prose: slice from the first '[' to
        # the last ']' so a stray sentence around the array doesn't break parsing.
        text = json_text.strip()
        start, end = text.find("["), text.rfind("]")
        if start != -1 and end != -1 and end > start:
            text = text[start : end + 1]

        judgments = json.loads(text)

        # Measure-don't-trust: a batch reply is only usable if it gives EXACTLY
        # one verdict per article in order. Anything else and we refuse to guess.
        if not isinstance(judgments, list) or len(judgments) != len(articles):
            raise ValueError(
                f"Batch judge returned {len(judgments) if isinstance(judgments, list) else 'non-list'} "
                f"verdict(s) for {len(articles)} article(s) — refusing to misalign them."
            )

        cleaned: List[Dict] = []
        for j in judgments:
            # Same minimal validation the single-article path does.
            assert "relevant" in j
            assert "relevance_score" in j
            assert "reasoning" in j
            j.setdefault("key_topics", [])
            j["status"] = "judged"  # a real verdict we can trust
            cleaned.append(j)
        return cleaned

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

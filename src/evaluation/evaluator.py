"""Evaluation framework for news filtering agent."""

import json
from pathlib import Path
from typing import Dict, List
from src.agents.base_agent import DailyQuotaExceeded
from src.agents.news_filter_agent import NewsFilterAgent
import asyncio


class FilterEvaluator:
    """
    Evaluates news filtering agent.

    Measures:
    - Accuracy (correct classification)
    - Precision (% of relevant that are actually relevant)
    - Recall (% of actual relevant found)
    """

    def __init__(self, golden_dataset_path: str):
        self.golden_dataset_path = Path(golden_dataset_path)
        self.agent = NewsFilterAgent()
        self.relevance_threshold = 6

    async def evaluate(self) -> Dict:
        """Run evaluation on golden dataset."""
        # Load golden dataset (UTF-8 — Windows defaults to cp1252; E2 boundary).
        with open(self.golden_dataset_path, encoding="utf-8") as f:
            dataset = json.load(f)

        test_cases = dataset["test_cases"]
        print(f"📊 Evaluating on {len(test_cases)} test cases...")

        results = []

        for test_case in test_cases:
            print(
                f"   [{test_case['id']}/{len(test_cases)}] {test_case['title'][:50]}..."
            )

            # Run agent. If the provider's per-DAY quota is hit (E9), stop the
            # run but keep the cases we already scored — a partial report beats
            # crashing and losing everything (same resilience as the summarizer).
            try:
                judgment = self.agent._judge_relevance(
                    {"title": test_case["title"], "summary": test_case["summary"]}
                )
            except DailyQuotaExceeded:
                print(
                    f"   🛑 Daily quota exhausted — stopping after "
                    f"{len(results)}/{len(test_cases)} cases. Re-run after reset."
                )
                break

            # Check prediction
            predicted_relevant = (
                judgment["relevant"]
                and judgment["relevance_score"] >= self.relevance_threshold
            )
            expected_relevant = test_case["expected_relevant"]

            correct = predicted_relevant == expected_relevant

            results.append(
                {
                    "test_case_id": test_case["id"],
                    "title": test_case["title"],
                    "expected": expected_relevant,
                    "predicted": predicted_relevant,
                    "correct": correct,
                    "score": judgment["relevance_score"],
                    "reasoning": judgment["reasoning"],
                }
            )

            status = "✅" if correct else "❌"
            print(
                f"      {status} Expected: {expected_relevant}, Predicted: {predicted_relevant}"
            )

        # Calculate metrics
        metrics = self._calculate_metrics(results)

        return {
            "results": results,
            "metrics": metrics,
            "test_cases": len(test_cases),
            "evaluated": len(results),
            "complete": len(results) == len(test_cases),
        }

    def _calculate_metrics(self, results: List[Dict]) -> Dict:
        """Calculate evaluation metrics."""
        # Guard: a fully quota-blocked run produces no results — don't divide by 0.
        if not results:
            return {
                "accuracy": 0,
                "precision": 0,
                "recall": 0,
                "f1_score": 0,
                "correct": 0,
                "total": 0,
            }

        # Accuracy
        correct = sum(1 for r in results if r["correct"])
        accuracy = correct / len(results)

        # Precision, Recall, F1
        true_positives = sum(1 for r in results if r["expected"] and r["predicted"])
        false_positives = sum(
            1 for r in results if not r["expected"] and r["predicted"]
        )
        false_negatives = sum(
            1 for r in results if r["expected"] and not r["predicted"]
        )

        precision = (
            true_positives / (true_positives + false_positives)
            if (true_positives + false_positives) > 0
            else 0
        )

        recall = (
            true_positives / (true_positives + false_negatives)
            if (true_positives + false_negatives) > 0
            else 0
        )

        f1 = (
            2 * (precision * recall) / (precision + recall)
            if (precision + recall) > 0
            else 0
        )

        return {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "correct": correct,
            "total": len(results),
        }

    async def save_report(self, evaluation: Dict, output_path: str):
        """Save evaluation report."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write UTF-8 — the agent's reasoning text can contain non-Latin / emoji
        # characters that crash on the cp1252 default (E2 on the file boundary).
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("# News Filter Agent - Evaluation Report\n\n")

            # Flag partial runs so a quota-truncated report can't be mistaken
            # for a full evaluation.
            if not evaluation.get("complete", True):
                f.write(
                    f"> ⚠️ **Partial run** — only "
                    f"{evaluation.get('evaluated', '?')}/{evaluation['test_cases']} "
                    f"cases evaluated (daily quota hit). Re-run after reset for full metrics.\n\n"
                )

            # Metrics
            metrics = evaluation["metrics"]
            f.write("## Overall Metrics\n\n")
            f.write(f"- **Accuracy:** {metrics['accuracy']:.1%}\n")
            f.write(f"- **Precision:** {metrics['precision']:.1%}\n")
            f.write(f"- **Recall:** {metrics['recall']:.1%}\n")
            f.write(f"- **F1 Score:** {metrics['f1_score']:.3f}\n")
            f.write(
                f"- **Test Cases:** {metrics['correct']}/{metrics['total']} correct\n\n"
            )

            # Results
            f.write("## Test Results\n\n")

            for result in evaluation["results"]:
                status = "✅ PASS" if result["correct"] else "❌ FAIL"
                f.write(f"### [{result['test_case_id']}] {status}\n\n")
                f.write(f"**Title:** {result['title']}\n\n")
                f.write(
                    f"- Expected: {'Relevant' if result['expected'] else 'Not Relevant'}\n"
                )
                f.write(
                    f"- Predicted: {'Relevant' if result['predicted'] else 'Not Relevant'} (score: {result['score']})\n"
                )
                f.write(f"- Reasoning: {result['reasoning']}\n\n")
                f.write("---\n\n")

        print(f"💾 Evaluation report saved to {output_path}")


# Run evaluation
async def run_evaluation():
    """Run evaluation and save report."""
    print("=" * 60)
    print("  News Filter Agent Evaluation")
    print("=" * 60)

    evaluator = FilterEvaluator("data/evaluation/golden_dataset.json")
    evaluation = await evaluator.evaluate()

    print("\n📊 Results:")
    print(f"   Accuracy:  {evaluation['metrics']['accuracy']:.1%}")
    print(f"   Precision: {evaluation['metrics']['precision']:.1%}")
    print(f"   Recall:    {evaluation['metrics']['recall']:.1%}")
    print(f"   F1 Score:  {evaluation['metrics']['f1_score']:.3f}")

    await evaluator.save_report(evaluation, "data/evaluation/evaluation_report.md")

    print("\n✅ Evaluation complete!")
    print("   Report: data/evaluation/evaluation_report.md")


if __name__ == "__main__":
    asyncio.run(run_evaluation())

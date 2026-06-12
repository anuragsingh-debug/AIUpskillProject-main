"""Evaluation framework for news filtering agent.

==========================================================================
PARALLEL EXAMPLE used in the comments below: "Grading a new hire"
--------------------------------------------------------------------------
Imagine a new junior employee whose ONE job is to look at a news article
and answer: "Is this about AI/ML? yes or no".

To test if they are good, we DON'T just trust them. We prepare an ANSWER
KEY: 20 articles where WE already know the right answer. We hand each one
to the junior, write down their answer, then compare against our key and
produce a REPORT CARD (accuracy / precision / recall / F1).

  - The junior employee      -> self.agent  (the real LLM filter agent)
  - The answer key           -> golden_dataset.json
  - The report card          -> evaluation_report.md
==========================================================================
"""

import json                                    # to read the answer key (a .json file)
from pathlib import Path                        # safe, OS-independent file paths
from typing import Dict, List                   # type hints (just documentation for shapes)
from src.agents.base_agent import DailyQuotaExceeded  # raised when LLM daily limit is hit
from src.agents.news_filter_agent import NewsFilterAgent  # the "junior employee" we test
import asyncio                                  # lets us run async functions (await)


class FilterEvaluator:
    """
    Evaluates news filtering agent.

    Measures:
    - Accuracy (correct classification)
    - Precision (% of relevant that are actually relevant)
    - Recall (% of actual relevant found)
    """

    def __init__(self, golden_dataset_path: str):
        # Remember WHERE the answer key lives (e.g. "data/evaluation/golden_dataset.json").
        self.golden_dataset_path = Path(golden_dataset_path)
        # Hire the junior we are about to test (the real LLM agent).
        self.agent = NewsFilterAgent()
        # The pass mark: the agent must score an article >= 6 to call it "relevant".
        self.relevance_threshold = 6

    async def evaluate(self) -> Dict:
        """Run evaluation on golden dataset."""
        # --- STEP 1: open the answer key file and load it into a Python dict. ---
        # encoding="utf-8" is REQUIRED: Windows defaults to cp1252 and would crash
        # on emoji / non-Latin characters inside the data (the "E2" boundary bug).
        with open(self.golden_dataset_path, encoding="utf-8") as f:
            dataset = json.load(f)

        # The JSON has a "test_cases" list -> the 20 graded questions on our answer key.
        test_cases = dataset["test_cases"]
        print(f"📊 Evaluating on {len(test_cases)} test cases...")

        # An empty notebook where we'll jot down how the junior did on each question.
        results = []

        # --- STEP 2: ASK the junior about ALL questions in ONE LLM call. ---
        # The whole golden set is handed over stapled together (one request, one
        # unit of the per-DAY quota) instead of 20 separate trips that would burn
        # 20 units and 429 partway through. The grading rule is unchanged — only
        # HOW MANY we ask per call changed, so the entire set fits one free quota.
        # If the per-DAY quota is already spent we don't crash: we keep an empty
        # (partial) report card rather than losing everything.
        cases = [
            {"title": tc["title"], "summary": tc["summary"]} for tc in test_cases
        ]
        try:
            if self.agent._is_local:
                # LOCAL model: there's no per-day quota to conserve, and a small
                # model is far more accurate judging ONE article at a time (it
                # gets the model's full attention plus the richer single-article
                # prompt, which carries more few-shot examples than the batch
                # prompt). Stapling 20 into one call made it lose calibration and
                # miss obvious AI articles (recall 54%). The extra calls are free
                # locally, so we spend them to buy accuracy.
                judgments = [self.agent._judge_relevance(c) for c in cases]
            else:
                # HOSTED free tier: staple the whole set into ONE call so the
                # entire evaluation fits inside a single per-DAY quota unit
                # (20 separate calls would burn 20 units and 429 partway through).
                judgments = self.agent._judge_relevance_batch(cases)
        except DailyQuotaExceeded:
            print(
                "   🛑 Daily quota exhausted before any case could be graded. "
                "Re-run after reset."
            )
            judgments = []  # nothing graded; metrics fall back to zeros below

        # --- STEP 3: grade each question against the one batched set of answers. ---
        for test_case, judgment in zip(test_cases, judgments):
            # Show which question we're on, e.g. "[3/20] Machine Learning in Health...".
            print(
                f"   [{test_case['id']}/{len(test_cases)}] {test_case['title'][:50]}..."
            )

            # --- STEP 4: turn the junior's answer into a clean yes/no. ---
            # The agent must say relevant=True AND give a score >= 6. Both, not either.
            # (Example: relevant=True but score=4 -> still counts as "No".)
            predicted_relevant = (
                judgment["relevant"]
                and judgment["relevance_score"] >= self.relevance_threshold
            )
            # The ground truth from the answer key: what the RIGHT answer actually is.
            expected_relevant = test_case["expected_relevant"]

            # --- STEP 5: GRADE it. Did the junior's answer match the answer key? ---
            correct = predicted_relevant == expected_relevant

            # Write this question's outcome into our notebook (for the report later).
            results.append(
                {
                    "test_case_id": test_case["id"],
                    "title": test_case["title"],
                    "expected": expected_relevant,      # right answer
                    "predicted": predicted_relevant,    # junior's answer
                    "correct": correct,                 # did they match?
                    "score": judgment["relevance_score"],   # the 0-10 score given
                    "reasoning": judgment["reasoning"],     # WHY the LLM decided that
                }
            )

            # Print a ✅ / ❌ next to this question so we can watch progress live.
            status = "✅" if correct else "❌"
            print(
                f"      {status} Expected: {expected_relevant}, Predicted: {predicted_relevant}"
            )

        # --- STEP 6: all questions done -> tally up the final REPORT CARD. ---
        metrics = self._calculate_metrics(results)

        # Hand back everything: per-question results + the summary metrics + counts.
        return {
            "results": results,
            "metrics": metrics,
            "test_cases": len(test_cases),                  # how many were on the key
            "evaluated": len(results),                      # how many we actually graded
            "complete": len(results) == len(test_cases),    # True only if we graded ALL
        }

    def _calculate_metrics(self, results: List[Dict]) -> Dict:
        """Calculate evaluation metrics."""
        # Safety net: if quota died before grading ANY question, there's nothing to
        # average — return zeros instead of crashing on a divide-by-zero.
        if not results:
            return {
                "accuracy": 0,
                "precision": 0,
                "recall": 0,
                "f1_score": 0,
                "correct": 0,
                "total": 0,
            }

        # --- ACCURACY = "how often was the junior right overall?" ---
        # Count the questions marked correct, divide by total graded.
        correct = sum(1 for r in results if r["correct"])
        accuracy = correct / len(results)

        # --- The four buckets every classification metric is built from. ---
        # TP: it IS AI, junior said AI            (correct catch)
        true_positives = sum(1 for r in results if r["expected"] and r["predicted"])
        # FP: it is NOT AI, junior wrongly said AI (false alarm)
        false_positives = sum(
            1 for r in results if not r["expected"] and r["predicted"]
        )
        # FN: it IS AI, junior missed it           (missed catch)
        false_negatives = sum(
            1 for r in results if r["expected"] and not r["predicted"]
        )

        # --- PRECISION = "when the junior SAYS AI, how often is it really AI?" ---
        # High precision = few false alarms. Guard against 0/0 if it never said "AI".
        precision = (
            true_positives / (true_positives + false_positives)
            if (true_positives + false_positives) > 0
            else 0
        )

        # --- RECALL = "of all the REAL AI articles, how many did the junior catch?" ---
        # High recall = few misses. Guard against 0/0 if there were no AI articles.
        recall = (
            true_positives / (true_positives + false_negatives)
            if (true_positives + false_negatives) > 0
            else 0
        )

        # --- F1 = single balanced score (harmonic mean of precision & recall). ---
        # It stays LOW unless BOTH are high — so the junior can't cheat by only
        # being cautious (high precision) or only being greedy (high recall).
        f1 = (
            2 * (precision * recall) / (precision + recall)
            if (precision + recall) > 0
            else 0
        )

        # Bundle the report card numbers together.
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
        # Where to write the human-readable report card (a Markdown file).
        output_path = Path(output_path)
        # Create the folder (e.g. data/evaluation/) if it doesn't exist yet.
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Open for writing as UTF-8 — the LLM's reasoning can contain emoji /
        # non-Latin text that would crash on Windows' cp1252 default (E2 bug).
        with open(output_path, "w", encoding="utf-8") as f:
            # Report title.
            f.write("# News Filter Agent - Evaluation Report\n\n")

            # If the run was cut short by quota, stamp a BIG warning at the top so
            # nobody mistakes a half-finished report for a full evaluation.
            if not evaluation.get("complete", True):
                f.write(
                    f"> ⚠️ **Partial run** — only "
                    f"{evaluation.get('evaluated', '?')}/{evaluation['test_cases']} "
                    f"cases evaluated (daily quota hit). Re-run after reset for full metrics.\n\n"
                )

            # --- Section 1: the headline numbers (the report card). ---
            metrics = evaluation["metrics"]
            f.write("## Overall Metrics\n\n")
            f.write(f"- **Accuracy:** {metrics['accuracy']:.1%}\n")    # .1% -> "90.0%"
            f.write(f"- **Precision:** {metrics['precision']:.1%}\n")
            f.write(f"- **Recall:** {metrics['recall']:.1%}\n")
            f.write(f"- **F1 Score:** {metrics['f1_score']:.3f}\n")    # .3f -> "0.923"
            f.write(
                f"- **Test Cases:** {metrics['correct']}/{metrics['total']} correct\n\n"
            )

            # --- Section 2: the detailed answer-by-answer breakdown. ---
            f.write("## Test Results\n\n")

            # Replay each graded question: pass/fail, the title, expected vs predicted,
            # and crucially the LLM's REASONING (so we can debug WHY it was wrong).
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
                f.write("---\n\n")  # divider between cases

        # Tell the user where the finished report card landed.
        print(f"💾 Evaluation report saved to {output_path}")


# ====================== The "press play" entry point ======================
async def run_evaluation(
    dataset_path: str = "data/evaluation/golden_dataset.json",
    report_path: str = "data/evaluation/evaluation_report.md",
):
    """Run evaluation and save report.

    Args default to the curated golden set, but either can be overridden so the
    SAME grader can score a different answer key (e.g. the harder real-world set
    built from actually-fetched articles) and write a separate report — without
    touching the curated baseline.
    """
    # Pretty header so the console output is easy to read.
    print("=" * 60)
    print("  News Filter Agent Evaluation")
    print(f"  Dataset: {dataset_path}")
    print("=" * 60)

    # 1) Create the grader, pointing it at the answer key.
    evaluator = FilterEvaluator(dataset_path)
    # 2) Run the whole grade-every-question loop (this is where LLM calls happen).
    evaluation = await evaluator.evaluate()

    # 3) Print the report card to the screen.
    print("\n📊 Results:")
    print(f"   Accuracy:  {evaluation['metrics']['accuracy']:.1%}")
    print(f"   Precision: {evaluation['metrics']['precision']:.1%}")
    print(f"   Recall:    {evaluation['metrics']['recall']:.1%}")
    print(f"   F1 Score:  {evaluation['metrics']['f1_score']:.3f}")

    # 4) Also save the full report card to a file for sharing / the project report.
    await evaluator.save_report(evaluation, report_path)

    print("\n✅ Evaluation complete!")
    print(f"   Report: {report_path}")

    # Hand the numbers back so a SUITE run can aggregate several datasets into one
    # combined summary (returns None-free dict; harmless for single-dataset callers).
    return evaluation


# The evaluation SUITE: every answer key we grade against, easiest first.
# The curated set is a textbook sanity check (clean, obvious headlines) — it is
# EXPECTED to hit ~100% and on its own proves almost nothing. The real-world set
# is messy live titles and is the number that actually reflects production
# quality. We always run BOTH so the flattering 100% never gets reported alone.
EVAL_SUITE = [
    {
        "name": "Curated (sanity check)",
        "dataset": "data/evaluation/golden_dataset.json",
        "report": "data/evaluation/evaluation_report.md",
        "trust": "low",   # easy/obvious cases — a floor, not the headline number
    },
    {
        "name": "Real-world (production signal)",
        "dataset": "data/evaluation/realworld_dataset.json",
        "report": "data/evaluation/evaluation_report_realworld.md",
        "trust": "high",  # messy live articles — THIS is the believable number
    },
]


async def run_suite(suite: List[Dict] = None):
    """Run the WHOLE evaluation suite and print one honest combined summary.

    Running only the curated set prints a lone "100%" that reads as naïve — no
    real classifier is perfect. So we grade every answer key in the suite and
    show them side by side, clearly labelling which number to actually trust.
    """
    suite = suite or EVAL_SUITE
    summary = []  # one row per dataset for the final leaderboard

    for entry in suite:
        # A missing dataset shouldn't kill the whole suite — skip it with a note.
        if not Path(entry["dataset"]).exists():
            print(f"\n⚠️  Skipping '{entry['name']}': {entry['dataset']} not found.")
            continue
        evaluation = await run_evaluation(entry["dataset"], entry["report"])
        summary.append({**entry, "metrics": evaluation["metrics"],
                        "complete": evaluation.get("complete", True)})

    # --- Combined leaderboard: every dataset's headline numbers in one place. ---
    print("\n" + "=" * 60)
    print("  COMBINED EVALUATION SUMMARY")
    print("=" * 60)
    for row in summary:
        m = row["metrics"]
        tag = "⭐ TRUST THIS" if row["trust"] == "high" else "🧪 sanity only"
        partial = "" if row["complete"] else "  (PARTIAL — quota hit)"
        print(f"\n  {row['name']}  [{tag}]{partial}")
        print(f"     Accuracy {m['accuracy']:.1%}   "
              f"Precision {m['precision']:.1%}   "
              f"Recall {m['recall']:.1%}   "
              f"F1 {m['f1_score']:.3f}   "
              f"({m['correct']}/{m['total']})")

    # A plain-language reminder so nobody quotes the curated 100% as THE result.
    print("\n  ℹ️  The curated set is a textbook sanity check and is expected to")
    print("     near 100%. Report the REAL-WORLD number as the project's accuracy.")
    print("=" * 60)
    return summary


# Only run when this file is launched directly (python -m src.evaluation.evaluator),
# NOT when it's imported by another module. asyncio.run(...) starts the async engine.
#   python -m src.evaluation.evaluator                     -> runs the FULL suite
#   python -m src.evaluation.evaluator <dataset> <report>  -> one specific answer key
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # Explicit dataset given: grade just that one (backward-compatible path).
        dataset = sys.argv[1]
        report = sys.argv[2] if len(sys.argv) > 2 else "data/evaluation/evaluation_report.md"
        asyncio.run(run_evaluation(dataset, report))
    else:
        # No args: run the whole suite so a lone, misleading 100% can't be the
        # only thing shown — the real-world number is always reported alongside.
        asyncio.run(run_suite())

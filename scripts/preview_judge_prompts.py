"""Preview the prompts the LLM judge would send for three representative cases.

Run from repo root::

    python scripts/preview_judge_prompts.py
"""
from __future__ import annotations

from evalkit.core.case import TestCase
from evalkit.evaluators.llm_judge import LLMJudgeEvaluator

SAMPLES = [
    {
        "label": "case A — clearly correct answer",
        "case": TestCase(
            id="cap_france",
            input="What is the capital of France?",
            expected="Paris",
            metadata={"category": "factual_lookup"},
        ),
        "actual": "The capital of France is Paris.",
    },
    {
        "label": "case B — partially correct (right city, wrong attribute)",
        "case": TestCase(
            id="cap_france_pop",
            input="What is the capital of France, and roughly how many people live there?",
            expected="Paris, around 2.1 million in the city proper.",
            metadata={"category": "factual_lookup"},
        ),
        "actual": "Paris is the capital. About 11 million people live in Paris.",
    },
    {
        "label": "case C — confidently wrong / hallucinated",
        "case": TestCase(
            id="rbi_loan_clf",
            input=(
                "Under RBI's Master Direction on Income Recognition (2024), how many days "
                "past due before a retail loan account is classified as NPA?"
            ),
            expected="90 days past due (DPD).",
            metadata={"category": "regulatory_lookup"},
        ),
        "actual": (
            "Per the RBI Master Direction, retail loan accounts must be classified as NPA "
            "after 30 days past due. This rule was tightened in 2024 to align with global "
            "standards under Basel III."
        ),
    },
]


def main() -> None:
    judge = LLMJudgeEvaluator(
        rubric=[
            {"name": "factual_accuracy",
             "description": "All factual claims are correct and traceable to the expected answer.",
             "weight": 3},
            {"name": "completeness",
             "description": "Every part of the input question is addressed.",
             "weight": 2},
            {"name": "calibration",
             "description": "The model expresses appropriate confidence (no hedging when correct, "
                            "no overconfidence when wrong).",
             "weight": 1},
        ],
        two_pass=True,
        pass_threshold=4.0,
    )
    print("=" * 80)
    print("SYSTEM PROMPT (sent on every judge call)")
    print("=" * 80)
    sys_msg, _ = judge.build_prompt(SAMPLES[0]["case"], "x")  # type: ignore[arg-type]
    print(sys_msg)
    print()
    for i, s in enumerate(SAMPLES, start=1):
        print("=" * 80)
        print(f"USER PROMPT — {s['label']}")
        print("=" * 80)
        _, user_msg = judge.build_prompt(s["case"], s["actual"])  # type: ignore[arg-type]
        print(user_msg)
        print()


if __name__ == "__main__":
    main()

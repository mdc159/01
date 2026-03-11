"""
critic.py — Critic / Evaluator (Self-Critique Loop).

Implements the "critic-reviser" pattern:
  STEP 1 → Worker produces output
  STEP 2 → Critic evaluates it against success criteria
  STEP 3 → If weak, critic proposes improvement
  STEP 4 → Worker revises (or loop escalates after N failures)

Uses the PROJECT model tier (gpt-4o) for most evaluations.
Only escalates to o1 (STRATEGIC tier) for systemic failure analysis.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

import llm
from config import Models
from state import ExperimentResult, SystemState

logger = logging.getLogger(__name__)

_CRITIC_SYSTEM = """\
You are a rigorous quality critic for an autonomous AI engineering system.

Evaluate the given output against the stated goal and success criteria.
Be concise and objective. Do not be lenient.

Return a JSON object with:
  - passed: bool
  - score: float  (0.0 – 1.0)
  - issues: list[str]
  - improvement_suggestion: str (empty string if passed)
"""


@dataclass
class CriticVerdict:
    passed: bool
    score: float
    issues: list[str]
    improvement_suggestion: str


def evaluate(
    state: SystemState,
    task_description: str,
    worker_output: str,
    success_criteria: list[str] | None = None,
) -> CriticVerdict:
    """
    Evaluate a worker's output against the task and success criteria.

    Returns a CriticVerdict. The caller (main loop) decides whether to
    retry, revise, or escalate based on verdict.passed and verdict.score.
    """
    criteria_block = ""
    if success_criteria:
        criteria_block = "SUCCESS CRITERIA:\n" + "\n".join(
            f"  - {c}" for c in success_criteria
        )

    messages = [
        {
            "role": "user",
            "content": (
                f"GOAL: {state.current_goal}\n\n"
                f"TASK: {task_description}\n\n"
                f"{criteria_block}\n\n"
                f"WORKER OUTPUT:\n{worker_output}"
            ),
        }
    ]

    raw = llm.call(messages, model=Models.PROJECT, system_prompt=_CRITIC_SYSTEM)

    try:
        data = json.loads(raw)
        verdict = CriticVerdict(
            passed=bool(data.get("passed", False)),
            score=float(data.get("score", 0.0)),
            issues=data.get("issues", []),
            improvement_suggestion=data.get("improvement_suggestion", ""),
        )
    except (json.JSONDecodeError, KeyError, TypeError):
        logger.warning("[CRITIC] Could not parse verdict JSON. Treating as failure.")
        verdict = CriticVerdict(
            passed=False,
            score=0.0,
            issues=["Could not parse critic response."],
            improvement_suggestion=raw,
        )

    # Record as an experiment in the state
    result = ExperimentResult(
        hypothesis=state.active_hypothesis,
        outcome="success" if verdict.passed else "failure",
        output=worker_output,
        metadata={"score": verdict.score, "issues": verdict.issues},
    )
    state.record_experiment(result)

    logger.info(
        "[CRITIC] Task=%r | passed=%s | score=%.2f | issues=%s",
        task_description[:60],
        verdict.passed,
        verdict.score,
        verdict.issues,
    )
    return verdict

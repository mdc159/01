"""
planner.py — Strategic Loop (o1).

This is the "CEO" of the system. Called INFREQUENTLY — only when:
  1. A new goal arrives and needs a project graph.
  2. The worker loop has failed N times and needs a fresh diagnosis.
  3. A periodic strategic review is triggered.

o1 is given the full context summary + failure logs and returns a
structured plan that drives the project loop.
"""

from __future__ import annotations

import json
import logging

import llm
from config import Models, Paths
from state import SystemState

logger = logging.getLogger(__name__)

# ── Load Context Document ────────────────────────────────────────

def _load_system_context() -> str:
    """Load the o1 architecture presentation document."""
    prompt_path = Paths.ROOT / "o1_system_prompt.md"
    if prompt_path.exists():
        return prompt_path.read_text()
    
    # Fallback minimal context if the file is missing
    return (
        "You are the Strategic Planner (CEO) for an autonomous engineering AI system. "
        "You think deeply to build JSON project graphs or diagnose systemic failures."
    )


# ── Prompt templates ─────────────────────────────────────────────

def _get_plan_system() -> str:
    return _load_system_context() + """

---
CURRENT OPERATION: STRATEGIC PLANNING
When given a goal, you will:
1. Identify the real underlying problem (reframe if necessary).
2. Define the key variables, constraints, and success metrics.
3. Produce a project graph as a JSON list of sub-tasks.

Output JSON only. No markdown fences. No extra commentary.
"""

def _get_diagnose_system() -> str:
    return _load_system_context() + """

---
CURRENT OPERATION: FAILURE DIAGNOSIS
You receive failure logs from a worker loop that has exhausted its retries.

Your job:
1. Identify the root cause of the repeated failures.
2. Find hidden assumptions that may be wrong.
3. Recommend an alternate architectural or algorithmic approach (do NOT just fix syntax errors).

Output a JSON object with keys: root_cause, hidden_assumptions, recommendation.
"""


def build_project_graph(state: SystemState) -> SystemState:
    """
    Call o1 to produce a project graph for the current goal.
    Updates state.project_graph and state.strategic_plan.
    """
    logger.info("[STRATEGIC] Building project graph for goal: %s", state.current_goal)

    messages = [
        {
            "role": "user",
            "content": (
                f"GOAL: {state.current_goal}\n\n"
                f"CONSTRAINTS:\n" + "\n".join(f"- {c}" for c in state.constraints) +
                "\n\nProduce a project graph as a JSON list of sub-task objects. "
                "Each sub-task must have: id, name, description, depends_on (list of ids)."
            ),
        }
    ]

    raw = llm.call(messages, model=Models.STRATEGIC, system_prompt=_get_plan_system())

    try:
        graph = json.loads(raw)
        state.project_graph = graph
        state.task_queue = [t["id"] for t in graph if not t.get("depends_on")]
    except json.JSONDecodeError:
        logger.warning("[STRATEGIC] Could not parse project graph JSON. Raw:\n%s", raw)
        state.project_graph = []

    state.strategic_plan = raw
    state.escalated = False
    logger.info("[STRATEGIC] Project graph built with %d nodes.", len(state.project_graph))
    return state


def diagnose_failures(state: SystemState) -> SystemState:
    """
    Call o1 to analyze a pattern of worker failures.
    Returns updated state with a new strategic recommendation.
    """
    logger.info(
        "[STRATEGIC] Diagnosing %d failures. Last error: %s",
        state.failure_count,
        state.last_error[:200],
    )

    failure_log = "\n".join(
        f"[{e.outcome.upper()}] {e.hypothesis}: {e.output[:400]}"
        for e in state.recent_experiments
        if e.outcome == "failure"
    )

    messages = [
        {
            "role": "user",
            "content": (
                f"GOAL: {state.current_goal}\n\n"
                f"CURRENT DESIGN:\n{json.dumps(state.current_design, indent=2)}\n\n"
                f"FAILURE LOG (last {len(state.recent_experiments)} attempts):\n{failure_log}"
            ),
        }
    ]

    raw = llm.call(messages, model=Models.STRATEGIC, system_prompt=_get_diagnose_system())

    try:
        diagnosis = json.loads(raw)
        recommendation = diagnosis.get("recommendation", raw)
    except json.JSONDecodeError:
        recommendation = raw

    # Surface the recommendation as a new hypothesis for the project loop
    state.active_hypothesis = recommendation
    state.failure_count = 0
    state.escalated = True
    logger.info("[STRATEGIC] Diagnosis complete. Recommendation surface to project loop.")
    return state


# ── Fix the lowercase typo for the diagnose prompt ──────────────
_diagnose_SYSTEM = _DIAGNOSE_SYSTEM

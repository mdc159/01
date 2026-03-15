"""
worker.py — Experiment Loop (fast execution).

The worker is stateless — it receives a task + context summary and
produces an output. It runs many times per project cycle (100s of
permutations) without burning expensive API tokens.

Uses the WORKER model tier (gpt-4o-mini or local Ollama).
"""

from __future__ import annotations

import logging

import llm
import memory
from config import Models
from state import SystemState

logger = logging.getLogger(__name__)

_WORKER_SYSTEM = """\
You are a focused execution agent in an autonomous engineering system.
You receive a specific task with full context. Execute it precisely.
Think through the task step by step internally — do NOT add filler text.
Return only the requested output.
"""


def run_task(
    state: SystemState,
    task: str,
    improvement_hint: str = "",
) -> str:
    """
    Execute a single concrete task using the WORKER model.

    Args:
        state:            Current system state (provides context summary).
        task:             Specific task description for this worker call.
        improvement_hint: Critic's suggestion from a prior failed attempt.

    Returns:
        The worker's raw output string.
    """
    context = state.context_summary()

    hint_block = ""
    if improvement_hint:
        hint_block = f"\n\nIMPROVEMENT HINT FROM PRIOR ATTEMPT:\n{improvement_hint}"

    # Inject relevant heuristics from prior successful experiments
    heuristics = memory.retrieve_heuristics(top_k=3)
    heuristics_block = ""
    if heuristics:
        heuristics_block = "\n\nPRIOR SUCCESSFUL PATTERNS:\n"
        for h in heuristics:
            heuristics_block += f"  - [{h['metric']}] {h['action'][:100]} (Δ{h.get('score_delta', 0):+.4f})\n"

    messages = [
        {
            "role": "user",
            "content": (
                f"SYSTEM CONTEXT:\n{context}\n\n"
                f"TASK:\n{task}"
                f"{hint_block}"
                f"{heuristics_block}"
            ),
        }
    ]

    logger.info("[WORKER] Running task: %s", task[:80])
    output = llm.call(messages, model=Models.WORKER, system_prompt=_WORKER_SYSTEM)
    logger.debug("[WORKER] Output (%d chars): %s...", len(output), output[:200])
    return output

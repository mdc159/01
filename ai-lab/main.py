"""
main.py — The Orchestration Engine.

Implements the three nested loops from the architecture:

  ┌─ STRATEGIC LOOP (o1) ──────────────────────────────────────────┐
  │  Called once at startup and on escalation / stuck detection.   │
  │                                                                │
  │  ┌─ PROJECT LOOP (gpt-4o) ─────────────────────────────────┐  │
  │  │  Iterates over the task queue. Evaluates batch results.   │  │
  │  │                                                           │  │
  │  │  ┌─ EXPERIMENT LOOP (gpt-4o-mini / local) ────────────┐  │  │
  │  │  │  Worker → Critic → Retry or Escalate.               │  │  │
  │  │  └────────────────────────────────────────────────────┘  │  │
  │  └─────────────────────────────────────────────────────────┘  │
  └────────────────────────────────────────────────────────────────┘

Usage:
    python main.py "Design a lightweight carbon-fibre prosthetic ankle joint"
"""

from __future__ import annotations

import logging
import sys

from config import Thresholds, Paths
from state import SystemState
import planner
import worker
import critic
import memory

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

Paths.ensure_dirs()

# ── State checkpoint path ────────────────────────────────────────
_STATE_FILE = Paths.STATE_DB.with_suffix(".json")


def load_or_create_state(goal: str) -> SystemState:
    if _STATE_FILE.exists():
        state = SystemState.load(_STATE_FILE)
        if state.current_goal == goal:
            logger.info("Resuming from checkpoint (loop #%d).", state.loop_iteration)
            return state
    state = SystemState(current_goal=goal)
    # Inject persisted heuristics into the working constraints
    state.heuristics = memory.retrieve_skills(top_k=10)
    return state


def experiment_loop(
    state: SystemState,
    task: str,
    success_criteria: list[str] | None = None,
) -> tuple[SystemState, bool]:
    """
    Inner loop: try a task, evaluate, retry with hints on failure.
    Returns (updated_state, success_flag).
    """
    improvement_hint = ""
    criteria = success_criteria or [
        "Output is directly relevant to the stated task.",
        "Output is complete and actionable.",
        "No hallucinated facts or contradictions with constraints.",
    ]

    for attempt in range(Thresholds.ESCALATE_TO_STRATEGIC_AFTER):
        output = worker.run_task(state, task, improvement_hint=improvement_hint)
        verdict = critic.evaluate(state, task, output, criteria)

        if verdict.passed:
            logger.info("✅ Task passed on attempt %d.", attempt + 1)
            return state, True
        else:
            logger.info(
                "❌ Attempt %d failed (score=%.2f). Issues: %s",
                attempt + 1,
                verdict.score,
                verdict.issues,
            )
            improvement_hint = verdict.improvement_suggestion

    logger.warning("⚠️  Task failed after %d attempts → escalating.", attempt + 1)
    return state, False


def project_loop(state: SystemState) -> SystemState:
    """
    Middle loop: process task queue, escalate stuck tasks to planner.
    """
    while state.task_queue:
        if state.loop_iteration >= Thresholds.MAX_PROJECT_ITERATIONS:
            raise RuntimeError(
                "Project loop exceeded MAX_PROJECT_ITERATIONS. "
                "Stopping to prevent infinite execution."
            )

        task_id = state.task_queue.pop(0)
        task_def = next(
            (t for t in state.project_graph if t["id"] == task_id),
            {"name": task_id, "description": task_id},
        )
        task_description = task_def.get("description", task_id)
        task_criteria = task_def.get("evaluation_criteria", [])
        if not isinstance(task_criteria, list):
            task_criteria = []
        state.active_hypothesis = task_description

        logger.info("── Project Loop: starting task [%s] %s", task_id, task_def["name"])

        state, success = experiment_loop(
            state,
            task_description,
            success_criteria=task_criteria,
        )

        if success:
            state.completed_tasks.append(task_id)
            state.task_replan_counts.pop(task_id, None)
            # Unlock dependent tasks
            for t in state.project_graph:
                if task_id in t.get("depends_on", []):
                    all_deps_done = all(
                        d in state.completed_tasks for d in t["depends_on"]
                    )
                    if all_deps_done and t["id"] not in state.task_queue:
                        state.task_queue.append(t["id"])
        else:
            state.task_replan_counts[task_id] = state.task_replan_counts.get(task_id, 0) + 1
            if (
                state.task_replan_counts[task_id]
                > Thresholds.MAX_STRATEGIC_REPLANS_PER_TASK
            ):
                raise RuntimeError(
                    f"Task {task_id} exceeded MAX_STRATEGIC_REPLANS_PER_TASK="
                    f"{Thresholds.MAX_STRATEGIC_REPLANS_PER_TASK}. "
                    "Manual intervention required."
                )

            # Escalate to strategic planner for diagnosis
            state = planner.diagnose_failures(state)
            # Re-queue the task with the new hypothesis
            state.task_queue.insert(0, task_id)

        state.loop_iteration += 1
        state.save(_STATE_FILE)
        logger.info("State checkpoint saved.")

    return state


def strategic_loop(goal: str) -> SystemState:
    """
    Outer loop: plan → project → (escalate back to plan if stuck).
    """
    state = load_or_create_state(goal)

    if not state.project_graph:
        logger.info("══ Strategic Loop: building project graph via o1.")
        state = planner.build_project_graph(state)
        if not state.task_queue:
            raise RuntimeError("Planner returned no executable tasks.")
        state.save(_STATE_FILE)

    logger.info("══ Entering project loop with %d tasks.", len(state.task_queue))
    state = project_loop(state)

    logger.info("══ All tasks complete. Goal achieved.")
    return state


if __name__ == "__main__":
    goal = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Research task"
    final_state = strategic_loop(goal)
    print("\n── COMPLETED TASKS ──")
    for t in final_state.completed_tasks:
        print(f"  ✅ {t}")
    print(f"\nArtifacts saved to: {Paths.ARTIFACTS}")

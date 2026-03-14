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
import opencode_executor

# ── Eval harness gate (optional — runs when cases file exists) ────
_EVAL_CASES = Paths.ROOT / "evals" / "knowledge_plane" / "cases.jsonl"
_EVAL_SCORE_THRESHOLD = float(__import__("os").environ.get("EVAL_SCORE_THRESHOLD", "0.56"))

# ── OpenCode execution mode ───────────────────────────────────────
# Set OPENCODE_EXECUTOR=1 to route experiment-loop tasks through
# opencode run --format json instead of the built-in worker.
_USE_OPENCODE = __import__("os").environ.get("OPENCODE_EXECUTOR", "") == "1"
_OPENCODE_AGENT = __import__("os").environ.get("OPENCODE_AGENT", "")  # e.g. "sisyphus"
_OPENCODE_MODEL = __import__("os").environ.get("OPENCODE_MODEL", "")  # e.g. "openai/gpt-5.3-codex"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

Paths.ensure_dirs()

# ── State checkpoint path ────────────────────────────────────────
_STATE_FILE = Paths.STATE_DB.with_suffix(".json")


def run_eval_gate() -> tuple[float, bool]:
    """
    Run the eval harness and return (score, passed).

    This is the system-level quality gate: after each project-loop task,
    we check whether the overall system quality still meets threshold.
    Python owns this decision (Option B architecture).

    Returns (0.0, True) if eval harness is not available.
    """
    if not _EVAL_CASES.exists():
        return 0.0, True  # No eval cases → gate passes by default

    try:
        import json
        import os
        import subprocess

        # Run the eval harness as a subprocess to avoid import tangles
        result = subprocess.run(
            [
                "uv", "run", "python", "-m", "evals.knowledge_plane.runner",
                "--cases", str(_EVAL_CASES),
                "--arm", "local",
                "--model", os.environ.get("KNOWLEDGE_PLANE_MODEL", "gpt-4o-mini"),
                "--local-backend", "evals.knowledge_plane.local_backend:RepoSearchBackend",
            ],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(Paths.ROOT),
        )

        if result.returncode != 0:
            logger.warning("📊 Eval harness failed: %s", result.stderr[:300])
            return 0.0, True

        # Parse the summary JSON from stdout (first JSON block)
        summary = json.loads(result.stdout.split("\n\n")[0])
        avg = summary.get("avg_case_score", 0.0)
        passed = avg >= _EVAL_SCORE_THRESHOLD

        logger.info(
            "📊 Eval gate: %.4f (threshold=%.2f) → %s",
            avg, _EVAL_SCORE_THRESHOLD, "PASS" if passed else "FAIL"
        )
        return avg, passed

    except Exception as e:
        logger.warning("📊 Eval gate skipped (error: %s)", e)
        return 0.0, True  # Don't block on eval harness errors


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

    When OPENCODE_EXECUTOR=1, routes execution through opencode run
    instead of the built-in worker. OpenCode handles its own retries
    via OMO agent loops, so we run it once and check the result.
    """
    # ── OpenCode execution path ───────────────────────────────────
    if _USE_OPENCODE and opencode_executor.is_available():
        logger.info("[OPENCODE] Executing task via OpenCode: %s", task[:80])
        result = opencode_executor.run_task(
            task,
            agent=_OPENCODE_AGENT or None,
            model=_OPENCODE_MODEL or None,
        )

        if result.success:
            logger.info(
                "✅ OpenCode task completed: %d steps, %d tokens, $%.4f, files=%s",
                result.steps, result.total_tokens, result.total_cost,
                result.files_changed or "none",
            )
            # Record as successful experiment
            from state import ExperimentResult
            state.record_experiment(ExperimentResult(
                hypothesis=task,
                outcome="success",
                output=result.text_output[:2000],
                metadata={
                    "executor": "opencode",
                    "agent": _OPENCODE_AGENT or "default",
                    "session_id": result.session_id,
                    "tokens": result.total_tokens,
                    "cost": result.total_cost,
                    "files_changed": result.files_changed,
                    "tools_used": [t["tool"] for t in result.tools_used],
                },
            ))
            return state, True
        else:
            logger.warning(
                "❌ OpenCode task failed: %s", result.error or "no DONE signal"
            )
            state.record_experiment(ExperimentResult(
                hypothesis=task,
                outcome="failure",
                output=result.error or result.text_output[:2000],
                metadata={"executor": "opencode", "session_id": result.session_id},
            ))
            return state, False

    # ── Built-in worker path ──────────────────────────────────────
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

            # T-02: Eval gate — check system quality after each task
            eval_score, eval_passed = run_eval_gate()
            if not eval_passed:
                logger.warning(
                    "📊 Eval gate FAILED after task %s (score=%.4f < %.2f). "
                    "Escalating to strategic tier.",
                    task_id, eval_score, _EVAL_SCORE_THRESHOLD,
                )
                state.last_error = f"Eval gate regression: {eval_score:.4f} < {_EVAL_SCORE_THRESHOLD}"
                state = planner.diagnose_failures(state)

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
        # T-01: Emit .sisyphus plan for OMO Atlas execution
        plan_path = planner.emit_sisyphus_plan(state)
        logger.info("══ Plan emitted: %s", plan_path)

        # If OpenCode executor is active, execute the plan directly
        if _USE_OPENCODE and opencode_executor.is_available():
            logger.info("══ Executing plan via OpenCode agent=%s", _OPENCODE_AGENT or "default")
            plan_result = opencode_executor.run_plan(
                plan_path,
                agent=_OPENCODE_AGENT or "sisyphus",
                model=_OPENCODE_MODEL or None,
                timeout=600,
            )
            if plan_result.success:
                logger.info("══ Plan executed successfully via OpenCode (%d steps, $%.4f)",
                            plan_result.steps, plan_result.total_cost)
            else:
                logger.warning("══ Plan execution failed: %s", plan_result.error)
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

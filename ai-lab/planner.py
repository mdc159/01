"""
planner.py — Strategic loop (o1-class reasoning).

The planner is invoked for:
  1) Initial project decomposition.
  2) Strategic diagnosis after repeated worker failures.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import llm
from config import Models, Paths
from state import SystemState

logger = logging.getLogger(__name__)


def _load_system_context() -> str:
    """Load strategist instructions (prompt + canonical product contract)."""
    sections: list[str] = []

    prompt_path = Paths.ROOT / "o1_system_prompt.md"
    if prompt_path.exists():
        sections.append(prompt_path.read_text())

    canon_path = Paths.ROOT.parent / "CANON.md"
    if canon_path.exists():
        sections.append(
            "=== PRODUCT CANON (AUTHORITATIVE) ===\n" + canon_path.read_text()
        )

    if sections:
        return "\n\n".join(sections)

    return (
        "You are the Strategic Planner (CEO) for an autonomous engineering AI system. "
        "Build executable project graphs and diagnose systemic failures."
    )


def _strip_markdown_fences(raw: str) -> str:
    text = raw.strip()
    if not text.startswith("```"):
        return text

    lines = text.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _parse_json(raw: str) -> Any:
    return json.loads(_strip_markdown_fences(raw))


def _normalize_task(task: dict[str, Any], index: int) -> dict[str, Any]:
    task_id = str(task.get("id") or task.get("task_id") or f"T-{index:02d}")

    dependencies = task.get("depends_on")
    if dependencies is None:
        dependencies = task.get("dependencies", [])
    if not isinstance(dependencies, list):
        dependencies = []

    criteria = task.get("evaluation_criteria", [])
    if not isinstance(criteria, list):
        criteria = []

    inputs = task.get("inputs", [])
    if not isinstance(inputs, list):
        inputs = []

    return {
        "id": task_id,
        "name": str(task.get("name") or task_id),
        "description": str(
            task.get("description")
            or task.get("objective")
            or task.get("name")
            or task_id
        ),
        "depends_on": [str(d) for d in dependencies if str(d).strip()],
        "methodology": str(task.get("methodology") or ""),
        "inputs": [str(i) for i in inputs if str(i).strip()],
        "evaluation_criteria": [str(c) for c in criteria if str(c).strip()],
        "notes": str(task.get("notes") or ""),
    }


def _normalize_project_graph(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        tasks = payload
    elif isinstance(payload, dict):
        tasks = payload.get("tasks") or payload.get("project_graph")
    else:
        tasks = None

    if not isinstance(tasks, list):
        raise ValueError("Planner output must contain a list of tasks.")

    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for i, raw_task in enumerate(tasks, start=1):
        if not isinstance(raw_task, dict):
            logger.warning("[STRATEGIC] Ignoring non-object task at index %d.", i)
            continue
        task = _normalize_task(raw_task, i)
        if task["id"] in seen:
            logger.warning("[STRATEGIC] Duplicate task id %r dropped.", task["id"])
            continue
        seen.add(task["id"])
        normalized.append(task)

    if not normalized:
        raise ValueError("Planner returned zero valid tasks.")

    valid_ids = {t["id"] for t in normalized}
    for t in normalized:
        kept = [d for d in t["depends_on"] if d in valid_ids and d != t["id"]]
        dropped = set(t["depends_on"]) - set(kept)
        if dropped:
            logger.warning(
                "[STRATEGIC] Task %s dropped invalid dependencies: %s",
                t["id"],
                sorted(dropped),
            )
        t["depends_on"] = kept

    return normalized


def _build_initial_task_queue(
    graph: list[dict[str, Any]],
    completed: list[str] | None = None,
) -> list[str]:
    done = set(completed or [])
    ready = [
        t["id"] for t in graph
        if t["id"] not in done and all(dep in done for dep in t.get("depends_on", []))
    ]
    if not ready and graph:
        raise ValueError(
            "No executable root task found. Graph may contain circular or unsatisfied dependencies."
        )
    return ready


def _get_plan_system() -> str:
    return _load_system_context() + """

---
CURRENT OPERATION: STRATEGIC PLANNING

Return JSON only (no markdown).
Build an executable project graph object:
{
  "project_name": "...",
  "global_constraints": ["..."],
  "tasks": [
    {
      "task_id": "T-01",
      "name": "...",
      "description": "...",
      "dependencies": [],
      "methodology": "...",
      "inputs": ["..."],
      "evaluation_criteria": ["..."],
      "notes": "..."
    }
  ]
}

Rules:
- Keep task count minimal but complete (typically 3-8 tasks).
- Dependencies must reference valid task IDs.
- Every task must be self-contained and executable by limited-context workers.
- evaluation_criteria should be concrete and testable.
"""


def _get_diagnose_system() -> str:
    return _load_system_context() + """

---
CURRENT OPERATION: FAILURE DIAGNOSIS

Return JSON only (no markdown).
Output object schema:
{
  "root_cause": "...",
  "hidden_assumptions": ["..."],
  "recommendation": "...",
  "updated_tasks": [
    {
      "task_id": "T-01",
      "name": "...",
      "description": "...",
      "dependencies": [],
      "methodology": "...",
      "inputs": ["..."],
      "evaluation_criteria": ["..."],
      "notes": "..."
    }
  ]
}

If no task graph changes are needed, return "updated_tasks": [].
"""


def build_project_graph(state: SystemState) -> SystemState:
    """Call strategist model and set a normalized, executable project graph."""
    logger.info("[STRATEGIC] Building project graph for goal: %s", state.current_goal)

    snapshot = {
        "goal": state.current_goal,
        "constraints": state.constraints,
        "heuristics": state.heuristics[-10:],
        "completed_tasks": state.completed_tasks,
        "loop_iteration": state.loop_iteration,
    }

    messages = [
        {
            "role": "user",
            "content": (
                "OBJECTIVE:\nCreate the minimum reliable project graph for this goal.\n\n"
                f"STATE SNAPSHOT:\n{json.dumps(snapshot, indent=2)}\n\n"
                "DECISION QUESTION:\n"
                "What task graph best maximizes progress under constraints while minimizing risk and rework?"
            ),
        }
    ]

    raw = llm.call(messages, model=Models.STRATEGIC, system_prompt=_get_plan_system())
    state.strategic_plan = raw

    try:
        payload = _parse_json(raw)
        graph = _normalize_project_graph(payload)
        state.project_graph = graph
        state.task_queue = _build_initial_task_queue(graph, completed=state.completed_tasks)
    except Exception as exc:
        raise RuntimeError(
            f"[STRATEGIC] Failed to build valid project graph: {exc}"
        ) from exc

    state.escalated = False
    logger.info(
        "[STRATEGIC] Project graph built with %d tasks (%d initially ready).",
        len(state.project_graph),
        len(state.task_queue),
    )
    return state


def diagnose_failures(state: SystemState) -> SystemState:
    """Call strategist model to diagnose repeated failures and reframe strategy."""
    logger.info(
        "[STRATEGIC] Diagnosing %d failures. Last error: %s",
        state.failure_count,
        state.last_error[:200],
    )

    failure_log = "\n".join(
        f"[{e.outcome.upper()}] {e.hypothesis}: {e.output[:400]}"
        for e in state.recent_experiments[-20:]
        if e.outcome == "failure"
    )

    snapshot = {
        "goal": state.current_goal,
        "active_hypothesis": state.active_hypothesis,
        "current_design": state.current_design,
        "task_queue": state.task_queue,
        "completed_tasks": state.completed_tasks,
    }

    messages = [
        {
            "role": "user",
            "content": (
                "OBJECTIVE:\nDiagnose the root cause of repeated failures and produce a corrected strategy.\n\n"
                f"STATE SNAPSHOT:\n{json.dumps(snapshot, indent=2)}\n\n"
                f"FAILURE LOG:\n{failure_log}\n\n"
                "DECISION QUESTION:\n"
                "What strategic change gives the highest chance of progress on the next cycle?"
            ),
        }
    ]

    raw = llm.call(messages, model=Models.STRATEGIC, system_prompt=_get_diagnose_system())
    state.strategic_plan = raw

    try:
        diagnosis = _parse_json(raw)
        if not isinstance(diagnosis, dict):
            raise ValueError("Diagnosis response must be an object.")
    except Exception as exc:
        raise RuntimeError(f"[STRATEGIC] Failed to parse diagnosis JSON: {exc}") from exc

    recommendation = str(diagnosis.get("recommendation") or "").strip()
    if not recommendation:
        recommendation = "Revise approach based on failure analysis."

    updated_tasks = diagnosis.get("updated_tasks", [])
    if isinstance(updated_tasks, list) and updated_tasks:
        graph = _normalize_project_graph({"tasks": updated_tasks})
        state.project_graph = graph
        state.task_queue = _build_initial_task_queue(graph, completed=state.completed_tasks)
        logger.info("[STRATEGIC] Applied updated task graph with %d tasks.", len(graph))

    state.active_hypothesis = recommendation
    state.failure_count = 0
    state.escalated = True
    logger.info("[STRATEGIC] Diagnosis complete.")
    return state

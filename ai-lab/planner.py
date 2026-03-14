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
import memory
from config import Models, O1Settings, Paths
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


def _get_v2_system() -> str:
    """Load system context + v2 contract output schema."""
    return _load_system_context() + """

---
CURRENT OPERATION: STRATEGIC TIER CALL (v2 contract)

Return JSON only (no markdown fences).
Your response MUST conform to this schema:
{
  "meta": {
    "caller": "planner|escalation",
    "confidence_score": 0.0,
    "confidence_rationale": "string"
  },
  "chosen_strategy": {
    "option_id": "A",
    "rationale": "string",
    "expected_outcome": "string"
  },
  "rejected_alternatives": [{"option_id": "B", "reason": "string"}],
  "assumptions": ["string"],
  "risk_forecast": [
    {
      "failure_mode": "string",
      "likelihood": "low|medium|high",
      "impact": "low|medium|high",
      "detection_signal": "string",
      "mitigation": "string"
    }
  ],
  "smallest_validating_experiment": {
    "description": "string",
    "duration": "string",
    "success_signal": "string",
    "failure_signal": "string"
  },
  "kill_criteria": {
    "stop_when": ["string"],
    "pivot_to": "string",
    "escalate_when": ["string"]
  },
  "ordered_tasks": [
    {
      "task_id": "T-01",
      "name": "string",
      "description": "string",
      "dependencies": [],
      "evaluation_criteria": ["string"],
      "risk": "low|medium|high"
    }
  ],
  "interface_contract": {
    "artifacts_emitted": ["string"],
    "state_updates_for_project_loop": "string",
    "worker_instructions_format": "string"
  },
  "memory_actions": [
    {
      "layer": "semantic|artifact|episodic",
      "action": "write|update|delete",
      "key": "string",
      "value": "string"
    }
  ],
  "verification": {
    "how_to_confirm_this_was_right": "string",
    "observable_result": "string",
    "reversal_conditions": ["string"]
  }
}

Rules:
- Keep ordered_tasks to 3-7 items.
- Make evaluation_criteria observable and testable.
- If confidence_score < confidence_threshold, prioritize smallest_validating_experiment over a full task graph.
- Always populate kill_criteria.
- memory_actions must be intentional — only write heuristics worth retaining.
"""


def _process_v2_response(state: SystemState, payload: dict[str, Any]) -> SystemState:
    """Extract v2 contract fields from a strategic response and apply them to state."""
    # Memory actions — write heuristics to skills DB
    mem_actions = payload.get("memory_actions", [])
    if isinstance(mem_actions, list) and mem_actions:
        memory.process_memory_actions(mem_actions)
        logger.info("[STRATEGIC] Processed %d memory actions.", len(mem_actions))

    # Store verification and kill criteria for downstream loops
    state.strategic_plan = json.dumps(payload, indent=2)

    # Check confidence threshold
    meta = payload.get("meta", {})
    confidence = float(meta.get("confidence_score", 1.0))
    threshold = O1Settings.CONFIDENCE_THRESHOLD

    if confidence < threshold:
        experiment = payload.get("smallest_validating_experiment", {})
        logger.warning(
            "[STRATEGIC] Confidence %.2f < threshold %.2f. "
            "Prioritizing validating experiment: %s",
            confidence, threshold,
            experiment.get("description", "N/A"),
        )

    return state


def build_project_graph(state: SystemState) -> SystemState:
    """Call strategist model using v2 contract and set a normalized, executable project graph."""
    logger.info("[STRATEGIC] Building project graph for goal: %s", state.current_goal)

    snapshot = json.dumps({
        "active_goal": state.current_goal,
        "runtime_modules": ["main.py", "planner.py", "worker.py", "critic.py", "state.py", "memory.py", "tools.py"],
        "recent_experiment_results": [
            f"[{e.outcome.upper()}] {e.hypothesis}: {e.output[:200]}"
            for e in state.recent_experiments[-5:]
        ],
        "known_constraints": state.constraints,
        "known_gaps": [state.last_error] if state.last_error else [],
    }, indent=2)

    skills = memory.retrieve_skills(top_k=10)
    heuristics_block = "\n".join(f"  - {h}" for h in skills) if skills else "  (none yet)"

    prompt = f"""## 0. Meta
- caller: planner
- confidence_threshold: {O1Settings.CONFIDENCE_THRESHOLD}
- budget_envelope: Keep task count to 3-7. Prefer local/cheap execution.

## 1. Objective
{state.current_goal}

## 2. Success Metric
The project graph is successful if it produces observable, measurable progress toward the objective within the first 3 task completions.

## 3. Current State Snapshot
{snapshot}

## 4. Constraints
- Single machine (Apple M4 Pro, 24GB unified memory)
- Local-first: prefer Ollama workers, escalate to API only when needed
- Blast radius: patch (no architectural rewrites unless escalation)
- Completed tasks so far: {json.dumps(state.completed_tasks)}

## 5. Prior Attempts & Failure Signatures
- Loop iteration: {state.loop_iteration}
- Failure count this cycle: {state.failure_count}
- Last error: {state.last_error[:400] if state.last_error else 'None'}
- Known heuristics from skills DB:
{heuristics_block}

## 6. Explicit Option Set
Present at least 2 candidate strategies and adjudicate between them.

## 7. Assumptions & Unknowns
List what you believe but haven't verified, and what data is missing.

## 8. Decision Question
Given the objective, constraints, and current state, which strategy and task graph maximizes validated progress per iteration while staying within budget?"""

    messages = [{"role": "user", "content": prompt}]
    raw = llm.call(messages, model=Models.STRATEGIC, system_prompt=_get_v2_system())

    try:
        payload = _parse_json(raw)
        if not isinstance(payload, dict):
            raise ValueError("v2 response must be a JSON object.")

        state = _process_v2_response(state, payload)

        # Extract task graph from v2 response
        tasks = payload.get("ordered_tasks", [])
        if tasks:
            graph = _normalize_project_graph({"tasks": tasks})
            state.project_graph = graph
            state.task_queue = _build_initial_task_queue(graph, completed=state.completed_tasks)
        else:
            raise ValueError("No ordered_tasks in strategic response.")

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
    """Call strategist model using v2 contract to diagnose repeated failures and reframe strategy."""
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

    snapshot = json.dumps({
        "active_goal": state.current_goal,
        "runtime_modules": ["main.py", "planner.py", "worker.py", "critic.py", "state.py", "memory.py", "tools.py"],
        "recent_experiment_results": [
            f"[{e.outcome.upper()}] {e.hypothesis}: {e.output[:200]}"
            for e in state.recent_experiments[-10:]
        ],
        "known_constraints": state.constraints,
        "known_gaps": [state.last_error[:400]] if state.last_error else [],
    }, indent=2)

    prompt = f"""## 0. Meta
- caller: escalation
- confidence_threshold: {O1Settings.CONFIDENCE_THRESHOLD}
- budget_envelope: Minimize cost. Prefer smallest corrective action.

## 1. Objective
Diagnose the root cause of {state.failure_count} consecutive failures and produce a corrected strategy.

## 2. Success Metric
The corrected strategy produces at least one successful experiment in the next cycle.

## 3. Current State Snapshot
{snapshot}

## 4. Constraints
- Active hypothesis: {state.active_hypothesis}
- Current design: {json.dumps(state.current_design, indent=2)}
- Task queue: {json.dumps(state.task_queue)}
- Completed: {json.dumps(state.completed_tasks)}
- Blast radius: patch | refactor (rewrite only if architecturally broken)

## 5. Prior Attempts & Failure Signatures
{failure_log}

Failure category analysis requested: logic | tooling | architecture | data | resource

## 6. Explicit Option Set
Present at least 2 candidate recovery strategies:
- Option A: Minimal patch to the current approach
- Option B: Reframe the hypothesis entirely
- Option C (if needed): Architectural change

## 7. Assumptions & Unknowns
What assumptions led to these failures? What data is missing?

## 8. Decision Question
Given {state.failure_count} consecutive failures with the signatures above, which recovery strategy maximizes the probability of successful progress on the next cycle?

Also run a pre-mortem: assume the chosen recovery strategy also fails after 3 more attempts. What are the most likely root causes and what early signals would predict them?"""

    messages = [{"role": "user", "content": prompt}]
    raw = llm.call(messages, model=Models.STRATEGIC, system_prompt=_get_v2_system())

    try:
        payload = _parse_json(raw)
        if not isinstance(payload, dict):
            raise ValueError("v2 diagnosis response must be a JSON object.")

        state = _process_v2_response(state, payload)

        # Extract recommendation from chosen strategy
        chosen = payload.get("chosen_strategy", {})
        recommendation = str(chosen.get("rationale") or chosen.get("expected_outcome") or "").strip()
        if not recommendation:
            recommendation = "Revise approach based on failure analysis."

        # Apply updated task graph if present
        tasks = payload.get("ordered_tasks", [])
        if isinstance(tasks, list) and tasks:
            graph = _normalize_project_graph({"tasks": tasks})
            state.project_graph = graph
            state.task_queue = _build_initial_task_queue(graph, completed=state.completed_tasks)
            logger.info("[STRATEGIC] Applied updated task graph with %d tasks.", len(graph))

    except Exception as exc:
        raise RuntimeError(f"[STRATEGIC] Failed to parse v2 diagnosis: {exc}") from exc

    state.active_hypothesis = recommendation
    state.failure_count = 0
    state.escalated = True
    logger.info("[STRATEGIC] Diagnosis complete.")
    return state


# ════════════════════════════════════════════════════════════════
#  .sisyphus/plans/ Emitter (OMO Integration — Option B)
# ════════════════════════════════════════════════════════════════

_PLANS_DIR = Paths.ROOT.parent / ".sisyphus" / "plans"


def _category_for_task(task: dict[str, Any]) -> str:
    """Heuristic: pick an OMO category based on task keywords."""
    desc = (task.get("description", "") + " " + task.get("name", "")).lower()
    if any(kw in desc for kw in ("test", "verify", "validate", "check")):
        return "quick"
    if any(kw in desc for kw in ("architect", "design", "diagnos", "review")):
        return "ultrabrain"
    if any(kw in desc for kw in ("refactor", "rewrite", "complex", "debug")):
        return "deep"
    if any(kw in desc for kw in ("doc", "write", "readme", "report")):
        return "writing"
    return "unspecified-low"


def _render_task(task: dict[str, Any], index: int) -> str:
    """Render a single task in Atlas-compatible checkbox format."""
    task_id = task.get("id", f"T-{index:02d}")
    name = task.get("name", task_id)
    desc = task.get("description", "")
    deps = task.get("depends_on", [])
    criteria = task.get("evaluation_criteria", [])
    methodology = task.get("methodology", "")
    category = _category_for_task(task)

    lines = [f"- [ ] {index}. {name}"]
    lines.append("")
    lines.append(f"  **What to do**: {desc}")
    if methodology:
        lines.append(f"  {methodology}")
    lines.append(f"  **Must NOT do**: Do not modify files outside the task scope.")
    lines.append("")
    lines.append(f"  **Recommended Agent Profile**:")
    lines.append(f"  - Category: `{category}`")
    lines.append("")

    if deps:
        lines.append(f"  **Parallelization**: Blocked By: {', '.join(deps)}")
    else:
        lines.append(f"  **Parallelization**: Can Parallel: YES | Wave 1")
    lines.append("")

    if criteria:
        lines.append(f"  **Acceptance Criteria**:")
        for c in criteria:
            lines.append(f"  - [ ] {c}")
    else:
        lines.append(f"  **Acceptance Criteria**:")
        lines.append(f"  - [ ] Task completes without errors")
    lines.append("")

    lines.append(f"  **Commit**: YES | Message: `feat(lab): {name.lower()}`")
    lines.append("")

    return "\n".join(lines)


def emit_sisyphus_plan(state: SystemState, plan_name: str | None = None) -> Path:
    """
    Render the current project graph as a .sisyphus/plans/*.md file
    compatible with OMO's Atlas executor and /start-work command.

    Returns the path to the generated plan file.
    """
    if not state.project_graph:
        raise ValueError("No project graph to emit. Run build_project_graph first.")

    _PLANS_DIR.mkdir(parents=True, exist_ok=True)

    if not plan_name:
        # Derive from goal
        slug = state.current_goal[:40].lower()
        slug = "".join(c if c.isalnum() or c == "-" else "-" for c in slug)
        slug = slug.strip("-") or "experiment"
        plan_name = slug

    plan_path = _PLANS_DIR / f"{plan_name}.md"

    # Build the plan markdown
    sections = []

    # Header
    sections.append(f"# {state.current_goal}")
    sections.append("")
    sections.append("## TL;DR")
    sections.append(f"> **Summary**: Execute task graph for: {state.current_goal}")
    sections.append(f"> **Deliverables**: {len(state.project_graph)} tasks")

    # Count waves
    has_deps = any(t.get("depends_on") for t in state.project_graph)
    if has_deps:
        sections.append(f"> **Parallel**: YES - multiple waves")
    else:
        sections.append(f"> **Parallel**: YES - all independent")

    sections.append(f"> **Critical Path**: {' → '.join(t['id'] for t in state.project_graph)}")
    sections.append("")

    # Context
    sections.append("## Context")
    sections.append("### Original Request")
    sections.append(f"Goal: {state.current_goal}")
    if state.active_hypothesis:
        sections.append(f"Active hypothesis: {state.active_hypothesis}")
    sections.append("")

    if state.constraints:
        sections.append("### Constraints")
        for c in state.constraints:
            sections.append(f"- {c}")
        sections.append("")

    # Tasks
    sections.append("## Tasks")
    sections.append("")
    sections.append("> EVERY task MUST have: Agent Profile + Parallelization + Acceptance Criteria.")
    sections.append("")

    for i, task in enumerate(state.project_graph, start=1):
        sections.append(_render_task(task, i))

    # Final Verification Wave
    sections.append("## Final Verification Wave")
    sections.append("")
    sections.append("- [ ] F1. Plan Compliance Audit — oracle")
    sections.append("- [ ] F2. Code Quality Review — unspecified-high")
    sections.append("")

    # Commit Strategy
    sections.append("## Commit Strategy")
    sections.append("One commit per task. Conventional commit format.")
    sections.append("")

    # Success Criteria
    sections.append("## Success Criteria")
    sections.append(f"All tasks pass acceptance criteria. Eval harness score ≥ baseline (0.562).")

    plan_content = "\n".join(sections)
    plan_path.write_text(plan_content)

    logger.info(
        "[STRATEGIC] Emitted .sisyphus plan: %s (%d tasks, %d bytes)",
        plan_path, len(state.project_graph), len(plan_content),
    )
    return plan_path

# Next o1 Question: MVP Definition and First Build Slice

Use this exact prompt (fill placeholders) when calling the strategic o1 model.

---

You are the strategist for this project.

## Objective
Define the smallest reliable MVP for this autonomous R&D lab and choose the first implementation slice.

## Success Metric
The MVP is successful if it can:
1. Build an executable task graph for a new goal.
2. Run worker + critic retries on at least one task.
3. Escalate to strategist after repeated failure.
4. Persist state and resume cleanly.
5. Stop safely on loop guardrails.

## Current State Snapshot
```json
{
  "canon_path": "CANON.md",
  "runtime_modules": [
    "main.py", "planner.py", "worker.py", "critic.py", "state.py", "memory.py", "tools.py"
  ],
  "known_constraints": [
    "deterministic-first architecture",
    "o1 required for strategic decisions",
    "single-machine friendly MVP"
  ],
  "known_gaps": [
    "tool execution loop is still text-only",
    "limited validation of strategist output",
    "MVP tasks need strict prioritization"
  ]
}
```

## Constraints
- Keep MVP scope minimal.
- Favor reliability over feature breadth.
- No speculative framework sprawl.
- Output must be directly implementable in this repo.

## Decision Question
What exact MVP scope and ordered task graph should we execute next to maximize delivery probability in the fewest steps?

## Required Output Schema (JSON only)
```json
{
  "mvp_name": "string",
  "mvp_scope": "string",
  "non_goals": ["string"],
  "ordered_tasks": [
    {
      "task_id": "T-01",
      "name": "string",
      "description": "string",
      "dependencies": ["T-00"],
      "evaluation_criteria": ["string"],
      "risk": "low|medium|high"
    }
  ],
  "first_pr_slice": {
    "objective": "string",
    "files": ["path"],
    "acceptance_checks": ["string"]
  },
  "escalation_triggers": ["string"],
  "open_questions": ["string"]
}
```

Rules:
- Return JSON only (no markdown fences).
- Keep `ordered_tasks` to 3-7 items.
- Make acceptance checks observable and testable.

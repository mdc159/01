## 0. Meta
- caller: planner
- confidence_threshold: 0.75
- budget_envelope: Architecture design only. No code. Output is a scaffold blueprint.

## 1. Objective
Design a compact, autonomous self-improving R&D system that:
- Accepts broad goals (e.g., "optimize local LLM inference on Apple Silicon")
- Decomposes them into executable experiments
- Runs experiments continuously at low cost
- Learns from outcomes (keeps what works, reverts what doesn't)
- Escalates to heavy reasoning models only when stuck

## 2. Success Metric
The architecture is successful if:
- A single developer can build and run it on one machine (Apple M4 Pro, 24GB)
- It can operate autonomously for hours/days without human intervention
- It measurably improves at its task over successive iterations
- Total core engine stays under ~1,500 lines of code
- Dependencies are minimal (no heavy frameworks)

## 3. Current State Snapshot
```json
{
  "active_goal": "Design the architecture from scratch",
  "runtime_modules": [],
  "recent_experiment_results": [],
  "known_constraints": [
    "Single machine: Apple M4 Pro, 24GB unified memory",
    "Local models available via Ollama (70B Q4 fits in 18GB)",
    "MLX available for native Apple Silicon inference",
    "OpenAI API available for heavy reasoning (O1/O3 class)",
    "Budget: minimize API spend, maximize local execution",
    "One developer, no team"
  ],
  "known_gaps": [
    "No existing code — this is a greenfield design"
  ]
}
```

## 4. Constraints
- Must run on a single Mac (no cloud infra required)
- Prefer local/free model execution for high-volume work
- API calls (O1/O3) reserved for rare, high-value strategic decisions
- No LangChain, no LangGraph, no heavy framework dependencies
- Core engine should be understandable by reading ~10 files
- Inspired by the autoresearch discipline: every experiment is atomic, metrics are the only truth, failures are reverted cleanly

## 5. Prior Attempts & Failure Signatures
None. Clean slate.

## 6. Explicit Option Set

| Option | Description | Estimated Cost | Risk |
|--------|-------------|---------------|------|
| A | Nested loop architecture (strategic → project → experiment) with tiered model routing | Medium | Might over-engineer for a single-developer system |
| B | Flat agent loop (single loop with conditional escalation) | Low | Might be too simple to handle complex multi-step goals |
| C | Graph-based task engine (DAG of tasks with dependency resolution) | Medium-High | Adds complexity but enables parallel execution |

## 7. Assumptions & Unknowns
- Assumptions:
  - A single developer can build something useful in ~1,500 LOC
  - Local 70B models are capable enough for execution-tier work
  - Autonomous operation for hours/days is achievable without sophisticated error recovery
  - Learning from past experiments (heuristic memory) meaningfully improves future performance
- Unknowns:
  - What is the right abstraction boundary between "planning" and "executing"?
  - How should state be managed across long-running autonomous sessions?
  - What is the minimum viable memory system for compound improvement?
  - Should the system self-evaluate or use a separate critic?

## 8. Decision Question
If you were designing this system from zero, with no existing code, what architecture would you build? What are the essential modules, how do they interact, and what does the core loop look like? Which of options A/B/C (or a different approach) best fits the constraints?

Return your response in the v2 output schema (JSON only).

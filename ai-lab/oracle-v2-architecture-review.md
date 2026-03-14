## 0. Meta
- caller: planner
- confidence_threshold: 0.75
- budget_envelope: This is a strategic review, not an execution task. No code changes — output is a validated (or corrected) architecture scaffold.

## 1. Objective
Validate or correct the overall architecture of this autonomous self-improving R&D lab. We want the Oracle's assessment: is the scaffolding right, or should it look fundamentally different?

## 2. Success Metric
The response either:
- Confirms the current architecture is sound and identifies the highest-leverage gap to fill next, OR
- Proposes a corrected scaffold with clear rationale for what's wrong and what changes

## 3. Current State Snapshot
```json
{
  "active_goal": "Validate architecture before filling in implementation details",
  "runtime_modules": [
    "main.py (~186 LOC) — three nested loops: strategic → project → experiment",
    "planner.py (~320 LOC) — O1 strategic planning + failure diagnosis, v2 contract",
    "worker.py (~65 LOC) — stateless task execution (fast tier)",
    "critic.py (~113 LOC) — rates worker output, suggests improvements",
    "state.py (~121 LOC) — 5-layer memory hierarchy, JSON checkpointing, resume",
    "memory.py (~130 LOC) — skills DB (heuristics) + artifact registry + memory actions",
    "llm.py (~186 LOC) — unified LLM client (O1/O3 + Ollama + standard)",
    "config.py (~101 LOC) — model routing, safety thresholds, env config",
    "tools.py (~86 LOC) — deterministic tools: Python exec, shell, file I/O"
  ],
  "total_loc": "~1,300",
  "recent_experiment_results": [],
  "known_constraints": [
    "Single machine: Apple M4 Pro, 24GB unified memory",
    "Local-first: Ollama for workers, API calls only for strategic tier",
    "Minimal dependencies: openai + python-dotenv only",
    "No LangChain, no LangGraph, no framework overhead",
    "Strategic tier is model-agnostic and eval-gated (O1/O3/any reasoning model)",
    "Claude Code is the orchestrator/executor in the broader ecosystem"
  ],
  "known_gaps": [
    "Tool execution loop is still text-only (no real shell/code execution yet)",
    "No vector search for skills DB (tag-based retrieval only)",
    "No eval harness for comparing retrieval strategies",
    "System has never been run end-to-end on a real goal",
    "No observability beyond logging and JSON checkpoints"
  ]
}
```

## 4. Constraints
- This is a V-model top-of-V review — 30,000 foot level
- Blast radius: we can refactor or restructure if the architecture is wrong
- The system should be runnable by a single developer on a Mac
- It must remain simple — ~1,500 LOC ceiling for the core engine
- Inspired by karpathy/autoresearch: atomic experiments, metrics as truth, keep/revert discipline

## 5. Prior Attempts & Failure Signatures
- No failures yet — system has not been run end-to-end
- Architecture was designed through iterative conversation (see docs/chat.md)
- v2 strategic query contract was just implemented based on cross-model evaluation (O3, GPT-5.4, Codex all reviewed the protocol)
- Three AutoResearch reference implementations available for pattern comparison

## 6. Explicit Option Set

| Option | Description | Estimated Cost | Risk |
|--------|-------------|---------------|------|
| A | Current architecture is fundamentally sound — identify the highest-leverage gap and fill it | Low (incremental) | Low — but risk of missing a structural flaw |
| B | Architecture needs restructuring — the three-loop model, module boundaries, or state design has a flaw that will compound as we scale | Medium (refactor) | Medium — churn before first real run |
| C | Architecture is over-engineered for the actual goal — simplify radically before running | Low (subtract) | Low — but might lose useful abstractions |

## 7. Assumptions & Unknowns
- Assumptions:
  - Three nested loops (strategic → project → experiment) is the right decomposition
  - 5-layer memory hierarchy is necessary and sufficient
  - Stateless workers with a separate critic is better than workers that self-evaluate
  - JSON checkpointing is sufficient for state persistence (no need for SQLite yet)
  - The system can meaningfully self-improve without human intervention for hours/days
- Unknowns:
  - Will the critic tier actually improve worker output, or is it overhead?
  - Is the escalation threshold (5 failures) the right number?
  - Does the v2 query contract produce measurably better strategic responses than v1?
  - What is the first goal that would constitute a real end-to-end validation?

## 8. Decision Question
Given the current ~1,300 LOC scaffold, the v2 strategic contract, and the constraint of a single developer on Apple Silicon — is this the right architecture for an autonomous self-improving R&D lab? If yes, what is the single highest-leverage gap to fill next? If no, what should the scaffold look like instead?

Return your response in the v2 output schema (JSON only).

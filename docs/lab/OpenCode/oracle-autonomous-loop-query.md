# Oracle Query: Ordered Path to Autonomous Self-Improvement (Replace OpenClaw)

You are the strategist for this project. You are being consulted because the correct ordering of implementation steps is unclear, particularly around memory system design.

## Objective
Design the ordered implementation plan to take this system from "human-driven improvement cycles" to "autonomous self-improvement that runs unattended." This replaces the opaque OpenClaw orchestration with a transparent, measurable, self-improving system we fully control.

## Success Metric
The system is successful when it can:
1. Analyze its own eval results and identify the weakest metric.
2. Generate an improvement hypothesis and emit a plan.
3. Execute the plan via OpenCode (already working).
4. Run the eval harness and compare before/after scores.
5. Keep the change if score improves; git-revert if it regresses.
6. Persist what it learned (heuristic) so future runs benefit.
7. Repeat steps 1-6 unattended for N cycles.

## Current State Snapshot
```json
{
  "working_components": {
    "3_loop_orchestration": "main.py — strategic/project/experiment loops",
    "strategic_planning": "planner.py — O1 builds task graphs, diagnoses failures",
    "plan_emission": "planner.emit_sisyphus_plan() → .sisyphus/plans/*.md",
    "eval_harness": "evals/knowledge_plane/ — 10 cases, 4 metrics, current score 0.778",
    "eval_gate": "main.py:run_eval_gate() — gates on score threshold",
    "opencode_executor": "opencode_executor.py — runs opencode, parses JSON events",
    "python_opencode_bridge": "main.py — OPENCODE_EXECUTOR=1 routes through OpenCode",
    "omo_plugin": "installed, all agents on flat-rate gpt-5.3-codex ($0/token)",
    "vector_search": "memory.py — Ollama nomic-embed-text, cosine similarity",
    "state_persistence": "state.py — checkpoint/resume via state.db.json",
    "skills_db": "memory.py — save_skill(), retrieve_skills(), vector search"
  },
  "memory_architecture_designed_but_hollow": {
    "layer_1_identity": "IMPLEMENTED — state.system_role, permanent",
    "layer_2_working": "IMPLEMENTED — state.current_goal, active_hypothesis",
    "layer_3_episodic": "BUILT BUT NOT PERSISTED — state.recent_experiments resets each run",
    "layer_4_semantic": "BUILT BUT NEVER CALLED — save_skill() exists, nothing triggers it",
    "layer_5_artifact": "BUILT — save_artifact(), list_artifacts()"
  },
  "validated_today": {
    "opencode_pilot": "opencode run --format json produces parseable event stream",
    "omo_sisyphus": "full agent pipeline works at $0.00 flat rate",
    "self_improvement_cycles": "4 cycles, all autonomous via OpenCode, score 0.547 → 0.778 (+42%)",
    "cycle_details": [
      "Cycle 1: grader bug fix (prefix match citations) +0.015",
      "Cycle 2: prompt fix (cite doc_ids not indices) +0.134",
      "Cycle 3: prompt fix (verbatim quoting) +0.052",
      "Cycle 4: retrieval dedup (one chunk per doc_id) +0.030"
    ]
  },
  "missing_for_autonomous_loop": [
    "Autonomous task generation — system identifies its own next improvement",
    "Keep/revert discipline — auto git-revert on score regression",
    "Episodic memory persistence — remember what was tried across runs",
    "Auto heuristic capture — save lessons from successful experiments",
    "End-to-end unattended run — run, walk away, come back to results",
    "Summarizing checkpoints — distill raw logs into insights (ORIGIN.md design rule)"
  ]
}
```

## Constraints
- **Self-reliance**: Build our own memory system. Do NOT depend on OMO's notepad system, boulder.json, or any third-party state format. Can read from OMO artifacts as input, but core functionality must work independently.
- **Minimal architecture**: No new dependencies. Pure Python + JSON files + git + existing Ollama embeddings.
- **Incremental**: Each step must be independently testable and valuable. No "build 5 things then test."
- **Hardware**: M4 Pro 24GB. Ollama + OpenCode must coexist.
- **Cost**: Heavy agents on GPT Pro flat rate ($0/token). Utility on cheap per-token.
- **Deterministic-first**: Python owns the decision loop. OpenCode is the executor. State is durable.
- **Store surprises, not everything**: Only failures, insights, decisions, and heuristics persist. Raw logs are transient.

## Prior Attempts and Lessons
From today's 4 improvement cycles:
- Prompt engineering yielded the biggest gains (cycle 2: +0.134 from one line change).
- Grader bugs can inflate/deflate scores — fix measurement before optimizing.
- Retrieval dedup gave modest but real improvement (+0.030).
- Gold fact coverage remains the hardest metric — requires either semantic matching or very precise prompting.
- The pattern works: emit plan → OpenCode executes → eval scores → human decides keep/revert. The "human decides" step is what we need to automate.

## Named Options for Key Design Decisions

### Memory Persistence Format
- **A) JSON files** — one file per memory layer (episodic.json, skills.json). Simple, git-trackable, already used for skills.
- **B) SQLite** — single state.db file. Better for querying experiment history. Still single-file, no new deps.
- **C) Hybrid** — SQLite for episodic (queryable history), JSON for semantic (git-trackable heuristics).

### Autonomous Task Generation
- **A) Template-based** — hardcoded improvement strategies: "if recall < threshold, try X; if facts < threshold, try Y." Simple, predictable, limited.
- **B) LLM-generated** — feed eval results to the PROJECT tier model, ask it to propose the next improvement. More flexible, costs tokens.
- **C) Hybrid** — template-based for known patterns, LLM escalation for novel situations.

### Keep/Revert Mechanism
- **A) Git-based** — commit before each change, revert on regression. Clean, auditable.
- **B) State-based** — snapshot state.db.json before/after, restore on regression. Doesn't revert code.
- **C) Both** — git commit for code changes, state snapshot for system state.

## Decision Questions
1. What is the correct implementation order for the missing components?
2. Which memory persistence format should we use?
3. What is the minimum viable autonomous loop — which components are truly required vs nice-to-have?
4. Should episodic memory and heuristic capture be wired into the existing experiment_loop in main.py, or do they need their own module?
5. How many unattended improvement cycles should the first test target? (1? 5? 10?)

## Required Output Schema (JSON only)
```json
{
  "meta": {
    "caller": "planner",
    "confidence_score": 0.0,
    "confidence_rationale": "string"
  },
  "design_decisions": {
    "memory_format": {
      "chosen": "A|B|C",
      "rationale": "string"
    },
    "task_generation": {
      "chosen": "A|B|C",
      "rationale": "string"
    },
    "keep_revert": {
      "chosen": "A|B|C",
      "rationale": "string"
    },
    "memory_module_location": {
      "chosen": "extend_main|new_module|extend_memory",
      "rationale": "string"
    },
    "first_test_cycles": {
      "count": 0,
      "rationale": "string"
    }
  },
  "ordered_tasks": [
    {
      "task_id": "T-01",
      "name": "string",
      "description": "string",
      "dependencies": [],
      "files_to_modify": ["string"],
      "evaluation_criteria": ["string"],
      "risk": "low|medium|high",
      "why_this_order": "string"
    }
  ],
  "minimum_viable_loop": {
    "required_tasks": ["T-01"],
    "nice_to_have_tasks": ["T-05"],
    "description": "string"
  },
  "kill_criteria": {
    "stop_when": ["string"],
    "pivot_to": "string"
  },
  "verification": {
    "how_to_confirm": "string",
    "observable_result": "string"
  }
}
```

Rules:
- Return JSON only (no markdown fences).
- Keep `ordered_tasks` to 5-8 items.
- Make evaluation criteria observable and testable.
- Each task must be independently valuable when completed.
- Respect the self-reliance constraint: no OMO/third-party dependencies in core path.

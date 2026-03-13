# O1 Strategic Decision Document

> **Purpose:** Structured input for O1 strategic reasoning, following the O1 Input Contract (CANON.md Section 14, 17, 18). This document is designed to be submitted as a single prompt to O1 for architectural adjudication.

---

## Objective

Design the **minimal viable self-improvement engine** — a generic, goal-agnostic loop system that can autonomously run try→measure→keep/revert experiments against any quantifiable objective.

### Explicit Success Metrics

1. The system can accept a goal with a measurable metric and autonomously run improvement experiments
2. State is checkpointed between every loop iteration — survives crashes and restarts
3. Memory prevents duplicate experiments — system queries past results before starting new ones
4. Escalation works — after N consecutive failures, the system escalates through tiers: worker → critic → frontier reasoning model (Opus 4.6, GPT 5.4) → O1 (only for genuinely novel strategic reframing, not routine debugging)
5. The first concrete use case (local LLM model optimization on M4 Pro) produces measurable improvement within 24 hours of autonomous operation
6. Total new code is under 500 LOC (excluding tests)

---

## Current State Snapshot

```json
{
  "hardware": {
    "machine": "Apple M4 Pro",
    "memory_gb": 24,
    "unified_memory": true,
    "gpu_cores": 20,
    "notes": "MLX preferred over Ollama (native speculative decoding, 10-25% faster on Apple Silicon, no HTTP overhead). 70B Q4 does NOT fit (~40GB). Practical ceiling: 32B Q4 (~20GB) + 1.5B draft (~1.5GB) = ~21.5GB."
  },
  "infrastructure": {
    "vps": "148.230.95.154 (obsidian.1215group.com) — 16+ Docker services",
    "database": "Postgres 16 + pgvector on VPS",
    "local_services": ["MLX (preferred, native Python API)", "Ollama (localhost:11434, fallback)", "Claude Code CLI (Max subscription)"]
  },
  "existing_code": {
    "ai_lab_package": {
      "total_loc": 1169,
      "modules": {
        "llm.py": "Unified LLM client with transparent O1/O3 API quirk handling — 130 LOC",
        "config.py": "Model routing, safety thresholds, .env loader — 101 LOC",
        "main.py": "Three nested loops: strategic → project → experiment — 186 LOC",
        "planner.py": "O1 strategic planning + failure diagnosis — 323 LOC",
        "critic.py": "Critic/evaluator with JSON verdict parsing — 113 LOC",
        "worker.py": "Stateless task execution (fast tier) — 65 LOC",
        "state.py": "5-layer memory hierarchy, JSON serialization, resume — 121 LOC",
        "memory.py": "Persistent skill heuristics + artifact registry — 95 LOC",
        "tools.py": "Deterministic tools: Python exec, shell, file I/O — 86 LOC"
      },
      "strategy_docs": {
        "CANON.md": "Product spec authority — 18 sections including O1 prompt contracts",
        "o1_system_prompt.md": "Chief Strategist role definition",
        "o1_next_question_mvp.md": "MVP scoping template for O1 queries"
      }
    },
    "reference_implementations": {
      "autoresearch_mlx": "Apple Silicon port of karpathy/autoresearch — autonomous ML research loop. Key pattern: modify→commit→run→measure→keep/revert with git branch as state (lives in agent-os/references/)."
    }
  },
  "models_available": {
    "local_mlx": {
      "viable_configs": [
        "Qwen2.5-32B Q4_0 + 1.5B Q4_K_M draft (~21GB, ~25-30 tok/s with speculative decoding)",
        "Qwen2.5-14B Q4_K_M + 1.5B Q6_K draft (~12GB, ~50-55 tok/s with speculative decoding)"
      ],
      "does_not_fit": "Qwen2.5-72B (~40GB+ at any quantization)",
      "speculative_decoding_data": {
        "source": "draftbench (alexziskind1/draftbench) — real M4 Max 128GB benchmarks, Qwen2.5 family",
        "key_finding": "1.5B draft is universal sweet spot: 79-86% acceptance, 55-200% speedup depending on target size",
        "why_1_5b": "0.5B too low acceptance (~60-70%), 3B/7B too slow as draft — draft generation becomes bottleneck",
        "draft_quant_insensitive": "1.5B is small enough that Q4 vs Q6 vs Q8 barely affects memory or speed"
      }
    },
    "local_ollama_fallback": ["qwen2.5-coder:32b", "gemma3:27b"],
    "cheap_api_baseline": {
      "purpose": "Establish cost-quality Pareto frontier — local models must BEAT these to justify local-only operation",
      "candidates": [
        {"model": "Kimi K2", "output_per_1M": "$0.60", "daily_50k": "$0.03", "notes": "SWE-bench 65.8%, purpose-built for agentic tool use"},
        {"model": "DeepSeek V3", "output_per_1M": "$1.10", "daily_50k": "$0.055", "notes": "HumanEval 89.9%, native function calling, proven workhorse"},
        {"model": "Qwen2.5-Coder-32B (Together)", "output_per_1M": "$0.20", "daily_50k": "$0.01", "notes": "Same model family as local — direct quality comparison possible"},
        {"model": "Gemini 2.5 Flash (no thinking)", "output_per_1M": "$0.60", "daily_50k": "$0.03", "notes": "1M context, strong tool calling"},
        {"model": "MiniMax M1", "output_per_1M": "$1.10", "daily_50k": "$0.055", "notes": "456B MoE, 1M context"}
      ],
      "reference_leaderboards": [
        "HuggingFace Open LLM Leaderboard v2 (general capabilities)",
        "Berkeley Function Calling Leaderboard / BFCL (tool use accuracy)",
        "BigCodeBench (code generation)"
      ]
    },
    "api_medium": ["gemini-2.5-flash (via API key)", "openrouter (backup)"],
    "api_heavy": ["claude-opus-4-6 (via Max subscription CLI)", "o1 (via OpenAI API)"]
  }
}
```

---

## Constraints

1. **Budget:** Near-$0 for continuous operation preferred, but not dogmatic. Cheap API models ($0.01-0.06/day at 50K tokens) are acceptable if they outperform local models on tool calling accuracy and code quality. API calls for rare strategic decisions (O1) and per-experiment evaluation (Gemini Flash). Local (MLX) preferred for offline/unattended operation and zero marginal cost.
2. **Memory:** 24GB unified. Practical ceiling: 32B Q4 target + 1.5B draft (~21.5GB). 70B does NOT fit at any quantization.
3. **Complexity:** Max 500 LOC of new code. Extend existing `ai-lab/` modules rather than greenfield.
4. **Dependencies:** Strongly prefer zero new dependencies. LangGraph is a possibility but must justify its weight.
5. **Autonomy:** Must run unattended for hours/days. No human-in-the-loop during execution.
6. **Safety:** All experiments must be reversible. No destructive actions without checkpointing.
7. **Generality:** The loop engine must be goal-agnostic. First use case is model optimization, but the same engine should work for code refactoring, prompt tuning, workflow optimization, etc.

---

## What Has Already Been Tried

1. **OpenClaw v1/v2 (agent-os):** Memory bank system with typed facts, hybrid retrieval. Worked for storage/recall. Failed at: autonomous improvement loops — no loop controller, no experiment discipline, no escalation. Became bloated (2000+ LOC).
2. **Manual agent mesh (agent-os):** 20 agents + 29 skills built by hand in `.claude/`. Works for human-directed tasks. Fails at: autonomous operation — agents don't self-direct.
3. **ai-lab/ (this repo):** Three-loop orchestration, O1 planning, critic/worker pattern, state checkpointing — all working. Missing: the autoresearch-style try→measure→keep/revert discipline for self-improvement goals.
4. **Autoresearch (reference):** Karpathy's pattern works beautifully for ML training. We've ported it to MLX. But it's hardcoded for one specific loop (train LLM, measure val_bpb). We need the generic version integrated into ai-lab/.

### Failure Signatures

- OpenClaw became bloated (2000+ LOC) before delivering a single autonomous improvement
- Previous attempts at "generic frameworks" produced abstractions without concrete first use cases
- LangChain evaluation showed our stack already covers most of what the framework offers, minus graph execution

---

## Key Decision Questions

### Q1: LangGraph vs Custom State Management

Given that `ai-lab/` already provides a working three-loop orchestration, O1 API handling, state checkpointing, and escalation — is LangGraph's graph execution engine worth the dependency weight?

**Specific sub-questions:**
- Does LangGraph's checkpointing save us meaningful implementation effort vs a simple JSON checkpoint system?
- Does graph-based conditional routing add value for our use case (which is essentially a linear loop with an escalation branch)?
- What's the realistic migration cost if we start custom and later want LangGraph?
- Does LangGraph have Apple Silicon / MLX-specific concerns?

### Q2: Optimal First Experiment — Model Optimization on M4 Pro

What is the optimal experiment sequence for local LLM optimization?

**Context:** We have 24GB unified memory with MLX (native speculative decoding support). Empirical data from draftbench (M4 Max 128GB, Qwen2.5 family) shows:
- **1.5B draft is the universal sweet spot** — 79-86% acceptance rate, 55-200% speedup
- **Qwen2.5 family** ideal for speculative decoding (shared tokenizer across sizes)
- Two viable configs for 24GB: 32B Q4 + 1.5B draft (~21GB, quality-focused) or 14B Q4 + 1.5B draft (~12GB, speed-focused)

**Specific sub-questions:**
- Which metrics should we optimize for? We prefer: **token efficiency** (useful output per token spent), **tool calling accuracy** (BFCL methodology), **improvement slope** (rate of improvement per iteration), and **rubric-based task completion quality** — NOT wall-clock time.
- Between 32B Q4 (quality, ~25-30 tok/s) and 14B Q4 (speed, ~50-55 tok/s), which is the better worker tier starting point?
- How do we evaluate "quality" for a worker model without expensive ground truth?
- Can we run worker + critic simultaneously on 24GB (e.g., 14B worker + 1.5B critic), or must they time-share?
- Should the first experiment benchmark these configs on OUR hardware (M4 Pro 24GB) before proceeding to loop construction?

### Q3: Minimal Viable Improvement Loop

What is the absolute minimum implementation that still qualifies as a self-improving system?

**Specific sub-questions:**
- What state fields are required for clean long-horizon evolution?
- What's the minimum checkpoint schema?
- Should the loop controller be a Python script, a Claude Code agent, or something else?
- How should the loop handle goals that don't have simple numeric metrics?

### Q4: Loop Chaining for Compound Goals

How should improvement loops compose to achieve complex objectives?

**Example:** "Optimize my development environment" requires: optimize LLMs → optimize tools that use LLMs → optimize workflows that use tools → optimize the orchestrator that manages workflows.

**Specific sub-questions:**
- Sequential chaining (finish one, start next) or concurrent?
- How does one loop's output become another loop's input?
- How do we prevent infinite recursion (loop optimizing itself)?
- What's the right granularity for loop boundaries?

### Q5: Local vs Cheap API — Where is the Crossover?

Given that cheap API models (DeepSeek V3 at $0.055/day, Kimi K2 at $0.03/day, Qwen2.5-Coder-32B at $0.01/day) may outperform local 32B Q4 on tool calling and code quality, how should we decide between local and API workers?

**Specific sub-questions:**
- Should the first experiment establish a **cost-quality Pareto frontier** by benchmarking local models against cheap API models on the same eval suite (BFCL + code tasks)?
- What's the right framework for this decision? Pure quality? Quality-per-dollar? Factor in latency, offline capability, privacy?
- Could a hybrid approach work — local for high-volume simple tasks, API for complex tool-calling chains?
- How do we keep this decision dynamic as both local models (new quantizations, new architectures) and API prices change?

---

## Canonical O1 Questions (Section 17 of CANON.md)

### 1. Problem Framing
What problem are we actually solving, and what is the most likely misframing?

### 2. Success Contract
What are the measurable success criteria and stopping conditions for the MVP?

### 3. Decomposition
What is the minimal viable decomposition that preserves reliability?

### 4. Failure Forecasting
What are the top 3 failure modes, their early warning signals, and mitigations?

### 5. Determinism Boundary
Which components must be deterministic (state management, checkpointing) and which should remain probabilistic (model selection, experiment ideas)?

### 6. State Design
What state fields are required for clean long-horizon evolution? Propose a concrete schema.

### 7. Escalation Policy
What precise thresholds should trigger escalation at each tier? The escalation chain is: **worker → critic → frontier model (Opus 4.6/GPT 5.4) → O1**.

**O1 invocation is a last resort with preconditions:**
1. Tier 3 (frontier model) is stuck AND improvement slope indicates significant gains remain (we're NOT past diminishing returns — if we are, accept the plateau, don't escalate)
2. Before calling O1, tier 3 must articulate: "What question am I trying to answer?" If it can't clearly state the question, that's the O1 signal — the framing is broken
3. O1 always validates the question before answering it. Never jump to solutions. (Ref: Hitchhiker's Guide — the answer "42" is useless without knowing the question. O1 is Deep Thought; don't waste it on a question nobody has verified.)

What signals distinguish "stuck on execution" (tier 3 handles), "past diminishing returns" (accept plateau, stop), and "asking the wrong question" (O1 territory)?

### 8. Evaluation Policy
How should experiment outputs be scored so we optimize for real progress, not proxy quality? Preferred metrics: token efficiency, tool calling accuracy (BFCL methodology), improvement slope per iteration, and rubric-based task completion quality. Wall-clock time is explicitly NOT a priority.

### 9. Cost and Latency
Where is heavy-model reasoning highest leverage (planning? evaluation? both?) and where is it waste? Note: we expect frontier reasoning models (Opus 4.6, GPT 5.4) to handle ~95% of what we currently route to O1. O1 should be reserved for genuinely novel strategic questions where the problem framing itself needs validation.

### 10. Reversibility and Safety
What decisions are hard to undo, and what guardrails are required before execution?

---

## Meta-Question: Validate Our Framing

Before answering the questions above, please evaluate the questions themselves:

1. **Are we asking the right questions?** If any of the questions above are poorly framed, misleading, or missing the point, say so. Tell us what we SHOULD be asking instead.
2. **Is there a better way to frame this problem?** We may have blind spots in our mental model. If our assumptions (listed in the state snapshot and constraints) reveal a flawed premise, call it out.
3. **What are we not seeing?** What obvious failure modes, architectural patterns, or prior art should we be aware of that this document doesn't reference?
4. **Do we share the same mental model?** Restate in 2-3 sentences what you understand our goal to be. If your restatement surprises us, we have a misalignment to fix before proceeding.

This section is the most important part of the prompt. A perfect answer to a wrong question is worse than no answer at all.

---

## Required Output Schema

```json
{
  "decision_framework": {
    "langgraph_vs_custom": {
      "recommendation": "langgraph | custom | hybrid",
      "rationale": "string",
      "rejected_alternative": "string",
      "confidence": "high | medium | low",
      "assumptions": ["string"]
    },
    "first_experiment_sequence": {
      "metric": "string (what we measure)",
      "experiments_ordered": [
        {
          "id": "E-01",
          "name": "string",
          "what_to_try": "string",
          "expected_outcome": "string",
          "evaluation_criteria": ["string"],
          "risk": "low | medium | high"
        }
      ]
    }
  },
  "mvp_scope": {
    "name": "string",
    "description": "string",
    "non_goals": ["string"],
    "state_schema": {
      "fields": [
        {
          "name": "string",
          "type": "string",
          "purpose": "string"
        }
      ]
    }
  },
  "task_graph": {
    "tasks": [
      {
        "task_id": "T-01",
        "name": "string",
        "description": "string",
        "dependencies": [],
        "methodology": "string",
        "inputs": ["string"],
        "evaluation_criteria": [
          "Rubric Item 1 (3 points): Condition X is met.",
          "Rubric Item 2 (4 points): Condition Y executes properly.",
          "Rubric Item 3 (3 points): Output matches format Z."
        ],
        "notes": "string"
      }
    ],
    "global_constraints": ["string"]
  },
  "loop_chaining_strategy": {
    "approach": "string",
    "recursion_guard": "string",
    "granularity_heuristic": "string"
  },
  "escalation_policy": {
    "tiers": [
      {
        "tier": 1,
        "role": "string",
        "models": ["string"],
        "escalation_signal": "string"
      }
    ],
    "plateau_detection": "string (how to detect diminishing returns — when to STOP escalating and accept current state)",
    "o1_preconditions": [
      "Tier 3 frontier model is stuck",
      "Improvement slope indicates significant gains remain (NOT past diminishing returns)",
      "Tier 3 cannot clearly articulate what question it is trying to answer"
    ],
    "o1_first_action": "Validate the question before answering it. Restate the problem. Identify framing errors. Only then propose solutions.",
    "three_way_signal": {
      "stuck_on_execution": "string (tier 3 handles — knows the question, can't find the answer)",
      "past_diminishing_returns": "string (accept plateau — stop escalating, the juice isn't worth the squeeze)",
      "wrong_question": "string (O1 territory — can't even articulate what we're optimizing for)"
    }
  },
  "meta_validation": {
    "restated_goal": "string (2-3 sentences — what you understand our goal to be)",
    "framing_issues": ["string (any questions above that are poorly framed or missing the point)"],
    "better_questions": ["string (questions we should be asking instead)"],
    "blind_spots": ["string (failure modes, patterns, or prior art we're not seeing)"],
    "mental_model_aligned": true
  },
  "escalation_triggers": ["string"],
  "open_questions": ["string"],
  "key_assumptions": ["string"]
}
```

---

## Reference: Architecture Diagrams

See `docs/lab/architecture.md` for full Mermaid diagrams of:
1. System overview (orchestrator → loops → tools → foundation)
2. Generic improvement loop state machine
3. Memory & state system layers
4. Agent topology with model tier mapping
5. Optimization sequence (layers 1→4)
6. Autoresearch pattern (the discipline we're abstracting)

---

## Reference: Autoresearch Loop Discipline

From `references/AutoResearch-mac/autoresearch-mlx/program.md`:

```
LOOP FOREVER:
1. Look at git state (current branch/commit)
2. Modify train.py with experimental idea
3. git commit -m "experiment: <description>"
4. Run experiment: uv run train.py > run.log 2>&1
5. Read results: grep "^val_bpb:" run.log
6. If improved → keep commit, advance branch
7. If worse → git reset --hard (revert to last keep)
8. Log result in results.tsv
9. Never stop. Loop until interrupted.
```

**Properties we preserve in our generic version:**
- Atomic experiments (committed before running)
- Single metric as truth (no subjective judgment)
- Git branch as state (tip = best known config)
- Autonomous operation (no human-in-the-loop)
- Crash recovery (revert to last good state)
- Results logging (structured record of all attempts)

---

## Reference: O1 AI Lab Patterns

From `ai-lab/` (this repo):

**Four-tier escalation:**
- Tier 1 (Worker): Fast, cheap — executes experiments and tries permutations (local MLX or cheap API)
- Tier 2 (Critic): Mid-tier — evaluates against success criteria (Gemini Flash, DeepSeek V3)
- Tier 3 (Frontier Reasoner): Opus 4.6, GPT 5.4 — diagnoses failures, reframes stuck experiments (~95% of "hard" problems)
- Tier 4 (Strategic Oracle / O1): Rare — only when the problem framing itself may be wrong, or for novel architectural decisions where shared mental model alignment is critical

**5-layer memory:** Identity → Working → Episodic → Semantic → Artifact

**Project graph schema:** task_id, name, description, dependencies, methodology, inputs, evaluation_criteria (10-point rubric), notes

**Strategic output contract:** Chosen strategy + rationale, rejected alternatives + reasons, key assumptions + confidence, concrete next tasks + evaluation criteria, escalation trigger conditions

---

## Reference: Speculative Decoding Benchmarks (draftbench)

**Source:** `alexziskind1/draftbench` — automated sweep tool for finding optimal draft model pairings with llama.cpp on Apple Silicon.

**Hardware:** M4 Max 128GB (benchmarks transfer in relative terms to M4 Pro 24GB, absolute throughput will differ).

### Key Results (Qwen2.5 family, llama.cpp)

| Target | Quant | Baseline tok/s | Best Draft | Draft Quant | With Draft tok/s | Speedup | Acceptance |
|--------|-------|----------------|------------|-------------|-----------------|---------|------------|
| 72B | Q8_0 | 6.45 | 1.5B | Q6_K | 19.33 | **+200%** | 84% |
| 72B | Q4_K_M | 9.36 | 1.5B | Q4_K_M | 18.74 | **+100%** | 83% |
| 32B | Q8_0 | 13.33 | 1.5B | Q6_K | 33.37 | **+150%** | 79% |
| 32B | Q4_K_M | 20.72 | 1.5B | Q6_K | 33.11 | **+60%** | 79% |
| 32B | Q4_0 | 23.56 | 1.5B | Q4_K_M | 36.49 | **+55%** | 86% |
| 14B | Q8_0 | 30.03 | 1.5B | Q4_0 | 66.98 | **+123%** | ~82% |
| 14B | FP16 | 16.82 | 1.5B | Q4_0 | 59.91 | **+256%** | ~80% |

### Implications for M4 Pro 24GB

- **72B: Does not fit** (~40GB+ at any quantization)
- **32B Q4_0 + 1.5B Q4_K_M: ~21GB** — fits tightly, quality-focused config, ~25-30 tok/s estimated
- **14B Q4_K_M + 1.5B Q6_K: ~12GB** — comfortable fit, speed-focused config, ~50-55 tok/s estimated, leaves room for concurrent processes
- **MLX preferred over Ollama:** MLX supports speculative decoding natively; Ollama does not
- **Draft quantization is nearly irrelevant** at 1.5B scale — pick Q4_K_M or Q6_K, difference is negligible

# CLAUDE.md — Autonomous R&D Lab (01)

A self-improving autonomous engineering system. O1 plans, workers execute, critics evaluate, and the system learns from every experiment. This repo builds and optimizes itself.

## What This Is

Three nested loops that run autonomously:
- **Strategic Loop** (O1) — Plans task graphs, diagnoses failures. Called rarely.
- **Project Loop** (GPT-4o / Gemini) — Evaluates results, manages task queue.
- **Experiment Loop** (Ollama / fast) — Executes tasks, runs 100s of attempts.

## Quick Start

```bash
cp .env.example .env        # Add your OPENAI_API_KEY
uv sync                     # Install deps
cd ai-lab && uv run main.py "Your goal here"
```

## Module Map (~1,700 LOC core + ~900 LOC evals)

| File | Role |
|------|------|
| `ai-lab/main.py` | Three-loop orchestration engine |
| `ai-lab/planner.py` | O1 strategic planning + failure diagnosis |
| `ai-lab/llm.py` | Unified LLM client (handles O1 API quirks) |
| `ai-lab/critic.py` | Worker output evaluation + scoring |
| `ai-lab/worker.py` | Stateless task execution (fast tier) |
| `ai-lab/state.py` | 5-layer memory hierarchy, JSON checkpoint/resume |
| `ai-lab/memory.py` | Skill heuristics DB + vector search (Ollama embeddings) |
| `ai-lab/config.py` | Model routing, thresholds, env config |
| `ai-lab/tools.py` | Deterministic tools: Python exec, shell, file I/O |
| `ai-lab/evals/knowledge_plane/` | A/B retrieval eval harness (10 cases, 5 buckets) |

## Key Documents

| Document | Purpose |
|----------|---------|
| `CANON.md` | Product spec authority — all decisions checked against this |
| `docs/ORIGIN.md` | Design narrative distilled from the founding GPT-5.4 conversation |
| `ai-lab/o1_system_prompt.md` | Chief Strategist role definition for O1 |
| `ai-lab/o1_next_question_mvp.md` | Template for structured O1 queries |
| `docs/lab/architecture.md` | Mermaid diagrams of full system architecture |
| `docs/lab/o1-strategy-prompt.md` | Structured O1 decision query for next phase |

## Key Rules

1. **CANON.md is the source of truth** — architecture changes are product-spec changes
2. **O1 questions must include**: objective, state snapshot, constraints, prior attempts, decision question, output schema (Section 18)
3. **State over context** — context windows are disposable; `state.db.json` is durable
4. **Escalation is bounded** — max 5 worker failures → critic escalation → O1 strategic replan
5. **Simplicity constraint** — no feature added unless it improves reliability, observability, or decision quality
6. **Keep docs in sync** — when adding new top-level directories, key files, or documents, update the Module Map and Key Documents above. Use `wc -l ai-lab/*.py` for accurate LOC if needed; do not hardcode line counts in docs

## Model Tiers

| Tier | Default Model | Role | Cost |
|------|---------------|------|------|
| STRATEGIC | `o1` | Planning, diagnosis | $$ (rare) |
| PROJECT | `gpt-4o` | Evaluation, routing | $ |
| WORKER | `gpt-4o-mini` | Execution, attempts | ¢ |
| LOCAL_WORKER | Ollama `qwen2.5-coder:14b` | Local execution | $0 |

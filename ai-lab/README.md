# AI Lab — Autonomous Engineering System

A LangGraph-inspired autonomous agent system with **OpenAI o1** as the strategic planner.

## Architecture

```
STRATEGIC LOOP  →  o1             (plan, diagnose failures)
PROJECT LOOP    →  gpt-4o         (evaluate, route tasks)
EXPERIMENT LOOP →  gpt-4o-mini    (execute, 100s of attempts)
```

## Quick Start

```bash
# 1. Provide dependencies
uv sync

# 2. Set your API key
cp .env.example .env
# Edit .env and paste your OPENAI_API_KEY

# 3. Run
cd ai-lab
uv run main.py "Design a lightweight prosthetic ankle joint"
```

## Configuration

All settings live in `.env` (copy from `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | *(required)* | Your OpenAI API key |
| `STRATEGIC_MODEL` | `o1` | Model for planning/diagnosis |
| `PROJECT_MODEL` | `gpt-4o` | Model for evaluation/routing |
| `WORKER_MODEL` | `gpt-4o-mini` | Model for execution |
| `O1_REASONING_EFFORT` | `high` | o1 reasoning depth: low/medium/high |
| `ESCALATE_THRESHOLD` | `5` | Worker failures before calling o1 |

## Module Overview

| File | Role |
|---|---|
| `config.py` | Loads `.env`, defines model tiers and thresholds |
| `llm.py` | Unified LLM client; handles o1's API quirks transparently |
| `state.py` | Mutable state object (5-layer memory hierarchy) |
| `planner.py` | Strategic loop — calls o1 for project graphs & failure diagnosis |
| `worker.py` | Experiment loop — stateless task execution |
| `critic.py` | Critic/evaluator — rates worker output, suggests improvements |
| `memory.py` | Persistent skill heuristics + artifact registry |
| `tools.py` | Deterministic tools (Python exec, shell, file I/O) |
| `main.py` | Orchestration engine — wires all three loops together |

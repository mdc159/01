# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

`o1-ai-lab` — a compact autonomous engineering/research system that decomposes broad goals into experiments, runs them continuously at low cost, learns from outcomes, and escalates to high-reasoning models (OpenAI o1) only when needed. Three nested loops (strategic → project → experiment) wrapped around the [autoresearch](https://github.com/karpathy/autoresearch) keep/revert discipline. No LangChain, no LangGraph — the whole engine is ~1,700 LOC of plain Python.

The system is designed to improve itself. Goal #001 was "optimize local LLM inference on Apple Silicon"; subsequent goals target the lab's own model routing, prompts, and loop structure.

## Common Commands

All Python work uses **uv** (not pip/venv directly). Python ≥3.10. Run commands from the **repo root** unless noted.

```bash
# Install / sync dependencies
uv sync

# Configure (required — at minimum set OPENAI_API_KEY)
cp .env.example .env && $EDITOR .env

# Initialize submodules (references/ contains 6 git submodules)
git submodule update --init --recursive

# ── Run the lab ─────────────────────────────────────────────────
cd ai-lab && uv run main.py "Your goal here"

# Route experiment-loop tasks through OpenCode/OMO agents instead of built-in worker
OPENCODE_EXECUTOR=1 OPENCODE_AGENT=sisyphus uv run main.py "Your goal"

# Ask o1 a strategic question directly (skips the loop machinery)
uv run ask_o1.py "Your question"
uv run ask_o1.py --file ../docs/lab/o1-strategy-prompt.md
uv run ask_o1.py --effort medium "Cheaper quick question"

# ── Tests / eval harness ───────────────────────────────────────
cd ai-lab && uv run python test_integration.py   # Plan→Execute→Evaluate pipeline
uv run python -m evals.knowledge_plane.runner \
    --cases evals/knowledge_plane/cases.jsonl \
    --arm local --model gpt-4o-mini \
    --local-backend evals.knowledge_plane.local_backend:RepoSearchBackend

# ── Daemon / goal queue / API server ───────────────────────────
cd ai-lab && uv run daemon.py                    # Poll goal queue, run goals
uv run daemon.py --submit "Your goal"            # Enqueue without running
uv run daemon.py --status                        # Show queue
uv run uvicorn api:app --host 0.0.0.0 --port 8100  # FastAPI + Telegram webhook
uv run heartbeat.py                              # Telegram bot (long-polling)
```

## Architecture — Critical Concepts

### Three nested loops (`ai-lab/main.py`)

```
STRATEGIC (o1) ──┐  called rarely: new goals, escalations, diagnosis
  PROJECT (gpt-4o) ──┐  task queue iteration, evaluation
    EXPERIMENT (worker/OpenCode) ──┐  try → critic → keep or retry
```

Escalation is bounded: after `ESCALATE_THRESHOLD` (default 5) worker failures on a task, the loop escalates to the strategic tier for replanning. `MAX_STRATEGIC_REPLANS_PER_TASK` (default 3) prevents infinite escalation. `MAX_PROJECT_ITERATIONS` (default 200) is the absolute safety cap.

### Model tiers are roles, not hardcoded models

`ai-lab/config.py:Models` routes four tiers (STRATEGIC / PROJECT / WORKER / LOCAL_WORKER) via env vars. Which model fills each tier is itself an optimization target — swapping is a `.env` edit, never a code change. `llm.py` handles o1/o3 API quirks transparently (`max_completion_tokens` instead of `max_tokens`, no temperature, no streaming, `reasoning_effort` parameter).

**Budget enforcement:** `config.py:Budget.CAP_USD` (default $5) tracks spend; at the cap the system auto-falls-back to Ollama. There's also a graceful startup path when `OPENAI_API_KEY` is missing — falls through to Ollama-only.

### State over context

Context windows are disposable. `ai-lab/state.py:SystemState` is the durable truth:
- **Identity / Working / Episodic / Semantic / Artifact** — 5-layer memory hierarchy
- Checkpointed to `state.db.json` between every loop iteration
- `SystemState.load(path)` resumes cleanly from any checkpoint
- `ai-lab/memory.py:EpisodicMemory` persists experiment-level history across runs in `episodic.json`

Heuristics learned across runs land in `skills.json` / `heuristics.json` and are re-injected into working constraints at session start.

### v2 Strategic Query Contract

Any call to the strategic tier must follow the 12-part protocol in `ai-lab/o1_next_question_v2.md`: meta + objective + state snapshot + constraints with blast radius + prior attempts + **explicit option set** (never open-ended "what's optimal?") + assumptions + decision question + required output schema. `ai-lab/o1_system_prompt.md` is the Chief Strategist role definition, auto-loaded as the system prompt in `planner.py:_load_system_context()`.

Key rule: **if strategist confidence < `O1_CONFIDENCE_THRESHOLD` (default 0.75), output an experiment, not a plan.** Uncertainty contracts beat confident plans built on shaky premises.

### Experiment atomicity (autoresearch discipline)

Every experiment follows: git commit → run → measure → keep (advance branch) or revert (`git reset --hard`). `ai-lab/tools.py` provides `git_snapshot()` / `git_revert()`. Metrics are the only truth — no subjective "looks better". The eval gate (`ai-lab/main.py:run_eval_gate`) runs `evals/knowledge_plane/runner.py`; score below `EVAL_SCORE_THRESHOLD` (default 0.56) blocks keep and reverts.

### OpenCode executor mode

When `OPENCODE_EXECUTOR=1`, `main.py` routes experiment-loop tasks through `opencode_executor.py` → `opencode run --format json` → OMO agents, instead of the built-in worker. OpenCode handles its own retries inside the agent loop, so the Python side runs it once and reads the structured result (session_id, tokens, cost, files_changed, tools_used). Select agent via `OPENCODE_AGENT=sisyphus`, model via `OPENCODE_MODEL=openai/gpt-5.3-codex`.

### Persistence backends

`ai-lab/db.py` abstracts goal-queue storage. Default is JSON files (`goals.json`, `episodic.json`, `skills.json`); if `DATABASE_URL` is set, it uses Postgres (psycopg) with the schema in `ai-lab/db/init.sql`. All modules call `db.*` — never read/write queue files directly.

## Key Files and Layout

```
ai-lab/              Core engine
├── main.py          Three-loop orchestration + OpenCode routing + eval gate
├── planner.py       o1 strategic planning, sisyphus plan emission, failure diagnosis
├── llm.py           Unified client (o1/o3 quirks + Ollama + OpenAI)
├── worker.py        Stateless task execution (fast tier)
├── critic.py        Output evaluation / scoring
├── state.py         5-layer memory, JSON checkpoint/resume
├── memory.py        Skills DB + EpisodicMemory + vector search
├── config.py        Models, Budget, Thresholds, Paths
├── tools.py         Deterministic: Python exec, shell, file I/O, git snapshot/revert
├── db.py            Goal queue (JSON or Postgres)
├── daemon.py        Long-running goal-queue poller
├── api.py           FastAPI + Telegram webhook
├── heartbeat.py     Telegram bot (long-polling) — "single point of contact"
├── opencode_executor.py   OpenCode JSON event bridge
├── ask_o1.py        Direct o1 CLI
├── o1_system_prompt.md    Chief Strategist role (loaded at planner startup)
├── o1_next_question_v2.md v2 query contract template
└── evals/knowledge_plane/ Eval harness (10 cases, 4 metrics, RRF retrieval)

docs/lab/            Architecture docs, mermaid diagrams, model-eval reports
.sisyphus/plans/     Planner-emitted markdown plans (Atlas-compatible checklists)
PRPs/                Product requirement prompts
references/          Git submodules (autoresearch variants, opencode, oh-my-opencode)
```

## Non-Obvious Gotchas

- **`CANON.md` was deleted** (commit `3838bf2`) but `planner.py:_load_system_context()` still tries to load it from `Paths.ROOT.parent / "CANON.md"`. The fallback path is silent — if you need the canon-aware system prompt back, check `tmp/CANON.md` for the historical content. The strategist currently runs without the canonical product contract.
- **`planner.py` also expects `CLAUDE.md` semantics from the deleted root files.** The old CLAUDE.md/CANON.md content survives in `tmp/` — treat that directory as the archive of pre-cleanup reference material, not live docs.
- **`ai-lab/artifacts/`, `state.db.json`, `episodic.json`, `skills.json`, `heuristics.json`, `goals.json`, `logs/` are all gitignored** and regenerate on run. Don't check them in.
- **Secrets:** `.env` is gitignored. API keys live there, not in shell rc files. The `config.py` loader reads from `<repo-root>/.env` relative to `ai-lab/config.py`.
- **Ollama is assumed at `http://localhost:11434`** and is the $0 fallback for everything. `LOCAL_WORKER_MODEL` defaults to `llama3` but the `.env.example` ships with `llama3.3:70b`.
- **Submodules matter:** `references/AutoResearch-mac/` has three forks (karpathy / mlx / macos) that goal #001 benchmarks. `references/opencode` and `references/oh-my-opencode` are live dependencies for the OpenCode executor path. Always `git submodule update --init --recursive` after cloning or pulling.
- **Test runner is not pytest.** `ai-lab/test_integration.py` is a standalone script (`uv run python test_integration.py`) that exercises plan-emission and the eval gate end-to-end, including cleanup of a throwaway `.sisyphus/plans/integration-test.md`.
- **VPS / launchd deployment:** `ai-lab/service/com.lab01.daemon.plist` + `keepalive.sh` are the macOS launchd unit. The daemon is designed to survive crashes via an external watchdog.

## Working Rules

1. **Simplicity constraint** — no feature added unless it improves reliability, observability, or decision quality. Two runtime deps only: `openai` + `python-dotenv` (FastAPI/uvicorn/psycopg/httpx are opt-in for the daemon/API layer).
2. **State over prompt history** — never shove more context into a prompt when a state field would do.
3. **Escalation is bounded** — fix the `ESCALATE_THRESHOLD` / `MAX_*` caps in `config.py:Thresholds` before loosening anywhere else.
4. **Reasoning models are not default workers** — keep `o1`/`o3` on the strategic tier only; route everything else through `WORKER_MODEL` or `LOCAL_WORKER_MODEL`.
5. **Self-reliance** — we own every line of the controller loop. Read from third-party state formats (OMO notepads, boulder.json); never depend on them.

# ai-lab/ — Core Engine

The Python modules that implement the three-loop orchestration. See the [root README](../README.md) for full documentation.

## Running

```bash
# Run the lab on a goal
uv run main.py "Your goal here"

# Direct O1 strategic query
uv run ask_o1.py "Your question"
uv run ask_o1.py --file ../docs/lab/o1-strategy-prompt.md

# Lower reasoning effort for cheaper queries
uv run ask_o1.py --effort medium "Quick question"
```

## Module Map

| Module | LOC | Purpose |
|--------|-----|---------|
| `main.py` | 186 | Three-loop orchestration (strategic → project → experiment) |
| `planner.py` | 323 | O1 strategic planning + failure diagnosis |
| `llm.py` | 185 | Unified LLM client: O1 + Ollama + standard OpenAI |
| `critic.py` | 113 | Worker output evaluation against success criteria |
| `state.py` | 121 | 5-layer memory hierarchy, JSON checkpoint/resume |
| `config.py` | 101 | Model routing, thresholds, env config |
| `memory.py` | 95 | Skill heuristics DB + artifact registry |
| `tools.py` | 86 | Deterministic tools: Python exec, shell, file I/O |
| `worker.py` | 65 | Stateless task execution (fast tier) |
| `ask_o1.py` | 97 | Direct O1 CLI for strategic queries |

## Strategy Documents

| Document | Purpose |
|----------|---------|
| `o1_system_prompt.md` | Chief Strategist role definition — loaded as system prompt for O1 |
| `o1_next_question_mvp.md` | Template for structured O1 MVP scoping queries |
| `o1_system_prompt_indexed_draft.md` | Indexed version with section references |

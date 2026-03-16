# Next Session — Goal 001 Complete, Choose Goal 002

## Where We Left Off

Goal 001 V-Model is **COMPLETE**. Full cycle validated:
- Quality ranking matches draftbench (14B coder wins at 24/25)
- MLX confirmed as preferred runtime (8.5 GB, 29 tok/s baseline, +124% with draft on long tasks)
- Bug found through measurable degradation, fixed, verified
- Report: `ai-lab/goal_001_results/GOAL_001_REPORT.md`

## Recommended Worker Tier Config (proven)

- **Runtime:** MLX
- **Target:** Qwen2.5-Coder-14B-Instruct Q4 (8.5 GB)
- **Draft:** Qwen2.5-Coder-1.5B-Instruct Q4 (0.9 GB) — for long tasks
- **Critic:** gpt-4o via API

## What's Next: Choose Goal 002

The lab architecture is validated. Now it needs a goal where we **don't know the answer**.

Candidates from the architecture docs:
1. **Autonomous code improvement** — point the lab at its own codebase and let it optimize
2. **Tool optimization** — fork-terminal workflows, parallel execution patterns
3. **Retrieval memory** — add vector search to skills DB, test against tag-based
4. **Eval harness extraction** — GPT-5.4's 2,691-line eval harness → `ai-lab/evals/`

The key question: which goal will produce the most **compound improvement** for subsequent goals?

## On Deck (not blocking)
- [ ] Extract GPT-5.4's eval harness into `ai-lab/evals/knowledge_plane/`
- [ ] Build the A/B retrieval comparison (local vs hosted)
- [ ] Add vector search to skills DB (currently tag-based)
- [ ] Observability beyond logging

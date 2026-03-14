# Goal 001: Find Optimal Local Worker Model Config on M4 Pro 24GB

## The Validation Play

We already know from Alex Ziskind's draftbench research (alexziskind1/draftbench)
that on Apple Silicon with Qwen2.5 family:

- 1.5B draft model is the universal sweet spot (79-86% acceptance rate)
- Two likely winners for 24GB: 32B Q4 + 1.5B draft (~21GB) or 14B Q4 + 1.5B draft (~12GB)

If our lab converges to one of these, the architecture validates.
If it finds something better, even better.

## Goal String (for main.py)

"Find the optimal local LLM configuration for the worker tier on Apple M4 Pro 24GB.
Evaluate Qwen2.5 model sizes (1.5B, 7B, 14B, 32B) with quantization variants
(Q4_0, Q4_K_M, Q5_K_M, Q8_0) and speculative decoding pairings.
Metric: highest quality score on a fixed task suite within 24GB memory ceiling.
Expected convergence: 14B or 32B target + 1.5B draft."

## Fixed Task Suite (the "metric")

Since we're evaluating inference quality (not training loss), we need a fixed benchmark:

1. **Code generation** — "Write a Python function that implements binary search"
2. **Structured output** — "Given this bug report, output JSON with: root_cause, fix, confidence"
3. **Tool calling** — "Given these available functions, call the right one for: check disk usage"
4. **Reasoning** — "A farmer has 17 sheep. All but 9 die. How many are left?"
5. **Instruction following** — "Rewrite this paragraph in exactly 3 sentences"

Each task scored 0-5 by the critic model. Total score = sum across all 5 tasks (max 25).

## Experiment Matrix

| Config | Target Model | Draft Model | Est. Memory | Est. Speed |
|--------|-------------|-------------|-------------|------------|
| A | Qwen2.5-7B Q4_K_M | none | ~5GB | fast |
| B | Qwen2.5-14B Q4_K_M | none | ~9GB | medium |
| C | Qwen2.5-14B Q4_K_M | Qwen2.5-1.5B Q4_K_M | ~10GB | medium+ |
| D | Qwen2.5-32B Q4_0 | none | ~18GB | slow |
| E | Qwen2.5-32B Q4_0 | Qwen2.5-1.5B Q4_K_M | ~19GB | medium |
| F | Qwen2.5-14B Q5_K_M | Qwen2.5-1.5B Q6_K | ~12GB | medium |

## Expected Convergence

Based on draftbench data (M4 Max 128GB), we expect:
- Configs D/E will be quality leaders but push memory limits on 24GB
- Config C or F will be the sweet spot (quality + headroom for critic)
- Config A will be fast but quality-limited
- 1.5B draft model should show clear speedup with minimal quality loss

## Success Criteria

1. Lab runs end-to-end without crashes for all 6 configs
2. Results clearly differentiate quality across configs
3. Winner aligns with draftbench predictions (validates both the lab AND the research)
4. Escalation triggers correctly if a config crashes or OOMs
5. Skills DB records the winning config as a reusable heuristic

## What This Validates

- Three-loop architecture works (strategic plans → project sequences → experiment runs)
- Worker + critic separation produces useful signal
- Keep/revert discipline works on inference benchmarks (not just training)
- Memory system retains useful heuristics
- Escalation fires when it should
- State checkpointing allows resume after interruption

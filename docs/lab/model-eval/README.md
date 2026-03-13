# Model Evaluation: Strategic Protocol & Platform Decision

Three models (GPT-5.4, Codex, O3) were asked the same two questions about our O1 usage. Their answers were synthesized by Claude Opus 4.6 into the upgraded protocol and system prompt.

## Questions Asked

1. **Protocol:** Are we framing our questions to the strategic reasoning tier in a way that maximally exploits chain-of-thought reasoning? What are we missing?
2. **Platform:** Should we build a dedicated O1-based Assistant on OpenAI's platform, or stick with raw API + our own pgvector + RRF retrieval?

## Responses

| File | Model | Question |
|------|-------|----------|
| `gpt54-q1-protocol.md` | GPT-5.4 | Q1: Protocol gaps |
| `o3-q1-protocol.md` | O3 | Q1: Protocol gaps + schema delta |
| `codex-q2-platform.md` | Codex | Q2: Platform decision |
| `o3-q2-platform.md` | O3 | Q2: Platform decision |
| `gpt54-q2-platform.md` | GPT-5.4 | Q2: Platform decision + A/B eval harness |

## Verdict

- **Q1:** Protocol upgraded from 6-part to 12-part contract (see `o1_next_question_v2.md`)
- **Q2:** Unanimous — local-first with raw API. Assistants API is optional convenience, not capability.

## Model Performance

| Model | Q1 Strength | Q2 Strength | Weakness |
|-------|-------------|-------------|----------|
| O3 | Drop-in schema delta, memory actions field | Dimension-by-dimension tables, decision flow | N/A |
| Codex | Good reframe, clean checklist | Direct "95%, skip it" | Less depth |
| GPT-5.4 | Best conceptual analysis, 5 prompt archetypes | Full A/B eval harness with code, Responses API migration | Repeatedly self-promoted as O1's replacement |

## Final Scorecard

All three models agreed: local-first architecture with raw API is the right default. The synthesis (implemented in `ai-lab/o1_next_question_v2.md` and `ai-lab/o1_system_prompt.md`) takes the best from each:
- **O3:** Schema structure, memory actions, confidence threshold logic
- **GPT-5.4:** Uncertainty contract, prompt archetypes, eval harness design
- **Codex:** Optimization framing, blast radius constraint, eval-gated migration

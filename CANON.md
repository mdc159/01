# Canon: Autonomous R&D Lab Objective Contract

Status: Active  
Owner: Project team  
Purpose: This is the source of truth for what we are building and how decisions are made.

## 1) Mission

Build a compact, long-horizon, autonomous engineering/research system that:
- Accepts broad goals.
- Decomposes them into executable experiments.
- Runs experiments continuously at low cost.
- Learns from outcomes.
- Escalates to high-reasoning models only when needed.

## 2) Core Philosophy

- Deterministic by default.
- Probabilistic only where reasoning is required.
- State over prompt history.
- Experiments over one-shot answers.
- Modular system over monolithic framework.

## 3) System Objective

Create a general-purpose goal engine that can handle coding, engineering, and research workflows by repeatedly executing:

Plan -> Act -> Evaluate -> Update State -> Repeat

For hard blocks:

Repeated failure -> Strategic diagnosis -> Replan

## 4) Operating Model (Three Nested Loops)

- Experiment Loop (minutes): run worker tasks, tools, checks, retries.
- Project Loop (hours/days): choose next tasks, track progress, adapt plan.
- Strategic Loop (days/weeks): architecture-level reframing and recovery when stuck.

## 5) Model Role Contract

- Worker tier (cheap/fast): execution, tool calls, implementation attempts.
- Critic tier (mid): evaluation, scoring, failure categorization, improvement hints.
- Strategist tier (o1-class reasoning): decomposition, diagnosis, reframing, decision frameworks.

Rule: reasoning models are not default workers.

## 6) State and Memory Contract

The system must maintain explicit external state as the source of truth.

Required layers:
- Structured state store: goals, constraints, hypotheses, task status, validated findings.
- Artifact store: files, outputs, logs, reports, simulation assets.
- Retrieval memory: distilled heuristics/insights for reuse.
- Runtime context: only what is needed for the current node/task.

Rule: context windows are disposable; state is durable.

## 7) Escalation Contract

Escalate only when at least one condition is met:
- Repeated failure without progress.
- High uncertainty or conflicting evidence.
- High-stakes decision with material downside.
- Need for architectural reframing (not just local patching).

Escalation input must include:
- Goal and constraints.
- What was tried.
- Failure signatures.
- Current state snapshot.
- Decision question.

Escalation output must include:
- Root cause hypothesis.
- Invalid assumptions.
- Recommended new approach.
- Concrete next tasks.

## 8) Determinism Boundary

Deterministic components:
- Workflow/state transitions.
- Routing policies.
- Tool interfaces.
- Persistence and artifact lineage.

Probabilistic components:
- Planning.
- Hypothesis generation.
- Ambiguous interpretation.
- Strategic tradeoff analysis.

## 9) Simplicity Constraint

Prefer the smallest architecture that preserves reliability.

Default build order:
1. State store.
2. Artifact store.
3. Retrieval memory.
4. Deterministic controller loop.
5. Worker + critic.
6. Strategic escalation.

No feature is added unless it improves reliability, observability, or decision quality.

## 10) Success Criteria

The system is successful when it can:
- Run for long periods without context collapse.
- Recover from failures through structured replanning.
- Improve over time via distilled reusable insights.
- Keep high-reasoning model usage sparse and high-leverage.
- Stay understandable, inspectable, and maintainable.

## 11) Non-Goals (for now)

- Building a bloated general assistant platform.
- Adding channels/plugins before core loop stability.
- Treating larger prompts as a substitute for state design.

## 12) Change Control

Any major prompt, architecture, or framework decision should be checked against this document first.

If a proposal conflicts with this canon, the canon wins unless explicitly revised.

## 13) Strategic Model Leverage Protocol (o1 Included by Design)

o1-class reasoning must be part of development, but used selectively for high-leverage decisions.

Mandatory o1 usage points:
- Project initialization: produce initial decomposition and risk map.
- Replanning after repeated failure: diagnose root cause and propose strategic pivot.
- Architecture decisions with long-term consequences: state model, loop design, evaluation policy, safety boundaries.
- High-uncertainty or high-stakes tradeoff decisions.

Default non-usage points:
- Routine execution steps.
- Brute-force retries.
- Deterministic transformations.
- Low-risk formatting or glue logic.

## 14) Multi-Model Reasoning Workflow (Gemini + o1 + Worker Stack)

Use role separation, not model averaging:
- Gemini (or peer frontier model): generate an alternative plan, critique, or edge-case challenge.
- o1 strategist: adjudicate, synthesize, and produce final decision framework.
- Worker/Critic tiers: implement and validate experimentally.

Decision pattern:
1. Generate candidate strategies (at least 2 when problem is ambiguous).
2. Run cross-model critique (Gemini challenges assumptions; o1 evaluates failure modes and selects approach).
3. Commit one executable plan to the deterministic controller.
4. Measure outcomes and feed back validated insights into state/memory.

o1 input contract for best leverage:
- Goal and explicit success metric.
- Current structured state snapshot.
- Constraints (time, cost, tools, risk).
- Attempts so far and failure signatures.
- Exact decision question to answer.
- Required output schema.

o1 output contract:
- Chosen strategy and rationale.
- Rejected alternatives with reasons.
- Key assumptions and confidence level.
- Concrete next tasks with evaluation criteria.
- Trigger conditions for next escalation.

## 15) Product Spec Authority

This document is the product specification authority for this project.

Implications:
- Architecture changes are product-spec changes.
- Prompt-contract changes are product-spec changes.
- Model-role changes are product-spec changes.
- State schema changes are product-spec changes.

No major implementation work should proceed without a spec-consistent decision record.

## 16) o1-in-the-Loop Spec Development Protocol

o1 must be used in defining the product, not only operating it.

Required spec cycle for major decisions:
1. Draft proposal (human or implementation model).
2. o1 strategic review (problem framing, tradeoffs, failure modes).
3. Peer model challenge (Gemini or equivalent) to stress-test assumptions.
4. o1 adjudication and final recommendation.
5. Canon/spec update with accepted decision and rationale.

A decision is "major" if it affects:
- Control loop structure.
- Escalation policy.
- State schema.
- Evaluation rubric policy.
- Safety or irreversible cost/risk exposure.

## 17) Canonical o1 Question Set (Ask These Explicitly)

For every major product decision, ask o1 these question classes directly.

Problem framing:
- "What problem are we actually solving, and what is the most likely misframing?"

Success contract:
- "What are the measurable success criteria and stopping conditions?"

Decomposition:
- "What is the minimal viable decomposition that preserves reliability?"

Failure forecasting:
- "What are the top failure modes, early warning signals, and mitigations?"

Determinism boundary:
- "Which components must be deterministic, and which should remain probabilistic?"

State design:
- "What state fields are required for clean long-horizon evolution?"

Escalation policy:
- "What precise thresholds should trigger strategic escalation?"

Evaluation policy:
- "How should outputs be scored so we optimize for real progress, not proxy quality?"

Cost and latency:
- "Where is high-reasoning spend highest leverage, and where is it waste?"

Reversibility and safety:
- "What decisions are hard to undo, and what guardrails are required before execution?"

## 18) o1 Question Quality Standard

Do not ask o1 vague prompts like "design the system."

Every o1 question must include:
- Objective and explicit success metric.
- Current state snapshot.
- Constraints (time, budget, tools, risk tolerance).
- What has already been tried.
- Exact decision to make.
- Required output schema.

If this context is missing, gather/compress first, then call o1.

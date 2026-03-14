# ORIGIN — How This System Was Designed

> The raw conversation that produced this architecture lives in [`docs/chat.md`](chat.md) — 4,461 lines of voice-transcribed dialogue between the project's creator and GPT-5.4. This document distills that conversation into a design narrative.

---

## 1. Origin Story

The creator of this system is an engineer, not a software developer. His career is in semiconductor manufacturing tooling — "I build the tool that builds the tools that builds the tools that makes the microprocessors." That background shapes everything about this project: he thinks in control loops, state machines, and deterministic systems. He approaches AI the same way he approaches a fabrication line — as infrastructure that must run reliably for long periods without human intervention.

The project started with a practical question: *How should I use OpenAI's O1 reasoning model?* Not as a chatbot, not as a code generator, but as a strategic reasoning layer inside a larger autonomous system. The conversation with GPT-5.4 began as model comparison (O1 vs GPT-5 vs Claude Opus) and evolved, over several hours, into a complete system architecture.

The motivating use case was ambitious: design a company that builds prosthetic limbs for orphans in India. Not a single-prompt task — a months-long engineering project requiring biomechanical research, CAD design, finite element simulation (ANSYS, COMSOL, MATLAB), supply chain analysis, materials sourcing, gait kinematics, company formation, and manufacturing logistics. The system needed to handle all of it autonomously, escalating to humans only when genuinely stuck.

This wasn't hypothetical. The creator was already running pieces of it — forked terminal calls through Codex, OpenCode with Oh My Open Code for multi-model routing, retry loops with prompt mutation, model fallback hierarchies. What he was missing, as he put it, was "the bigger picture."

---

## 2. Core Philosophy

Six principles emerged from the conversation. The first four came from the user; the last two crystallized through dialogue.

### "Deterministic everything, probabilistic only where reasoning is required"

> "I want as much of the system 100% determinate as possible and only use LLMs and the correct LLMs when you need a decision that's indeterminate in nature."
> — *chat.md, line ~3540*

This is the foundational design constraint. State transitions, workflow routing, retry logic, tool interfaces, persistence, artifact lineage — all deterministic. Planning, hypothesis generation, ambiguous interpretation, strategic tradeoff analysis — those are the only places where LLMs belong.

This maps directly to CANON.md Section 8 (Determinism Boundary).

### "The Japanese Engineer Principle"

> "I worked with an amazing Japanese engineer once... instead of answering my question, he answered the question that I should have asked him in the first place."
> — *chat.md, line ~743*

The best systems don't answer the question posed — they reformulate the question space before solving it. This principle drives the strategic tier's design: O1 isn't asked "fix this bug." It's asked "given these failure signatures, what is the actual problem, and what should we try instead?" Every O1 query follows a structured contract (CANON Section 18) precisely because vague questions waste the most expensive resource in the system.

### "The Millionaire Lifeline Model"

> "He was like my, you know, what would you call that? Like that television show when you got stuck on a question and you were allowed to call one person, but only one person."
> — *chat.md, line ~929*

Named after *Who Wants to Be a Millionaire?*, this principle governs model economics. The powerful reasoning model (O1) is consulted rarely and strategically — like a phone-a-friend lifeline. Local models handle 90-95% of work. Mid-tier models handle evaluation. O1 enters only when: stakes are high, reasoning depth is large, or uncertainty is high.

GPT-5.4 formalized this into the four-question framework: (1) What problem am I actually solving? (2) What variables determine the outcome? (3) What strategies are available? (4) How might this fail? These became the backbone of the O1 query contract.

### "Agents should build systems that solve problems, not solve problems directly"

> "The smartest agent builders eventually realize this: Agents shouldn't solve problems. They should build systems that solve problems."
> — *GPT-5.4, chat.md, line ~1416*

Instead of fixing a bug, the agent builds a test harness, debugging workflow, patch generator, and verification step. That *system* then fixes future bugs automatically. This is the difference between a task executor and a self-improving lab.

### "State over context"

This principle emerged when the conversation hit a wall. The user was already doing sub-agents with fresh context, scoped prompts, progressive repo discovery — all correct patterns. But the system still drifted. GPT-5.4 diagnosed the real issue:

> "The system's beliefs about the world never update cleanly... Iteration 24: 'hinge joint might work' — even though it already proved hinge joints fail."
> — *GPT-5.4, chat.md, line ~3118*

The fix wasn't more memory. It was explicit state mutation. Workers read state, workers write updates. The LLM is a stateless reasoning engine — everything real lives outside it. Context windows are disposable; `state.db.json` is durable.

This maps to CANON.md Section 6 (State and Memory Contract).

### "Experiments over answers"

> "Instead of solving 'fix python bug', the agent creates capability: python_debug_pipeline."
> — *GPT-5.4, chat.md, line ~1619*

The system thinks in experiments, not tasks. Each attempt answers: What did we try? Did it work? What changed? This turns the system into a continuous learning machine rather than a retry loop.

---

## 3. The Three Nested Loops

This was the "sauce" moment. The user had been describing his system — retry loops, model fallbacks, prompt mutation — and sensing it was close to something but not quite there. GPT-5.4 had been circling the same idea from the research side. When they finally converged:

> "Quit teasing me, give me the sauce."
> — *User, chat.md, line ~2586*

> "The trick is that the system is not a single loop. It's three nested loops."
> — *GPT-5.4, chat.md, line ~2593*

### The Architecture

```
Strategic Loop (days/weeks)
        |
Project Loop (hours/days)
        |
Experiment Loop (minutes)
```

Each loop operates at a different time horizon and uses a different model tier:

| Loop | Time Scale | Model Tier | Purpose |
|------|-----------|------------|---------|
| Experiment | seconds-minutes | Local (Ollama) | Run attempts, measure, keep/revert |
| Project | hours-days | Mid-tier (GPT-4o) | Review experiments, update plan, launch new experiments |
| Strategic | days-weeks | Reasoning (O1) | Ask "are we solving the right problem?" |

The experiment loop runs hundreds or thousands of times — this is the Mac Mini running 24/7 as a "tireless graduate student." The project loop periodically steps back to check if experiments are converging. The strategic loop fires only on new goals or after repeated failure — this is the "professor you ask when you're stuck."

The user recognized this immediately as "a REPL loop inside a REPL loop inside a REPL loop." GPT-5.4 mapped it to scientific method automation. Both were right.

### How This Maps to ai-lab/

| Loop | Implementation | File |
|------|---------------|------|
| Experiment Loop | Worker attempts with critic scoring, retry or escalate | `main.py`, `worker.py`, `critic.py` |
| Project Loop | Task queue management, progress tracking, plan adaptation | `main.py`, `planner.py` |
| Strategic Loop | O1 strategic planning, failure diagnosis, architecture reframing | `planner.py`, `llm.py` |

The three-loop structure is the organizing principle of `main.py` (~186 LOC). Everything else in ai-lab/ serves one of these loops.

---

## 4. Architecture Convergence

Late in the conversation, GPT-5.4 produced an 8-component diagram that "most serious agent systems converge to." The user called out the pattern of teasing ("You just said you weren't gonna do it, and you did it again. I'm gonna start calling you Columbo.") and GPT-5.4 finally delivered:

### The 8-Component Architecture

```
        GOAL / TRIGGER
              |
        1. PLANNER
              |
        2. TASK QUEUE
              |
        3. WORKER POOL
              |
        4. TOOL LAYER
              |
        5. ARTIFACT STORE
              |
        6. STATE DATABASE
              |
        7. CRITIC / EVALUATOR
              |
        8. LEARNING / SKILL STORE
              |
              '-----------> feeds back to planner
```

### What Was Actually Built

| Component | GPT-5.4's Box | ai-lab/ Implementation |
|-----------|--------------|----------------------|
| Planner | "Uses a strong model (like o1) to break a goal into tasks" | `planner.py` (323 LOC) — O1 strategic planning + failure diagnosis |
| Task Queue | "Deterministic. Redis / SQLite / Postgres" | Task graph in `state.py` — JSON-serialized, checkpoint/resume |
| Worker Pool | "Cheap models or tool runners" | `worker.py` (65 LOC) — stateless task execution |
| Tool Layer | "MATLAB, COMSOL, ANSYS, CAD, filesystem, web APIs" | `tools.py` (86 LOC) — Python exec, shell, file I/O |
| Artifact Store | "CAD files, simulation results, code, datasets" | Filesystem + `memory.py` artifact registry |
| State Database | "Not vector memory. Actual project state." | `state.py` (121 LOC) — 5-layer memory hierarchy, JSON checkpoints |
| Critic / Evaluator | "Did the experiment succeed?" | `critic.py` (113 LOC) — scoring + improvement hints |
| Learning / Skill Store | "Stores reusable solutions" | `memory.py` (95 LOC) — skill heuristics DB |

The mapping is nearly 1:1. The system that emerged from the conversation was built in ~1,200 LOC with two dependencies (`openai`, `python-dotenv`). No LangChain, no LangGraph, no framework overhead.

---

## 5. The State Revelation

The conversation circled for a while — the user describing memory problems, GPT-5.4 offering memory solutions, the user saying "I'm already doing that." The breakthrough came when GPT-5.4 reframed the problem:

> "What you need isn't more memory. You need explicit state mutation."
> — *GPT-5.4, chat.md, line ~3137*

The distinction:

| What most systems do | What this system does |
|---------------------|---------------------|
| Logs, logs, logs, logs | State update, state update, state update |
| LLM reconstructs state from history | Workers read structured state object |
| Memory grows unboundedly | State is the current truth; history is archived |

The user had asked multiple frontier coding models whether LangChain/LangGraph should be part of the system. They all said "overkill." GPT-5.4 pointed out they were answering the wrong question — they assumed a chatbot, not an autonomous research system. For long-running stateful workflows, explicit state orchestration is necessary.

But the conclusion wasn't "use LangGraph." It was: the *pattern* LangGraph uses (state object + state transitions + nodes) is correct, but ai-lab/ already implements it in ~300 LOC without the dependency weight. The system stores state as a structured JSON object that workers read and write. No hallucination. No forgetting.

GPT-5.4 proposed treating context like a computer memory hierarchy:

```
CPU registers   -> system prompt (identity, ~200 tokens)
RAM             -> active context (current task, hypothesis)
SSD             -> vector memory (retrieved knowledge)
Hard drive      -> raw logs (archived experiments)
```

This became the 5-layer memory model in `state.py`.

---

## 6. Memory Hierarchy

The 5-layer memory stack, drawn from the CPU registers analogy:

| Layer | Name | Contents | Persistence | Size |
|-------|------|----------|-------------|------|
| 1 | Identity | System role, rules, goal, constraints | Permanent | ~200 tokens |
| 2 | Working | Current experiment, hypothesis, plan, recent observations | Active session | Variable |
| 3 | Episodic | Recent experiment results, outcomes | Rolling buffer | Last N experiments |
| 4 | Semantic | Learned heuristics, validated constraints | Persistent | Grows over time |
| 5 | Artifact | Files, simulation outputs, code, designs | Filesystem | Unbounded |

Key design decisions:

- **Only load what matters now.** The prompt is: system memory + current task + retrieved memories. Not the entire history.
- **Summarizing checkpoints.** Every few iterations, raw logs are distilled into insights. "Iteration 1-4 failed" becomes "hinge design consistently fails under torsion."
- **Sub-agent isolation.** Workers run in fresh context windows. Only structured results return to the controller. This prevents context pollution and reasoning collapse.
- **Store surprises, not everything.** Only surprises, failures, insights, and decisions are persisted. Everything else is noise.

---

## 7. Model Tier Strategy

The user's hierarchy idea, refined through conversation:

```
Tier 1: Reasoning models (O1/O3)    — strategy, called rarely
Tier 2: Frontier models (GPT-4o)    — evaluation, called per-project-iteration
Tier 3: Local models (Ollama 70B)   — execution, called continuously
```

The governing principle: **cheap models execute, reasoning models decide.**

The system routes by task complexity, not by model preference. Which model fills each tier is itself an optimization target — one of the lab's first self-improvement goals.

The user's insight about rate limit cascading was ahead of its time: "start with the top tier, but you're gonna run into a rate limit, then drop down... keep going down the list." This became the model routing logic in `config.py`.

### Why Not One Model?

> "The biggest mistake people make is using one model for everything."
> — *GPT-5.4, chat.md, line ~297*

A reasoning model answering routine execution tasks is waste. A fast model attempting strategic planning is failure. The tier system ensures each dollar of compute goes where it produces the most leverage.

---

## 8. Scientific Grounding

The project's architecture — rubric-based evaluation, iterative experiment loops, strategic escalation — is independently validated by several lines of published AI research.

### Rubric-Based Evaluation and the Critic Tier

The AI Scientist (Sakana AI, 2024) demonstrated that an LLM reviewer applying a structured rubric — scoring novelty, significance, experimental rigor, clarity — can distinguish between high-quality and low-quality research outputs at above-random accuracy. This is the empirical basis for the critic tier's design: `critic.py` receives worker output and applies multi-dimensional evaluation criteria to produce a score that drives escalation decisions.

ScienceAgentBench (Ohio State, 2024) showed that decomposing research tasks into independently scorable sub-steps enables partial credit and fine-grained failure diagnosis — the same pattern used when the project loop evaluates experiment results against task-specific criteria.

### Experiment Loops and Many-Attempt Strategy

MLAgentBench (Stanford, 2023) demonstrated that running 100 fast attempts and selecting the best consistently outperforms running 10 careful attempts. This validates the experiment loop's core strategy: local models executing hundreds of cheap attempts while the critic filters for progress.

Both MLAgentBench and The AI Scientist identified the same failure mode the project's escalation policy addresses: without strategic replanning, agents loop indefinitely on tasks they cannot solve. The 5-failure escalation threshold (CANON Section 7) exists because of this empirically documented failure mode.

### Expert-Level Scientific Reasoning

GPQA (NYU/Scale AI, 2023) established that expert-level scientific reasoning requires multi-step inference that fails under standard prompting — PhD domain experts achieve ~65%, GPT-4 ~39%. FrontierMath (Epoch AI, 2024) showed even O1/O3 struggle below 2% at the true research frontier.

These benchmarks validate the strategic escalation mechanism: a fast-tier model cannot plan at the frontier without help from a reasoning model. The Millionaire Lifeline architecture isn't just economical — it's architecturally necessary, because the problem difficulty at the strategic layer exceeds what execution-tier models can handle.

### The FrontierScience Paper

The FrontierScience paper (referenced in `docs/frontierscience-paper (1).pdf`) is OpenAI's benchmark for expert-level scientific reasoning — evaluating AI systems on research-grade problems that require genuine domain expertise. Its rubric-based evaluation methodology mirrors the critic tier, and its decomposition of research problems into evaluable sub-tasks mirrors the experiment loop. The paper provides external validation that the three-loop architecture is not just a software pattern but reflects the structure of scientific reasoning itself.

### Key References

| Paper | Year | Relevance |
|-------|------|-----------|
| GPQA (arXiv:2311.12983) | 2023 | Expert-level science QA; validates need for strategic tier |
| The AI Scientist (arXiv:2408.06292) | 2024 | Autonomous research loop with rubric-based review |
| MLAgentBench (arXiv:2310.03302) | 2023 | Iterative experiment loops; many-attempt strategy |
| ScienceAgentBench (arXiv:2410.05080) | 2024 | Research sub-task decomposition with per-step scoring |
| FrontierMath (arXiv:2411.04872) | 2024 | Research-frontier difficulty; O1/O3 capability limits |
| autoresearch (Karpathy) | 2024 | Try-measure-keep/revert discipline; the direct ancestor |

---

## 9. What Was Built

The conversation produced a complete system design. Here is the mapping from conversation ideas to implemented code:

| Conversation Idea | Where It Landed |
|-------------------|----------------|
| "Three nested loops" | `main.py` — strategic, project, experiment loops |
| "O1 as strategic planner" | `planner.py` — O1 query contract with structured input/output |
| "Deterministic everything" | `tools.py` — Python exec, shell, file I/O; no LLM in the tool layer |
| "State over context" | `state.py` — JSON checkpoint/resume, 5-layer memory |
| "Millionaire Lifeline" | `config.py` — 3-tier model routing with escalation thresholds |
| "Critic loop" | `critic.py` — scoring + improvement hints |
| "Stateless workers" | `worker.py` — fresh context per task, structured results only |
| "Skills database" | `memory.py` — persistent heuristics + artifact registry |
| "O1 API quirks" | `llm.py` — unified client handling O1's lack of system messages |
| "CPU registers analogy" | `state.py` — identity/working/episodic/semantic/artifact layers |
| "LangGraph is the pattern, not the dependency" | No framework deps — 2 packages total |
| "Agents build systems, not solve problems" | The lab improves its own model selection, tools, and workflows |

### What Was Deliberately Not Built

- No LangChain/LangGraph (the pattern is implemented; the dependency isn't needed)
- No vector database (JSON tag-based retrieval; vector search deferred until needed)
- No plugin/skill marketplace (the system is compact by design)
- No multi-channel integration (CLI only; surfaces can be added later)
- No bloated assistant platform (this is a research lab, not a chatbot)

This aligns with CANON.md Section 9 (Simplicity Constraint): "Prefer the smallest architecture that preserves reliability."

---

## 10. Key References

| Reference | Role in This Project |
|-----------|---------------------|
| [`docs/chat.md`](chat.md) | Raw 4,461-line conversation archive — the primary source for this document |
| [`CANON.md`](../CANON.md) | Product spec authority — all design decisions checked against this |
| [`ai-lab/o1_system_prompt.md`](../ai-lab/o1_system_prompt.md) | Chief Strategist role definition for O1 |
| [`ai-lab/o1_next_question_mvp.md`](../ai-lab/o1_next_question_mvp.md) | Template for structured O1 queries |
| [`docs/lab/architecture.md`](lab/architecture.md) | Mermaid diagrams of full system architecture |
| [`docs/frontierscience-paper (1).pdf`](frontierscience-paper%20(1).pdf) | OpenAI's FrontierScience benchmark paper |
| [autoresearch](https://github.com/karpathy/autoresearch) | Karpathy's try-measure-keep/revert discipline |
| [The AI Scientist](https://arxiv.org/abs/2408.06292) | Sakana AI's autonomous research agent with rubric-based review |
| [MLAgentBench](https://arxiv.org/abs/2310.03302) | Stanford's iterative experiment loop benchmark |
| [ScienceAgentBench](https://arxiv.org/abs/2410.05080) | OSU's research sub-task decomposition benchmark |
| [GPQA](https://arxiv.org/abs/2311.12983) | Graduate-level science QA benchmark |
| [FrontierMath](https://arxiv.org/abs/2411.04872) | Epoch AI's research-frontier math benchmark |

---

*This document was distilled from a GPT-5.4 conversation that took place during the project's founding phase. The conversation is preserved in full at `docs/chat.md`. CANON.md remains the authoritative product specification.*

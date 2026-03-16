# Product Specification — Long-Horizon Autonomous Goal Engine

## Status

Draft v0.1

## Purpose

Define the intended product behavior and architecture for a compact, long-horizon autonomous engineering/research system that accepts broad goals, decomposes them into executable work, runs low-cost iterative experiments, learns from outcomes, and escalates to stronger reasoning only when necessary.

This spec is derived primarily from the uploaded design chat and aligned with the current canon. It is intended to be the document you compare against the current repo to identify gaps, accidental divergence, and under-specified areas.

---

## 1. Product Vision

Build a general-purpose goal engine for coding, engineering, and research workflows.

The system should behave less like a one-shot chatbot and more like a persistent search-and-improvement machine:

* accept a broad user goal
* turn it into structured plans and experiments
* execute many cheap attempts continuously
* evaluate outcomes systematically
* store reusable lessons
* replan when stuck
* escalate to frontier reasoning only when strategically justified

The system is fundamentally an iterative search process guided by LLMs, not a conversational wrapper around a single model.

---

## 2. Core Product Principles

### 2.1 Deterministic by default

Deterministic machinery owns workflow transitions, routing, persistence, lineage, retries, and approvals.

### 2.2 Probabilistic only where reasoning is required

Models are used for planning, critique, interpretation, synthesis, diagnosis, and strategic reframing.

### 2.3 State over prompt history

Prompt history is not the source of truth. Canonical state must live outside the context window.

### 2.4 Experiments over one-shot answers

The product should optimize for repeated attempts, feedback, and convergence rather than impressive first replies.

### 2.5 Modular system over monolithic framework

The product should remain compact and inspectable. Components should be replaceable without collapsing the whole system.

### 2.6 Sparse use of high-reasoning models

The strongest models are planners, judges, and reframers — not default workers.

---

## 3. Product Objective

Repeatedly execute the following loop:

**Plan → Act → Evaluate → Update State → Repeat**

For hard blocks:

**Repeated failure → Diagnose → Reframe → Replan**

The product succeeds when it can continue progressing toward long-horizon goals without context collapse, while keeping expensive reasoning sparse and high-leverage.

---

## 4. Operating Model — Three Nested Loops

### 4.1 Experiment Loop (fast loop, minutes)

Purpose: execute concrete attempts.

Responsibilities:

* select next runnable task instance
* choose tools and worker model
* execute attempt
* collect outputs, logs, metrics, errors
* run evaluation checks
* write results to state/artifacts
* retry, mutate prompt, switch worker, or stop

Examples:

* run tests
* modify code
* launch CAD or simulation workflow
* scrape references
* run benchmark or comparison

Primary characteristics:

* high frequency
* cheap models/tools dominate
* strongly instrumented
* deterministic orchestration around probabilistic workers

### 4.2 Project Loop (medium loop, hours to days)

Purpose: determine whether local experiments are advancing the project.

Responsibilities:

* review completed experiments and failure patterns
* update task graph and priorities
* create new experiment batches
* mark findings as validated, tentative, or invalidated
* decide whether local retries remain justified
* package escalation when project-level progress stalls

Primary characteristics:

* lower cadence than experiment loop
* planner + critic heavy
* responsible for project trajectory, not individual tool calls

### 4.3 Strategic Loop (slow loop, days to weeks)

Purpose: handle reframing, architecture decisions, and persistent failure.

Responsibilities:

* ask whether the system is solving the right problem
* diagnose repeated failure modes
* compare alternative strategies
* revise decomposition, evaluation policy, or state design
* generate decision records and spec updates

Primary characteristics:

* rare
* expensive reasoning allowed
* output is strategic guidance and new constraints, not direct execution

---

## 5. Agent / Role Model

The system should not be built as one giant omni-agent. It should use explicit role separation.

### 5.1 Goal Interpreter

Turns broad user goals into structured project definitions.

Outputs:

* clarified objective
* constraints
* success criteria
* candidate decomposition
* project record or update request

### 5.2 Planner

Creates or revises project plans and task graphs.

Outputs:

* task list
* dependencies
* recommended sequencing
* experiment proposals
* stopping conditions

### 5.3 Worker

Executes individual tasks.

Inputs:

* assigned task
* minimal runtime context
* tools
* model selection

Outputs:

* result
* logs
* artifacts
* structured status

### 5.4 Critic / Evaluator

Determines whether the worker output is valid and useful.

Outputs:

* pass/fail
* score
* failure type
* improvement hints
* promotion or rejection of findings

### 5.5 Failure Analyst (Ralph-loop function)

Transforms failed attempts into reusable diagnosis.

Outputs:

* failure signature
* probable root cause class
* prompt mutation suggestion
* model-routing suggestion
* retry recommendation
* escalation recommendation

### 5.6 Strategist / Replanner

Reserved for strong reasoning models.

Responsibilities:

* decomposition at project start
* diagnose repeated failure
* resolve ambiguous tradeoffs
* reframe approach when local search stagnates
* produce explicit decision frameworks

---

## 6. Ralph Loop / Failure-Learning System

The product must include a self-improving retry mechanism that turns failed attempts into better future attempts instead of random repetition.

### 6.1 Trigger

A Ralph loop begins when a worker attempt fails, underperforms, or produces ambiguous output.

### 6.2 Inputs

* task type
* worker model
* prompt used
* tools used
* runtime context summary
* result/logs/errors
* critic score
* prior attempts on the same task

### 6.3 Core behavior

For each failure:

1. classify the failure
2. determine whether it was tool, context, prompt, routing, or reasoning related
3. generate a better next attempt package
4. store the learning in a reusable model/task playbook
5. retry only if expected value remains positive

### 6.4 Required failure classes

At minimum:

* tool/interface failure
* missing context
* bad decomposition
* prompt mismatch
* model capability limitation
* nondeterministic external failure
* evaluation ambiguity
* task should escalate

### 6.5 Learning outputs

The Ralph loop should update a model/task behavior store with entries such as:

* best prompt style for model X on task Y
* when model X should be avoided
* minimal context packet needed for task class Z
* common failure signatures and mitigations

### 6.6 Guardrails

The Ralph loop must not create infinite retry churn.

It must obey:

* max attempts per task
* max attempts per strategy family
* escalating thresholds
* cost/time budget caps
* cooldown or human review for repeated identical failures

---

## 7. State and Memory Architecture

The product requires layered memory with explicit boundaries.

### 7.1 Structured State Store (source of truth)

Stores:

* goals
* projects
* task graph
* constraints
* statuses
* hypotheses
* validated findings
* escalation records
* approval state
* metrics

Properties:

* queryable
* durable
* versioned where practical
* independent of chat history

### 7.2 Artifact Store

Stores:

* code outputs
* CAD files
* simulation assets
* documents
* logs
* reports
* benchmark outputs

Properties:

* immutable or append-safe lineage preferred
* linked from structured state

### 7.3 Retrieval Memory

Stores distilled reusable insights.

Examples:

* model playbooks
* successful workflow patterns
* domain heuristics
* reusable prompt fragments
* failure mitigations

Properties:

* optimized for retrieval and reuse
* should contain distilled insight, not every raw trace

### 7.4 Runtime Context

Only the minimal context needed for the current node/task.

Properties:

* disposable
* rebuildable from state + artifacts + retrieval memory

### 7.5 Identity / Preference Memory

Stores persistent user/operator preferences.

Examples:

* style preferences
* reporting preferences
* challenge level / anti-sycophancy stance
* standing constraints
* aesthetic preferences

Properties:

* separate from project state
* available to chat/intake layers and relevant generation tasks
* not allowed to silently mutate project truth

---

## 8. Canonical Data Objects

At minimum the system should model these entities:

* Goal
* Project
* Task
* TaskAttempt
* Evaluation
* FailureReport
* EscalationPacket
* Finding
* Artifact
* HeuristicEntry
* UserPreference
* ApprovalRequest
* DecisionRecord

### 8.1 Project

Required fields:

* id
* title
* goal_id
* description
* owner
* status
* success_criteria
* constraints
* current_strategy
* created_at / updated_at

### 8.2 Task

Required fields:

* id
* project_id
* parent_task_id (optional)
* task_type
* description
* status
* priority
* dependencies
* assigned_role
* escalation_level
* retry_count
* success_criteria

### 8.3 TaskAttempt

Required fields:

* id
* task_id
* model
* toolchain
* prompt_fingerprint
* context_summary
* started_at / completed_at
* result_status
* artifact_ids
* raw_metrics

### 8.4 Evaluation

Required fields:

* id
* attempt_id
* evaluator
* score
* pass_fail
* failure_type
* notes

### 8.5 FailureReport

Required fields:

* id
* attempt_id
* signature
* root_cause_hypothesis
* recommended_fix
* retry_recommended
* escalate_recommended

### 8.6 HeuristicEntry

Required fields:

* id
* scope (model/task/tool/workflow)
* trigger_pattern
* recommended_pattern
* evidence_links
* confidence
* last_validated_at

---

## 9. Controller / Control Plane

The control plane is the deterministic core that decides what happens next.

Responsibilities:

* consume user/project events
* maintain state transitions
* schedule runnable tasks
* invoke workers/critics
* enforce concurrency limits
* enforce escalation thresholds
* enforce approvals and guardrails
* publish status/proposal events
* maintain artifact lineage

The controller must not be replaced by a chat transcript or a single LLM session.

---

## 10. Model Routing Policy

### 10.1 Worker tier (cheap / local / fast)

Used for:

* tool execution
* implementation attempts
* draft generation
* data transformation
* repeated low-cost search

### 10.2 Critic tier (mid)

Used for:

* evaluating outputs
* classifying failures
* scoring progress
* proposing bounded improvements

### 10.3 Strategist tier (strong reasoning)

Used for:

* project initialization
* ambiguous tradeoff decisions
* repeated failure diagnosis
* architecture changes
* strategic reframing

### 10.4 Routing rules

The system should always ask:

* is this worth reasoning about?
* is this a worker problem, critic problem, or strategist problem?
* do we have enough structured state to ask the strategist well?

Reasoning models should be called after compression, not as a substitute for compression.

---

## 11. Escalation Contract

Escalation occurs only when one or more conditions are met:

* repeated failure without measurable progress
* conflicting evaluation signals
* high-stakes or hard-to-reverse decision
* project-level stagnation
* architectural reframing required

### 11.1 Escalation input packet must include

* goal
* project state snapshot
* task or experiment summary
* what was tried
* failure signatures
* constraints
* exact decision question
* required output schema

### 11.2 Escalation output must include

* chosen strategy
* rejected alternatives
* root cause hypothesis
* invalid assumptions
* concrete next tasks
* evaluation criteria
* trigger for next escalation

---

## 12. Evaluation Policy

The product must optimize for real progress, not pretty text.

Each attempt should be scored against explicit criteria such as:

* correctness
* objective progress toward project goal
* reversibility/safety
* time/cost consumed
* artifact quality
* reproducibility

The evaluation layer should support both deterministic checks and model-based critique.

Validated outcomes should be promoted into findings or heuristics only when evidence supports reuse.

---

## 13. Telegram / Operator Interface

Telegram is an operator console, not the source of truth.

### 13.1 Required interaction modes

* Chat mode
* Intake / clarification mode
* Project / task commit mode
* Ops mode (status, pause, resume, inspect)
* Proposal review mode
* Approval / denial mode

### 13.2 Project silo model

The interface must support multiple concurrent projects without cross-contamination.

Recommended model:

* one major project maps to one Telegram chat, topic, or stable session identity
* each session maps to a backend project or workspace key
* project creation in chat can instantiate a new project record
* cross-project linking must be explicit, not incidental

### 13.3 Chat mode behavior

Allows conversational exploration and user-selected model switching.

Rules:

* chat does not mutate canonical project state by default
* user must explicitly save, commit, or convert output into a project/task object

### 13.4 Intake mode behavior

Used to turn rough ideas into structured tasks or projects.

Outputs:

* clarified objective
* constraints
* success metrics
* ambiguity markers
* recommended project/task creation

### 13.5 Ops mode behavior

Supports:

* status
* next tasks
* failures
* escalations
* heartbeat summaries
* approvals
* pause/resume

---

## 14. Heartbeat and Proactive Behavior

The heartbeat is a scheduler and notifier, not the reasoning brain.

Responsibilities:

* trigger periodic status summaries
* surface stale projects or blocked tasks
* invoke low-cost proposal generation
* check health of channels and worker loops
* enqueue periodic reviews

### 14.1 Background proposal engine

Low-cost background models may continuously generate:

* process improvement proposals
* candidate next tasks
* new experiment ideas
* memory distillation opportunities
* risk or drift warnings

These outputs should become **proposal objects** requiring evaluation or approval, not direct unreviewed action.

### 14.2 Health behavior

Heartbeat infrastructure should expose:

* alive / stale status
* queue depth
* worker availability
* retry storms
* unacknowledged failures
* escalation backlog

---

## 15. Reference Implementation Patterns to Reuse

These are implementation patterns, not the product definition.

### 15.1 From OpenClaw

Useful patterns:

* per-chat/topic session silos
* sequentialization keys per chat/topic/control lane
* webhook or polling ingestion with deduplication
* heartbeat scheduling
* thread binding to subagents
* health monitoring and auto-restart

### 15.2 From Popebot

Useful patterns:

* channel adapter interface
* central route dispatcher
* SQLite/LangGraph checkpointing per thread or session
* provider/model factory abstraction
* per-role concurrency locks
* cron/file/webhook trigger runtime
* tool factory closures with bound context

The product should adapt these patterns where they strengthen reliability without inheriting unnecessary framework bulk.

---

## 16. Non-Goals

For the current phase, the system is not trying to be:

* a bloated general assistant platform
* a giant plugin marketplace
* a fully autonomous authority without approvals
* a prompt-only memory system
* an architecture that depends on endless strategist calls

---

## 17. Success Criteria

The product is successful when it can:

* accept broad goals and turn them into structured project work
* run for long periods without context collapse
* isolate concurrent projects cleanly
* recover from local failure through structured diagnosis and replanning
* improve over time via reusable heuristics and model/task playbooks
* keep strong reasoning usage sparse and strategic
* remain understandable and inspectable

---

## 18. Minimal Build Order

1. Structured state store
2. Artifact store
3. Retrieval memory / heuristic store
4. Deterministic controller
5. Worker + critic loop
6. Failure analyst / Ralph loop
7. Strategic escalation packet flow
8. Telegram operator interface with project silos
9. Heartbeat summaries and proposal engine

---

## 19. Repo Alignment Checklist

Use this spec to compare against the current repo.

### 19.1 Present vs missing

For each of these, mark:

* present
* partial
* missing
* present but misaligned

Checklist:

* explicit project/task state model
* task attempt and evaluation records
* failure report schema
* heuristic/model-playbook storage
* deterministic controller loop
* planner / worker / critic / strategist separation
* escalation packet format
* project silo/session mapping
* Telegram mode separation
* heartbeat scheduler
* approval gates
* artifact lineage
* observability and health checks

### 19.2 Drift questions

* Where does the repo rely on prompt history instead of explicit state?
* Where are retries occurring without diagnosis?
* Where are strong models being used as workers instead of strategists?
* Where is project isolation implicit rather than enforced?
* Where is memory raw rather than distilled?
* What major architecture choices exist in code but not in the spec?
* What claims in the spec are not yet represented in code?

### 19.3 Output expected from repo audit

* alignment summary
* drift list
* missing primitives
* unsafe ambiguities
* recommended implementation order
* decisions that must update the spec before coding continues

---

## 20. Open Questions Requiring Strategic Review

These should be reviewed explicitly before large implementation moves:

* exact state schema and entity relationships
* escalation thresholds per task family
* project silo/session identity design in Telegram
* approval model for destructive actions
* heuristic validation policy
* how much council-style critique is worth keeping
* boundary between chat memory and canonical project memory
* how to version decision records and spec changes

---

## 21. Immediate Next Step

Run a repo audit against this spec.

Expected process:

1. inspect current implementation
2. map current components to spec sections
3. identify drift, gaps, and accidental complexity
4. propose minimal changes required to converge on the target architecture
5. separate code changes from spec changes

This spec is intentionally opinionated. If the repo proves a better pattern, revise the spec explicitly rather than allowing implicit drift.

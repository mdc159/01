My read: **no, a dedicated hosted “O1 Assistant as knowledge plane” is not obviously worth it for your architecture.** If your control plane, state, and execution stay local, then OpenAI’s hosted retrieval mostly buys you **managed retrieval plumbing**, not a qualitatively different reasoning layer. The docs describe file search as a hosted tool over vector stores that does semantic **and** keyword search, with automatic tool execution, while the Retrieval API exposes automatic chunking/indexing, metadata filters, query rewriting, reranking, and hybrid-search tuning. Since you already have pgvector + FTS + RRF, you’ve already rebuilt most of the core retrieval substrate. ([OpenAI Developers][1])

**1) Does built-in file search give you anything you can’t replicate with pgvector + RRF?**
Not in a fundamental sense. What OpenAI gives you out of the box is: automatic chunking/embedding/indexing, semantic+keyword retrieval, optional query rewrite, metadata filtering, reranking / score thresholds, hybrid search weighting, automatic model-invoked tool calls, and file citations in the model output. Those are nice product features, but they are not magic capabilities. The one thing that is meaningfully different from a plain DIY retriever is the **tight integration into the model’s own tool loop**: the model can decide to call file search during a response and cite the files it used. If your local orchestrator already decides when to retrieve and can inject retrieved passages cleanly, that gap shrinks a lot. ([OpenAI Developers][1])

**2) For canon docs / runbooks / heuristics / failure taxonomies, is hosted retrieval meaningfully better than your own vector store?**
Usually **no**. Those are exactly the kinds of curated, relatively stable corpora where a custom store tends to do very well, because you can control chunking, metadata, freshness, and ranking policy. OpenAI’s own docs frame retrieval and file search as ways to search your data and then synthesize responses from the results; they do not present hosted retrieval as a separate reasoning engine. So if your local retriever already surfaces the right chunks, the model’s strategic quality should come mostly from the **model + prompt + eval loop**, not from whether the chunks came from OpenAI vector stores or your own pgvector store. Hosted retrieval is better when you want lower implementation effort, less ingestion code, automatic citations, and a turnkey baseline to compare against. ([OpenAI Developers][2])

**3) Is there a tool-use or persistent-thread advantage that justifies the lock-in?**
There is **some** advantage, but probably not enough for your stated goal. OpenAI’s current guidance is to build new work on the **Responses API**, not the older Assistants API; the docs label Assistants under **Legacy**, and they call Responses the recommended API for new projects. Responses also supports built-in tools, `previous_response_id`, and compatibility with the Conversations API for persistent state. So yes, there is a hosted-state / hosted-tooling convenience story — but it is not unique to Assistants, and it is not required if your local control plane already owns state and tool execution. ([OpenAI Developers][3])

So the practical answer is: **raw API calls with structured prompts + your own retrieval stack is probably the right default.** I’d only move the “knowledge plane” onto OpenAI if you want one of these three very specific wins: first, much less retrieval plumbing to maintain; second, automatic in-model file-search tool use with citations; third, a fast hosted baseline for A/B testing against your local retriever. Otherwise, keep retrieval local and treat OpenAI as the **reasoning tier**, not the knowledge substrate. That lines up with OpenAI’s own recommendation to use Responses for reasoning models and to build evals around prompt/model changes rather than assume the platform wrapper itself is the main source of quality. ([OpenAI Developers][3])

One extra wrinkle: if you’re designing this fresh in 2026, I would not anchor the architecture to **o1 specifically**. OpenAI’s model pages now describe **o1** as a **previous full o-series reasoning model**, while their current guidance says to start with **GPT-5.4** for complex reasoning/coding and use the Responses API for the best reasoning-model experience. That doesn’t invalidate your O1 protocol work, but it does argue for making the “hosted strategic tier” model-pluggable instead of O1-specific. ([OpenAI Developers][4])

My blunt recommendation: **keep your knowledge plane local, call OpenAI for reasoning, and benchmark hosted file search only as a challenger baseline.** The clean eval is: same exported corpus, same decision prompts, compare your `aos/retrieve.py` against OpenAI file search on retrieval hit-rate, citation usefulness, end-to-end latency, and downstream strategic-answer quality. OpenAI explicitly recommends pinning model versions and building evals as you iterate, which is exactly the right way to settle this instead of arguing from vibes. ([OpenAI Developers][3])

I can sketch the exact A/B harness for `local_retrieve -> Responses` versus `Responses(file_search)` next.

[1]: https://developers.openai.com/api/docs/guides/tools-file-search/ "File search | OpenAI API"
[2]: https://developers.openai.com/api/docs/guides/retrieval/ "Retrieval | OpenAI API"
[3]: https://developers.openai.com/api/docs/guides/text/ "Text generation | OpenAI API"
[4]: https://developers.openai.com/api/docs/models/o1?utm_source=chatgpt.com "o1 Model | OpenAI API"


Yep — and I’d do it in a way that answers **your actual architecture question**, not just “which API feels nicer.”

One important note first: in the **public `master` tree** I can see `ai-lab/llm.py`, `planner.py`, `memory.py`, and the O1 prompt docs, but I **cannot verify `aos/retrieve.py` from the current public tree**. The visible `memory.py` is still a lightweight JSON/tag heuristic store, and `llm.py` is the current abstraction point for model calls. So I’d build the harness around that seam, while treating your pgvector+FTS+RRF retriever as an external adapter. ([GitHub][1])

The cleanest experiment is:

**A. Local retrieval plane**
Your own pgvector + FTS + RRF retriever returns top-k snippets, you inject them into the prompt, then call the reasoning model.

**B. Hosted retrieval plane**
Same prompt, same model, same corpus, but retrieval happens through OpenAI `file_search` in the Responses API instead of your local stack. OpenAI’s docs say `file_search` is a hosted tool over vector stores using semantic + keyword search, and the Responses API is now the recommended interface for new projects with built-in tool use and optional stateful context. ([OpenAI Developers][2])

That gives you the answer you actually care about:

* Is hosted retrieval finding better evidence?
* Does that improve strategic answers?
* Is any gain large enough to justify lock-in?

## What to measure

I would score four things, in this order:

**1. Retrieval quality**
Did the system surface the right canon/runbook/heuristic/failure-taxonomy chunks?

**2. Decision quality**
Did the final answer produce the better strategic recommendation?

**3. Groundedness**
Were claims actually supported by retrieved material, or did the model freewheel?

**4. Operational cost**
Latency, token spend, upload/index maintenance, and implementation pain.

For your use case, retrieval quality alone is not enough. A retriever can fetch decent chunks and still lead to weak architecture choices. So the primary scoreboard should be **end-to-end strategic utility**, with retrieval as a diagnostic layer. That lines up with your repo’s design: strategic loop, project loop, experiment loop, metrics as truth, and model routing via a unified client. ([GitHub][1])

## The benchmark set

Build a small but sharp eval corpus: **30–50 cases**. Split them into five buckets.

1. **Canon lookup**
   “What does the system currently consider authoritative for X?”

2. **Architecture adjudication**
   “Choose between option A/B/C under these constraints.”

3. **Failure diagnosis**
   “Given symptoms and prior attempts, identify likely root cause and next discriminating test.”

4. **Heuristic reuse**
   “What prior lesson or pattern should be reused here?”

5. **Runbook synthesis**
   “Given the current state, what exact next actions should the operator or worker take?”

Each case should have:

* `question`
* `expected_supporting_docs`
* `gold_facts`
* `grading_rubric`
* `expected_output_schema`

That way you can score both retrieval and answer quality without guessing after the fact.

A good JSONL shape:

```json
{
  "id": "arch_012",
  "bucket": "architecture_adjudication",
  "question": "Should the strategic tier remain O1-only or become model-pluggable?",
  "context": {
    "current_state": "...",
    "constraints": ["local-first", "rare hosted calls", "low ops drag"],
    "already_tried": ["hard-coded o1 route in planner", "manual strategy docs"]
  },
  "expected_supporting_docs": [
    "CANON.md",
    "docs/lab/architecture.md",
    "ai-lab/o1_system_prompt.md"
  ],
  "gold_facts": [
    "strategic tier is called rarely",
    "model routing is intended to be configurable",
    "system optimizes model selection over time"
  ],
  "grading_rubric": {
    "support_recall": 0.25,
    "decision_quality": 0.35,
    "groundedness": 0.25,
    "actionability": 0.15
  }
}
```

## The test matrix

Don’t compare “local retrieval + Chat Completions” against “hosted retrieval + Responses.” That muddies the result.

Run this matrix instead:

**Model:** same reasoning model on both arms
**Prompt schema:** same
**Output schema:** same
**Corpus:** same docs
**Only variable:** retrieval plane

So the two main contenders are:

* `local_retrieve -> Responses(model, no file_search)`
* `Responses(model, file_search enabled)`

That matters because OpenAI explicitly recommends the Responses API for new builds, says it supports built-in tools including file search, and says passing prior response context can improve multi-turn reasoning. If you used Chat Completions on one side and Responses on the other, you wouldn’t know whether retrieval or API style caused the difference. ([OpenAI Developers][3])

## My recommended harness layout

Given your current repo shape, I’d add this as a **sidecar eval package**, not jam it into the main loop first.

```text
ai-lab/
  evals/
    knowledge_plane/
      cases.jsonl
      runner.py
      graders.py
      metrics.py
      adapters.py
      exporters.py
      results/
```

And in `adapters.py`:

```python
from dataclasses import dataclass
from typing import List, Protocol

@dataclass
class RetrievedChunk:
    doc_id: str
    chunk_id: str
    text: str
    score: float
    source: str  # "local" or "openai_file_search"

class Retriever(Protocol):
    def retrieve(self, query: str, k: int = 8) -> List[RetrievedChunk]:
        ...

class LocalRetriever:
    def __init__(self, local_backend):
        self.backend = local_backend  # your aos/retrieve.py adapter

    def retrieve(self, query: str, k: int = 8) -> List[RetrievedChunk]:
        rows = self.backend.search(query=query, top_k=k)
        return [
            RetrievedChunk(
                doc_id=r["doc_id"],
                chunk_id=r["chunk_id"],
                text=r["text"],
                score=r["score"],
                source="local",
            )
            for r in rows
        ]

class OpenAIFileSearchRetriever:
    """
    Thin wrapper that asks the model to use file_search, but returns the
    retrieved chunks/results for evaluation, not just the final answer.
    """
    def __init__(self, client, vector_store_id: str, model: str):
        self.client = client
        self.vector_store_id = vector_store_id
        self.model = model

    def retrieve(self, query: str, k: int = 8) -> List[RetrievedChunk]:
        resp = self.client.responses.create(
            model=self.model,
            input=query,
            tools=[{
                "type": "file_search",
                "vector_store_ids": [self.vector_store_id],
                "max_num_results": k,
            }],
            tool_choice={"type": "file_search"},
            include=["file_search_call.results"],
            store=False,
        )

        chunks = []
        for item in getattr(resp, "output", []):
            if getattr(item, "type", None) == "file_search_call":
                for r in getattr(item, "results", []):
                    chunks.append(
                        RetrievedChunk(
                            doc_id=getattr(r, "filename", "unknown"),
                            chunk_id=getattr(r, "file_id", "unknown"),
                            text=getattr(r, "text", ""),
                            score=float(getattr(r, "score", 0.0) or 0.0),
                            source="openai_file_search",
                        )
                    )
        return chunks
```

That `include=["file_search_call.results"]` bit comes straight from the current Responses API surface, which allows you to inspect file search results explicitly rather than treating hosted retrieval as a black box. ([OpenAI Developers][4])

## Then separate retrieval from reasoning

This is the key design choice.

Do **not** let hosted file search and local retrieval also differ in answer generation style. Normalize both into the same “context pack,” then call the model the same way.

```python
def build_context_pack(chunks):
    header = "Retrieved context:\n"
    body = "\n\n".join(
        f"[{i+1}] {c.doc_id}\n{c.text}" for i, c in enumerate(chunks)
    )
    return header + body

def answer_with_context(client, model, system_prompt, case, context_pack):
    prompt = f"""
Objective: {case['question']}

Current state:
{case['context']['current_state']}

Constraints:
- {'\n- '.join(case['context']['constraints'])}

Already tried:
- {'\n- '.join(case['context']['already_tried'])}

Retrieved evidence:
{context_pack}

Return JSON with:
- answer
- key_evidence_ids
- assumptions
- confidence
- next_action
"""
    return client.responses.create(
        model=model,
        input=[
            {"role": "developer", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        text={"format": {"type": "json_object"}},
        store=False,
    )
```

That lets you score:

* retrieval quality on the chunks
* answer quality on the identical reasoning prompt

This is a much cleaner experiment than letting OpenAI’s hosted tool both retrieve and synthesize on one side while your system injects context manually on the other.

## Grading

Use two graders:

**A. Deterministic grader**

* support recall@k
* whether expected docs were retrieved
* whether cited evidence IDs exist in retrieved set
* latency
* token usage
* dollar cost

**B. LLM grader**
Ask a critic model to score:

* strategic usefulness
* correctness
* groundedness
* actionability
* whether missing evidence should have blocked a decision

That mirrors your repo’s critic/evaluator pattern already. ([GitHub][1])

A compact score formula:

```python
final_score = (
    0.30 * support_recall +
    0.30 * groundedness +
    0.25 * decision_quality +
    0.10 * actionability +
    0.05 * cost_efficiency
)
```

## What I strongly suspect you’ll find

My bet is:

* For **curated internal docs** like canon docs, runbooks, distilled heuristics, and failure taxonomies, your local retriever will get very close.
* Hosted file search may do a bit better on mixed keyword/semantic recall and lower engineering effort.
* The biggest incremental platform value is not “better knowledge,” but **agentic built-in tooling + convenience + statefulness** in Responses. OpenAI says Responses is the recommended API for new projects, supports built-in tools like file search, and supports stateful context via stored conversations / previous responses. ([OpenAI Developers][3])

So I would test three levels, in order:

**Level 1 — retrieval only**
Local vs hosted, same downstream prompt.

**Level 2 — end-to-end QA**
Local context injection vs model-chosen `file_search`.

**Level 3 — multi-turn memory**
Only if you actually care whether hosted state beats your local state manager.

That last one matters because you said you want the reasoning quality, not the platform. If level 1 and 2 are already near parity, there’s no reason to marry the knowledge plane to OpenAI.

## One very practical repo-specific suggestion

Your visible `llm.py` currently routes O1-family models through `chat.completions.create(...)` and injects the system prompt there. For this eval, I would **not** mutate that path yet. I’d create a parallel eval-only Responses client so you can compare retrieval planes without destabilizing the current engine. After the experiment, if Responses wins materially, then fold it back into `llm.py`. ([GitHub][5])

That gives you a low-drama progression:

1. keep current lab runtime untouched
2. build eval sidecar
3. run 30–50 benchmark cases
4. compare local retrieval vs hosted file search
5. only then decide whether hosted knowledge plane is real or just shiny managed plumbing

If you want, I’ll turn this into an actual `runner.py` scaffold and a `cases.jsonl` starter set tailored to your repo.

[1]: https://github.com/mdc159/01 "GitHub - mdc159/01 · GitHub"
[2]: https://developers.openai.com/api/docs/guides/tools-file-search/ "File search | OpenAI API"
[3]: https://developers.openai.com/api/docs/guides/migrate-to-responses/ "Migrate to the Responses API | OpenAI API"
[4]: https://developers.openai.com/api/reference/resources/responses/methods/create/ "Create a model response | OpenAI API Reference"
[5]: https://github.com/mdc159/01/blob/master/ai-lab/llm.py "01/ai-lab/llm.py at master · mdc159/01 · GitHub"


Yep — and now that we’ve re-anchored on the current repo, I think the right next move is to turn that discussion into a **repo-native evaluation design note**, not another abstract debate.

Why this fits the repo as it exists today:

Your repo already defines the system as three nested loops with a **strategic tier called rarely**, a **project/critic tier**, and a **fast worker loop**; it also says durable external state matters more than prompt history, and that the strategist should be used for decomposition, diagnosis, and reframing rather than day-to-day execution. The repo also already has a unified `llm.call()` seam, plus dedicated strategist prompt docs, which makes this an unusually clean place to run a retrieval-plane A/B test without destabilizing the core engine. ([GitHub][1])

The one thing I’d sharpen while doing it: make the design note **model-pluggable**, not permanently “O1 knowledge plane” branded. OpenAI’s current docs say the **Responses API is recommended for new projects**, with built-in tools like file search, and their model guidance now says to start with **GPT-5.4** for complex reasoning/coding while `o1` is listed as a **previous full o-series reasoning model**. That does not invalidate your current O1-centric architecture, but it does mean the eval should answer “hosted retrieval vs local retrieval” separately from “which strategic model wins.” ([OpenAI Developers][2])

Here’s the draft I’d drop into the repo as `docs/lab/knowledge-plane-eval-prd.md`:

---

# Knowledge Plane Evaluation PRD

## Status

Draft

## Owner

Project team

## Purpose

Determine whether the lab should keep retrieval fully local or introduce OpenAI-hosted retrieval as a selective knowledge plane for strategic reasoning tasks.

This document exists to answer a concrete engineering question:

**Does OpenAI hosted retrieval provide a meaningful capability advantage over our local retrieval stack, or is it mainly managed convenience?**

The lab wants **reasoning quality**, not platform dependence.

## Background

The current system architecture is local-first:

* Control plane stays local
* State stays local
* Execution stays local
* High-reasoning models are called selectively for planning, diagnosis, and reframing

The repo canon already states:

* deterministic by default
* state over prompt history
* retrieval memory as a reusable layer
* strategist tier only when needed
* modular system over monolithic framework

This evaluation does **not** ask whether hosted APIs are convenient. It asks whether they improve the system enough to justify lock-in. ([GitHub][3])

## Current Hypothesis

**Primary hypothesis:**
Our local retrieval stack should achieve near-parity for curated internal knowledge artifacts such as canon docs, architecture runbooks, distilled heuristics, and failure taxonomies.

**Secondary hypothesis:**
OpenAI hosted retrieval may improve convenience, citations, and built-in tool orchestration, but will not provide a decisive reasoning advantage if the same evidence is already surfaced by local retrieval.

**Null hypothesis:**
Hosted retrieval does not materially improve end-to-end strategic answer quality relative to local retrieval + structured prompting.

This is consistent with OpenAI’s current platform shape: file search is a hosted tool over uploaded/vectorized files, while the Responses API is positioned as the recommended modern interface for tool-using, stateful, agent-like workflows. ([OpenAI Developers][4])

## Questions To Answer

1. Does OpenAI `file_search` retrieve better supporting evidence than the local retriever?
2. If yes, does that actually improve strategic recommendations?
3. Is any gain large enough to justify hosting part of the knowledge plane?
4. Are the gains limited to convenience, or do they materially change lab performance?

## Non-Goals

* Replacing the local control plane
* Replacing the local state system
* Replacing worker execution with hosted tools
* Choosing a permanent strategic model
* Refactoring the runtime before evidence exists

## Decision Rule

We adopt hosted retrieval only if it beats local retrieval on **end-to-end strategic utility**, not just ease of setup.

Hosted retrieval must show a clear win on at least one of:

* strategic answer quality
* evidence recall for critical docs
* groundedness / citation usefulness
* multi-turn tool workflow simplicity that materially reduces system complexity

If hosted retrieval only improves convenience while local retrieval remains near-parity on quality, the default decision is:

**Keep the knowledge plane local.**

## Architecture Under Test

### Arm A — Local Retrieval Plane

Local retriever returns top-k evidence chunks from internal knowledge sources. Retrieved context is injected into the strategic prompt. Model call uses raw API prompting through the lab’s LLM abstraction.

### Arm B — Hosted Retrieval Plane

Same corpus is exported to OpenAI vector storage. Retrieval happens through OpenAI `file_search` in the Responses API. The same strategic question is asked against the hosted evidence path.

OpenAI documents `file_search` as a built-in retrieval tool and positions Responses as the recommended API for new projects with tool use and stateful interaction support. ([OpenAI Developers][4])

## Critical Experimental Constraint

The comparison must isolate the **retrieval plane**.

Do **not** compare:

* different models
* different prompt schemas
* different output schemas
* different task sets

The only variable should be:
**where retrieval happens**

## Evaluation Corpus

Build a benchmark set of 30–50 cases across five buckets:

### 1. Canon Retrieval

Questions whose ideal answer depends on canon or architectural source-of-truth documents.

### 2. Architecture Adjudication

Questions that require choosing among explicit options under constraints.

### 3. Failure Diagnosis

Questions that require identifying likely causes, missing evidence, and next discriminating tests.

### 4. Heuristic Reuse

Questions that should surface prior distilled lessons or known patterns.

### 5. Runbook Synthesis

Questions that require producing the next implementable action plan from current state and known constraints.

Each case must include:

* question
* current state snapshot
* constraints
* prior attempts
* expected supporting docs
* gold facts
* expected output schema
* grading rubric

## Metrics

### Retrieval Metrics

* support recall@k
* whether expected docs appear in retrieved results
* ranking quality for top evidence
* retrieval latency

### Strategic Answer Metrics

* correctness
* groundedness
* actionability
* quality of option comparison
* quality of uncertainty handling
* quality of next-step recommendation

### Operational Metrics

* API cost
* ingestion overhead
* maintenance complexity
* observability/debuggability

## Grading

Use two graders.

### Deterministic Grader

Checks:

* expected supporting docs retrieved
* cited evidence appears in retrieved set
* schema compliance
* cost and latency

### Model-Based Grader

Scores:

* strategic usefulness
* groundedness
* whether recommendation actually follows from evidence
* whether uncertainty was handled correctly
* whether the smallest next experiment was well chosen

## Success Criteria

The evaluation is successful if it produces a decision with evidence strong enough to support one of these outcomes:

### Outcome A — Stay Local

Local retrieval is within 5–10% of hosted retrieval on strategic utility and better on control or simplicity.

### Outcome B — Hybrid

Keep local retrieval as default, but allow hosted retrieval for selected document classes or selected strategic workflows.

### Outcome C — Hosted Knowledge Plane

Hosted retrieval materially outperforms local retrieval on strategic utility and the operational tradeoff is worth it.

## Implementation Plan

### Phase 1 — Eval Harness Only

Add an isolated eval package rather than modifying runtime orchestration.

Proposed location:

`ai-lab/evals/knowledge_plane/`

Contents:

* `cases.jsonl`
* `runner.py`
* `graders.py`
* `metrics.py`
* `adapters.py`
* `exporters.py`
* `results/`

### Phase 2 — Local Adapter

Wrap the existing local retrieval path behind a common adapter interface.

### Phase 3 — Hosted Adapter

Create an OpenAI Responses + `file_search` adapter against the exported corpus.

### Phase 4 — Normalize Prompting

Use the same strategic prompt structure and same output schema for both arms.

### Phase 5 — Run Eval Set

Run all benchmark cases across both arms and collect retrieval + answer metrics.

### Phase 6 — Decision Memo

Write a short decision note:

* winner
* why it won
* what tradeoff was accepted
* what remains uncertain

## Interface Contract

Both retrieval arms must emit the same normalized object:

* source
* doc_id
* chunk_id
* text
* score
* metadata

Both answer arms must emit the same JSON:

* answer
* key_evidence_ids
* assumptions
* confidence
* next_action
* kill_criteria
* escalation_trigger

## Exit Criteria

This PRD is complete when:

1. The benchmark set exists
2. Both retrieval adapters run
3. Both arms use the same downstream prompt and output schema
4. Results can be compared in one report
5. The team can make a go / no-go decision on hosted retrieval

## Default Recommendation Pending Eval

Proceed with the harness assuming the likely default is:

**Local retrieval remains the main knowledge plane. Hosted retrieval is evaluated as a challenger, not assumed as the future architecture.**

---

My opinionated take: this is the right doc because it matches the repo’s actual shape. The repo already says the system should be modular, stateful, retrieval-aware, and strategist-sparing, and `llm.call()` is already the natural seam for controlled experiments. So this isn’t “new architecture.” It’s a measurement harness for a question your current architecture is already set up to answer. ([GitHub][5])

Two small upgrades I’d make immediately when you commit this:

First, rename the question from **“Should we build an O1 Assistant knowledge plane?”** to **“Should retrieval remain local-first or become hybrid-hosted?”** That avoids prematurely baking in one model or one vendor surface. OpenAI’s current docs really do point toward Responses as the modern tool surface, and away from treating older assistant-style abstractions as the center of gravity. ([OpenAI Developers][2])

Second, add one explicit rule to the PRD:
**Hosted retrieval only wins if it improves end-to-end strategic decisions, not just retrieval cosmetics.**
That’s the guardrail that keeps you from buying shiny plumbing.

If you want, I’ll turn this next into the companion `runner.py` scaffold and a 10-case starter `cases.jsonl` tailored to the repo as it stands now.

[1]: https://raw.githubusercontent.com/mdc159/01/master/README.md "raw.githubusercontent.com"
[2]: https://developers.openai.com/api/docs/guides/migrate-to-responses/?utm_source=chatgpt.com "Migrate to the Responses API"
[3]: https://raw.githubusercontent.com/mdc159/01/master/CANON.md "raw.githubusercontent.com"
[4]: https://developers.openai.com/api/docs/guides/tools-file-search/?utm_source=chatgpt.com "File search | OpenAI API"
[5]: https://raw.githubusercontent.com/mdc159/01/master/ai-lab/llm.py "raw.githubusercontent.com"


Absolutely — and no apology needed. Here’s a **repo-fit starter scaffold** you can drop in now.

I shaped this around the current public repo: the lab already has a unified `llm.call()` seam, a strategist tier called rarely, canon/state-first principles, and explicit O1 prompt docs. I **did not** assume `aos/retrieve.py` exists in the public tree, so the local retrieval adapter is written against a generic `search(query, top_k)` interface that you can point at your actual retriever. That keeps this eval harness isolated and avoids mutating the current runtime path in `ai-lab/llm.py`. ([GitHub][1])

I’d add this under:

```text
ai-lab/evals/knowledge_plane/
  __init__.py
  runner.py
  adapters.py
  graders.py
  metrics.py
  cases.jsonl
  README.md
```

OpenAI’s current docs also make this a clean comparison target: `file_search` is exposed as a built-in tool in the Responses API, and Responses is the recommended surface for new tool-using flows. ([OpenAI Developers][2])

## `ai-lab/evals/knowledge_plane/README.md`

````md
# Knowledge Plane Eval Harness

This package compares two retrieval planes for strategic reasoning tasks:

1. Local retrieval plane
   - Our own retriever returns top-k chunks
   - Chunks are injected into the prompt
   - Model answers from the same prompt contract

2. Hosted retrieval plane
   - OpenAI `file_search` retrieves top-k chunks from an uploaded vector store
   - Retrieved chunks are normalized into the same context pack
   - Model answers from the same prompt contract

The comparison isolates retrieval as the independent variable.

## Goals

- Compare retrieval quality
- Compare end-to-end strategic answer quality
- Measure latency and cost
- Decide whether hosted retrieval adds real capability or just convenience

## Environment

Required:
- `OPENAI_API_KEY`

Optional:
- `KNOWLEDGE_PLANE_MODEL=gpt-5.4`
- `OPENAI_VECTOR_STORE_ID=vs_...`

## Running

```bash
cd ai-lab
uv run evals/knowledge_plane/runner.py \
  --cases evals/knowledge_plane/cases.jsonl \
  --arm both \
  --model ${KNOWLEDGE_PLANE_MODEL:-gpt-5.4}
````

## Local Adapter Contract

The local retriever passed into `LocalRetriever` must implement:

```python
search(query: str, top_k: int) -> list[dict]
```

Expected row keys:

* `doc_id`
* `chunk_id`
* `text`
* `score`
* optional `metadata`

## Output

Results are written to:

* `evals/knowledge_plane/results/latest.json`

````

## `ai-lab/evals/knowledge_plane/adapters.py`

```python
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Protocol


@dataclass
class RetrievedChunk:
    doc_id: str
    chunk_id: str
    text: str
    score: float
    source: str
    metadata: dict[str, Any] | None = None


class LocalSearchBackend(Protocol):
    def search(self, query: str, top_k: int = 8) -> list[dict[str, Any]]:
        ...


class LocalRetriever:
    def __init__(self, backend: LocalSearchBackend):
        self.backend = backend

    def retrieve(self, query: str, k: int = 8) -> list[RetrievedChunk]:
        rows = self.backend.search(query=query, top_k=k)
        chunks: list[RetrievedChunk] = []
        for i, row in enumerate(rows):
            chunks.append(
                RetrievedChunk(
                    doc_id=str(row.get("doc_id", "unknown")),
                    chunk_id=str(row.get("chunk_id", f"local-{i}")),
                    text=str(row.get("text", "")),
                    score=float(row.get("score", 0.0)),
                    source="local",
                    metadata=row.get("metadata", {}),
                )
            )
        return chunks


class OpenAIFileSearchRetriever:
    """
    Uses Responses API file_search to retrieve chunks from a hosted vector store.

    Requires:
    - openai>=1.x
    - vector_store_id to already exist
    """

    def __init__(self, client: Any, vector_store_id: str, model: str):
        self.client = client
        self.vector_store_id = vector_store_id
        self.model = model

    def retrieve(self, query: str, k: int = 8) -> list[RetrievedChunk]:
        resp = self.client.responses.create(
            model=self.model,
            input=query,
            tools=[
                {
                    "type": "file_search",
                    "vector_store_ids": [self.vector_store_id],
                    "max_num_results": k,
                }
            ],
            tool_choice={"type": "file_search"},
            include=["file_search_call.results"],
            store=False,
        )

        chunks: list[RetrievedChunk] = []

        for item in getattr(resp, "output", []):
            if getattr(item, "type", None) != "file_search_call":
                continue

            for i, result in enumerate(getattr(item, "results", []) or []):
                text = getattr(result, "text", "") or ""
                filename = getattr(result, "filename", None) or "unknown"
                file_id = getattr(result, "file_id", None) or f"openai-{i}"
                score = getattr(result, "score", None)
                metadata = {
                    "filename": filename,
                    "file_id": file_id,
                }
                chunks.append(
                    RetrievedChunk(
                        doc_id=str(filename),
                        chunk_id=str(file_id),
                        text=text,
                        score=float(score or 0.0),
                        source="openai_file_search",
                        metadata=metadata,
                    )
                )

        return chunks


def build_context_pack(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "No retrieved evidence."

    lines: list[str] = []
    for idx, chunk in enumerate(chunks, start=1):
        lines.append(
            f"[{idx}] doc_id={chunk.doc_id} chunk_id={chunk.chunk_id} "
            f"score={chunk.score:.4f} source={chunk.source}\n{chunk.text}".strip()
        )
    return "\n\n".join(lines)


def chunks_to_jsonable(chunks: list[RetrievedChunk]) -> list[dict[str, Any]]:
    return [asdict(c) for c in chunks]
````

## `ai-lab/evals/knowledge_plane/graders.py`

```python
from __future__ import annotations

import json
from typing import Any


def deterministic_retrieval_grade(
    retrieved_doc_ids: list[str],
    expected_supporting_docs: list[str],
) -> dict[str, Any]:
    expected = set(expected_supporting_docs)
    got = set(retrieved_doc_ids)

    hits = expected.intersection(got)
    recall = (len(hits) / len(expected)) if expected else 1.0

    return {
        "expected_count": len(expected),
        "hit_count": len(hits),
        "support_recall": recall,
        "hits": sorted(hits),
        "misses": sorted(expected - got),
    }


def schema_grade(answer_obj: dict[str, Any]) -> dict[str, Any]:
    required = [
        "answer",
        "key_evidence_ids",
        "assumptions",
        "confidence",
        "next_action",
        "kill_criteria",
        "escalation_trigger",
    ]
    missing = [k for k in required if k not in answer_obj]
    return {
        "schema_ok": len(missing) == 0,
        "missing_fields": missing,
    }


def gold_fact_coverage(answer_text: str, gold_facts: list[str]) -> dict[str, Any]:
    answer_lower = answer_text.lower()
    matched = [fact for fact in gold_facts if fact.lower() in answer_lower]
    coverage = (len(matched) / len(gold_facts)) if gold_facts else 1.0
    return {
        "gold_fact_coverage": coverage,
        "matched_gold_facts": matched,
    }


def try_parse_json(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except Exception:
        return {"_raw_text": text, "_json_parse_failed": True}
```

## `ai-lab/evals/knowledge_plane/metrics.py`

```python
from __future__ import annotations

from typing import Any


def aggregate_case_score(
    support_recall: float,
    schema_ok: bool,
    gold_fact_coverage: float,
) -> dict[str, Any]:
    score = (
        0.40 * support_recall
        + 0.35 * gold_fact_coverage
        + 0.25 * (1.0 if schema_ok else 0.0)
    )
    return {
        "case_score": round(score, 4),
        "weights": {
            "support_recall": 0.40,
            "gold_fact_coverage": 0.35,
            "schema_ok": 0.25,
        },
    }


def summarize_results(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"count": 0, "avg_case_score": 0.0}

    avg = sum(r["aggregate"]["case_score"] for r in rows) / len(rows)
    by_arm: dict[str, list[float]] = {}
    for row in rows:
        by_arm.setdefault(row["arm"], []).append(row["aggregate"]["case_score"])

    return {
        "count": len(rows),
        "avg_case_score": round(avg, 4),
        "by_arm": {
            arm: {
                "count": len(scores),
                "avg_case_score": round(sum(scores) / len(scores), 4),
            }
            for arm, scores in by_arm.items()
        },
    }
```

## `ai-lab/evals/knowledge_plane/runner.py`

```python
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from openai import OpenAI

from adapters import (
    LocalRetriever,
    OpenAIFileSearchRetriever,
    build_context_pack,
    chunks_to_jsonable,
)
from graders import (
    deterministic_retrieval_grade,
    gold_fact_coverage,
    schema_grade,
    try_parse_json,
)
from metrics import aggregate_case_score, summarize_results


RESULTS_DIR = Path(__file__).resolve().parent / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


# ---- Local retriever injection point ----------------------------------------
class DummyLocalBackend:
    """
    Replace this with your real retrieval backend adapter.

    Expected shape:
        backend.search(query: str, top_k: int) -> list[dict]
    """

    def search(self, query: str, top_k: int = 8) -> list[dict[str, Any]]:
        # Stub implementation so the scaffold runs.
        return [
            {
                "doc_id": "CANON.md",
                "chunk_id": "stub-1",
                "text": f"Stub local retrieval result for query: {query}",
                "score": 0.1,
                "metadata": {"stub": True},
            }
        ][:top_k]


def load_cases(path: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def strategic_prompt(case: dict[str, Any], context_pack: str) -> str:
    constraints = "\n".join(f"- {x}" for x in case["context"]["constraints"])
    already_tried = "\n".join(f"- {x}" for x in case["context"]["already_tried"])

    return f"""You are the strategist for this project.

## Objective
{case["question"]}

## Success Metric
Return the highest-leverage answer grounded in the retrieved evidence.

## Current State Snapshot
{json.dumps(case["context"], indent=2)}

## Constraints
{constraints}

## What's Already Been Tried
{already_tried}

## Decision Question
{case["decision_question"]}

## Retrieved Evidence
{context_pack}

## Required Output Schema
Return JSON only with this schema:
{{
  "answer": "string",
  "key_evidence_ids": ["string"],
  "assumptions": ["string"],
  "confidence": 0.0,
  "next_action": "string",
  "kill_criteria": ["string"],
  "escalation_trigger": "string"
}}
""".strip()


def answer_with_context(
    client: OpenAI,
    model: str,
    case: dict[str, Any],
    context_pack: str,
) -> tuple[str, dict[str, Any]]:
    prompt = strategic_prompt(case, context_pack)

    started = time.time()
    resp = client.responses.create(
        model=model,
        input=prompt,
        text={"format": {"type": "json_object"}},
        store=False,
    )
    latency = time.time() - started

    text = getattr(resp, "output_text", "") or ""
    usage = getattr(resp, "usage", None)

    usage_dict = {}
    if usage:
        usage_dict = {
            "input_tokens": getattr(usage, "input_tokens", None),
            "output_tokens": getattr(usage, "output_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
        }

    return text, {
        "latency_sec": round(latency, 3),
        "usage": usage_dict,
    }


def run_arm(
    arm: str,
    case: dict[str, Any],
    client: OpenAI,
    model: str,
    vector_store_id: str | None,
) -> dict[str, Any]:
    if arm == "local":
        retriever = LocalRetriever(DummyLocalBackend())
    elif arm == "hosted":
        if not vector_store_id:
            raise RuntimeError("OPENAI_VECTOR_STORE_ID is required for hosted arm.")
        retriever = OpenAIFileSearchRetriever(client, vector_store_id, model)
    else:
        raise ValueError(f"Unknown arm: {arm}")

    retrieved = retriever.retrieve(case["retrieval_query"], k=case.get("top_k", 8))
    context_pack = build_context_pack(retrieved)
    answer_text, llm_meta = answer_with_context(client, model, case, context_pack)

    answer_obj = try_parse_json(answer_text)

    retrieval_grade = deterministic_retrieval_grade(
        retrieved_doc_ids=[c.doc_id for c in retrieved],
        expected_supporting_docs=case["expected_supporting_docs"],
    )
    schema = schema_grade(answer_obj)
    fact_grade = gold_fact_coverage(
        answer_text=answer_obj.get("answer", answer_text),
        gold_facts=case["gold_facts"],
    )
    aggregate = aggregate_case_score(
        support_recall=retrieval_grade["support_recall"],
        schema_ok=schema["schema_ok"],
        gold_fact_coverage=fact_grade["gold_fact_coverage"],
    )

    return {
        "case_id": case["id"],
        "arm": arm,
        "question": case["question"],
        "retrieved": chunks_to_jsonable(retrieved),
        "answer_raw": answer_text,
        "answer_obj": answer_obj,
        "retrieval_grade": retrieval_grade,
        "schema_grade": schema,
        "fact_grade": fact_grade,
        "aggregate": aggregate,
        "llm_meta": llm_meta,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cases",
        required=True,
        help="Path to cases.jsonl",
    )
    parser.add_argument(
        "--arm",
        choices=["local", "hosted", "both"],
        default="both",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("KNOWLEDGE_PLANE_MODEL", "gpt-5.4"),
    )
    args = parser.parse_args()

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    vector_store_id = os.environ.get("OPENAI_VECTOR_STORE_ID")

    cases = load_cases(args.cases)
    arms = ["local", "hosted"] if args.arm == "both" else [args.arm]

    rows: list[dict[str, Any]] = []
    for case in cases:
        for arm in arms:
            print(f"Running case={case['id']} arm={arm}", file=sys.stderr)
            row = run_arm(
                arm=arm,
                case=case,
                client=client,
                model=args.model,
                vector_store_id=vector_store_id,
            )
            rows.append(row)

    summary = summarize_results(rows)
    payload = {
        "model": args.model,
        "case_count": len(cases),
        "run_count": len(rows),
        "summary": summary,
        "results": rows,
    }

    out_path = RESULTS_DIR / "latest.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(json.dumps(summary, indent=2))
    print(f"\nWrote results to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## `ai-lab/evals/knowledge_plane/cases.jsonl`

Here’s a **10-case starter set**. I kept them tightly aligned with the repo’s current canon, README, and strategist contract. Those sources explicitly define the three-loop architecture, strategist escalation conditions, state-over-prompt-history, retrieval memory, and the current O1-centric framing. ([GitHub][3])

```json
{"id":"canon_001","bucket":"canon_retrieval","question":"What is the repo's source of truth for architectural decisions and what operating principles does it define?","retrieval_query":"source of truth architectural decisions operating principles deterministic state over prompt history retrieval memory","decision_question":"What document should govern architectural choices, and which principles should be treated as binding defaults?","context":{"current_state":"Repo initialized with canon, README, and strategy prompt docs. Need to determine which document should dominate architectural choices.","constraints":["Prefer explicit source-of-truth documents over inferred behavior","Return only principles that are clearly stated in repo docs"],"already_tried":["Read README informally","Compared top-level docs manually"]},"expected_supporting_docs":["CANON.md"],"gold_facts":["source of truth","deterministic by default","state over prompt history","modular system over monolithic framework"],"top_k":6}
{"id":"canon_002","bucket":"canon_retrieval","question":"When should the strategic reasoning tier be invoked versus the worker and critic tiers?","retrieval_query":"strategic loop escalation worker critic called rarely failure diagnosis new goals","decision_question":"What events justify escalation to the strategist tier, and what should stay in lower tiers?","context":{"current_state":"Need explicit routing policy for heavy reasoning calls.","constraints":["Keep strategic usage sparse","Use only repo-grounded criteria"],"already_tried":["Skimmed README model tiers","Skimmed canon escalation contract"]},"expected_supporting_docs":["CANON.md","README.md","ai-lab/o1_system_prompt.md"],"gold_facts":["repeated failure without progress","high uncertainty or conflicting evidence","high-stakes decision with material downside","reasoning models are not default workers"],"top_k":8}
{"id":"arch_001","bucket":"architecture_adjudication","question":"Should retrieval remain a local-first system responsibility or be moved into a hosted knowledge plane by default?","retrieval_query":"retrieval memory state durable context windows disposable modular simplicity constraint hosted retrieval local-first","decision_question":"Given the repo's architecture principles, which default is more aligned: local-first retrieval or hosted retrieval by default?","context":{"current_state":"Evaluating a possible hosted knowledge plane while keeping control plane and execution local.","constraints":["Preserve explicit external state as source of truth","Prefer smallest architecture that preserves reliability","Do not optimize for convenience alone"],"already_tried":["Discussed hosted retrieval conceptually","Identified need for eval harness"]},"expected_supporting_docs":["CANON.md","README.md"],"gold_facts":["state is durable","retrieval memory distilled heuristics insights for reuse","prefer the smallest architecture that preserves reliability","no feature is added unless it improves reliability observability or decision quality"],"top_k":8}
{"id":"arch_002","bucket":"architecture_adjudication","question":"Should the strategic model interface remain O1-specific or become model-pluggable?","retrieval_query":"model selection optimization target not specific models llm.call swapping models config change strategic tier current default","decision_question":"What architecture choice better fits the repo today: O1-specific strategy wiring or a pluggable strategic tier abstraction?","context":{"current_state":"Repo currently frames O1 as the strategic tier but also says model selection is itself an optimization target.","constraints":["Respect current repo language","Prefer future-proofing only if it does not add unnecessary complexity"],"already_tried":["Reviewed README model tier section","Reviewed llm abstraction at high level"]},"expected_supporting_docs":["README.md","CANON.md"],"gold_facts":["system routes to three tiers based on task complexity not specific models","which model fills each tier is itself an optimization target","swapping models is a config change not a code change"],"top_k":8}
{"id":"failure_001","bucket":"failure_diagnosis","question":"The worker has failed a task six times with no measurable progress. What should the system do next?","retrieval_query":"worker fails 5+ times strategic loop escalate repeated failure no progress failure diagnosis","decision_question":"What is the correct next system action after repeated worker failure, and what must be included in the escalation payload?","context":{"current_state":"Worker loop is stuck on a task and retries are no longer producing new evidence.","constraints":["Follow explicit escalation contract","Prefer structured replanning over ad hoc retrying"],"already_tried":["Continued worker retries","Collected basic logs"]},"expected_supporting_docs":["CANON.md","ai-lab/o1_system_prompt.md"],"gold_facts":["repeated failure without progress","goal and constraints","what was tried","failure signatures","current state snapshot","decision question"],"top_k":8}
{"id":"failure_002","bucket":"failure_diagnosis","question":"The team keeps stuffing more conversation history into prompts to fix drift. Is that aligned with the repo architecture?","retrieval_query":"context windows disposable state durable runtime context only what is needed explicit external state source of truth","decision_question":"Should drift be addressed by larger prompt history or by strengthening explicit state and retrieval memory?","context":{"current_state":"Observed tendency to compensate for drift by adding more transcript context.","constraints":["Must follow canon memory contract","Answer should recommend a structural fix, not a chat habit"],"already_tried":["Longer prompts","Manual copy-paste context"]},"expected_supporting_docs":["CANON.md","ai-lab/o1_system_prompt.md"],"gold_facts":["state over prompt history","context windows are disposable","runtime context only what is needed for the current node task","explicit external state as the source of truth"],"top_k":8}
{"id":"heuristic_001","bucket":"heuristic_reuse","question":"What recurring design heuristic should be applied when evaluating any new subsystem proposal?","retrieval_query":"simplicity constraint smallest architecture preserves reliability no feature unless improves reliability observability decision quality","decision_question":"What default design heuristic should govern new subsystem additions?","context":{"current_state":"Need a concise reusable heuristic for evaluating proposed subsystems such as hosted retrieval, more memory layers, or new agents.","constraints":["Heuristic must be repo-native","Must be short enough to reuse in future reviews"],"already_tried":["Informal architecture discussions","Ad hoc tradeoff analysis"]},"expected_supporting_docs":["CANON.md"],"gold_facts":["prefer the smallest architecture that preserves reliability","no feature is added unless it improves reliability observability or decision quality"],"top_k":6}
{"id":"heuristic_002","bucket":"heuristic_reuse","question":"What is the repo's reusable lesson about where probabilistic reasoning belongs versus where determinism belongs?","retrieval_query":"deterministic boundary probabilistic components planning workflow state transitions routing policies persistence artifact lineage","decision_question":"How should the system split deterministic machinery from probabilistic reasoning?","context":{"current_state":"Need to decide whether a new capability belongs in deterministic orchestration or model-driven reasoning.","constraints":["Answer must map categories correctly","Prefer explicit canon categories"],"already_tried":["Discussed deterministic-first informally"]},"expected_supporting_docs":["CANON.md"],"gold_facts":["workflow state transitions","routing policies","persistence and artifact lineage","planning","hypothesis generation","strategic tradeoff analysis"],"top_k":8}
{"id":"runbook_001","bucket":"runbook_synthesis","question":"What is the smallest reliable MVP the strategist should define next for this repo?","retrieval_query":"smallest reliable MVP first build slice ordered task graph persist state resume cleanly stop safely loop guardrails","decision_question":"What exact MVP scope and ordered task graph should be executed next?","context":{"current_state":"Repo includes an MVP strategist prompt but implementation prioritization remains open.","constraints":["Keep scope minimal","Favor reliability over feature breadth","Output must be directly implementable in this repo"],"already_tried":["Drafted strategist prompt","Outlined runtime modules"]},"expected_supporting_docs":["ai-lab/o1_next_question_mvp.md","CANON.md"],"gold_facts":["build an executable task graph for a new goal","run worker + critic retries on at least one task","escalate to strategist after repeated failure","persist state and resume cleanly","stop safely on loop guardrails"],"top_k":8}
{"id":"runbook_002","bucket":"runbook_synthesis","question":"What exact information must be bundled when submitting a strategic question to the strategist model?","retrieval_query":"objective success metric current state snapshot constraints what was tried decision question required output schema escalation input must include","decision_question":"What is the minimal but sufficient question contract for a strategist escalation?","context":{"current_state":"Need a consistent template for high-cost strategic calls.","constraints":["Must be grounded in repo docs","Should be specific enough for automated generation later"],"already_tried":["Used informal question formats","Drafted one MVP-specific O1 prompt"]},"expected_supporting_docs":["CANON.md","ai-lab/o1_next_question_mvp.md"],"gold_facts":["goal and constraints","what was tried","failure signatures","current state snapshot","decision question","required output schema"],"top_k":8}
```

## What I’d change first once this is in

Because the current public `llm.py` still routes O1/O3-family calls through `chat.completions.create(...)`, I’d keep this harness **parallel** rather than splicing it into the live runtime yet. That lets you compare retrieval planes cleanly without mixing “new retrieval plane” with “new model transport layer” in the same step. ([GitHub][1])

## First two edits I’d make in your repo after pasting this

Replace the dummy backend with your real retriever:

```python
# in runner.py
from your_module import YourRealRetrieverBackend
...
retriever = LocalRetriever(YourRealRetrieverBackend(...))
```

Then add a tiny export script for hosted evals only, so the hosted arm is testing the **same canon corpus** rather than a differently curated one. OpenAI’s hosted `file_search` is vector-store based, so parity of exported documents matters a lot. ([OpenAI Developers][2])

If you want, the next clean step is for me to draft the matching `exporters.py` that ingests `CANON.md`, `README.md`, `ai-lab/*.md`, and `docs/lab/*.md` into one hosted eval corpus.

[1]: https://raw.githubusercontent.com/mdc159/01/master/ai-lab/llm.py "raw.githubusercontent.com"
[2]: https://developers.openai.com/api/docs/guides/tools-file-search/?utm_source=chatgpt.com "File search | OpenAI API"
[3]: https://raw.githubusercontent.com/mdc159/01/master/README.md "raw.githubusercontent.com"

Yep — proceed it is. Below is the missing half so the harness becomes a genuinely matched set: exporter for the hosted corpus, a tiny package init, and one small runner upgrade so you don’t have to hand-edit `DummyLocalBackend`. I based the exporter on the current repo layout (`ai-lab/`, `docs/lab/`, `references/AutoResearch-mac/`, root docs) and on OpenAI’s current vector-store/file-search flow (`vector_stores.files.upload_and_poll(...)`, then Responses `file_search` against `vector_store_ids`). The repo’s dependency floor is only `openai>=1.30.0`, so whether you already have these helpers depends on the actual SDK version installed locally. ([GitHub][1])

Add this as `ai-lab/evals/knowledge_plane/__init__.py`:

```python
"""Knowledge-plane evaluation harness."""
```

Add this as `ai-lab/evals/knowledge_plane/exporters.py`:

```python
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Iterable

from openai import OpenAI


HERE = Path(__file__).resolve().parent
RESULTS_DIR = HERE / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# exporters.py lives at:
# repo_root/ai-lab/evals/knowledge_plane/exporters.py
DEFAULT_REPO_ROOT = HERE.parents[3]

DEFAULT_PATTERNS = [
    "README.md",
    "CANON.md",
    "CLAUDE.md",
    ".env.example",
    "pyproject.toml",
    "requirements.txt",
    "docs/lab/**/*.md",
    "ai-lab/**/*.md",
]

OPTIONAL_CODE_PATTERNS = [
    "ai-lab/**/*.py",
]

OPTIONAL_REFERENCE_PATTERNS = [
    "references/AutoResearch-mac/**/*.md",
    "references/AutoResearch-mac/**/*.txt",
    "references/AutoResearch-mac/**/*.py",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def expand_patterns(repo_root: Path, patterns: list[str]) -> list[Path]:
    seen: set[Path] = set()
    out: list[Path] = []

    for pattern in patterns:
        for path in repo_root.glob(pattern):
            if not path.is_file():
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            out.append(path)

    return sorted(out, key=lambda p: str(p.relative_to(repo_root)))


def collect_paths(
    repo_root: Path,
    include_code: bool = False,
    include_references: bool = False,
) -> list[Path]:
    patterns = list(DEFAULT_PATTERNS)
    if include_code:
        patterns.extend(OPTIONAL_CODE_PATTERNS)
    if include_references:
        patterns.extend(OPTIONAL_REFERENCE_PATTERNS)
    return expand_patterns(repo_root, patterns)


def create_vector_store(client: OpenAI, name: str) -> str:
    vs = client.vector_stores.create(name=name)
    return vs.id


def upload_paths(
    client: OpenAI,
    vector_store_id: str,
    repo_root: Path,
    paths: Iterable[Path],
) -> list[dict]:
    manifest: list[dict] = []

    for idx, path in enumerate(paths, start=1):
        rel = str(path.relative_to(repo_root))
        stat = path.stat()
        digest = sha256_file(path)

        print(f"[{idx}] Uploading {rel} ...")
        with path.open("rb") as f:
            vs_file = client.vector_stores.files.upload_and_poll(
                vector_store_id=vector_store_id,
                file=f,
            )

        entry = {
            "path": rel,
            "bytes": stat.st_size,
            "sha256": digest,
            "vector_store_file_id": getattr(vs_file, "id", None),
            "file_id": getattr(vs_file, "file_id", None),
            "status": getattr(vs_file, "status", None),
        }
        manifest.append(entry)

    return manifest


def write_manifest(
    manifest_path: Path,
    payload: dict,
) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export repo docs into an OpenAI vector store for hosted file_search evals."
    )
    parser.add_argument(
        "--repo-root",
        default=str(DEFAULT_REPO_ROOT),
        help="Path to repo root. Defaults to auto-detected repo root.",
    )
    parser.add_argument(
        "--vector-store-id",
        default=None,
        help="Existing vector store ID to append to. If omitted, a new vector store is created.",
    )
    parser.add_argument(
        "--name",
        default=None,
        help="Vector store name when creating a new store.",
    )
    parser.add_argument(
        "--include-code",
        action="store_true",
        help="Include ai-lab/**/*.py in the exported corpus.",
    )
    parser.add_argument(
        "--include-references",
        action="store_true",
        help="Include references/AutoResearch-mac/**/*.{md,txt,py} in the exported corpus.",
    )
    parser.add_argument(
        "--manifest-out",
        default=str(RESULTS_DIR / "export_manifest.json"),
        help="Where to write the export manifest JSON.",
    )
    args = parser.parse_args()

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required.")

    repo_root = Path(args.repo_root).resolve()
    if not repo_root.exists():
        raise RuntimeError(f"Repo root does not exist: {repo_root}")

    paths = collect_paths(
        repo_root=repo_root,
        include_code=args.include_code,
        include_references=args.include_references,
    )

    if not paths:
        raise RuntimeError("No files matched the export patterns.")

    client = OpenAI(api_key=api_key)

    vector_store_id = args.vector_store_id
    created_new_store = False
    if not vector_store_id:
        name = args.name or f"knowledge-plane-eval-{time.strftime('%Y%m%d-%H%M%S')}"
        vector_store_id = create_vector_store(client, name)
        created_new_store = True

    manifest_entries = upload_paths(
        client=client,
        vector_store_id=vector_store_id,
        repo_root=repo_root,
        paths=paths,
    )

    payload = {
        "repo_root": str(repo_root),
        "vector_store_id": vector_store_id,
        "created_new_store": created_new_store,
        "file_count": len(manifest_entries),
        "include_code": args.include_code,
        "include_references": args.include_references,
        "patterns": {
            "default": DEFAULT_PATTERNS,
            "optional_code": OPTIONAL_CODE_PATTERNS if args.include_code else [],
            "optional_references": OPTIONAL_REFERENCE_PATTERNS if args.include_references else [],
        },
        "files": manifest_entries,
    }

    manifest_path = Path(args.manifest_out).resolve()
    write_manifest(manifest_path, payload)

    print("\nDone.")
    print(f"Vector store: {vector_store_id}")
    print(f"Manifest:     {manifest_path}")
    print("\nExport this before running the hosted arm:")
    print(f"export OPENAI_VECTOR_STORE_ID={vector_store_id}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Then make this small upgrade in `ai-lab/evals/knowledge_plane/runner.py` so the local arm can load your real retriever by import path instead of hardcoding a stub:

```python
from importlib import import_module
```

```python
def load_local_backend(spec: str | None):
    if not spec:
        return DummyLocalBackend()

    if ":" not in spec:
        raise ValueError(
            "Local backend spec must look like 'package.module:ClassName'"
        )

    module_name, class_name = spec.split(":", 1)
    module = import_module(module_name)
    cls = getattr(module, class_name)
    return cls()
```

Add this CLI argument:

```python
parser.add_argument(
    "--local-backend",
    default=os.environ.get("KNOWLEDGE_PLANE_LOCAL_BACKEND"),
    help="Import path for local retrieval backend, e.g. 'aos.retrieve:RetrieverBackend'",
)
```

Then change this part:

```python
if arm == "local":
    retriever = LocalRetriever(load_local_backend(args.local_backend))
```

and thread `args.local_backend` into `run_arm(...)` from `main()`.

The intended usage is now:

```bash
cd ai-lab

# 1) Export the same doc corpus into a hosted vector store
uv run evals/knowledge_plane/exporters.py \
  --include-code \
  --include-references

# 2) Point the hosted arm at that vector store
export OPENAI_VECTOR_STORE_ID=vs_...

# 3) Point the local arm at your real retriever
export KNOWLEDGE_PLANE_LOCAL_BACKEND='aos.retrieve:RetrieverBackend'

# 4) Run both arms
uv run evals/knowledge_plane/runner.py \
  --cases evals/knowledge_plane/cases.jsonl \
  --arm both \
  --model gpt-5.4
```

That keeps the comparison apples-to-apples: same benchmark cases, same downstream reasoning prompt, same model, only the retrieval plane changes. That matches the repo’s current architecture goal of keeping the strategic tier sparse and high-leverage, while treating model choice and system boundaries as optimization targets rather than dogma. ([GitHub][2])

One practical note: the exporter defaults to **docs first** and only includes code or the AutoResearch references when you explicitly opt in. That’s deliberate — your benchmark question is mostly about canon docs, runbooks, heuristics, and failure taxonomies, not “can file search retrieve arbitrary source files.” The repo already makes canon and explicit state the source of truth, with retrieval memory as a reusable layer and the strategist reserved for decomposition, diagnosis, and reframing. ([GitHub][3])

The next clean move is to tighten `cases.jsonl` so every case names the exact expected docs from the exporter manifest. That gives you a sharper support-recall score and prevents silent drift between the local and hosted corpora.

[1]: https://github.com/mdc159/01 "https://github.com/mdc159/01"
[2]: https://raw.githubusercontent.com/mdc159/01/master/README.md "https://raw.githubusercontent.com/mdc159/01/master/README.md"
[3]: https://raw.githubusercontent.com/mdc159/01/master/CANON.md "https://raw.githubusercontent.com/mdc159/01/master/CANON.md"

Exactly. The repo already leans that way: **CANON is the source of truth**, **state is durable**, **context windows are disposable**, and major decisions are supposed to be checked against canon first. That means the eval harness should be strict about identifiers, manifests, and schema contracts instead of relying on fuzzy matching. ([GitHub][1])

I’d lock it down like this:

**1. One canonical document ID format**
Use **repo-relative paths only** as `doc_id`, everywhere:

* `CANON.md`
* `README.md`
* `ai-lab/o1_next_question_mvp.md`
* `docs/lab/knowledge-plane-eval-prd.md`

No filenames without paths, no hosted file IDs as primary IDs, no aliases. The repo already treats explicit external state as the source of truth, so these IDs should be stable and human-readable. ([GitHub][1])

**2. Manifest is the corpus contract**
Every hosted export should write a manifest with:

* `doc_id`
* `sha256`
* `bytes`
* `exported_at`
* `vector_store_file_id`
* optional `source_class` like `canon|runbook|prompt|code|reference`

Then `cases.jsonl` must reference only `doc_id` values that actually exist in that manifest. If a case expects `CANON.md` and it is not in the manifest, the run should fail before evaluation starts. That fits the repo’s “metrics are truth” and “failures are reverted cleanly” mindset. ([GitHub][2])

**3. Local and hosted retrieval must emit the same normalized chunk object**
Both arms should return:

```json
{
  "doc_id": "string",
  "chunk_id": "string",
  "text": "string",
  "score": 0.0,
  "source": "local|openai_file_search",
  "metadata": {}
}
```

That matters because `llm.call()` is already your abstraction seam for model routing; the retrieval side should get the same treatment. ([GitHub][2])

**4. Cases should reference evidence by canonical doc ID, not by intuition**
Each case should contain:

* `expected_supporting_docs`
* `allowed_supporting_docs` if useful
* `gold_facts`
* `retrieval_query`
* `decision_question`

And `expected_supporting_docs` should be validated against the manifest before the run starts. No silent drift. The repo’s escalation contract is already explicit about required inputs like goal, constraints, what was tried, failure signatures, and decision question; the eval cases should be equally explicit. ([GitHub][1])

**5. Answer grading should reject unknown evidence IDs**
If the model returns:

```json
"key_evidence_ids": ["CANON.md", "ai-lab/o1_next_question_mvp.md"]
```

then every cited ID must exist in the retrieved chunk set for that run. If not, groundedness fails. That keeps the system aligned with the repo’s bias toward inspectability and maintainability. ([GitHub][1])

**6. Separate primary IDs from transport IDs**
Hosted IDs like `vector_store_file_id` or OpenAI `file_id` should live in metadata only. They are useful for debugging, but they should never replace canonical `doc_id`. Otherwise your eval becomes vendor-shaped instead of repo-shaped. Given the repo’s explicit preference for modular systems and swapping models as a config change, that separation matters. ([GitHub][1])

**7. Freeze a corpus version per eval run**
Add a `corpus_version` derived from the manifest hash. Every result file should record:

* `corpus_version`
* `model`
* `arm`
* `case_set_version`

That way you can compare runs cleanly instead of wondering whether retrieval changed because the corpus changed. The repo’s design is built around explicit state and repeatable loops, so this is very on-brand. ([GitHub][1])

My recommended rule set, in one line:

> **If it is not in the manifest under a canonical repo-relative `doc_id`, it does not exist for eval purposes.** ([GitHub][1])

The next concrete patch should do three things:

* validate `cases.jsonl` against the export manifest before running,
* normalize hosted results back to repo-relative `doc_id`,
* fail grading when `key_evidence_ids` cite anything outside the retrieved set. ([GitHub][1])

I’ll draft those validation and normalization patches next.

[1]: https://raw.githubusercontent.com/mdc159/01/master/CANON.md "raw.githubusercontent.com"
[2]: https://raw.githubusercontent.com/mdc159/01/master/README.md "raw.githubusercontent.com"

Perfect. This is the hardening pass that makes the harness **standardized instead of merely functional**.

It matches the repo’s current rules: `CANON.md` is the product-spec authority, state is durable, major architecture/prompt/model-role changes should be checked against canon, and the strategic tier is already defined around a stricter v2 query contract. The repo also already has a single `llm.call()` seam, which is exactly why this eval harness can stay isolated and still be repo-native. ([GitHub][1])

The two key facts from OpenAI’s current platform docs that drive this patch are: vector-store ingestion is done with `client.vector_stores.create(...)` plus `client.vector_stores.files.upload_and_poll(...)`, and if you want the actual file-search hits back for grading, you need `include=["file_search_call.results"]`, which returns items including `filename`, `file_id`, `score`, and `text`. That means the manifest must be the canonical translator from hosted transport IDs back to repo-relative `doc_id`. ([OpenAI Developers][2])

## What this patch set adds

1. Canonical `doc_id` and corpus version helpers
2. A manifest index that maps `upload_name` and `file_id` back to repo-relative `doc_id`
3. Case validation against the manifest before the run starts
4. Hosted result normalization back to canonical `doc_id`
5. Groundedness checks that fail if the model cites evidence it did not actually retrieve
6. A stricter exporter that stages deterministic upload filenames so hosted retrieval can be normalized cleanly

With this, you have a **complete Phase-1 evaluation harness** for the knowledge-plane question, assuming you wire in your real local retriever. ([GitHub][1])

---

## 1) Add `ai-lab/evals/knowledge_plane/normalization.py`

```python
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


def canonical_doc_id(path: str | Path) -> str:
    """
    Canonical doc IDs are always repo-relative POSIX-style paths.
    """
    return str(Path(path).as_posix()).lstrip("./")


def safe_upload_name(doc_id: str, sha256_hex: str) -> str:
    """
    Deterministic hosted filename derived from canonical doc_id.
    We do NOT trust hosted filenames to equal repo-relative paths.
    """
    stem = re.sub(r"[^A-Za-z0-9._-]+", "__", doc_id)
    short = sha256_hex[:12]
    return f"{short}__{stem}"


def manifest_corpus_version(manifest: dict[str, Any]) -> str:
    """
    Stable corpus version from doc_id + sha256 pairs.
    """
    items = sorted(
        (f["doc_id"], f["sha256"])
        for f in manifest.get("files", [])
    )
    raw = json.dumps(items, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def build_manifest_index(manifest: dict[str, Any]) -> dict[str, Any]:
    by_doc_id: dict[str, dict[str, Any]] = {}
    by_upload_name: dict[str, dict[str, Any]] = {}
    by_file_id: dict[str, dict[str, Any]] = {}

    for entry in manifest.get("files", []):
        doc_id = entry["doc_id"]
        by_doc_id[doc_id] = entry

        upload_name = entry.get("upload_name")
        if upload_name:
            by_upload_name[upload_name] = entry

        file_id = entry.get("file_id")
        if file_id:
            by_file_id[file_id] = entry

    return {
        "by_doc_id": by_doc_id,
        "by_upload_name": by_upload_name,
        "by_file_id": by_file_id,
    }


def normalize_hosted_doc_id(
    *,
    filename: str | None,
    file_id: str | None,
    manifest_index: dict[str, Any],
) -> str:
    """
    Resolve hosted retrieval results back to canonical repo-relative doc_id.
    """
    if file_id and file_id in manifest_index["by_file_id"]:
        return manifest_index["by_file_id"][file_id]["doc_id"]

    if filename and filename in manifest_index["by_upload_name"]:
        return manifest_index["by_upload_name"][filename]["doc_id"]

    raise KeyError(
        f"Unable to normalize hosted result to canonical doc_id "
        f"(filename={filename!r}, file_id={file_id!r})"
    )


def validate_cases_against_manifest(
    cases: list[dict[str, Any]],
    manifest: dict[str, Any],
) -> None:
    known = set(build_manifest_index(manifest)["by_doc_id"].keys())

    missing_refs: list[tuple[str, str]] = []
    for case in cases:
        for doc_id in case.get("expected_supporting_docs", []):
            if doc_id not in known:
                missing_refs.append((case["id"], doc_id))

    if missing_refs:
        pretty = "\n".join(f"- case={cid} missing doc_id={doc}" for cid, doc in missing_refs)
        raise RuntimeError(
            "cases.jsonl references docs not present in export manifest:\n" + pretty
        )


def validate_retrieved_doc_ids_known(
    retrieved_doc_ids: list[str],
    manifest: dict[str, Any],
) -> None:
    known = set(build_manifest_index(manifest)["by_doc_id"].keys())
    unknown = sorted(set(retrieved_doc_ids) - known)
    if unknown:
        raise RuntimeError(
            "Retriever returned doc_ids not present in manifest:\n- "
            + "\n- ".join(unknown)
        )
```

---

## 2) Replace `exporters.py` with a manifest-driven staged uploader

This version writes canonical `doc_id`, deterministic `upload_name`, and a corpus manifest. It stages temp copies with the deterministic upload names so the hosted arm can normalize results reliably. That’s necessary because the Responses/file-search result surface gives you `filename` and `file_id`, not your repo-relative path for free. ([OpenAI Developers][2])

```python
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Iterable

from openai import OpenAI

from normalization import canonical_doc_id, manifest_corpus_version, safe_upload_name


HERE = Path(__file__).resolve().parent
RESULTS_DIR = HERE / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_REPO_ROOT = HERE.parents[3]

DEFAULT_PATTERNS = [
    "README.md",
    "CANON.md",
    "CLAUDE.md",
    ".env.example",
    "pyproject.toml",
    "requirements.txt",
    "docs/lab/**/*.md",
    "ai-lab/**/*.md",
]

OPTIONAL_CODE_PATTERNS = [
    "ai-lab/**/*.py",
]

OPTIONAL_REFERENCE_PATTERNS = [
    "references/AutoResearch-mac/**/*.md",
    "references/AutoResearch-mac/**/*.txt",
    "references/AutoResearch-mac/**/*.py",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def expand_patterns(repo_root: Path, patterns: list[str]) -> list[Path]:
    seen: set[Path] = set()
    out: list[Path] = []

    for pattern in patterns:
        for path in repo_root.glob(pattern):
            if not path.is_file():
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            out.append(path)

    return sorted(out, key=lambda p: str(p.relative_to(repo_root)))


def collect_paths(
    repo_root: Path,
    include_code: bool = False,
    include_references: bool = False,
) -> list[Path]:
    patterns = list(DEFAULT_PATTERNS)
    if include_code:
        patterns.extend(OPTIONAL_CODE_PATTERNS)
    if include_references:
        patterns.extend(OPTIONAL_REFERENCE_PATTERNS)
    return expand_patterns(repo_root, patterns)


def create_vector_store(client: OpenAI, name: str) -> str:
    vs = client.vector_stores.create(name=name)
    return vs.id


def write_manifest(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def upload_paths(
    client: OpenAI,
    vector_store_id: str,
    repo_root: Path,
    paths: Iterable[Path],
) -> list[dict]:
    manifest_entries: list[dict] = []

    with tempfile.TemporaryDirectory(prefix="kp_export_") as tmp:
        tmpdir = Path(tmp)

        for idx, path in enumerate(paths, start=1):
            doc_id = canonical_doc_id(path.relative_to(repo_root))
            sha256_hex = sha256_file(path)
            upload_name = safe_upload_name(doc_id, sha256_hex)
            staged_path = tmpdir / upload_name
            shutil.copy2(path, staged_path)

            print(f"[{idx}] Uploading {doc_id} as {upload_name} ...")
            with staged_path.open("rb") as f:
                vs_file = client.vector_stores.files.upload_and_poll(
                    vector_store_id=vector_store_id,
                    file=f,
                )

            entry = {
                "doc_id": doc_id,
                "path": doc_id,
                "upload_name": upload_name,
                "bytes": path.stat().st_size,
                "sha256": sha256_hex,
                "vector_store_file_id": getattr(vs_file, "id", None),
                "file_id": getattr(vs_file, "file_id", None),
                "status": getattr(vs_file, "status", None),
            }
            manifest_entries.append(entry)

    return manifest_entries


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export repo docs into an OpenAI vector store for knowledge-plane evals."
    )
    parser.add_argument("--repo-root", default=str(DEFAULT_REPO_ROOT))
    parser.add_argument("--vector-store-id", default=None)
    parser.add_argument("--name", default=None)
    parser.add_argument("--include-code", action="store_true")
    parser.add_argument("--include-references", action="store_true")
    parser.add_argument(
        "--manifest-out",
        default=str(RESULTS_DIR / "export_manifest.json"),
    )
    args = parser.parse_args()

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required.")

    repo_root = Path(args.repo_root).resolve()
    if not repo_root.exists():
        raise RuntimeError(f"Repo root does not exist: {repo_root}")

    paths = collect_paths(
        repo_root=repo_root,
        include_code=args.include_code,
        include_references=args.include_references,
    )
    if not paths:
        raise RuntimeError("No files matched the export patterns.")

    client = OpenAI(api_key=api_key)

    vector_store_id = args.vector_store_id
    created_new_store = False
    if not vector_store_id:
        name = args.name or f"knowledge-plane-eval-{time.strftime('%Y%m%d-%H%M%S')}"
        vector_store_id = create_vector_store(client, name)
        created_new_store = True

    files = upload_paths(
        client=client,
        vector_store_id=vector_store_id,
        repo_root=repo_root,
        paths=paths,
    )

    payload = {
        "repo_root": str(repo_root),
        "vector_store_id": vector_store_id,
        "created_new_store": created_new_store,
        "file_count": len(files),
        "include_code": args.include_code,
        "include_references": args.include_references,
        "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "files": files,
    }
    payload["corpus_version"] = manifest_corpus_version(payload)

    manifest_path = Path(args.manifest_out).resolve()
    write_manifest(manifest_path, payload)

    print("\nDone.")
    print(f"Vector store:    {vector_store_id}")
    print(f"Corpus version:  {payload['corpus_version']}")
    print(f"Manifest:        {manifest_path}")
    print(f"export OPENAI_VECTOR_STORE_ID={vector_store_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

---

## 3) Patch `adapters.py` so hosted results normalize back to canonical `doc_id`

```python
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Protocol

from normalization import canonical_doc_id, normalize_hosted_doc_id


@dataclass
class RetrievedChunk:
    doc_id: str
    chunk_id: str
    text: str
    score: float
    source: str
    metadata: dict[str, Any] | None = None


class LocalSearchBackend(Protocol):
    def search(self, query: str, top_k: int = 8) -> list[dict[str, Any]]:
        ...


class LocalRetriever:
    def __init__(self, backend: LocalSearchBackend):
        self.backend = backend

    def retrieve(self, query: str, k: int = 8) -> list[RetrievedChunk]:
        rows = self.backend.search(query=query, top_k=k)
        chunks: list[RetrievedChunk] = []
        for i, row in enumerate(rows):
            chunks.append(
                RetrievedChunk(
                    doc_id=canonical_doc_id(str(row.get("doc_id", "unknown"))),
                    chunk_id=str(row.get("chunk_id", f"local-{i}")),
                    text=str(row.get("text", "")),
                    score=float(row.get("score", 0.0)),
                    source="local",
                    metadata=row.get("metadata", {}),
                )
            )
        return chunks


class OpenAIFileSearchRetriever:
    def __init__(
        self,
        client: Any,
        vector_store_id: str,
        model: str,
        manifest_index: dict[str, Any],
    ):
        self.client = client
        self.vector_store_id = vector_store_id
        self.model = model
        self.manifest_index = manifest_index

    def retrieve(self, query: str, k: int = 8) -> list[RetrievedChunk]:
        resp = self.client.responses.create(
            model=self.model,
            input=query,
            tools=[
                {
                    "type": "file_search",
                    "vector_store_ids": [self.vector_store_id],
                    "max_num_results": k,
                }
            ],
            tool_choice={"type": "file_search"},
            include=["file_search_call.results"],
            store=False,
        )

        chunks: list[RetrievedChunk] = []

        for item in getattr(resp, "output", []):
            if getattr(item, "type", None) != "file_search_call":
                continue

            for i, result in enumerate(getattr(item, "results", []) or []):
                filename = getattr(result, "filename", None)
                file_id = getattr(result, "file_id", None)

                doc_id = normalize_hosted_doc_id(
                    filename=filename,
                    file_id=file_id,
                    manifest_index=self.manifest_index,
                )

                chunks.append(
                    RetrievedChunk(
                        doc_id=doc_id,
                        chunk_id=f"{doc_id}::hosted-{i}",
                        text=getattr(result, "text", "") or "",
                        score=float(getattr(result, "score", 0.0) or 0.0),
                        source="openai_file_search",
                        metadata={
                            "filename": filename,
                            "file_id": file_id,
                        },
                    )
                )

        return chunks


def build_context_pack(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "No retrieved evidence."

    lines: list[str] = []
    for idx, chunk in enumerate(chunks, start=1):
        lines.append(
            f"[{idx}] doc_id={chunk.doc_id} chunk_id={chunk.chunk_id} "
            f"score={chunk.score:.4f} source={chunk.source}\n{chunk.text}".strip()
        )
    return "\n\n".join(lines)


def chunks_to_jsonable(chunks: list[RetrievedChunk]) -> list[dict[str, Any]]:
    return [asdict(c) for c in chunks]
```

---

## 4) Patch `graders.py` to enforce groundedness

This is the bit that stops the model from citing docs it never actually saw.

```python
from __future__ import annotations

import json
from typing import Any


def deterministic_retrieval_grade(
    retrieved_doc_ids: list[str],
    expected_supporting_docs: list[str],
) -> dict[str, Any]:
    expected = set(expected_supporting_docs)
    got = set(retrieved_doc_ids)

    hits = expected.intersection(got)
    recall = (len(hits) / len(expected)) if expected else 1.0

    return {
        "expected_count": len(expected),
        "hit_count": len(hits),
        "support_recall": recall,
        "hits": sorted(hits),
        "misses": sorted(expected - got),
    }


def schema_grade(answer_obj: dict[str, Any]) -> dict[str, Any]:
    required = [
        "answer",
        "key_evidence_ids",
        "assumptions",
        "confidence",
        "next_action",
        "kill_criteria",
        "escalation_trigger",
    ]
    missing = [k for k in required if k not in answer_obj]
    return {
        "schema_ok": len(missing) == 0,
        "missing_fields": missing,
    }


def evidence_citation_grade(
    answer_obj: dict[str, Any],
    retrieved_doc_ids: list[str],
) -> dict[str, Any]:
    cited = answer_obj.get("key_evidence_ids", [])
    if not isinstance(cited, list):
        cited = []

    retrieved = set(retrieved_doc_ids)
    bad = sorted([doc_id for doc_id in cited if doc_id not in retrieved])

    return {
        "citations_ok": len(bad) == 0,
        "cited_count": len(cited),
        "invalid_citations": bad,
    }


def gold_fact_coverage(answer_text: str, gold_facts: list[str]) -> dict[str, Any]:
    answer_lower = answer_text.lower()
    matched = [fact for fact in gold_facts if fact.lower() in answer_lower]
    coverage = (len(matched) / len(gold_facts)) if gold_facts else 1.0
    return {
        "gold_fact_coverage": coverage,
        "matched_gold_facts": matched,
    }


def try_parse_json(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except Exception:
        return {"_raw_text": text, "_json_parse_failed": True}
```

---

## 5) Patch `metrics.py` so bad citations hurt the score

```python
from __future__ import annotations

from typing import Any


def aggregate_case_score(
    support_recall: float,
    schema_ok: bool,
    gold_fact_coverage: float,
    citations_ok: bool,
) -> dict[str, Any]:
    score = (
        0.35 * support_recall
        + 0.25 * gold_fact_coverage
        + 0.20 * (1.0 if schema_ok else 0.0)
        + 0.20 * (1.0 if citations_ok else 0.0)
    )
    return {
        "case_score": round(score, 4),
        "weights": {
            "support_recall": 0.35,
            "gold_fact_coverage": 0.25,
            "schema_ok": 0.20,
            "citations_ok": 0.20,
        },
    }


def summarize_results(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"count": 0, "avg_case_score": 0.0}

    avg = sum(r["aggregate"]["case_score"] for r in rows) / len(rows)
    by_arm: dict[str, list[float]] = {}
    for row in rows:
        by_arm.setdefault(row["arm"], []).append(row["aggregate"]["case_score"])

    return {
        "count": len(rows),
        "avg_case_score": round(avg, 4),
        "by_arm": {
            arm: {
                "count": len(scores),
                "avg_case_score": round(sum(scores) / len(scores), 4),
            }
            for arm, scores in by_arm.items()
        },
    }
```

---

## 6) Patch `runner.py` to validate cases and manifest before running

This is the “no silent drift” patch.

```python
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from importlib import import_module
from pathlib import Path
from typing import Any

from openai import OpenAI

from adapters import (
    LocalRetriever,
    OpenAIFileSearchRetriever,
    build_context_pack,
    chunks_to_jsonable,
)
from graders import (
    deterministic_retrieval_grade,
    evidence_citation_grade,
    gold_fact_coverage,
    schema_grade,
    try_parse_json,
)
from metrics import aggregate_case_score, summarize_results
from normalization import (
    build_manifest_index,
    manifest_corpus_version,
    validate_cases_against_manifest,
    validate_retrieved_doc_ids_known,
)

RESULTS_DIR = Path(__file__).resolve().parent / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


class DummyLocalBackend:
    def search(self, query: str, top_k: int = 8) -> list[dict[str, Any]]:
        return [
            {
                "doc_id": "CANON.md",
                "chunk_id": "stub-1",
                "text": f"Stub local retrieval result for query: {query}",
                "score": 0.1,
                "metadata": {"stub": True},
            }
        ][:top_k]


def load_local_backend(spec: str | None):
    if not spec:
        return DummyLocalBackend()

    if ":" not in spec:
        raise ValueError(
            "Local backend spec must look like 'package.module:ClassName'"
        )

    module_name, class_name = spec.split(":", 1)
    module = import_module(module_name)
    cls = getattr(module, class_name)
    return cls()


def load_json(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_cases(path: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def strategic_prompt(case: dict[str, Any], context_pack: str) -> str:
    constraints = "\n".join(f"- {x}" for x in case["context"]["constraints"])
    already_tried = "\n".join(f"- {x}" for x in case["context"]["already_tried"])

    return f"""You are the strategist for this project.

## Objective
{case["question"]}

## Success Metric
Return the highest-leverage answer grounded in the retrieved evidence.

## Current State Snapshot
{json.dumps(case["context"], indent=2)}

## Constraints
{constraints}

## What's Already Been Tried
{already_tried}

## Decision Question
{case["decision_question"]}

## Retrieved Evidence
{context_pack}

## Required Output Schema
Return JSON only with this schema:
{{
  "answer": "string",
  "key_evidence_ids": ["string"],
  "assumptions": ["string"],
  "confidence": 0.0,
  "next_action": "string",
  "kill_criteria": ["string"],
  "escalation_trigger": "string"
}}
""".strip()


def answer_with_context(
    client: OpenAI,
    model: str,
    case: dict[str, Any],
    context_pack: str,
) -> tuple[str, dict[str, Any]]:
    prompt = strategic_prompt(case, context_pack)

    started = time.time()
    resp = client.responses.create(
        model=model,
        input=prompt,
        text={"format": {"type": "json_object"}},
        store=False,
    )
    latency = time.time() - started

    text = getattr(resp, "output_text", "") or ""
    usage = getattr(resp, "usage", None)

    usage_dict = {}
    if usage:
        usage_dict = {
            "input_tokens": getattr(usage, "input_tokens", None),
            "output_tokens": getattr(usage, "output_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
        }

    return text, {
        "latency_sec": round(latency, 3),
        "usage": usage_dict,
    }


def run_arm(
    *,
    arm: str,
    case: dict[str, Any],
    client: OpenAI,
    model: str,
    vector_store_id: str | None,
    manifest: dict[str, Any],
    manifest_index: dict[str, Any],
    local_backend_spec: str | None,
) -> dict[str, Any]:
    if arm == "local":
        retriever = LocalRetriever(load_local_backend(local_backend_spec))
    elif arm == "hosted":
        if not vector_store_id:
            raise RuntimeError("OPENAI_VECTOR_STORE_ID is required for hosted arm.")
        retriever = OpenAIFileSearchRetriever(
            client=client,
            vector_store_id=vector_store_id,
            model=model,
            manifest_index=manifest_index,
        )
    else:
        raise ValueError(f"Unknown arm: {arm}")

    retrieved = retriever.retrieve(case["retrieval_query"], k=case.get("top_k", 8))
    retrieved_doc_ids = [c.doc_id for c in retrieved]
    validate_retrieved_doc_ids_known(retrieved_doc_ids, manifest)

    context_pack = build_context_pack(retrieved)
    answer_text, llm_meta = answer_with_context(client, model, case, context_pack)

    answer_obj = try_parse_json(answer_text)

    retrieval_grade = deterministic_retrieval_grade(
        retrieved_doc_ids=retrieved_doc_ids,
        expected_supporting_docs=case["expected_supporting_docs"],
    )
    schema = schema_grade(answer_obj)
    citations = evidence_citation_grade(answer_obj, retrieved_doc_ids)
    fact_grade = gold_fact_coverage(
        answer_text=answer_obj.get("answer", answer_text),
        gold_facts=case["gold_facts"],
    )
    aggregate = aggregate_case_score(
        support_recall=retrieval_grade["support_recall"],
        schema_ok=schema["schema_ok"],
        gold_fact_coverage=fact_grade["gold_fact_coverage"],
        citations_ok=citations["citations_ok"],
    )

    return {
        "case_id": case["id"],
        "arm": arm,
        "question": case["question"],
        "retrieved": chunks_to_jsonable(retrieved),
        "answer_raw": answer_text,
        "answer_obj": answer_obj,
        "retrieval_grade": retrieval_grade,
        "schema_grade": schema,
        "citation_grade": citations,
        "fact_grade": fact_grade,
        "aggregate": aggregate,
        "llm_meta": llm_meta,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", required=True)
    parser.add_argument(
        "--manifest",
        default=str(RESULTS_DIR / "export_manifest.json"),
        help="Export manifest produced by exporters.py",
    )
    parser.add_argument(
        "--arm",
        choices=["local", "hosted", "both"],
        default="both",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("KNOWLEDGE_PLANE_MODEL", "gpt-5.4"),
    )
    parser.add_argument(
        "--local-backend",
        default=os.environ.get("KNOWLEDGE_PLANE_LOCAL_BACKEND"),
        help="Import path like 'aos.retrieve:RetrieverBackend'",
    )
    args = parser.parse_args()

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    vector_store_id = os.environ.get("OPENAI_VECTOR_STORE_ID")

    manifest = load_json(args.manifest)
    manifest_index = build_manifest_index(manifest)

    cases = load_cases(args.cases)
    validate_cases_against_manifest(cases, manifest)

    arms = ["local", "hosted"] if args.arm == "both" else [args.arm]

    rows: list[dict[str, Any]] = []
    for case in cases:
        for arm in arms:
            print(f"Running case={case['id']} arm={arm}", file=sys.stderr)
            row = run_arm(
                arm=arm,
                case=case,
                client=client,
                model=args.model,
                vector_store_id=vector_store_id,
                manifest=manifest,
                manifest_index=manifest_index,
                local_backend_spec=args.local_backend,
            )
            rows.append(row)

    payload = {
        "model": args.model,
        "case_count": len(cases),
        "run_count": len(rows),
        "corpus_version": manifest.get("corpus_version") or manifest_corpus_version(manifest),
        "vector_store_id": manifest.get("vector_store_id"),
        "summary": summarize_results(rows),
        "results": rows,
    }

    out_path = RESULTS_DIR / "latest.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(json.dumps(payload["summary"], indent=2))
    print(f"\nWrote results to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

---

## 7) Small `cases.jsonl` rule change

Every `expected_supporting_docs` entry must be a canonical repo-relative `doc_id` that exists in the manifest.

Good:

```json
{"expected_supporting_docs":["CANON.md","README.md","ai-lab/o1_next_question_mvp.md"]}
```

Bad:

```json
{"expected_supporting_docs":["canon","README","o1 prompt file"]}
```

---

## 8) Run sequence

```bash
cd ai-lab

# Export the exact eval corpus
uv run evals/knowledge_plane/exporters.py \
  --include-code \
  --include-references

# Use the emitted vector store
export OPENAI_VECTOR_STORE_ID=vs_...

# Point local arm at your real retriever
export KNOWLEDGE_PLANE_LOCAL_BACKEND='aos.retrieve:RetrieverBackend'

# Run the matched eval
uv run evals/knowledge_plane/runner.py \
  --cases evals/knowledge_plane/cases.jsonl \
  --manifest evals/knowledge_plane/results/export_manifest.json \
  --arm both \
  --model gpt-5.4
```

---

## What this leaves you with

At that point, yes: you have a **complete, detailed Phase-1 harness** for the knowledge-plane decision.

Not “complete forever,” but complete enough to answer the architectural question cleanly:

* same corpus,
* same canonical IDs,
* same downstream strategist prompt,
* same model,
* only the retrieval plane changes,
* and the grader now rejects fake grounding. ([GitHub][1])

The best next step is to wire your actual local backend into `KNOWLEDGE_PLANE_LOCAL_BACKEND` and then tighten the `cases.jsonl` set so every expected doc exactly matches the export manifest.

[1]: https://raw.githubusercontent.com/mdc159/01/master/CANON.md "raw.githubusercontent.com"
[2]: https://developers.openai.com/api/docs/guides/retrieval/ "Retrieval | OpenAI API"

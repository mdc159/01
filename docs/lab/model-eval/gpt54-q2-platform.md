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

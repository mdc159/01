# Improve retrieval recall by deduplicating results per doc_id

## TL;DR
> **Summary**: Execute task graph for: Improve retrieval recall by deduplicating results per doc_id
> **Deliverables**: 1 tasks
> **Parallel**: YES - all independent
> **Critical Path**: dedup-retrieval

## Context
### Original Request
Goal: Improve retrieval recall by deduplicating results per doc_id

### Constraints
- Only modify local_backend.py
- Only modify the search() method of RepoSearchBackend
- Keep the function signature unchanged
- The deduplication should keep the highest-scoring chunk per doc_id

## Tasks

> EVERY task MUST have: Agent Profile + Parallelization + Acceptance Criteria.

- [ ] 1. Add doc-level deduplication to RepoSearchBackend.search()

  **What to do**: In ai-lab/evals/knowledge_plane/local_backend.py, the search() method returns raw top-k chunks ranked by cosine similarity. This means one document can dominate results with multiple chunks (e.g. architecture.md appearing 4 times), pushing other relevant documents out of the top-k. Fix: after scoring all chunks, deduplicate by doc_id — keep only the highest-scoring chunk per unique doc_id, then return top_k from the deduplicated list. This ensures diverse document coverage in the results.
  **Must NOT do**: Do not modify files outside the task scope.

  **Recommended Agent Profile**:
  - Category: `ultrabrain`

  **Parallelization**: Can Parallel: YES | Wave 1

  **Acceptance Criteria**:
  - [ ] Task completes without errors

  **Commit**: YES | Message: `feat(lab): add doc-level deduplication to reposearchbackend.search()`

## Final Verification Wave

- [ ] F1. Plan Compliance Audit — oracle
- [ ] F2. Code Quality Review — unspecified-high

## Commit Strategy
One commit per task. Conventional commit format.

## Success Criteria
All tasks pass acceptance criteria. Eval harness score ≥ baseline (0.562).
# Improve gold fact coverage by instructing model to use exact phrases from evidence

## TL;DR
> **Summary**: Execute task graph for: Improve gold fact coverage by instructing model to use exact phrases from evidence
> **Deliverables**: 1 tasks
> **Parallel**: YES - all independent
> **Critical Path**: fix-fact-prompt

## Context
### Original Request
Goal: Improve gold fact coverage by instructing model to use exact phrases from evidence

### Constraints
- Only modify runner.py — do not change graders.py or metrics.py
- Only modify the strategic_prompt() function
- Keep the existing schema and instructions intact — add to them

## Tasks

> EVERY task MUST have: Agent Profile + Parallelization + Acceptance Criteria.

- [ ] 1. Update strategic_prompt to instruct verbatim evidence quoting

  **What to do**: In ai-lab/evals/knowledge_plane/runner.py, the strategic_prompt() function does not instruct the model to use exact phrases from the retrieved evidence. The gold_fact_coverage grader uses substring matching, so the model must include key phrases verbatim. Add an instruction to the prompt telling the model: "In your answer, quote key phrases and terminology exactly as they appear in the retrieved evidence. Do not paraphrase technical terms, principles, or named concepts — use the exact wording from the source." Place this instruction in the Objective or Required Output Schema section.
  **Must NOT do**: Do not modify files outside the task scope.

  **Recommended Agent Profile**:
  - Category: `unspecified-low`

  **Parallelization**: Can Parallel: YES | Wave 1

  **Acceptance Criteria**:
  - [ ] Task completes without errors

  **Commit**: YES | Message: `feat(lab): update strategic_prompt to instruct verbatim evidence quoting`

## Final Verification Wave

- [ ] F1. Plan Compliance Audit — oracle
- [ ] F2. Code Quality Review — unspecified-high

## Commit Strategy
One commit per task. Conventional commit format.

## Success Criteria
All tasks pass acceptance criteria. Eval harness score ≥ baseline (0.562).
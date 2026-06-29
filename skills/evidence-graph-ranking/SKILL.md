---
name: evidence-graph-ranking
description: Build the causal evidence graph, merge duplicate symptoms and shared origins, score supported leaves, and generate final actionable RCA leaves. Use after leaf evaluation to select trustworthy primary and secondary candidates.
---

# Evidence Graph and Ranking

## Purpose

Transform a flat set of leaf classifications into non-duplicated causal chains with transparent scoring and verification plans.

## Trigger

Always, after `leaf-evaluator`. Critical.

## Required input

- All evaluated leaves.
- Skill findings, dependency graph, interference edges, validation, and paired metrics.
- Ownership/action templates and ranking policy.

## Workflow

1. Filter normal final candidates to DIRECT or CONTRIBUTING DUT regressions; keep correlation candidates only when explicitly requested.
2. Map symptoms to dependency/interference evidence and mechanism-specific metrics.
3. Merge waiter/owner, parent/child, and shared-origin leaves into causal groups.
4. Compute score from phase relevance, critical-path evidence, delta, mechanism/origin evidence, validation, and uniqueness.
5. Calculate local/exclusive/nested deltas and preserve overlap groups.
6. Generate six-part final leaves: Symptom, Location, Mechanism, Origin, Ownership, and Action.
7. Attach rejected alternatives and a controlled verification plan.
8. Select primary leaf and retain secondary/local DUT-better leaves when configured.

## Algorithm contract

Ranking favors mechanism-specific direct evidence over umbrella durations. Shared intervals and origins are deduplicated before final selection.

## Main outputs

- `state.final_leaves`
- `final_leaf`
- `state.evidence_graph`
- score breakdown
- rejected alternatives
- verification plans

## Leaf and workflow integration

The report generator serializes these final artifacts. Controlled experiments later promote `FINAL_CANDIDATE` to `CONFIRMED` outside this single-run workflow.

## Guardrails

- Do not choose `CORRELATION_ONLY` as primary RCA by default.
- Do not double-count waiter, owner, parent, and nested metric intervals.
- Generic phase/umbrella leaves cannot replace a stronger mechanism-specific leaf.
- Unresolved mechanism/origin must remain a supported hypothesis, not a confirmed cause.
- Final contribution totals must disclose overlap and non-additivity.

## Failure handling

- Allow an empty final-leaf set when evidence is insufficient; do not fabricate a root cause.
- Preserve ranked supported/correlation candidates for troubleshooting.

## Known limitation

RCA confirmation requires controlled fix/retest and preferably multiple iterations.

## Implementation

- Manifest: `skills/evidence-graph-ranking/skill.yaml`
- Deterministic implementation: `skills/evidence-graph-ranking/skill.py`
- Entry contract: `run(state, config)`
- Shared state model: `app_entry_rca.core.models.AnalysisState`
- Missing-evidence policy: `NOT_OBSERVABLE`

## Tests

Covered by skill-contract, taxonomy-integrity, guardrail, output-contract, and DUT/REF integration tests under `tests/`.

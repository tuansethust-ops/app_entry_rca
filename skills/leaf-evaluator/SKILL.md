---
name: leaf-evaluator
description: Evaluate all 151 P1-P8 FTA leaves against DUT-versus-REF metrics using 41 declarative automatic rules. Use after diagnostic skills to classify leaf status, causality, millisecond deltas, observability, and overlap semantics.
---

# Leaf Evaluator

## Purpose

Evaluate every predefined FTA leaf consistently without turning missing evidence or correlation into a false root cause.

## Trigger

Always, after phase localization and all selected diagnostic skills. Critical.

## Required input

- All prior skill findings and paired metrics.
- `taxonomy/leaf_registry.json` with 151 leaf definitions.
- `taxonomy/leaf_rules.yaml` with 70 automatic rules.
- `taxonomy/thresholds.yaml`, capabilities, validation, and launch type.

## Workflow

1. Load the full registry and rule contracts.
2. For each leaf, check applicability to launch type and scenario.
3. Check required capabilities and metric availability.
4. Evaluate paired DUT/REF delta, threshold, one-sided evidence, and contradiction conditions.
5. Apply causality prerequisites and fallback causality caps.
6. Classify status: DUT_REGRESSION, DUT_BETTER, EQUIVALENT, DUT_ONLY, REF_ONLY, NOT_APPLICABLE, NOT_OBSERVABLE, or INSUFFICIENT_EVIDENCE.
7. Compute `local_delta_ms`, `exclusive_contribution_ms`, nested deltas, overlap group, and additive flag.
8. Apply post-filters for GC liveness, correlation-only evidence, and overlap guardrails.

## Algorithm contract

Declarative rules own automatic classification. Unmapped taxonomy leaves remain `NOT_OBSERVABLE` by design and must list missing evidence.

## Main outputs

- `state.leaves` / `all_leaf_nodes` for all 151 leaves
- per-leaf status, confidence, causality, metric and evidence
- `local_delta_ms`
- `exclusive_contribution_ms`
- `nested_deltas_ms`
- `overlap_group`
- `additive`

## Leaf and workflow integration

`evidence-graph-ranking` consumes evaluated leaves, deduplicates shared symptoms/origins, and selects final candidates. This skill does not confirm RCA.

## Guardrails

- `NOT_OBSERVABLE` means missing evidence, not equality.
- Do not sum overlapping or nested deltas.
- GC/kswapd total CPU or temporal overlap alone remains correlation-only.
- D-state alone cannot satisfy a storage-causality rule.
- Generic umbrella duration leaves must not outrank mechanism-specific direct leaves.

## Failure handling

- Fail on malformed registry/rule schema or duplicate leaf IDs.
- Leave a leaf unobservable when required metrics are not emitted.
- Record fallback metric use and cap causality/confidence.

## Known limitation

Only 70 leaves currently have automatic rules; the remaining taxonomy is preserved for observability/instrumentation expansion.

## Implementation

- Manifest: `skills/leaf-evaluator/skill.yaml`
- Deterministic implementation: `skills/leaf-evaluator/skill.py`
- Entry contract: `run(state, config)`
- Shared state model: `app_entry_rca.core.models.AnalysisState`
- Missing-evidence policy: `NOT_OBSERVABLE`

## Tests

Covered by skill-contract, taxonomy-integrity, guardrail, output-contract, and DUT/REF integration tests under `tests/`.

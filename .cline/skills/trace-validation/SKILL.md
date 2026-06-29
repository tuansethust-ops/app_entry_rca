---
name: trace-validation
description: Validate DUT-versus-REF comparability, launch identity, endpoint semantics, marker coverage, and trace capability symmetry. Use before interpreting phase or leaf deltas and whenever results look inconsistent.
---

# Trace Validation

## Purpose

Prevent invalid DUT/REF comparisons from producing convincing but incorrect root-cause leaves.

## Trigger

Always, after `launch-context`. Critical; strict validation can stop the workflow.

## Required input

- DUT/REF launch contexts.
- Trace capability matrices and backend provenance.
- Optional external metadata such as thermal state, compiler artifacts, package state, and trace environment.

## Workflow

1. Check target package, selected launch instance, and actual launch type.
2. Check endpoint compatibility: input, first-frame metric/proxy, and system_server activityIdle server end.
3. Compare parser backend and capability symmetry.
4. Detect trace truncation, missing scheduler data, missing markers, or suspicious duration.
5. Score comparability and classify as `COMPARABLE`, `PARTIALLY_COMPARABLE`, or `NOT_COMPARABLE`.
6. Publish missing evidence and the leaves/skills affected by each gap.

## Algorithm contract

Validation is a gate, not a performance analyzer. It must separate scenario mismatch from DUT regression.

## Main outputs

- `state.validation`
- `comparability_score`
- `marker_matrix`
- capability asymmetry list
- validation warnings/reasons

## Leaf and workflow integration

Leaf evaluation and candidate ranking cap confidence according to validation status. `NOT_COMPARABLE` must prevent a normal primary RCA in strict mode.

## Guardrails

- Different actual launch types are not directly comparable.
- Different first-frame endpoints must be reported, not silently aligned.
- Missing capability means unknown, not equal.
- Trace parser/backend differences must be included in the report.

## Failure handling

- In non-strict mode, continue with `PARTIALLY_COMPARABLE` and explicit limitations.
- In strict mode, stop on target, launch-type, or endpoint mismatch.

## Known limitation

Dataset, compiler filter, thermal state, cache state, and package state may require dumpstate or metadata snapshots outside the trace. App/build version metadata is diagnostic only and is not a comparability gate.

## Implementation

- Manifest: `skills/trace-validation/skill.yaml`
- Deterministic implementation: `skills/trace-validation/skill.py`
- Entry contract: `run(state, config)`
- Shared state model: `app_entry_rca.core.models.AnalysisState`
- Missing-evidence policy: `NOT_OBSERVABLE`

## Tests

Covered by skill-contract, taxonomy-integrity, guardrail, output-contract, and DUT/REF integration tests under `tests/`.

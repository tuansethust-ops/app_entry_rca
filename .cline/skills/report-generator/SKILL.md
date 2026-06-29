---
name: report-generator
description: Write stable JSON, CSV, and Markdown outputs for the app_entry_rca workflow and validate output contracts. Use as the final workflow skill or when regenerating reports from an existing analysis state.
---

# Report Generator

## Purpose

Produce machine-readable and human-readable artifacts without changing analysis semantics.

## Trigger

Always, after evidence graph and ranking. Critical.

## Required input

- Complete `AnalysisState` including validation, contexts, metrics, leaves, findings, graphs, and final leaves.
- Output directory and schema files.

## Workflow

1. Validate required state objects and output schemas.
2. Write validation, context, phase, routing, observability, skill-run, finding, and raw-metric artifacts.
3. Write all 151 leaves to JSON and CSV.
4. Write `ms_diff_summary.json` with local/nested deltas and overlap notes.
5. Write final leaves, primary final leaf, evidence graph, taxonomy changes, and automation coverage.
6. Render `report.md` with first-frame and activityIdle endpoints, P1-P8 comparison, candidate ranking, guardrails, and limitations.
7. Record workflow/skill/taxonomy versions, trace hashes, backend, command, and generation timestamp.

## Algorithm contract

Serialization is deterministic for the same input, workflow version, and taxonomy/rule version.

## Main outputs

- `analysis_summary.json`
- `validation.json`
- `launch_context.json`
- `phase_comparison.json`
- `routing.json`
- `observability.json`
- `skill_runs.json`
- `skill_findings.json`
- `raw_metrics.json`
- `ms_diff_summary.json`
- `all_leaf_nodes.json/.csv`
- `final_leaves.json`
- `final_leaf.json`
- `evidence_graph.json`
- `automation_coverage.json`
- `report.md`

## Leaf and workflow integration

These are the public workflow artifacts consumed by Cline, users, dashboards, and future RAG/verification stages.

## Guardrails

- Do not alter causality/status while formatting.
- Do not omit `NOT_OBSERVABLE` leaves from the full registry output.
- Always state that overlapping deltas are non-additive.
- Always distinguish first-frame endpoint from system_server activityIdle completion.
- Preserve structured evidence as objects rather than Python-string serialization.

## Failure handling

- Fail if core output contracts cannot be serialized.
- Write an error/partial manifest when noncritical optional artifacts fail.

## Known limitation

Schema validation guarantees structure, not scientific correctness of the source trace markers.

## Implementation

- Manifest: `skills/report-generator/skill.yaml`
- Deterministic implementation: `skills/report-generator/skill.py`
- Entry contract: `run(state, config)`
- Shared state model: `app_entry_rca.core.models.AnalysisState`
- Missing-evidence policy: `NOT_OBSERVABLE`

## Tests

Covered by skill-contract, taxonomy-integrity, guardrail, output-contract, and DUT/REF integration tests under `tests/`.

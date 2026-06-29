---
name: app-entry-rca
description: Run the complete evidence-driven DUT-versus-REF Android app-entry RCA workflow using the canonical P1-P7 FTA timeline, P8 cross-cutting evidence, and routed diagnostic skills. Use when the user supplies DUT and REF Perfetto/atrace traces and wants phase comparison, leaf classifications, final root-cause candidates, millisecond deltas, or a deep dive into GC, reclaim, Binder, I/O, ART, rendering, scheduling, or activityIdle.
---

# App Entry RCA

## Purpose

Execute one deterministic top-level workflow that coordinates reusable diagnostic skills, evaluates the corrected FTA leaf taxonomy, and generates evidence-backed RCA candidates for Android app-entry regressions.

## Trigger

Use when the task compares DUT and REF Android app-entry traces, asks to run `app_entry_rca`, or asks to review an existing `app_entry_rca` output directory.

## Required input

- DUT trace path.
- REF trace path.
- Optional target package and zero-based launch index.
- Optional `trace_processor_shell` path for the preferred Perfetto SQL backend. If omitted, use `tools/perfetto/trace_processor_shell(.exe)` when present.
- Optional output directory and strict-validation setting.

## Workflow

1. Read `.clinerules/workflows/app_entry_rca.md` and resolve repository root and trace paths. Accept `/app_entry_rca <DUT_TRACE_PATH> <REF_TRACE_PATH>` as the positional Cline form.
2. Run `python scripts/doctor.py --dut "<DUT>" --ref "<REF>"` when the environment is unknown.
3. Execute the deterministic CLI or Windows launcher.
4. Let `workflows/app_entry_rca/workflow.yaml` invoke always-on skills and route diagnostic skills from candidate activation and observability.
5. Verify generated artifacts before interpreting results.
6. Read validation, launch context, phase comparison, millisecond summary, final leaf, all final leaves, and evidence graph in that order.
7. Present first-frame and system_server activityIdle endpoints separately, including overlap and non-additivity notes.

## Algorithm contract

This is an orchestrator skill, not an independent analyzer. It must delegate measurement and classification to the deterministic workflow and its internal skills:

- `trace-ingestion`
- `launch-context`
- `trace-validation`
- `phase-localizer`
- `running-analysis`
- `runnable-analysis`
- `wait-dependency-analysis`
- `block-io-analysis`
- `memory-gc-analysis`
- `art-runtime-analysis`
- `render-frame-analysis`
- `system-interference-analysis`
- `leaf-evaluator`
- `evidence-graph-ranking`
- `report-generator`

The orchestrator must not invent missing trace evidence, manually override leaf causality, or sum overlapping durations. It should report RCA candidates unless experiment or fix verification is provided.

## Main outputs

- Validation, launch context, phase comparison, routing, observability, skill runs, findings, and raw metrics.
- Corrected FTA leaves in JSON/CSV.
- Millisecond-difference summary with overlap groups.
- Ranked final leaves, primary final leaf, evidence graph, verification plans, and Markdown report.
- Raw phase intervals, raw marker slices, critical-path analysis, and generated diagrams when present.

## Leaf and workflow integration

The skill uses the canonical app-entry model:

- P1-P7 are timeline phases that identify where regression occurs.
- P8 is cross-cutting evidence that explains why a P1-P7 node or leaf regressed.
- Cold entry uses P1 Touch Duration through P7 activityIdle.
- Warm entry uses P1 Touch Duration through P6 activityIdle.
- `leaf-evaluator` classifies leaves after routed evidence skills complete.
- `evidence-graph-ranking` suppresses duplicate downstream symptoms and ranks actionable RCA candidates.

## Guardrails

- Do not manually run every routed analyzer; let the workflow router select them.
- `NOT_OBSERVABLE` means unknown, not equal.
- Do not sum overlapping parent, child, nested, or cross-phase deltas.
- GC/kswapd overlap alone is correlation-only.
- D-state alone is not storage causality.
- P2 may overlap P3; P8 is cross-cutting and not a sequential launch phase.
- First frame and system_server activityIdle completion are separate endpoints.
- Only DIRECT or CONTRIBUTING leaves may become the normal primary RCA.
- App/build version metadata is diagnostic only, not a comparability gate.

## Failure handling

- Stop when trace parsing or critical workflow skills fail.
- Respect `workflows/app_entry_rca/workflow.yaml` `error_policy.fail_fast: true` for critical failures.
- If validation is partial, continue only with explicit confidence and observability limitations.
- An empty `final_leaf.json` means insufficient causal evidence, not proof that DUT has no regression.

## Known limitation

- Trace schemas and available Perfetto data sources vary by platform, build, and trace config.
- Some evidence chains, such as Binder server attribution, lock ownership, GPU fence causes, and file/page mapping, may be partially observable only.
- Without repeated runs or fix/experiment verification, the output should be treated as RCA candidate rather than confirmed RCA.
- External metadata such as thermal state, compiler filter, package/cache state, and automation timing may be needed to explain some regressions.

## Implementation

- Cline workflow: `.clinerules/workflows/app_entry_rca.md`
- Canonical workflow: `workflows/app_entry_rca/workflow.yaml`
- CLI: `python -m app_entry_rca.cli ...`
- Cross-platform runner: `python scripts/run_app_entry_rca.py ...`
- Windows launcher: `windows/run.ps1` or `run_app_entry_rca.bat`

## Tests

Run `python -m pytest -q`. The suite validates Cline discovery, skill frontmatter, workflow contracts, taxonomy, P7 semantics, evidence guardrails, output contracts, and DUT/REF integration.


## CPU Core/Frequency Skill

- `cpu-core-frequency-analysis` enriches P1-P7 node/leaf intervals with CPU core, migration, cluster, and CPU frequency evidence.
- Output artifact: `cpu_core_frequency.json`.
- Missing CPU-frequency counters are treated as `NOT_OBSERVABLE`, not equal.


## Optional positional form

Use `/app_entry_rca <DUT_TRACE_PATH> <REF_TRACE_PATH>` as shorthand for the deterministic CLI positional form. The first path is DUT and the second path is REF.

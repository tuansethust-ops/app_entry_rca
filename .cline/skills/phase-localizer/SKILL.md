---
name: phase-localizer
description: Build P1-P7 timing segments, model P8 as cross-cutting context, compare DUT and REF, and activate candidate groups for routed analysis. Use after validation to identify where a launch difference occurs.
---

# Phase Localizer

## Purpose

Convert launch markers into phase/candidate context without treating phase duration itself as a root cause.

## Trigger

Always, after `trace-validation`. Critical because it drives analyzer routing.

## Required input

- Validated DUT/REF launch contexts.
- `taxonomy/phases.yaml`, `candidates.yaml`, `group_activation.yaml`, and thresholds.
- Normalized trace/slice/thread-state data.

## Workflow

1. Construct P1 through P7 intervals using canonical markers.
2. Represent P2 cold-launch orchestration as functional segments/union that may overlap P3.
3. Treat P4 as callback/control-flow context and P5 as nested resource/data work domain.
4. Set P7 from first-frame completion to the end of system_server `activityIdle::server`.
5. Compare paired phase/segment metrics and activate candidate groups that cross configured thresholds.
6. Select routed skills using candidate-to-analyzer mapping and trace observability.

## Algorithm contract

Use wall-clock union for overlapping segments. Never sum P2/P3 or P4/P5 as independent sequential contributions.

## Main outputs

- `phase_comparison`
- `active_phases`
- `activated_groups`
- `selected_skills`
- `routing_reasons`
- P7 pre-server and server-handler metrics

## Leaf and workflow integration

The router executes only selected diagnostic skills. The leaf evaluator later converts candidate metrics into all 151 taxonomy leaf statuses.

## Guardrails

- A phase delta is a localization signal, not a final cause.
- P8 is cross-cutting and must not be added to total launch time.
- P7 total tail is an umbrella metric; it does not prove MessageQueue starvation.
- Do not add overlapping phase or nested domain deltas.

## Failure handling

- Keep a phase `NOT_OBSERVABLE` if required boundaries are missing.
- Do not activate candidates from fabricated or fallback-zero durations.

## Known limitation

Accurate first-presented-frame localization requires FrameTimeline/SurfaceFlinger data; `finishDrawing` is only a proxy.

## Implementation

- Manifest: `skills/phase-localizer/skill.yaml`
- Deterministic implementation: `skills/phase-localizer/skill.py`
- Entry contract: `run(state, config)`
- Shared state model: `app_entry_rca.core.models.AnalysisState`
- Missing-evidence policy: `NOT_OBSERVABLE`

## Tests

Covered by skill-contract, taxonomy-integrity, guardrail, output-contract, and DUT/REF integration tests under `tests/`.

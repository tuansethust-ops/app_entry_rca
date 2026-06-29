---
name: launch-context
description: Detect the target package, launch candidate, process and thread identities, actual launch type, and canonical app-entry markers for DUT and REF. Use after trace ingestion or when launch selection and P7 activityIdle boundaries are uncertain.
---

# Launch Context

## Purpose

Create one coherent launch context per trace so every later metric is measured against the same target, launch instance, process identities, and endpoints.

## Trigger

Always, after `trace-ingestion`. Critical; failure to identify a coherent launch prevents phase analysis.

## Required input

- Normalized DUT/REF traces.
- Optional target package and zero-based launch index.
- Marker aliases and process/thread metadata.

## Workflow

1. Find launch candidates and resolve the requested or auto-detected package.
2. Resolve launcher, system_server, target process, app main thread, RenderThread, Zygote, and relevant provider/service identities.
3. Classify actual launch type: cold, prestarted-cold, warm, or hot using process evidence rather than framework labels alone.
4. Resolve input/startActivity/process/bind/lifecycle/traversal/finishDrawing or FrameTimeline markers.
5. Resolve the exact `IActivityClientController::activityIdle::server` slice in system_server; keep generic `activityIdle` only as reduced-confidence fallback.
6. Store marker timestamps, slice ownership, confidence, and ambiguity warnings.

## Algorithm contract

Marker selection must be deterministic and launch-index scoped. The same semantic marker must be selected independently for DUT and REF, then checked by validation.

## Main outputs

- `state.contexts[DUT/REF]`
- `launch_type`
- `target_pid`/main TID
- `launcher_pid`
- `system_pid`
- `render_tid`
- canonical P1-P7 markers including activityIdle server start/end

## Leaf and workflow integration

The phase localizer uses these markers to define P1-P7. P7 ends at the end of the system_server activityIdle server slice.

## Guardrails

- Framework warm/cold labels must not override process-start evidence.
- Do not mix markers belonging to different launch instances or activities.
- Do not treat `activityIdle` as equivalent to first frame.
- If the exact server AIDL slice is unavailable, mark the fallback and lower confidence.

## Failure handling

- Ask for a package or launch index only when multiple candidates cannot be disambiguated.
- Mark individual endpoints unobservable rather than fabricating timestamps.

## Known limitation

First meaningful frame generally requires app-specific markers; generic traces may only expose first presented frame or `finishDrawing` proxy.

## Implementation

- Manifest: `skills/launch-context/skill.yaml`
- Deterministic implementation: `skills/launch-context/skill.py`
- Entry contract: `run(state, config)`
- Shared state model: `app_entry_rca.core.models.AnalysisState`
- Missing-evidence policy: `NOT_OBSERVABLE`

## Tests

Covered by skill-contract, taxonomy-integrity, guardrail, output-contract, and DUT/REF integration tests under `tests/`.

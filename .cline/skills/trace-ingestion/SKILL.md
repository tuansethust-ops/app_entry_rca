---
name: trace-ingestion
description: Normalize DUT and REF Perfetto, atrace, or systrace inputs into the app_entry_rca internal trace model and detect available capabilities. Use when the app-entry workflow starts, when a trace backend fails, or when observability must be debugged.
---

# Trace Ingestion

## Purpose

Load both trace files through the preferred Perfetto SQL backend or the systrace fallback, normalize events/slices/scheduler intervals, and publish trace capabilities without inferring root cause.

## Trigger

Always. This is the first workflow skill and is critical; failure stops the workflow.

## Required input

- DUT and REF trace paths from `state.inputs`.
- Optional `--backend`, `--trace-processor`, and `--traceconv` settings.
- `workflow.yaml` step configuration and repository assets.

## Workflow

1. Validate that DUT and REF paths exist and are readable.
2. Select backend: Perfetto SQL when available; otherwise use traceconv/systrace fallback.
3. Parse and normalize slices, scheduler intervals, process/thread metadata, counters, and raw events.
4. Detect capabilities such as scheduler state, Binder, FrameTimeline, GPU, file/page, block I/O, GC, reclaim, and counters.
5. Record backend name, trace hash, duration, parser warnings, and provenance.
6. Emit `NOT_OBSERVABLE` capability flags instead of replacing missing data with zero.

## Algorithm contract

This skill only normalizes evidence. It must not classify a leaf, compare performance, or promote a causal explanation.

## Main outputs

- `state.traces[DUT/REF]`
- `state.capabilities[DUT/REF]`
- `event_count`
- `slice_count`
- `sched_interval_count`
- `trace_duration_s`
- trace SHA-256 and backend provenance

## Leaf and workflow integration

All later skills consume this normalized trace model. `trace-validation` uses the capability matrix to determine which FTA leaves are observable.

## Guardrails

- Do not claim a feature is absent merely because the fallback parser cannot observe it.
- Do not convert missing markers/events into a numeric zero.
- Do not silently fall back from Perfetto SQL to a lossy backend; record the fallback and lost capabilities.
- DUT and REF may use different backends only if validation reports the comparability impact.

## Failure handling

- Stop when neither trace can be parsed.
- Report backend errors and the exact missing executable/path.
- Keep partial capability information only when both traces remain analyzable.

## Known limitation

Systrace conversion can lose FrameTimeline, Binder transaction IDs, counters, file attribution, and structured thread-state detail.

## Implementation

- Manifest: `skills/trace-ingestion/skill.yaml`
- Deterministic implementation: `skills/trace-ingestion/skill.py`
- Entry contract: `run(state, config)`
- Shared state model: `app_entry_rca.core.models.AnalysisState`
- Missing-evidence policy: `NOT_OBSERVABLE`

## Tests

Covered by skill-contract, taxonomy-integrity, guardrail, output-contract, and DUT/REF integration tests under `tests/`.

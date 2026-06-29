---
name: running-analysis
description: Measure CPU Running time for critical launch threads and candidate-owned intervals, separating extra CPU work from waiting. Use when phase localization activates CPU-execution candidates.
---

# Running Analysis

## Purpose

Determine whether DUT spends more on-CPU time in a critical path and expose nested state decomposition for later mechanism analysis.

## Trigger

Routed. Run only when selected by candidate activation and scheduler evidence is observable.

## Required input

- Launch context and candidate intervals.
- Scheduler intervals/sched_slice data.
- Critical process/thread identities from prior skills.

## Workflow

1. Intersect candidate intervals with scheduler Running intervals for the owning thread.
2. Compute per-marker and per-thread Running time for DUT and REF.
3. Publish D-state and Sleeping decomposition as nested evidence where the code provides it.
4. Identify large running slices/functions without assuming they are causal.
5. Emit structured findings for leaf evaluation.

## Algorithm contract

CPU execution metrics are inclusive unless explicitly marked exclusive. Parent and child Running deltas belong to the same overlap group.

## Main outputs

- `critical_thread_state_ms`
- `*_running_ms`
- `*_sleeping_ms`
- `*_d_ms`
- top CPU-owned candidate intervals

## Leaf and workflow integration

Feeds Running-related leaves across P1-P7 and supports P8 interference analysis. It does not decide whether extra work is justified.

## Guardrails

- Running time is not the same as wall-clock duration.
- Do not add parent and nested Running metrics.
- Same work at lower frequency and extra work require different origin evidence.
- Without scheduler data, leave Running metrics unobservable.

## Failure handling

- Emit `NOT_OBSERVABLE` when scheduler intervals or thread identity are missing.
- Record partial coverage when only a subset of the candidate interval is traced.

## Known limitation

Function-level attribution depends on slices or profiling markers; scheduler data alone only shows CPU execution time.

## Implementation

- Manifest: `skills/running-analysis/skill.yaml`
- Deterministic implementation: `skills/running-analysis/skill.py`
- Entry contract: `run(state, config)`
- Shared state model: `app_entry_rca.core.models.AnalysisState`
- Missing-evidence policy: `NOT_OBSERVABLE`

## Tests

Covered by skill-contract, taxonomy-integrity, guardrail, output-contract, and DUT/REF integration tests under `tests/`.

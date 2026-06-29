---
name: runnable-analysis
description: Measure critical-thread Runnable delay and attribute exact CPU occupants, scheduling restrictions, or launch-time contention. Use when a launch thread is ready to run but not scheduled.
---

# Runnable Analysis

## Purpose

Distinguish CPU contention from cpuset/uclamp/priority/frequency problems using exact temporal overlap.

## Trigger

Routed. Run when scheduler data is available and candidate groups require scheduling analysis.

## Required input

- Critical thread and candidate intervals.
- Runnable/sched intervals and CPU ownership timelines.
- Optional CPU topology, cpuset, uclamp, priority, and frequency metadata.

## Workflow

1. Measure Runnable time for each critical candidate interval.
2. For every Runnable interval, find the task actually running on the relevant CPU.
3. Exclude idle/swapper entries and separate same-process internal concurrency from external P8 interference.
4. Aggregate exact blocker overlap by process/thread and CPU.
5. Publish topology and policy limitations when eligibility cannot be proven.

## Algorithm contract

Only exact critical-Runnable versus blocker-Running overlap can support contention. Total CPU usage alone is correlation.

## Main outputs

- `critical_runnable_ms`
- `critical_runnable_blockers`
- `critical_runnable_blocker_overlap_ms`
- `render_runnable_occupants_ms`
- `runnable_analysis_cpus`

## Leaf and workflow integration

Supports scheduling leaves in P1-P7 and creates interference edges consumed by P8/system-interference and ranking.

## Guardrails

- Do not assume fixed CPU IDs are big cores.
- Do not call an idle CPU a blocker; investigate eligibility/policy instead.
- Do not promote total process CPU to contention without interval overlap.
- Separate same-process worker competition from external interference.

## Failure handling

- Mark blocker attribution unresolved when CPU/topology data is missing.
- Keep Runnable duration observable even if origin attribution is incomplete.

## Known limitation

Cpuset/uclamp/affinity root cause needs task-profile or counter evidence beyond scheduler intervals.

## Implementation

- Manifest: `skills/runnable-analysis/skill.yaml`
- Deterministic implementation: `skills/runnable-analysis/skill.py`
- Entry contract: `run(state, config)`
- Shared state model: `app_entry_rca.core.models.AnalysisState`
- Missing-evidence policy: `NOT_OBSERVABLE`

## Tests

Covered by skill-contract, taxonomy-integrity, guardrail, output-contract, and DUT/REF integration tests under `tests/`.

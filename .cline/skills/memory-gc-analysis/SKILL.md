---
name: memory-gc-analysis
description: Separate direct GC blocking, GC CPU competition, overlap-only, direct reclaim, kswapd, compaction, swap, and process churn. Use for traces containing GC, memory pressure, reclaim, LMKD, or page-residency symptoms.
---

# Memory and GC Analysis

## Purpose

Apply evidence-first memory semantics so GC/kswapd overlap is not mistaken for root cause.

## Trigger

Routed. Run when memory/GC candidate groups are activated or trace capabilities show relevant events.

## Required input

- Launch context and critical intervals.
- GC slices/events, thread states, scheduler intervals, reclaim/kswapd/swap/compaction events.
- `taxonomy/gc_thresholds.yaml` and memory-related leaf rules.

## Workflow

1. Classify GC by process, cause, collector type, and launch overlap.
2. Detect direct blocking: `WaitForGcToComplete`, STW, or allocation stall on a critical path.
3. Measure exact GC-worker Running versus critical-thread Runnable overlap for contributing competition.
4. Keep overlap-only GC as correlation.
5. Measure direct reclaim/compaction on critical threads.
6. Measure kswapd/swap activity and promote only when exact causal/interference evidence exists.
7. Detect process kill/restart or warm-to-cold conversion when supported.

## Algorithm contract

Causality levels are ordered: direct blocking > exact resource competition > temporal overlap only.

## Main outputs

- `wait_for_gc_ms`
- `gc_competition_cpu_ms`
- `gc_overlap_ms`
- `target_direct_reclaim_ms`
- kswapd/reclaim/swap findings
- memory interference edges

## Leaf and workflow integration

Feeds p4.activitystart_or_activityresume.heap_allocation_and_app_side_gc and p8.cross_cutting_system_evidence.memory_pressure_reclaim_swap_and_churn and p8.cross_cutting_system_evidence.direct_gc_blocking leaves. Evidence graph merges memory pressure origins shared by ART/resource/database/page-fault symptoms.

## Guardrails

- GC overlap alone is `CORRELATION_ONLY`.
- kswapd total CPU alone is `CORRELATION_ONLY`.
- Direct reclaim on the critical thread is different from background kswapd activity.
- GC worker competition requires exact temporal/resource overlap.
- Do not promote low MemAvailable without reclaim/swap/eviction/kill consequences.

## Failure handling

- Preserve GC events with limited causality when critical-thread linkage is unavailable.
- Report missing heap/process-state data needed to explain the trigger.

## Known limitation

Heap thresholds, target footprint, LMKD rationale, and page eviction origin may require ART/LMKD/dumpstate instrumentation.

## Implementation

- Manifest: `skills/memory-gc-analysis/skill.yaml`
- Deterministic implementation: `skills/memory-gc-analysis/skill.py`
- Entry contract: `run(state, config)`
- Shared state model: `app_entry_rca.core.models.AnalysisState`
- Missing-evidence policy: `NOT_OBSERVABLE`

## Tests

Covered by skill-contract, taxonomy-integrity, guardrail, output-contract, and DUT/REF integration tests under `tests/`.

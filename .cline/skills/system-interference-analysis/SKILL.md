---
name: system-interference-analysis
description: Analyze P8 cross-process CPU, IRQ/softirq, background jobs, dex2oat, memory/storage workload, thermal/power, and policy interference. Use when critical launch work may be delayed by system-wide activity.
---

# System Interference Analysis

## Purpose

Identify external workload or policy origins while requiring exact linkage to a critical launch symptom.

## Trigger

Routed. Run when P8 candidate groups are activated or other analyzers emit interference edges.

## Required input

- Launch/pre-launch windows.
- Scheduler ownership, Runnable blocker edges, process starts, IRQ/softirq, I/O, memory, GC, and optional thermal/power counters.
- Candidate group and critical-object context.

## Workflow

1. Aggregate top Running owners in the launch and pre-launch windows.
2. Measure IRQ/softirq, dex2oat/package jobs, vendor daemons, and other background workload.
3. Consume exact Runnable-blocker, GC-competition, I/O, and memory interference edges.
4. Separate same-process internal work from external P8 interference.
5. Classify deterministic DUT-only behavior versus one-shot noise or environment mismatch.
6. Publish owner/trigger candidates without replacing the local phase symptom.

## Algorithm contract

P8 explains origin; it is not a sequential phase. A system workload becomes contributing only with exact critical-resource linkage.

## Main outputs

- `top_running_owners_ms`
- `irq_softirq_cpu_ms`
- `dex2oat_cpu_ms`
- background process-start/workload findings
- `state.interference_edges`

## Leaf and workflow integration

Evidence graph connects P8 origins to affected P1-P7 leaves and converges shared causes such as memory pressure or package optimization.

## Guardrails

- Total CPU, kswapd, GC, or I/O volume alone is correlation.
- Do not treat the target app own worker threads as external interference.
- Thermal/power/policy leaves require counters or configuration evidence.
- Random one-run activity must not be promoted without reproducibility evidence.

## Failure handling

- Keep unlinked background workload as correlation-only.
- Report missing thermal/task-profile/job metadata needed for ownership.

## Known limitation

Single DUT/REF traces cannot establish reproducibility; multi-iteration analysis is required for deterministic P8 confirmation.

## Implementation

- Manifest: `skills/system-interference-analysis/skill.yaml`
- Deterministic implementation: `skills/system-interference-analysis/skill.py`
- Entry contract: `run(state, config)`
- Shared state model: `app_entry_rca.core.models.AnalysisState`
- Missing-evidence policy: `NOT_OBSERVABLE`

## Tests

Covered by skill-contract, taxonomy-integrity, guardrail, output-contract, and DUT/REF integration tests under `tests/`.

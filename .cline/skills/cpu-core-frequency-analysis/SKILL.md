---
name: cpu-core-frequency-analysis
description: Attribute canonical app-entry node and leaf intervals to CPU cores, CPU migration, and CPU frequency / DVFS evidence. Use after phase localization and scheduler analysis when sched or counter data is observable.
---

# CPU Core Frequency Analysis

## Purpose

Determine where critical app-entry work actually ran: CPU core, cluster, migration behavior, and CPU frequency during each canonical phase or marker interval.

This skill answers:

- Which CPU did a node or leaf run on?
- How much Running time was spent on each CPU?
- Did the critical thread migrate between CPUs?
- What CPU frequency was active during the Running interval?
- Is the regression more consistent with Application work, CPU placement, DVFS, thermal/power policy, or scheduling interference?

## Trigger

Run after `phase-localizer` and after scheduler-oriented skills when either scheduler data or counter data is observable.

Typical triggers:

- candidate groups under P1-P7 require running/runnable analysis
- P8 CPU scheduling evidence is activated
- `thread_state.cpu` is available
- CPU frequency counters are available in Perfetto `counter` / `cpu_counter_track`

## Required input

- DUT and REF launch contexts.
- Canonical phase windows from `phase-localizer`.
- Marker slices for critical app-entry leaves.
- `thread_state` with `cpu` when available.
- CPU frequency counters from Perfetto counter tables when available.
- Optional config:
  - `little_cpus`
  - `big_cpus`
  - `prime_cpus`
  - `cpu_clusters`
  - `top_subjects`

## Workflow

1. Build analyzable subjects from canonical P1-P7 phase windows and critical marker slices.
2. Resolve the critical thread for each subject.
3. Collect Running intervals for that thread inside the subject interval.
4. Aggregate Running time by CPU.
5. Compute dominant CPU, migration count, and cluster distribution.
6. Read CPU frequency counters for the CPUs used by the thread.
7. Compute weighted average, min, max, and sample count for frequency during Running intervals.
8. Store per-trace and DUT/REF differential output in `cpu_core_frequency.json`.
9. Publish summary findings for evidence graph ranking and report generation.
10. Mark frequency values as `NOT_OBSERVABLE` when counters are missing; do not infer frequency from CPU number alone.

## Algorithm contract

The skill is evidence-first.

It may conclude CPU placement or frequency evidence only when the trace directly contains scheduler CPU and/or CPU frequency counter data. It must not infer CPU frequency from device model, CPU ID, cluster name, or expected hardware layout.

Durations are local evidence for the subject interval. They are not exclusive contribution estimates and must not be added across overlapping P1-P7 windows.

Frequency is computed only over intervals where the critical thread is actually Running. Runnable or Sleeping time is reported separately by other skills and must not be mixed into frequency averages.

## Main outputs

- `cpu_core_frequency.json`
- `state.metrics[label]["cpu_core_frequency"]`
- `state.metrics[label]["cpu_core_frequency_by_subject"]`
- `state.metrics[label]["cpu_core_frequency_summary"]`
- skill finding: `CPU-CORE-FREQ-SUMMARY`
- optional evidence graph hints for CPU placement and frequency differences

## Leaf and workflow integration

This skill enriches candidate leaves from P1-P7 with P8 CPU evidence.

Examples:

- `P4 activityStart / Activity onCreate` ran mostly on little CPUs at lower frequency than REF.
- `P6 first Choreographer#doFrame / traversal` migrated between clusters and spent Running time at lower frequency.
- `P7 post-first-frame tail` ran on the same CPU core as REF with similar frequency, so the regression likely comes from more app work rather than DVFS.

The skill feeds evidence into `leaf-evaluator` and `evidence-graph-ranking`, but it does not directly mark a root cause unless differential evidence and critical-path relevance support it.

## Guardrails

- CPU total alone is not causal.
- Frequency evidence without Running overlap is not assigned to a leaf.
- CPU frequency counter absence means `NOT_OBSERVABLE`, not equal.
- CPU core ID is not automatically equivalent to big/little/prime unless cluster config is provided.
- Do not treat P8 as a timeline phase.
- Do not sum frequency or CPU-placement evidence across overlapping windows.

## Failure handling

- If scheduler data is missing, emit a low-confidence finding and mark CPU placement as `NOT_OBSERVABLE`.
- If frequency counters are missing, still report CPU placement if scheduler data exists.
- If only frequency counters exist without thread CPU state, report launch-window frequency availability but do not assign frequency to leaf Running time.
- The workflow continues because this is a diagnostic enrichment skill, not a critical gate.

## Known limitation

CPU frequency counter names and schemas vary by Perfetto version, kernel, and device vendor. Some traces expose `cpu_counter_track`; others expose only generic `track` names. Some traces do not include frequency counters at all. Cluster classification requires either config or reliable CPU cluster metadata; otherwise the skill reports CPU IDs only.

## Implementation

- Manifest: `skills/cpu-core-frequency-analysis/skill.yaml`
- Deterministic implementation: `skills/cpu-core-frequency-analysis/skill.py`
- Entry contract: `run(state, config)`
- Shared state model: `app_entry_rca.core.models.AnalysisState`
- Missing-evidence policy: `NOT_OBSERVABLE`

## Tests

Covered by skill-contract tests, workflow validation tests, and CPU-core-frequency unit tests using a fake trace backend.

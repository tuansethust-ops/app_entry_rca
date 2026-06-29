# app_entry_rca Canonical Architecture

This branch aligns the RCA engine with the canonical Android app-entry FTA defined by the project owner.

## Canonical timeline model

### Cold Entry

```text
P1 Touch Duration
P2 Launch Preparation
  ├─ P2-1 system_server + launcher workflow
  └─ P2-2 target app process launch
P3 bindApplication
P4 activityStart
P5 activityResume
P6 first Choreographer#doFrame
P7 activityIdle
```

Cold gate rule:

```text
activityStart gate = max(P2-1 end, P3 bindApplication end)
```

### Warm Entry

```text
P1 Touch Duration
P2 Launch Preparation
P3 activityStart
P4 activityResume
P5 first Choreographer#doFrame
P6 activityIdle
```

Warm gate rule:

```text
activityStart gate = P2 Launch Preparation end
```

## P8 semantics

`P8 Cross-cutting System Evidence` is not a timeline phase. It explains why P1-P7 become worse than REF.

Examples:

- CPU scheduling / runnable latency
- binder / lock dependency
- D-state / I/O / page fault
- GC / reclaim / kswapd
- thermal / DVFS
- RenderThread / GPU / fence
- test environment / config difference

Never compute total launch time as `P1 + ... + P8`.

## Runtime pipeline

```text
DUT trace + REF trace
  -> trace-ingestion
  -> launch-context
  -> trace-validation
  -> phase-localizer
  -> routed evidence analyzers
  -> leaf-evaluator
  -> evidence-graph-ranking
  -> report-generator
```

## Main artifacts

- `phase_comparison.json`: canonical P1-P7/P8 comparison
- `raw_phase_intervals.json`: extracted phase and P2 branch intervals
- `raw_marker_slices.json`: raw marker slices used by the localizer
- `critical_path.json`: activityStart gate analysis
- `raw_metrics.json`: paired metric table and numeric deltas
- `all_leaf_nodes.json/csv`: evaluated taxonomy leaves
- `final_leaves.json`: ranked RCA candidates
- `report.md`: human-readable RCA report

## Canonical leaf ID policy

This branch uses semantic canonical IDs for groups and leaves. Runtime taxonomy no longer uses legacy numeric IDs such as `P3.7.4` or `P6.2.1`.

Canonical leaf IDs follow this pattern:

```text
<p-phase>.<canonical-phase-name>.<group-name>.<leaf-name>
```

Examples:

```text
p3.bindapplication_or_activitystart.framework_bindapplication_bootstrap.bindapplication
p4.activitystart_or_activityresume.activity_instantiation_and_lifecycle.oncreate_saved_state_restore
p6.first_choreographer_doframe_or_activityidle.measure_and_layout_traversal.performmeasure_onmeasure
p8.cross_cutting_system_evidence.cpu_capacity_and_scheduler_interference.exact_same_cpu_blocker_on_critical_runnable
```

The `phase` field still remains `P1` through `P8` for report grouping and FTA readability. The `id` field is now semantic and stable for rules, reports and Cline references.


## Canonical FTA contract for Cline

Do not rename the canonical app-entry phases.

Cold Entry:
`P1 Touch Duration -> P2 Launch Preparation -> P3 bindApplication -> P4 activityStart -> P5 activityResume -> P6 first Choreographer#doFrame -> P7 activityIdle`

Warm Entry:
`P1 Touch Duration -> P2 Launch Preparation -> P3 activityStart -> P4 activityResume -> P5 first Choreographer#doFrame -> P6 activityIdle`

P8 is cross-cutting system evidence only. It is never a sequential phase and must not be included in additive launch-time accounting.

When modifying extraction or rules, preserve output artifacts:
- `raw_phase_intervals.json`
- `raw_marker_slices.json`
- `critical_path.json`
- `phase_comparison.json`
- `all_leaf_nodes.json/csv`
- `final_leaves.json`


## CPU Core/Frequency Skill

- `cpu-core-frequency-analysis` enriches P1-P7 node/leaf intervals with CPU core, migration, cluster, and CPU frequency evidence.
- Output artifact: `cpu_core_frequency.json`.
- Missing CPU-frequency counters are treated as `NOT_OBSERVABLE`, not equal.

## Positional Cline form

Cline may be called with two trace paths directly:

```text
/app_entry_rca <DUT_TRACE_PATH> <REF_TRACE_PATH>
```

When invoked this way, treat the first positional path as DUT and the second positional path as REF, then run:

```bash
python scripts/run_app_entry_rca.py "<DUT_TRACE_PATH>" "<REF_TRACE_PATH>" --backend perfetto --include-better-final
```

If the user adds a package name or output directory, convert them to named flags:

```bash
python scripts/run_app_entry_rca.py "<DUT_TRACE_PATH>" "<REF_TRACE_PATH>" \
  --target "<PACKAGE_NAME>" \
  --out "<OUTPUT_DIR>" \
  --backend perfetto \
  --include-better-final
```

Default Trace Processor path is project-local:

```text
tools/perfetto/trace_processor_shell
tools/perfetto/trace_processor_shell.exe
```

Only pass `--trace-processor` when the executable is outside `tools/perfetto/`.

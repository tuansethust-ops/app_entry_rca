# app_entry_rca Workflow

## Inputs

- DUT trace
- REF trace
- optional target package
- optional zero-based launch index
- optional traceconv path

## Execution stages

1. **Ingestion**: normalize both traces and detect data-source capabilities.
2. **Context**: select a coherent launch and classify launch type from process evidence.
3. **Validation**: compare target, launch type, endpoint and marker coverage.
4. **Localization**: create P1-P8 windows/segments and activate taxonomy groups.
5. **Diagnostics**: route reusable skills from candidate groups and observability, including `cpu-core-frequency-analysis` when scheduler or CPU-frequency evidence is available.
6. **CPU placement/frequency enrichment**: attach CPU core, migration, cluster, and frequency evidence to canonical phase/marker intervals when observable.
7. **Evaluation**: evaluate all taxonomy leaves using `leaf_rules.yaml`.
8. **Ranking**: combine shared evidence, suppress duplicate downstream symptoms and rank final leaves.
9. **Reporting**: write stable artifacts.

## Failure policy

Core stages are critical and `workflow.yaml` sets `error_policy.fail_fast: true`, so critical-stage failures stop the workflow immediately. Specialized analyzers are noncritical: if one cannot run because its data source is missing, the workflow continues and leaves are marked `NOT_OBSERVABLE` rather than inventing zeros.

## Non-additive durations

P2 functional system_server segments may overlap P3. P4 and P5 can also describe the same wall-clock interval from different dimensions. The workflow never claims that summing P1-P8 yields total launch time.


## Runtime entry points

- Cross-platform: `python scripts/run_app_entry_rca.py ...`
- Windows: `windows/run.ps1` or `run_app_entry_rca.bat`
- Cline: `.clinerules/workflows/app_entry_rca.md` invoked as `/app_entry_rca`

The runtime entry points all load this workflow's YAML definition and invoke the same internal skills.

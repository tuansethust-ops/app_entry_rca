# App Entry RCA v1 — canonical semantic leaf IDs

Evidence-driven DUT-vs-REF Android app-entry analysis using canonical P1-P7 app-launch FTA phases, P8 cross-cutting evidence, semantic leaf IDs, reusable diagnostic skills and a deterministic workflow.

`app_entry_rca` is **one workflow** that orchestrates multiple reusable skills. It can be run directly on Windows/Linux/macOS, invoked from Cline as `/app_entry_rca`, or accessed via the **Interactive Web UI**.

## Interactive Web UI (New) 🌟

The analyzer now includes a modern, high-performance web interface for visualizing trace comparisons, tracking progress in real-time, and exploring interactive reports.

### Features
- **File Browser**: Select local `.log` or `.perfetto` traces directly from your filesystem without uploading.
- **Live Analysis**: Real-time progress tracking and live log streaming via WebSockets.
- **Interactive Dashboards**: Sortable root cause tables, phase comparison Gantt charts, and evidence trees.
- **Batch Mode**: Analyze entire directories of trace files concurrently.

### Run Web Server

```bash
# Ensure dependencies are installed
pip install fastapi uvicorn python-multipart pyyaml aiofiles

# Launch the server
python run_web.py
```
Then navigate to `http://localhost:8000` in your browser.

## One workflow, multiple skills

Canonical workflow definition:

```text
workflows/app_entry_rca/workflow.yaml
```

Cline integration:

```text
.clinerules/workflows/app_entry_rca.md
.cline/skills/app-entry-rca/SKILL.md
.cline/skills/<internal-skill>/SKILL.md
```

See [Windows and Cline usage](docs/windows_and_cline.md).

## Fast start on Windows

```bat
install_windows.bat
run_app_entry_rca.bat -Dut "D:\trace\DUT.perfetto" -Ref "D:\trace\REF.perfetto" -Out "D:\trace\result" -IncludeBetterFinal
```

## Fast start in Cline

Open this repository as the workspace and run:

```text
/app_entry_rca
```

Mention the DUT and REF trace paths. Cline will run the same deterministic Python workflow used by Windows.

## Reviewed engine changes inherited from v4

- Replaced prototype-only skill stubs with explicit skill contracts, routing reasons, findings and limitations.
- Added a declarative `leaf_rules.yaml` instead of embedding all leaf rules in Python.
- Corrected phase semantics:
  - P2 reports functional segment union and functional sum separately.
  - P3 ends at `bindApplication` delivery rather than including the complete bind body.
  - P5 remains a work domain nested in app callbacks.
- Removed the hard-coded CPU6-7 assumption. Render competition uses configured CPUs or CPUs where RenderThread actually ran.
- GC competition now uses same/unknown-CPU interval overlap between GC Running and critical Runnable intervals.
- Added explicit observability, routing and skill findings outputs.
- Added `p1.touch_duration.input_event_delivery.end_to_end_input_event_delivery_latency End-to-end input event delivery latency`; `p1.touch_duration.input_event_delivery.inputreader_processing_delay` remains dedicated to true InputReader processing.
- Added contract, taxonomy, routing, phase-semantics and golden DUT/REF tests.

## Run (CLI)

```bash
python app_entry_rca.py \
  --dut DUT.perfetto \
  --ref REF.perfetto \
  --out output \
  --include-better-final
```

For a Perfetto protobuf trace, provide Perfetto `traceconv`:

```bash
python app_entry_rca.py \
  --dut DUT.pftrace \
  --ref REF.pftrace \
  --traceconv /path/to/traceconv \
  --out output
```

Multiple launches can be selected with:

```bash
--launch-index 1
```

Use `--strict-validation` only when a target or launch-type mismatch must abort the workflow. By default the workflow still writes diagnostic output and marks the pair invalid/partially comparable.

## Architecture

```text
Trace pair
  -> trace-ingestion
  -> launch-context
  -> trace-validation
  -> phase-localizer
  -> capability skills selected by routing
  -> leaf-evaluator
  -> evidence-graph-ranking
  -> report-generator
```

Skills are capabilities such as scheduler, wait dependency, I/O, GC, ART and rendering. Canonical P1-P7, P8 cross-cutting evidence, and the predefined semantic leaf taxonomy live in taxonomy/config, not in separate phase agents.

## Main outputs

- `analysis_summary.json`: top-level execution and result summary, including first-frame proxy delta.
- `validation.json`: pair comparability and marker coverage.
- `launch_context.json`: target, launch type, PIDs and marker semantics.
- `phase_comparison.json`: canonical P1-P7 windows/segments plus P8 evidence row and DUT-REF deltas.
- `routing.json`: activated groups, selected skills and reasons.
- `observability.json`: available trace data sources/capabilities.
- `skill_runs.json`: duration, status and metrics produced by every skill.
- `skill_findings.json`: structured per-skill observations.
- `ms_diff_summary.json`: first-frame regression and local/nested millisecond deltas with overlap guardrails.
- `all_leaf_nodes.json/csv`: every predefined leaf, including better/equivalent/not-observable.
- `automation_coverage.json`: which taxonomy leaves have automatic evidence rules versus instrumentation/future-rule placeholders.
- `final_leaves.json`: ranked case-specific six-part leaves.
- `final_leaf.json`: highest-ranked DUT regression.
- `evidence_graph.json`: causal/evidence graph.
- `report.md`: readable report.

## Important semantics

- `NOT_OBSERVABLE` does not mean DUT and REF are equal.
- A one-sided duration marker is normally `INSUFFICIENT_EVIDENCE`; explicitly modeled event-presence rules may use `DUT_ONLY`/`REF_ONLY`.
- GC overlap is correlation-only unless direct wait or exact competition is proven.
- P2 can overlap P3; do not add all phase durations into one total.
- `finishDrawing` is a presentation proxy. True present-time analysis needs FrameTimeline/SurfaceFlinger data.

## Tests

```bash
pytest -q
```

Run the golden pair test:

```bash
DUT_TRACE=/path/DUT.perfetto \
REF_TRACE=/path/REF.perfetto \
pytest -q
```

## Distribution note

The supported distribution is the source project (or an editable install with `pip install -e .`) because the workflow dynamically loads top-level `skills/`, `taxonomy/` and `workflows/` assets. A standalone wheel is not currently claimed as a supported deployment format.


## Millisecond delta semantics

The report separates three timing concepts:

- `local_delta_ms`: DUT−REF delta of the candidate window.
- `exclusive_contribution_ms`: attributed paired contribution when measurable.
- `nested_deltas_ms`: child/state evidence inside the same parent window.

All candidate records carry an `overlap_group` and `additive=false`. Parent, child and cross-phase deltas must not be summed directly.

## Cline skill discovery

All internal capabilities are real Cline project skills under `.cline/skills/<name>/SKILL.md`. Each file contains YAML frontmatter whose `name` matches the directory and whose `description` tells Cline when to activate the skill. Canonical copies live under `skills/<name>/SKILL.md` and are kept identical by tests. See `docs/CLINE_SKILL_FORMAT.md`.


## Canonical architecture update

This version uses the project-owner canonical FTA naming:

- Cold: `P1 Touch Duration -> P2 Launch Preparation -> P3 bindApplication -> P4 activityStart -> P5 activityResume -> P6 first Choreographer#doFrame -> P7 activityIdle`
- Warm: `P1 Touch Duration -> P2 Launch Preparation -> P3 activityStart -> P4 activityResume -> P5 first Choreographer#doFrame -> P6 activityIdle`
- `P8 Cross-cutting System Evidence` is not a sequential launch phase; it explains why P1-P7 regress.

See `docs/CANONICAL_ARCHITECTURE.md`.

New output artifacts include `raw_phase_intervals.json`, `raw_marker_slices.json`, and `critical_path.json`.


## v1 semantic leaf ID policy

Runtime taxonomy no longer uses legacy numeric leaf IDs such as `P3.7.4` or `P6.2.1`. Group and leaf IDs are semantic and canonical, for example:

```text
p3.bindapplication_or_activitystart.framework_bindapplication_bootstrap.bindapplication
p6.first_choreographer_doframe_or_activityidle.measure_and_layout_traversal.performmeasure_onmeasure
p8.cross_cutting_system_evidence.storage_and_filesystem_contention.file_backed_page_fault_or_i_o_wait
```

The short `phase` field remains `P1` through `P8` only for report grouping and FTA readability.


## Diagrams

- `diagrams/app_entry_fta_leaf.svg`: corrected canonical FTA leaf diagram.
- `diagrams/app_entry_rca_flowchart.svg`: runtime RCA workflow diagram.


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

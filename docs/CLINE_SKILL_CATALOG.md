# Cline Skill Catalog

All project skills are discoverable under `.cline/skills/<name>/SKILL.md`.

| Skill | Description |
|---|---|
| `app-entry-rca` | Run the complete evidence-driven DUT-versus-REF Android app-entry RCA workflow using P1-P8 FTA taxonomy and routed diagnostic skills. Use when the user supplies two Perfetto/atrace traces and wants phase comparison, all leaf classifications, final root-cause candidates, millisecond deltas, or a deep dive into GC, reclaim, Binder, I/O, ART, rendering, or activityIdle. |
| `art-runtime-analysis` | Analyze APK/DEX/OAT/VDEX/AppImage preparation, compiler artifacts, class initialization, JIT, linker, JNI, and native first-use work. Use for cold/prestarted launches or class/runtime-heavy app initialization. |
| `block-io-analysis` | Analyze critical D-state, page faults, file/page waits, filesystem locks, reclaim, and block-device requests. Use when launch-critical threads block in I/O-related states or resource loading is slow. |
| `evidence-graph-ranking` | Build the causal evidence graph, merge duplicate symptoms and shared origins, score supported leaves, and generate final actionable RCA leaves. Use after leaf evaluation to select trustworthy primary and secondary candidates. |
| `launch-context` | Detect the target package, launch candidate, process and thread identities, actual launch type, and canonical app-entry markers for DUT and REF. Use after trace ingestion or when launch selection and P7 activityIdle boundaries are uncertain. |
| `leaf-evaluator` | Evaluate all 151 P1-P8 FTA leaves against DUT-versus-REF metrics using 41 declarative automatic rules. Use after diagnostic skills to classify leaf status, causality, millisecond deltas, observability, and overlap semantics. |
| `memory-gc-analysis` | Separate direct GC blocking, GC CPU competition, overlap-only, direct reclaim, kswapd, compaction, swap, and process churn. Use for traces containing GC, memory pressure, reclaim, LMKD, or page-residency symptoms. |
| `phase-localizer` | Build P1-P7 timing segments, model P8 as cross-cutting context, compare DUT and REF, and activate candidate groups for routed analysis. Use after validation to identify where a launch difference occurs. |
| `render-frame-analysis` | Analyze P6 frame scheduling, traversal, RecyclerView/layout, draw, RenderThread/HWUI, Vulkan, texture upload, GPU/fences, SurfaceFlinger, and the P7 tail to system_server activityIdle. Use for first-frame or post-frame regressions. |
| `report-generator` | Write stable JSON, CSV, and Markdown outputs for the app_entry_rca workflow and validate output contracts. Use as the final workflow skill or when regenerating reports from an existing analysis state. |
| `runnable-analysis` | Measure critical-thread Runnable delay and attribute exact CPU occupants, scheduling restrictions, or launch-time contention. Use when a launch thread is ready to run but not scheduled. |
| `running-analysis` | Measure CPU Running time for critical launch threads and candidate-owned intervals, separating extra CPU work from waiting. Use when phase localization activates CPU-execution candidates. |
| `system-interference-analysis` | Analyze P8 cross-process CPU, IRQ/softirq, background jobs, dex2oat, memory/storage workload, thermal/power, and policy interference. Use when critical launch work may be delayed by system-wide activity. |
| `trace-ingestion` | Normalize DUT and REF Perfetto, atrace, or systrace inputs into the app_entry_rca internal trace model and detect available capabilities. Use when the app-entry workflow starts, when a trace backend fails, or when observability must be debugged. |
| `trace-validation` | Validate DUT-versus-REF comparability, launch identity, endpoint semantics, marker coverage, and trace capability symmetry. Use before interpreting phase or leaf deltas and whenever results look inconsistent. |
| `wait-dependency-analysis` | Build Binder, monitor, futex, worker, and callback dependency chains for critical Sleeping or blocked launch intervals. Use when a candidate thread waits instead of executing. |

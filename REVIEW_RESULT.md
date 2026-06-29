# App Entry RCA v4 Review Result

## Review verdict

The previous project was a functional prototype. Version 4 is now a contract-driven workflow with explicit skill routing, observability, declarative leaf rules, causal deduplication and integration tests.

## Critical corrections

1. P2 uses overlap-safe functional segment union instead of summing overlapping work.
2. P3 ends at bind delivery and no longer absorbs the complete app-side bind body.
3. P5 is modeled as a nested work domain, not a sequential wall-clock phase.
4. Render scheduling no longer assumes CPU 6-7 are big cores.
5. GC competition uses real interval overlap, not `min(gc_cpu, runnable)`.
6. One-sided markers use explicit rule semantics instead of automatic DUT-only conclusions.
7. The preBind/ActivityStarter chain is deduplicated into one primary causal leaf.
8. Every skill has a manifest, algorithm, trigger, outputs, guardrails and limitations.
9. Every workflow run records routing reasons, skill timing, metrics and findings.
10. Structured final-leaf evidence is emitted as JSON objects rather than opaque strings.

## Coverage

- 15 capability skills.
- 261 taxonomy leaves.
- 56 automatic evidence rules in the current text-trace backend.
- Remaining leaves stay explicit `NOT_OBSERVABLE` and list required evidence; they are not silently treated as equivalent.
- `automation_coverage.json` makes this distinction machine-readable.

## Validation

- Python compile check: passed.
- Unit and contract tests: 12 passed.
- Golden DUT/REF integration test: passed.
- Installed console command `app-entry-rca`: passed.
- Primary result on the supplied pair: `DUT-R04`, ActivityStarter/attach preBind lock serialization.

## Known limitations

- Native Perfetto protobuf input requires `traceconv` in the current backend.
- True display-present timing requires FrameTimeline/SurfaceFlinger data; `finishDrawing` is only a proxy.
- File path attribution, major-fault attribution, GPU counters, thermal and task-profile leaves require corresponding trace data sources.
- Source/editable installation is supported; a standalone wheel with all dynamically loaded assets is not claimed yet.

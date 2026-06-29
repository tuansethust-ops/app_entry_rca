# v3 Review and v4 Corrections

## Critical issues found

1. Most skills were only 10-20 line metric stubs with identical documentation.
2. Router effectively enabled almost all analyzers and did not record why.
3. Leaf evaluation hard-coded a small subset of rules in Python.
4. P3 included the whole `bindApplication` body, overlapping P4.
5. P2 summed overlapping functional segments.
6. Render analysis assumed CPU6-7 were big cores.
7. GC competition used `min(gc_cpu, critical_runnable)`, which is not an overlap calculation.
8. One-sided missing markers were sometimes interpreted as DUT-only evidence without a rule contract.
9. `ActivityThreadMain`, attach orchestration and process-to-bind delay could become three duplicate final leaves for one lock chain.
10. Output lacked routing, observability and structured skill findings.

## Corrections implemented

- Added skill manifests with stage, dependencies, triggers and outputs.
- Added detailed per-skill algorithms and guardrails.
- Added explicit capability detection and observability output.
- Added declarative leaf rules with applicability and one-sided semantics.
- Added causal deduplication: preBind lock chain covers downstream ActivityThreadMain/attach/bind symptoms.
- Added transparent score breakdown and verification steps.
- Added exact/same-CPU interval overlap for GC competition.
- Inferred RenderThread competition CPUs from actual RenderThread execution when topology is unavailable.
- Added test coverage for contracts, taxonomy, routing, P2 overlap semantics and the DUT/REF golden pair.

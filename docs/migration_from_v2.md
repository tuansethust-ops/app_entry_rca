# Migration to v4

## From the monolithic analyzer

Parsing, metrics, rules and reports are now separated into workflow stages and capability skills.

## From v3 skill prototype

v4 adds:

- explicit skill contracts and dependencies;
- declarative leaf rules;
- routing and observability artifacts;
- overlap-safe P2 semantics;
- corrected P3 boundary;
- topology-safe RenderThread analysis;
- exact interval-based GC competition;
- generic metric units instead of treating every value as milliseconds;
- causal deduplication and verification steps;
- 12 automated tests including the golden DUT/REF pair.

Output consumers should prefer generic fields `dut_value`, `ref_value`, `delta_value`, `metric_unit`. Millisecond compatibility fields remain populated for `ms` metrics.

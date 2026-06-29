# Memory/GC Skill

The GC skill separates:

- **Direct blocking**: `WaitForGcToComplete`, STW or allocation stall on the critical path.
- **Resource competition**: same/unknown-CPU interval overlap between GC-worker Running and critical-thread Runnable intervals.
- **Overlap only**: GC exists in the launch window without direct block or competition proof.

It also reports target direct reclaim, kswapd CPU and GC owner (`target`, `system_server`, `other`).

Guardrails:

- `min(total_gc_cpu, total_runnable)` is not a valid competition estimate and is no longer used.
- Overlap-only is always correlation-only.
- Heap thresholds in `gc_thresholds.yaml` are context, not proof of the active runtime configuration.

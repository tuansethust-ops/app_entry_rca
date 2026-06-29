# App Entry RCA — Full Workflow

- Workflow: `app_entry_rca`
- Version: `6.2.0`
- Canonical completion endpoint: end of
  `IActivityClientController::activityIdle::server` in system_server.
- Schema: `6.0`

## Architecture

```text
DUT trace + REF trace
  → Trace ingestion and capability detection
  → Launch context and true cold/warm/hot classification
  → Pair validation
  → P1–P8 localization and candidate activation
  → Candidate-to-analyzer routing
  → Reusable diagnostic skills
  → Evaluate every predefined leaf
  → Build dependency/interference/evidence graph
  → Deduplicate shared causes and rank candidates
  → Generate final six-part leaf and reports
```

## Workflow steps

| Order | Skill | Mode | Critical | Responsibility |
|---:|---|---|---|---|
| 1 | `trace-ingestion` | `always` | `True` | Open Perfetto SQL when available; systrace fallback; declare capabilities. |
| 2 | `launch-context` | `always` | `True` | Select target launch, markers, process/thread IDs and actual launch type. |
| 3 | `trace-validation` | `always` | `True` | Validate DUT/REF comparability and missing evidence. |
| 4 | `phase-localizer` | `always` | `True` | Build P1–P8 segments and activate candidate groups. |
| 5 | `running-analysis` | `routed` | `False` | Attribute additional CPU execution and nested work. |
| 6 | `runnable-analysis` | `routed` | `False` | Measure scheduler delay and competing CPU owners. |
| 7 | `wait-dependency-analysis` | `routed` | `False` | Build Binder/monitor/futex/worker dependency chains. |
| 8 | `block-io-analysis` | `routed` | `False` | Analyze D-state, blocked reason, page fault, file and storage paths. |
| 9 | `memory-gc-analysis` | `routed` | `False` | Analyze direct GC block, STW, GC competition, reclaim, kswapd, compaction and swap. |
| 10 | `art-runtime-analysis` | `routed` | `False` | Analyze DEX/OAT/VDEX, class/JIT/linker/runtime bootstrap. |
| 11 | `render-frame-analysis` | `routed` | `False` | Analyze VSync, traversal, RenderThread, Vulkan/GPU, BufferQueue and presentation. |
| 12 | `system-interference-analysis` | `routed` | `False` | Analyze CPU, memory, I/O, background workload, thermal and task-profile causes. |
| 13 | `leaf-evaluator` | `always` | `True` | Evaluate all leaves with observability, applicability and evidence-level rules. |
| 14 | `evidence-graph-ranking` | `always` | `True` | Create causal graph, suppress duplicate symptoms and rank final candidates. |
| 15 | `report-generator` | `always` | `True` | Write stable JSON/CSV/Markdown artifacts. |

## Routing contract

A routed skill executes only when both conditions hold:

1. At least one activated candidate maps to that skill.
2. The trace exposes at least one required or useful capability.

Missing capability does not produce a zero. The corresponding leaf remains `NOT_OBSERVABLE` or `INSUFFICIENT_EVIDENCE`.

## Status semantics

| Status | Meaning |
|---|---|
| `DUT_REGRESSION` | DUT is measurably worse and the rule requirements are met. |
| `DUT_BETTER` | DUT is measurably better. |
| `EQUIVALENT` | Both are observable and delta is below the rule threshold. |
| `DUT_ONLY` / `REF_ONLY` | Observable event exists on only one side. |
| `NOT_APPLICABLE` | Leaf does not apply, for example cold-only P3 on a true warm launch. |
| `NOT_OBSERVABLE` | Required trace data/marker is absent. |
| `INSUFFICIENT_EVIDENCE` | Symptom exists but causal prerequisites are not proven. |

## Causality semantics

| Level | Promotion rule |
|---|---|
| `DIRECT` | Critical path is directly blocked or extended by the mechanism. |
| `CONTRIBUTING` | Exact temporal/resource interference with the critical path is demonstrated. |
| `CORRELATION_ONLY` | Activity overlaps the launch, but no causal edge is proven. Never selected as primary RCA. |
| `REJECTED` | Evidence contradicts the hypothesis. |

## Non-additive phase semantics

- P2 can split around P3 during cold launch.
- P4 is callback/control-flow location; P5 is a nested resource/data work domain.
- P6 ends at a selected presentation proxy or actual FrameTimeline present event.
- P7 measures post-frame tail against a named milestone.
- P8 is cross-cutting and is never summed as a sequential phase.

## Final leaf contract

```json
{
  "symptom": "measured DUT/REF difference",
  "location": "phase, callback, process, thread and interval",
  "mechanism": "direct execution/wait/interference mechanism",
  "origin": "underlying trigger or state",
  "ownership": "component/team/config owner",
  "action": "targeted mitigation",
  "evidence": [],
  "rejected_alternatives": [],
  "verification_plan": {}
}
```

## Stable output artifacts

`analysis_summary.json`, `validation.json`, `launch_context.json`, `phase_comparison.json`, `routing.json`, `observability.json`, `skill_runs.json`, `skill_findings.json`, `raw_metrics.json`, `all_leaf_nodes.json`, `all_leaf_nodes.csv`, `dependency_graph.json`, `interference_edges.json`, `evidence_graph.json`, `final_leaves.json`, `final_leaf.json`, `automation_coverage.json`, `provenance.json`, and `report.md`.

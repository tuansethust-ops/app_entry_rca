---
name: wait-dependency-analysis
description: Build Binder, monitor, futex, worker, and callback dependency chains for critical Sleeping or blocked launch intervals. Use when a candidate thread waits instead of executing.
---

# Wait Dependency Analysis

## Purpose

Follow the wait to the responsible server, lock owner, worker, or downstream dependency rather than blaming the waiting thread.

## Trigger

Routed. Run when candidate groups expose Sleeping, Binder, monitor, futex, or synchronization evidence.

## Required input

- Critical candidate intervals and thread states.
- Binder transactions/slices, monitor contention, futex, and callback markers.
- Process/thread ownership metadata.

## Workflow

1. Identify waiting intervals and classify Binder, lock/futex, worker join, timer/policy, or unknown wait.
2. Resolve the immediate server thread, lock owner, or worker when evidence exists.
3. Traverse nested dependencies with cycle detection and a bounded depth.
4. Attach Running/Runnable/D-state evidence for each dependency node.
5. Build structured dependency graph nodes and edges.

## Algorithm contract

The waiter symptom and owner mechanism are one causal chain. They must not become duplicate independent root causes.

## Main outputs

- `monitor_dependencies`
- `binder_dependencies`
- `critical_sleeping_ms`
- `state.dependency_graph`
- resolved/unresolved dependency findings

## Leaf and workflow integration

Feeds P2/P3/P4/P5/P7 wait leaves and evidence-graph convergence. Downstream I/O or scheduling analysis may own the final origin.

## Guardrails

- Binder duration without client/server linkage is insufficient for direct causality.
- Monitor contention must identify waiter interval and owner when possible.
- Do not double-count waiter duration and nested server work.
- Stop traversal on cycles and report unresolved endpoints.

## Failure handling

- Keep the wait observable while marking owner/origin unresolved.
- Record missing Binder transaction IDs or monitor-owner evidence explicitly.

## Known limitation

Text traces often lack Binder transaction IDs, making nested Binder attribution lower confidence.

## Implementation

- Manifest: `skills/wait-dependency-analysis/skill.yaml`
- Deterministic implementation: `skills/wait-dependency-analysis/skill.py`
- Entry contract: `run(state, config)`
- Shared state model: `app_entry_rca.core.models.AnalysisState`
- Missing-evidence policy: `NOT_OBSERVABLE`

## Tests

Covered by skill-contract, taxonomy-integrity, guardrail, output-contract, and DUT/REF integration tests under `tests/`.

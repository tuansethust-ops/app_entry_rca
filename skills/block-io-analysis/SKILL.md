---
name: block-io-analysis
description: Analyze critical D-state, page faults, file/page waits, filesystem locks, reclaim, and block-device requests. Use when launch-critical threads block in I/O-related states or resource loading is slow.
---

# Block I/O Analysis

## Purpose

Distinguish storage/file-page latency from reclaim, compaction, filesystem locking, and unknown D-state mechanisms.

## Trigger

Routed. Run when candidate groups require file/page/block-I/O evidence and relevant trace capabilities exist.

## Required input

- Critical candidate intervals and D-state thread-state data.
- Raw ftrace/filemap/page-fault/block events when available.
- Optional inode/path, block request, and reclaim metadata.

## Workflow

1. Measure critical D-state within candidate intervals.
2. Classify blocked reasons using kernel caller/event evidence.
3. Attribute page faults or waits to files/inodes/paths when available.
4. Link block requests to queue/service latency and competing I/O owners when possible.
5. Separate direct reclaim/compaction into memory-origin evidence.
6. Emit unresolved D-state as insufficient evidence, not storage root cause.

## Algorithm contract

D-state is a symptom. Direct causality requires blocked-reason or file/page/block attribution on the critical path.

## Main outputs

- `critical_d_state_ms`
- `page_fault_event_count`
- `block_io_event_count`
- blocked-reason categories
- file/page/block attribution findings

## Leaf and workflow integration

Feeds P3/P5/P7 I/O leaves and P8 storage/memory origins. Reclaim findings are shared with `memory-gc-analysis`.

## Guardrails

- D-state alone is not proof of slow storage.
- Major fault, direct reclaim, block queue delay, and filesystem lock are different mechanisms.
- Do not infer a file path without filemap/inode evidence.
- Avoid double-counting the same blocked interval under parent resource-loading leaves.

## Failure handling

- Keep duration metrics with `INSUFFICIENT_EVIDENCE` when blocked reason is unknown.
- List required instrumentation for path or block attribution.

## Known limitation

Exact file and request attribution requires Perfetto/raw ftrace sources that may be absent from atrace text.

## Implementation

- Manifest: `skills/block-io-analysis/skill.yaml`
- Deterministic implementation: `skills/block-io-analysis/skill.py`
- Entry contract: `run(state, config)`
- Shared state model: `app_entry_rca.core.models.AnalysisState`
- Missing-evidence policy: `NOT_OBSERVABLE`

## Tests

Covered by skill-contract, taxonomy-integrity, guardrail, output-contract, and DUT/REF integration tests under `tests/`.

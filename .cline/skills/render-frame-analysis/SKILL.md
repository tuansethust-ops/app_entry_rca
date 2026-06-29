---
name: render-frame-analysis
description: Analyze P6 frame scheduling, traversal, RecyclerView/layout, draw, RenderThread/HWUI, Vulkan, texture upload, GPU/fences, SurfaceFlinger, and the P7 tail to system_server activityIdle. Use for first-frame or post-frame regressions.
---

# Render and Frame Analysis

## Purpose

Locate whether frame latency is on the UI thread, RenderThread CPU path, GPU/fence path, composition path, or post-first-frame activityIdle tail.

## Trigger

Routed. Run when P6/P7 render or completion candidate groups are activated.

## Required input

- Launch context with traversal/first-frame/activityIdle markers.
- UI/RenderThread slices, scheduler states, FrameTimeline/GPU/SF data when available.
- System_server activityIdle server slice and monitor contention evidence.

## Workflow

1. Measure frame scheduling/VSync admission and first traversal.
2. Decompose measure, layout, RecyclerView onLayout, draw, and display-list work.
3. Measure RenderThread `DrawFrames` and scheduler states.
4. Measure Vulkan finish-frame CPU work, texture/glyph upload, GPU completion/fence, BufferQueue, and SF/HWC when observable.
5. Select first presented frame from FrameTimeline when available; otherwise label `finishDrawing`/DrawFrames as a proxy.
6. Measure P7 from first-frame completion to system_server activityIdle server end.
7. Separate pre-server tail, Binder delivery when observable, server handler state, and server monitor contention.

## Algorithm contract

CPU render preparation, texture upload, GPU execution, fence wait, and composition are separate leaves. Nested deltas share overlap groups and are non-additive.

## Main outputs

- `traversal_ms`
- `recycler_view_onlayout_ms`
- `draw_frames_ms`
- `vulkan_finish_ms`
- `texture_upload_ms`
- `gpu_wait_ms`
- `p7_to_activity_idle_server_ms`
- `activity_idle_server_ms` and state/lock decomposition

## Leaf and workflow integration

Feeds P6 and P7 leaves. Ranking distinguishes local first-frame regression from total activityIdle completion behavior.

## Guardrails

- `finishDrawing` is a proxy unless FrameTimeline/SF present data exists.
- Do not call CPU-side Vulkan/HWUI time GPU execution.
- Do not sum first traversal, RecyclerView layout, DrawFrames, and nested Vulkan deltas.
- P7 total tail and server handler can move in opposite directions; report both.
- Generic activityIdle is a lower-confidence fallback to the exact system_server AIDL slice.

## Failure handling

- Mark GPU/SF leaves unobservable when only app slices exist.
- Keep first-frame proxy semantics explicit in every report.

## Known limitation

Hardware present timing, HWC, GPU frequency, and fence attribution depend on corresponding Perfetto data sources.

## Implementation

- Manifest: `skills/render-frame-analysis/skill.yaml`
- Deterministic implementation: `skills/render-frame-analysis/skill.py`
- Entry contract: `run(state, config)`
- Shared state model: `app_entry_rca.core.models.AnalysisState`
- Missing-evidence policy: `NOT_OBSERVABLE`

## Tests

Covered by skill-contract, taxonomy-integrity, guardrail, output-contract, and DUT/REF integration tests under `tests/`.

# App Entry RCA 6.1 changes

- Added `input_to_first_frame_proxy_ms` using the start of `finishDrawing` when FrameTimeline present data is unavailable.
- Added `ms_diff_summary.json` with main contributor deltas and overlap guardrails.
- Final leaves now contain:
  - `local_delta_ms`
  - `exclusive_contribution_ms`
  - `nested_deltas_ms`
  - `overlap_group`
  - `additive`
  - `delta_note`
- Added automatic p6.first_choreographer_doframe_or_activityidle.measure_and_layout_traversal.performlayout_or_onlayout RecyclerView initial `RV OnLayout` analysis.
- Removed the incorrect automatic mapping of `traversal_to_draw_start_ms` to p6.first_choreographer_doframe_or_activityidle.frame_scheduling_and_vsync_admission.scheduletraversals_delay frame scheduling.
- Changed contribution calculation from an absolute DUT duration to a paired DUT-REF contribution magnitude.
- Parent `startActivity` is reported as umbrella context; exact Runnable delay remains a causal child candidate.
- Added D-state and Sleeping state decomposition for major launch windows.
- Removed idle/swapper threads from CPU blocker lists.
- Added final-leaf JSON schema and millisecond-delta tests.

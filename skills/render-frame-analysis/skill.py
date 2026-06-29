from __future__ import annotations

from app_entry_rca.core.helpers import dur, gap, state_for_slice, val
from app_entry_rca.core.models import SkillFinding


def _contained_slices(trace, parent, pattern):
    if parent is None:
        return []
    return [
        item
        for item in trace.find_slices(pattern, tid=parent.tid, start=parent.ts, end=parent.end)
        if item.ts >= parent.ts and item.end <= parent.end and item is not parent
    ]


def _max_ms(items):
    return max((item.dur_ms for item in items), default=None)


def _sum_ms(items):
    return sum(item.dur_ms for item in items) if items else None


def run(state, config):
    for label, context in state.contexts.items():
        markers = context.marker_slices
        trace = state.traces[label]
        traversal = markers.get("traversal")
        draw = markers.get("draw_frames")
        vulkan = markers.get("vulkan_finish")
        texture = markers.get("texture_upload")
        gpu_wait = markers.get("gpu_wait")
        finish = markers.get("finish_drawing")
        idle = markers.get("activity_idle_server") or markers.get("activity_idle")
        idle_client = markers.get("activity_idle_client")

        traversal_state = state_for_slice(trace, traversal)
        draw_state = state_for_slice(trace, draw)
        vulkan_state = state_for_slice(trace, vulkan)
        idle_state = state_for_slice(trace, idle)
        idle_monitor_contention = _contained_slices(trace, idle, r"monitor contention")

        # Keep RecyclerView layout separate from the parent traversal. The max
        # metric is the primary paired metric because summing repeated nested
        # slices can double count parent/child or retry spans.
        rv_layout_slices = _contained_slices(
            trace,
            traversal,
            r"^RV OnLayout$|RecyclerView.*(?:onLayout|OnLayout)|(?:onLayout|OnLayout).*RecyclerView",
        )
        generic_layout_slices = _contained_slices(
            trace,
            traversal,
            r"^performLayout$|(?:^|[ .:#])onLayout(?:$|[ (])",
        )
        rv_layout_max = _max_ms(rv_layout_slices)
        rv_layout_total = _sum_ms(rv_layout_slices)
        layout_max = _max_ms(generic_layout_slices)

        state.metrics[label].update(
            {
                "traversal_ms": dur(traversal),
                "traversal_running_ms": val(traversal_state, "Running"),
                "traversal_runnable_ms": val(traversal_state, "Runnable"),
                "measure_ms": dur(markers.get("measure")),
                "recycler_onlayout_max_ms": rv_layout_max,
                "recycler_onlayout_total_ms": rv_layout_total,
                "generic_onlayout_max_ms": layout_max,
                "draw_frames_ms": dur(draw),
                "draw_frames_running_ms": val(draw_state, "Running"),
                "draw_frames_runnable_ms": val(draw_state, "Runnable"),
                "vulkan_finish_ms": dur(vulkan),
                "vulkan_running_ms": val(vulkan_state, "Running"),
                "vulkan_runnable_ms": val(vulkan_state, "Runnable"),
                "texture_upload_ms": dur(texture),
                "gpu_wait_ms": dur(gpu_wait),
                "preinit_allocator_ms": dur(markers.get("preinit_allocator")),
                "allocate_buffers_ms": dur(markers.get("allocate_buffers")),
                "dequeue_buffer_ms": dur(markers.get("dequeue_buffer")),
                "traversal_to_draw_start_ms": gap(traversal, draw, use_a_end=False),
                "draw_to_finish_drawing_ms": gap(draw, finish, use_a_end=True),
                # Canonical P7 endpoint: end of system_server
                # IActivityClientController::activityIdle::server.
                "first_frame_to_idle_ms": (
                    (idle.end - (finish or draw).end) * 1000.0
                    if idle and (finish or draw) else None
                ),
                "p7_to_activity_idle_server_ms": (
                    (idle.end - (finish or draw).end) * 1000.0
                    if idle and (finish or draw) else None
                ),
                "activity_idle_server_ms": dur(idle),
                "activity_idle_server_running_ms": val(idle_state, "Running"),
                "activity_idle_server_runnable_ms": val(idle_state, "Runnable"),
                "activity_idle_server_sleeping_ms": val(idle_state, "Sleeping"),
                "activity_idle_server_d_ms": val(idle_state, "D"),
                "activity_idle_server_monitor_contention_ms": (
                    _sum_ms(idle_monitor_contention) or 0.0 if idle else None
                ),
                "activity_idle_client_to_server_ms": (
                    (idle.ts - idle_client.ts) * 1000.0 if idle and idle_client else None
                ),
                "frame_endpoint_semantics": context.endpoint_semantics,
                "p7_endpoint_semantics": (
                    "IActivityClientController::activityIdle::server_end"
                    if markers.get("activity_idle_server_aidl")
                    else ("legacy_system_server_activityIdle_end" if idle else "unavailable")
                ),
            }
        )
        if draw:
            evidence = [item.name for item in (traversal, draw, vulkan, texture, gpu_wait, finish) if item]
            if rv_layout_slices:
                evidence.append(f"longest RV OnLayout={rv_layout_max:.3f}ms")
            state.add_finding(
                SkillFinding(
                    finding_id=f"{label}-FRAME-SUMMARY",
                    skill="render-frame-analysis",
                    trace_label=label,
                    title="First-frame render summary",
                    category="render",
                    severity="INFO",
                    confidence="HIGH" if finish else "MEDIUM",
                    value={
                        "traversal_ms": dur(traversal),
                        "recycler_onlayout_max_ms": rv_layout_max,
                        "draw_frames_ms": dur(draw),
                        "vulkan_ms": dur(vulkan),
                        "texture_ms": dur(texture),
                        "gpu_wait_ms": dur(gpu_wait),
                    },
                    evidence=evidence,
                    notes=f"Presentation proxy={context.endpoint_semantics}; true display-present timestamps require FrameTimeline/SurfaceFlinger SQL data.",
                )
            )

        if idle:
            idle_evidence = [idle.name]
            idle_evidence.extend(item.name for item in idle_monitor_contention)
            state.add_finding(
                SkillFinding(
                    finding_id=f"{label}-P7-ACTIVITY-IDLE-SERVER",
                    skill="render-frame-analysis",
                    trace_label=label,
                    title="P7 completion at system_server activityIdle",
                    category="post_frame_completion",
                    severity="WARNING" if idle.dur_ms >= 5.0 else "INFO",
                    confidence="HIGH" if markers.get("activity_idle_server_aidl") else "MEDIUM",
                    phase="P7",
                    group="p7.activityidle.activityidle_client_or_server_reporting_and_system_server_handling",
                    metric_name="activity_idle_server_ms",
                    value={
                        "server_duration_ms": idle.dur_ms,
                        "server_running_ms": val(idle_state, "Running"),
                        "server_runnable_ms": val(idle_state, "Runnable"),
                        "server_sleeping_ms": val(idle_state, "Sleeping"),
                        "server_d_ms": val(idle_state, "D"),
                        "monitor_contention_ms": _sum_ms(idle_monitor_contention) or 0.0,
                    },
                    evidence=idle_evidence,
                    notes="P7 ends at the end of the system_server activityIdle AIDL server slice.",
                    evidence_level="DIRECT",
                    root_cause_key="p7:activity_idle_server_handling",
                    contribution_ms=idle.dur_ms,
                )
            )

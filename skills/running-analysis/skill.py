from app_entry_rca.core.helpers import critical_slices, state_breakdown_for_markers, val
from app_entry_rca.core.models import SkillFinding


def run(state, config):
    for label, context in state.contexts.items():
        trace = state.traces[label]
        markers = context.marker_slices
        p1_start = markers.get("input_delivery") or markers.get("active_launch")
        p1_end = markers.get("do_active_launch") or markers.get("start_activity_server")
        p1_states = (
            trace.state_ms(context.launcher_pid, p1_start.ts, p1_end.ts)
            if p1_start and p1_end and context.launcher_pid > 0
            else {}
        )
        breakdown = state_breakdown_for_markers(trace, context)
        metrics = {
            "critical_thread_state_ms": breakdown,
            "p1_running_ms": val(p1_states, "Running"),
        }
        aliases = {
            "start_activity_server_running_ms": "start_activity_server",
            "attach_running_ms": "attach_server",
            "activity_thread_main_running_ms": "activity_thread_main",
            "bind_running_ms": "bind_application",
            "activity_start_running_ms": "activity_start",
            "activity_resume_running_ms": "activity_resume",
            "traversal_running_ms": "traversal",
            "draw_frames_running_ms": "draw_frames",
            "vulkan_running_ms": "vulkan_finish",
        }
        for metric, marker in aliases.items():
            metrics[metric] = val(breakdown.get(marker, {}), "Running")

        # Preserve full state decomposition for parent launch windows. These
        # metrics are reported as nested evidence and must not be summed with
        # the parent duration because they partition/overlap the same window.
        state_aliases = {
            "start_activity_server": "start_activity_server",
            "bind_application": "bind_application",
            "activity_start": "activity_start",
            "activity_resume": "activity_resume",
            "traversal": "traversal",
            "draw_frames": "draw_frames",
            "vulkan": "vulkan_finish",
        }
        for prefix, marker in state_aliases.items():
            values = breakdown.get(marker, {})
            metrics[f"{prefix}_d_ms"] = val(values, "D")
            metrics[f"{prefix}_sleeping_ms"] = val(values, "Sleeping")
        state.metrics[label].update(metrics)

        longest = sorted(
            ((name, val(values, "Running")) for name, values in breakdown.items()),
            key=lambda item: item[1],
            reverse=True,
        )[:5]
        state.add_finding(
            SkillFinding(
                finding_id=f"{label}-RUNNING-SUMMARY",
                skill="running-analysis",
                trace_label=label,
                title="Critical-thread CPU execution summary",
                category="running",
                severity="INFO",
                confidence="HIGH" if context.observability.get("sched") else "LOW",
                value=dict(longest),
                evidence=[f"{name}: Running={value:.3f}ms" for name, value in longest],
            )
        )

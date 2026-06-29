from __future__ import annotations

from app_entry_rca.core.helpers import state_breakdown_for_markers, val
from app_entry_rca.core.intervals import critical_runnable_intervals, running_blocker_edges
from app_entry_rca.core.models import SkillFinding


def run(state, config):
    configured_cpus = tuple(int(x) for x in config.get("performance_cpus", config.get("big_cpus", [])))
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
            "p1_runnable_ms": val(p1_states, "Runnable"),
            "critical_runnable_ms": {name: val(values, "Runnable") for name, values in breakdown.items()},
        }
        aliases = {
            "start_activity_server_runnable_ms": "start_activity_server",
            "attach_runnable_ms": "attach_server",
            "activity_thread_main_runnable_ms": "activity_thread_main",
            "bind_runnable_ms": "bind_application",
            "activity_start_runnable_ms": "activity_start",
            "activity_resume_runnable_ms": "activity_resume",
            "traversal_runnable_ms": "traversal",
            "draw_frames_runnable_ms": "draw_frames",
            "vulkan_runnable_ms": "vulkan_finish",
        }
        for metric, marker in aliases.items():
            metrics[metric] = val(breakdown.get(marker, {}), "Runnable")

        runnable_by_marker = critical_runnable_intervals(trace, context)
        all_edges = []
        for victim, intervals in runnable_by_marker.items():
            item = markers.get(victim)
            if not item or not intervals:
                continue
            all_edges.extend(running_blocker_edges(trace, intervals, victim=victim, exclude_tids=[item.tid]))
        all_edges.sort(key=lambda edge: edge["overlap_ms"], reverse=True)
        state.interference_edges.extend({"trace": label, **edge} for edge in all_edges)
        metrics["critical_runnable_blockers"] = all_edges[:100]
        metrics["critical_runnable_blocker_overlap_ms"] = sum(edge["overlap_ms"] for edge in all_edges)

        draw = markers.get("draw_frames")
        render_intervals = trace.intervals(draw.tid, "Runnable", draw.ts, draw.end) if draw else []
        render_running = trace.intervals(draw.tid, "Running", draw.ts, draw.end) if draw else []
        inferred_cpus = tuple(sorted({item.cpu for item in render_running if item.cpu is not None}))
        cpus = configured_cpus or inferred_cpus
        occupants = trace.running_occupants(render_intervals, cpus=cpus, exclude_tids=[context.render_tid]) if render_intervals else {}
        metrics["render_runnable_occupants_ms"] = dict(sorted(occupants.items(), key=lambda item: item[1], reverse=True))
        metrics["runnable_analysis_cpus"] = list(cpus)
        state.metrics[label].update(metrics)

        top = sorted(metrics["critical_runnable_ms"].items(), key=lambda item: item[1], reverse=True)[:5]
        evidence = [f"{name}: Runnable={value:.3f}ms" for name, value in top]
        evidence.extend(
            f"{edge['victim']} <- {edge['blocker_comm']}: {edge['overlap_ms']:.3f}ms"
            for edge in all_edges[:5]
        )
        state.add_finding(
            SkillFinding(
                finding_id=f"{label}-RUNNABLE-SUMMARY",
                skill="runnable-analysis",
                trace_label=label,
                title="Critical-thread scheduling-delay and blocker summary",
                category="runnable",
                severity="WARNING" if all_edges and all_edges[0]["overlap_ms"] >= 5 else "INFO",
                confidence="HIGH" if context.observability.get("sched") else "LOW",
                value={"top_runnable": dict(top), "top_blockers": all_edges[:10]},
                evidence=evidence,
                notes="A blocker is reported only for exact Running-vs-Runnable interval overlap; total CPU usage alone is non-causal.",
                evidence_level="DIRECT" if all_edges else "NONE",
            )
        )

from __future__ import annotations

import re

from app_entry_rca.core.config import load_json, load_yaml
from app_entry_rca.core.helpers import analysis_window, dur, gap, state_for_slice, val
from app_entry_rca.core.canonical import phase_name as canonical_phase_name, P8_NOTE
from app_entry_rca.workflow.router import select_analyzers


def _segment(start_s, end_s, *, name=None):
    if start_s is None or end_s is None or end_s < start_s:
        return None
    item = {"start_s": start_s, "end_s": end_s, "duration_ms": (end_s - start_s) * 1000.0}
    if name:
        item["name"] = name
    return item


def _window(start_slice, end_slice, *, start_at_end=False, end_at_start=False):
    if not start_slice or not end_slice:
        return None
    start = start_slice.end if start_at_end else start_slice.ts
    end = end_slice.ts if end_at_start else end_slice.end
    return _segment(start, end)


def _union_duration_ms(segments):
    ranges = sorted((item["start_s"], item["end_s"]) for item in segments)
    if not ranges:
        return 0.0
    merged = [list(ranges[0])]
    for start, end in ranges[1:]:
        if start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return sum((end - start) * 1000.0 for start, end in merged)


def _p2(ctx, markers):
    """Canonical P2 Launch Preparation.

    Cold: union of P2-1 system_server + launcher workflow and P2-2 target app process launch.
    Warm: system_server + launcher workflow only.
    """
    segments = []
    start_server = markers.get("start_activity_server")
    if start_server:
        item = _segment(start_server.ts, start_server.end, name="P2-1 system_server + launcher workflow")
        if item:
            segments.append(item)

    if ctx.launch_type == "cold":
        request = markers.get("process_request")
        activity_thread = markers.get("activity_thread_main")
        start_proc = markers.get("start_proc")
        if request and activity_thread:
            item = _segment(request.ts, activity_thread.end, name="P2-2 target app process launch")
            if item:
                segments.append(item)
        elif request and start_proc:
            item = _segment(request.ts, start_proc.end, name="P2-2 target app process launch")
            if item:
                segments.append(item)

    segments = [item for item in segments if item]
    if not segments:
        return None
    return {
        "name": "Launch Preparation",
        "segments": segments,
        "functional_sum_ms": sum(item["duration_ms"] for item in segments),
        "wall_union_ms": _union_duration_ms(segments),
        "duration_ms": _union_duration_ms(segments),
        "start_s": min(item["start_s"] for item in segments),
        "end_s": max(item["end_s"] for item in segments),
        "overlap_possible": ctx.launch_type == "cold",
        "duration_semantics": "union of canonical P2 branches; cold P2-1/P2-2 may overlap",
    }

def _candidate_groups(project_root, active_phases, contexts):
    activation = load_yaml(project_root / "taxonomy" / "group_activation.yaml").get("groups", {})
    groups = []
    all_caps = {name for context in contexts.values() for name, value in context.observability.items() if value}
    all_markers = {name for context in contexts.values() for name, item in context.marker_slices.items() if item}
    launch_types = {context.launch_type for context in contexts.values()}
    for group, rule in activation.items():
        phase = rule.get("phase")
        if phase not in active_phases:
            continue
        allowed = set(rule.get("launch_types", []))
        if allowed and not (allowed & launch_types):
            continue
        marker_req = set(rule.get("requires_any_markers", []))
        cap_req = set(rule.get("requires_any_capabilities", []))
        if rule.get("always_if_phase"):
            groups.append(group); continue
        marker_ok = bool(marker_req & all_markers) if marker_req else False
        cap_ok = bool(cap_req & all_caps) if cap_req else False
        if marker_ok or cap_ok:
            groups.append(group)
    return groups


def run(state, config):
    phase_data = {}
    for label, context in state.contexts.items():
        markers = context.marker_slices
        window_start, window_end = analysis_window(context)

        first_frame_start = markers.get("choreographer_doframe") or markers.get("traversal") or markers.get("draw_frames")
        first_frame_end = markers.get("finish_drawing") or markers.get("draw_frames") or markers.get("choreographer_doframe")
        idle_server = markers.get("activity_idle_server") or markers.get("activity_idle")

        if context.launch_type == "cold":
            phase = {
                "P1": _window(
                    markers.get("input_delivery") or markers.get("active_launch"),
                    markers.get("do_active_launch") or markers.get("start_activity_server"),
                    end_at_start=True,
                ),
                "P2": _p2(context, markers),
                "P3": _segment(markers["bind_application"].ts, markers["bind_application"].end, name="bindApplication")
                    if markers.get("bind_application") else None,
                "P4": _segment(markers["activity_start"].ts, markers["activity_start"].end, name="activityStart")
                    if markers.get("activity_start") else None,
                "P5": _segment(markers["activity_resume"].ts, markers["activity_resume"].end, name="activityResume")
                    if markers.get("activity_resume") else None,
                "P6": _segment(first_frame_start.ts, first_frame_end.end, name="first Choreographer#doFrame")
                    if first_frame_start and first_frame_end else None,
                "P7": _segment(first_frame_end.end, idle_server.end, name="activityIdle")
                    if first_frame_end and idle_server else None,
                "P8": {"name": "Cross-cutting System Evidence", "start_s": window_start, "end_s": window_end, "duration_ms": (window_end - window_start) * 1000.0, "note": P8_NOTE},
            }
        else:
            phase = {
                "P1": _window(
                    markers.get("input_delivery") or markers.get("active_launch"),
                    markers.get("do_active_launch") or markers.get("start_activity_server"),
                    end_at_start=True,
                ),
                "P2": _p2(context, markers),
                "P3": _segment(markers["activity_start"].ts, markers["activity_start"].end, name="activityStart")
                    if markers.get("activity_start") else None,
                "P4": _segment(markers["activity_resume"].ts, markers["activity_resume"].end, name="activityResume")
                    if markers.get("activity_resume") else None,
                "P5": _segment(first_frame_start.ts, first_frame_end.end, name="first Choreographer#doFrame")
                    if first_frame_start and first_frame_end else None,
                "P6": _segment(idle_server.ts, idle_server.end, name="activityIdle")
                    if idle_server else None,
                "P7": None,
                "P8": {"name": "Cross-cutting System Evidence", "start_s": window_start, "end_s": window_end, "duration_ms": (window_end - window_start) * 1000.0, "note": P8_NOTE},
            }
        for phase_id, item in phase.items():
            if item is not None:
                item.setdefault("phase_name", canonical_phase_name(phase_id, context.launch_type))
                item.setdefault("role", "cross-cutting" if phase_id == "P8" else "canonical_timeline_phase")
        phase_data[label] = phase

        input_slice = markers.get("input_delivery")
        event_latency = None
        if input_slice:
            match = re.search(r"eventTimeNano=(\d+)", input_slice.name)
            if match:
                event_latency = (input_slice.ts - int(match.group(1)) / 1e9) * 1000.0

        idle_server = markers.get("activity_idle_server") or markers.get("activity_idle")
        idle_client = markers.get("activity_idle_client")
        first_frame_completion = markers.get("finish_drawing") or markers.get("draw_frames")
        idle_server_states = state_for_slice(state.traces[label], idle_server)

        state.metrics[label].update(
            {
                "window_start_s": window_start,
                "window_end_s": window_end,
                "launch_window_ms": (window_end - window_start) * 1000.0,
                "p1_event_latency_ms": event_latency,
                "p1_total_ms": phase["P1"]["duration_ms"] if phase.get("P1") else None,
                "p2_wall_union_ms": phase["P2"]["wall_union_ms"] if phase.get("P2") else None,
                "p2_functional_sum_ms": phase["P2"]["functional_sum_ms"] if phase.get("P2") else None,
                "p3_wall_ms": phase["P3"]["duration_ms"] if phase.get("P3") else None,
                "phase_P1_ms": phase["P1"]["duration_ms"] if phase.get("P1") else None,
                "phase_P2_ms": phase["P2"]["duration_ms"] if phase.get("P2") else None,
                "phase_P3_ms": phase["P3"]["duration_ms"] if phase.get("P3") else None,
                "phase_P4_ms": phase["P4"]["duration_ms"] if phase.get("P4") else None,
                "phase_P5_ms": phase["P5"]["duration_ms"] if phase.get("P5") else None,
                "phase_P6_ms": phase["P6"]["duration_ms"] if phase.get("P6") else None,
                "phase_P7_ms": phase["P7"]["duration_ms"] if phase.get("P7") else None,
                "launching_activity_ms": dur(markers.get("launching_activity")),
                "active_launch_ms": dur(markers.get("active_launch")),
                "do_active_launch_ms": dur(markers.get("do_active_launch")),
                "start_activity_server_ms": dur(markers.get("start_activity_server")),
                "start_activity_inner_ms": dur(markers.get("start_activity_inner")),
                "process_request_to_start_proc_ms": gap(markers.get("process_request"), markers.get("start_proc")),
                "process_request_to_bind_ms": gap(markers.get("process_request"), markers.get("bind_application")),
                "attach_server_ms": dur(markers.get("attach_server")),
                "finish_attach_server_ms": dur(markers.get("finish_attach_server")),
                "attach_orchestration_total_ms": sum(
                    value for value in (dur(markers.get("attach_server")), dur(markers.get("finish_attach_server"))) if value is not None
                ) if markers.get("attach_server") or markers.get("finish_attach_server") else None,
                "prebind_contention_ms": dur(markers.get("prebind_contention")),
                "activity_thread_main_ms": dur(markers.get("activity_thread_main")),
                "bind_application_ms": dur(markers.get("bind_application")),
                "activity_start_ms": dur(markers.get("activity_start")),
                "activity_start_gate_gap_ms": (
                    (markers["activity_start"].ts - max(
                        *(x for x in [
                            markers.get("start_activity_server").end if markers.get("start_activity_server") else None,
                            markers.get("bind_application").end if markers.get("bind_application") else None,
                        ] if x is not None)
                    )) * 1000.0
                    if context.launch_type == "cold" and markers.get("activity_start") and (markers.get("start_activity_server") or markers.get("bind_application"))
                    else (
                        (markers["activity_start"].ts - markers["start_activity_server"].end) * 1000.0
                        if context.launch_type != "cold" and markers.get("activity_start") and markers.get("start_activity_server")
                        else None
                    )
                ),
                "activity_start_gate_blocker": (
                    "P3 bindApplication"
                    if context.launch_type == "cold" and markers.get("bind_application") and (not markers.get("start_activity_server") or markers["bind_application"].end >= markers["start_activity_server"].end)
                    else ("P2-1 system_server + launcher workflow" if context.launch_type == "cold" and markers.get("start_activity_server") else ("P2 Launch Preparation" if context.launch_type != "cold" else None))
                ),
                "perform_create_ms": dur(markers.get("perform_create")),
                "activity_resume_ms": dur(markers.get("activity_resume")),
                "perform_resume_ms": dur(markers.get("perform_resume")),
                "finish_drawing_ms": dur(markers.get("finish_drawing")),
                "activity_idle_ms": dur(idle_server),  # backward-compatible alias
                "activity_idle_server_ms": dur(idle_server),
                "activity_idle_server_running_ms": val(idle_server_states, "Running"),
                "activity_idle_server_runnable_ms": val(idle_server_states, "Runnable"),
                "activity_idle_server_sleeping_ms": val(idle_server_states, "Sleeping"),
                "activity_idle_server_d_ms": val(idle_server_states, "D"),
                "activity_idle_client_ms": dur(idle_client),
                "activity_idle_client_to_server_ms": (
                    (idle_server.ts - idle_client.ts) * 1000.0
                    if idle_client and idle_server else None
                ),
                "p7_to_activity_idle_server_start_ms": (
                    (idle_server.ts - first_frame_completion.end) * 1000.0
                    if first_frame_completion and idle_server else None
                ),
                "p7_to_activity_idle_server_ms": (
                    (idle_server.end - first_frame_completion.end) * 1000.0
                    if first_frame_completion and idle_server else None
                ),
                # User-visible endpoint uses the start of finishDrawing as a
                # deterministic proxy when FrameTimeline present data is absent.
                "input_to_first_frame_proxy_ms": (
                    (markers["finish_drawing"].ts - window_start) * 1000.0
                    if markers.get("finish_drawing") else None
                ),
                "input_to_activity_idle_ms": (
                    (idle_server.end - window_start) * 1000.0 if idle_server else None
                ),
                "input_to_activity_idle_server_ms": (
                    (idle_server.end - window_start) * 1000.0 if idle_server else None
                ),
                "activity_idle_endpoint_semantics": (
                    "IActivityClientController::activityIdle::server_end"
                    if markers.get("activity_idle_server_aidl")
                    else ("legacy_system_server_activityIdle_end" if idle_server else "unavailable")
                ),
                "first_frame_proxy_semantics": (
                    "finishDrawing_start" if markers.get("finish_drawing") else context.endpoint_semantics
                ),
            }
        )

    thresholds = load_yaml(state.project_root / "taxonomy" / "thresholds.yaml")
    activation_ms = float(config.get("activation_ms", thresholds.get("phase_activation_ms", 5.0)))
    comparison = {}
    active = []
    for phase_id in [f"P{i}" for i in range(1, 9)]:
        dut = phase_data["DUT"].get(phase_id)
        ref = phase_data["REF"].get(phase_id)
        dut_value = dut.get("duration_ms") if dut else None
        ref_value = ref.get("duration_ms") if ref else None
        delta = dut_value - ref_value if dut_value is not None and ref_value is not None else None
        comparison[phase_id] = {
            "dut": dut,
            "ref": ref,
            "delta_ms": delta,
            "phase_name": (dut or ref or {}).get("phase_name") if (dut or ref) else None,
            "role": "cross-cutting" if phase_id == "P8" else "canonical_timeline_phase",
            "activated": phase_id == "P8" or (delta is not None and abs(delta) > activation_ms),
        }
        if comparison[phase_id]["activated"]:
            active.append(phase_id)

    # Keep observed phases routable even when DUT and REF are equivalent. This is
    # required because the user wants BETTER/EQUIVALENT leaves, not only regressions.
    for phase_name in ("P1", "P2", "P3", "P4", "P5", "P6", "P7"):
        if phase_name not in active and (phase_data["DUT"].get(phase_name) or phase_data["REF"].get(phase_name)):
            active.append(phase_name)

    state.phase_comparison = comparison
    state.active_phases = active
    state.activated_groups = _candidate_groups(state.project_root, active, state.contexts)
    selected, reasons = select_analyzers(state)
    state.selected_skills = selected
    state.routing_reasons = reasons

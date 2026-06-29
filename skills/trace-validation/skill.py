from __future__ import annotations

from app_entry_rca.core.models import SkillFinding


def _structural_counts(trace):
    fn = getattr(trace, "summary_counts", None)
    if callable(fn):
        try:
            return fn()
        except Exception:
            return {}
    return {
        "slice_count": len(getattr(trace, "slices", [])),
        "thread_state_count": sum(len(v) for v in getattr(trace, "states", {}).values()),
        "event_count": len(getattr(trace, "events", [])),
    }


def run(state, config):
    dut = state.contexts["DUT"]
    ref = state.contexts["REF"]
    reasons: list[str] = []
    warnings: list[str] = []
    checks: dict = {}

    checks["same_target"] = dut.target_package == ref.target_package
    if not checks["same_target"]:
        reasons.append(f"Target mismatch DUT={dut.target_package}, REF={ref.target_package}")

    checks["same_launch_type"] = dut.launch_type == ref.launch_type
    if not checks["same_launch_type"]:
        reasons.append(f"Launch type mismatch DUT={dut.launch_type}, REF={ref.launch_type}")

    checks["same_endpoint_semantics"] = dut.endpoint_semantics == ref.endpoint_semantics
    if not checks["same_endpoint_semantics"]:
        warnings.append(
            f"Endpoint mismatch DUT={dut.endpoint_semantics}, REF={ref.endpoint_semantics}; P6/P7 deltas may not be comparable."
        )

    required_markers = {
        "P1": ["active_launch", "do_active_launch"],
        "P2": ["start_activity_server"],
        "P3": ["process_request", "bind_application"],
        "P4": ["activity_start", "activity_resume"],
        "P6": ["traversal", "draw_frames"],
    }
    marker_matrix = {}
    for label, context in state.contexts.items():
        marker_matrix[label] = {}
        for phase, names in required_markers.items():
            available = [name for name in names if context.marker_slices.get(name)]
            complete = len(available) == len(names)
            if phase == "P3" and context.launch_type != "cold":
                complete = True
            marker_matrix[label][phase] = {"required": names, "available": available, "complete": complete}
        warnings.extend(context.warnings)

    structural = {}
    for label, trace in state.traces.items():
        capabilities = state.capabilities.get(label, {})
        counts = _structural_counts(trace)
        structural[label] = counts
        if not capabilities.get("sched"):
            warnings.append(f"{label}: thread_state/sched data unavailable; Running/Runnable analysis is limited.")

        # Query-backed Perfetto traces intentionally do not materialize trace.slices.
        # Validate using database counts and resolved launch markers instead.
        slice_count = int(counts.get("slice_count", 0) or 0)
        has_launch_marker = any(state.contexts[label].marker_slices.values())
        if slice_count < 10 and not has_launch_marker:
            reasons.append(f"{label}: insufficient slices/launch markers for app-entry analysis.")
        elif slice_count < 10:
            warnings.append(f"{label}: very few slices were observed; leaf coverage will be limited.")

        for event in getattr(trace, "events", []):
            if "LOST EVENTS" in getattr(event, "details", "").upper():
                warnings.append(f"{label}: trace reports lost events.")
                break
        duration = state.metrics[label].get("trace_duration_s")
        if duration is not None and duration < 1.0:
            warnings.append(f"{label}: trace duration is only {duration:.3f}s; pre-launch P8 context is limited.")

    checks["structural_counts"] = structural
    checks["backend_pair"] = {
        label: getattr(trace, "backend_name", "unknown") for label, trace in state.traces.items()
    }
    if len(set(checks["backend_pair"].values())) > 1:
        warnings.append("DUT and REF were parsed by different backends; compare only shared observable leaves.")

    decision = "INVALID_COMPARISON" if reasons else ("PARTIALLY_COMPARABLE" if warnings else "VALID")
    score = max(0, 100 - 40 * len(reasons) - min(40, 5 * len(set(warnings))))
    state.validation = {
        "decision": decision,
        "comparability_score": score,
        "reasons": reasons,
        "warnings": list(dict.fromkeys(warnings)),
        "checks": checks,
        "marker_matrix": marker_matrix,
        "capabilities": state.capabilities,
    }

    for index, message in enumerate(reasons, 1):
        state.add_finding(
            SkillFinding(
                finding_id=f"PAIR-INVALID-{index}",
                skill="trace-validation",
                trace_label="PAIR",
                title="Invalid comparison",
                category="validation",
                severity="ERROR",
                confidence="HIGH",
                value=message,
                evidence=[message],
                evidence_level="DIRECT",
            )
        )
    if reasons and state.options.get("strict_validation"):
        raise ValueError("; ".join(reasons))

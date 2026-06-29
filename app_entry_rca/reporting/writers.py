from __future__ import annotations

import csv
import json
from pathlib import Path

import yaml

from app_entry_rca.core.contracts import validate_leaf_dict
from app_entry_rca.core.canonical import phase_name, P8_NOTE

SCHEMA_VERSION = "7.0"


def dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def _status_counts(items):
    counts = {}
    for item in items:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    return dict(sorted(counts.items()))


def _paired_metric(state, metric: str):
    dut = state.metrics["DUT"].get(metric)
    ref = state.metrics["REF"].get(metric)
    delta = float(dut) - float(ref) if isinstance(dut, (int, float)) and isinstance(ref, (int, float)) else None
    return {"metric": metric, "dut_ms": dut, "ref_ms": ref, "delta_ms": round(delta, 3) if delta is not None else None}


def _build_ms_diff_summary(state):
    endpoint = _paired_metric(state, "input_to_first_frame_proxy_ms")
    endpoint["semantics"] = state.metrics["DUT"].get("first_frame_proxy_semantics")

    completion_endpoint = _paired_metric(state, "input_to_activity_idle_server_ms")
    completion_endpoint["semantics"] = state.metrics["DUT"].get("activity_idle_endpoint_semantics")

    contributors = []

    io = _paired_metric(state, "critical_io_d_ms")
    if io["delta_ms"] is not None and io["delta_ms"] > 0.5:
        contributors.append({
            "id": "critical_file_page_io",
            "title": "Critical file/page I/O wait",
            "local_delta_ms": io["delta_ms"],
            "exclusive_contribution_ms": io["delta_ms"],
            "nested_deltas_ms": {
                key: value
                for key, value in {
                    "critical_d_total_ms": _paired_metric(state, "critical_d_total_ms")["delta_ms"],
                    "critical_direct_reclaim_ms": _paired_metric(state, "critical_direct_reclaim_ms")["delta_ms"],
                }.items() if value is not None
            },
            "overlap_group": "CROSS_PHASE_CRITICAL_IO",
            "additive": False,
        })

    traversal = _paired_metric(state, "traversal_ms")
    rv = _paired_metric(state, "recycler_onlayout_max_ms")
    if traversal["delta_ms"] is not None and traversal["delta_ms"] > 0.5:
        contributors.append({
            "id": "first_traversal_layout",
            "title": "First traversal / RecyclerView initial layout",
            "local_delta_ms": traversal["delta_ms"],
            "exclusive_contribution_ms": rv["delta_ms"] if rv["delta_ms"] is not None and rv["delta_ms"] > 0 else None,
            "nested_deltas_ms": {
                key: value
                for key, value in {
                    "recycler_onlayout_max_ms": rv["delta_ms"],
                    "traversal_running_ms": _paired_metric(state, "traversal_running_ms")["delta_ms"],
                    "traversal_runnable_ms": _paired_metric(state, "traversal_runnable_ms")["delta_ms"],
                }.items() if value is not None
            },
            "overlap_group": "P6_FIRST_TRAVERSAL",
            "additive": False,
        })

    draw = _paired_metric(state, "draw_frames_ms")
    if draw["delta_ms"] is not None and draw["delta_ms"] > 0.5:
        contributors.append({
            "id": "hwui_skia_cpu_render",
            "title": "HWUI/Skia CPU-side render work",
            "local_delta_ms": draw["delta_ms"],
            "exclusive_contribution_ms": None,
            "nested_deltas_ms": {
                key: value
                for key, value in {
                    "drawframes_running_ms": _paired_metric(state, "draw_frames_running_ms")["delta_ms"],
                    "drawframes_runnable_ms": _paired_metric(state, "draw_frames_runnable_ms")["delta_ms"],
                    "vulkan_finish_ms": _paired_metric(state, "vulkan_finish_ms")["delta_ms"],
                    "texture_upload_ms": _paired_metric(state, "texture_upload_ms")["delta_ms"],
                    "gpu_wait_ms": _paired_metric(state, "gpu_wait_ms")["delta_ms"],
                }.items() if value is not None
            },
            "overlap_group": "P6_RENDERTHREAD_FIRST_FRAME",
            "additive": False,
        })

    art = _paired_metric(state, "open_dex_oat_ms")
    if art["delta_ms"] is not None and art["delta_ms"] > 0.5:
        contributors.append({
            "id": "art_appimage_oat_preparation",
            "title": "ART AppImage/OAT preparation",
            "local_delta_ms": art["delta_ms"],
            "exclusive_contribution_ms": art["delta_ms"],
            "nested_deltas_ms": {
                key: value
                for key, value in {
                    "artifact_status_ms": _paired_metric(state, "artifact_status_ms")["delta_ms"],
                    "bind_application_parent_ms": _paired_metric(state, "bind_application_ms")["delta_ms"],
                    "bind_application_d_state_ms": _paired_metric(state, "bind_application_d_ms")["delta_ms"],
                }.items() if value is not None
            },
            "overlap_group": "P3_BIND_APPLICATION",
            "additive": False,
        })

    start_activity = _paired_metric(state, "start_activity_server_ms")
    if start_activity["delta_ms"] is not None and start_activity["delta_ms"] > 0.5:
        contributors.append({
            "id": "system_server_start_activity",
            "title": "system_server startActivity orchestration",
            "local_delta_ms": start_activity["delta_ms"],
            "exclusive_contribution_ms": _paired_metric(state, "p2_outer_exclusive_ms")["delta_ms"],
            "nested_deltas_ms": {
                key: value
                for key, value in {
                    "outer_exclusive_ms": _paired_metric(state, "p2_outer_exclusive_ms")["delta_ms"],
                    "running_ms": _paired_metric(state, "start_activity_server_running_ms")["delta_ms"],
                    "runnable_ms": _paired_metric(state, "start_activity_server_runnable_ms")["delta_ms"],
                    "d_state_ms": _paired_metric(state, "start_activity_server_d_ms")["delta_ms"],
                    "sleeping_ms": _paired_metric(state, "start_activity_server_sleeping_ms")["delta_ms"],
                }.items() if value is not None
            },
            "overlap_group": "P2_START_ACTIVITY",
            "additive": False,
        })

    p7 = _paired_metric(state, "p7_to_activity_idle_server_ms")
    if p7["delta_ms"] is not None and abs(p7["delta_ms"]) > 0.5:
        contributors.append({
            "id": "p7_to_system_server_activity_idle",
            "title": "P7 tail to system_server activityIdle",
            "local_delta_ms": p7["delta_ms"],
            "exclusive_contribution_ms": None,
            "nested_deltas_ms": {
                key: value
                for key, value in {
                    "server_handler_ms": _paired_metric(state, "activity_idle_server_ms")["delta_ms"],
                    "server_running_ms": _paired_metric(state, "activity_idle_server_running_ms")["delta_ms"],
                    "server_runnable_ms": _paired_metric(state, "activity_idle_server_runnable_ms")["delta_ms"],
                    "server_sleeping_ms": _paired_metric(state, "activity_idle_server_sleeping_ms")["delta_ms"],
                    "server_d_state_ms": _paired_metric(state, "activity_idle_server_d_ms")["delta_ms"],
                    "server_monitor_contention_ms": _paired_metric(state, "activity_idle_server_monitor_contention_ms")["delta_ms"],
                    "client_to_server_ms": _paired_metric(state, "activity_idle_client_to_server_ms")["delta_ms"],
                }.items() if value is not None
            },
            "overlap_group": "P7_TO_SYSTEM_SERVER_ACTIVITY_IDLE",
            "additive": False,
        })

    return {
        "schema_version": SCHEMA_VERSION,
        "endpoint": endpoint,
        "completion_endpoint": completion_endpoint,
        "contributors": contributors,
        "guardrail": "All contributor deltas are local/inclusive or nested measurements. They overlap and must not be summed to reproduce the endpoint delta.",
    }



def _slice_to_dict(item):
    if item is None:
        return None
    return {
        "name": item.name,
        "start_s": item.ts,
        "end_s": item.end,
        "duration_ms": item.dur_ms,
        "tid": item.tid,
        "tgid": item.tgid,
        "comm": item.comm,
        "cpu": item.cpu,
    }


def _build_raw_phase_intervals(state):
    rows = []
    for label in ("DUT", "REF"):
        ctx = state.contexts[label]
        for phase_id, item in state.phase_comparison.items():
            phase_item = item.get(label.lower())
            if not phase_item:
                continue
            base = {
                "trace": label,
                "entry_type": ctx.launch_type,
                "phase": phase_id,
                "phase_name": phase_item.get("phase_name") or phase_name(phase_id, ctx.launch_type),
                "role": phase_item.get("role", "canonical_timeline_phase"),
                "start_s": phase_item.get("start_s"),
                "end_s": phase_item.get("end_s"),
                "duration_ms": phase_item.get("duration_ms"),
                "duration_semantics": phase_item.get("duration_semantics"),
            }
            rows.append(base)
            for segment in phase_item.get("segments", []) or []:
                rows.append({
                    **base,
                    "leaf": segment.get("name"),
                    "start_s": segment.get("start_s"),
                    "end_s": segment.get("end_s"),
                    "duration_ms": segment.get("duration_ms"),
                    "role": "phase_branch_or_leaf_interval",
                })
    return {"schema_version": SCHEMA_VERSION, "rows": rows, "p8_note": P8_NOTE}


def _build_raw_marker_slices(state):
    out = {}
    for label, ctx in state.contexts.items():
        out[label] = {
            "entry_type": ctx.launch_type,
            "target_package": ctx.target_package,
            "markers": {name: _slice_to_dict(item) for name, item in ctx.marker_slices.items()},
        }
    return {"schema_version": SCHEMA_VERSION, **out}


def _build_critical_path(state):
    out = {"schema_version": SCHEMA_VERSION, "DUT": {}, "REF": {}, "delta": {}}
    for label in ("DUT", "REF"):
        ctx = state.contexts[label]
        metrics = state.metrics[label]
        if ctx.launch_type == "cold":
            out[label] = {
                "entry_type": "cold",
                "rule": "activityStart gate = max(P2-1 end, P3 bindApplication end)",
                "blocker": metrics.get("activity_start_gate_blocker"),
                "handoff_gap_ms": metrics.get("activity_start_gate_gap_ms"),
                "phase_P2_ms": metrics.get("phase_P2_ms"),
                "phase_P3_ms": metrics.get("phase_P3_ms"),
            }
        else:
            out[label] = {
                "entry_type": ctx.launch_type,
                "rule": "activityStart gate = P2 Launch Preparation end",
                "blocker": metrics.get("activity_start_gate_blocker"),
                "handoff_gap_ms": metrics.get("activity_start_gate_gap_ms"),
                "phase_P2_ms": metrics.get("phase_P2_ms"),
            }
    for key in ("handoff_gap_ms", "phase_P2_ms", "phase_P3_ms"):
        d = out["DUT"].get(key)
        r = out["REF"].get(key)
        out["delta"][key] = round(d - r, 3) if isinstance(d, (int, float)) and isinstance(r, (int, float)) else None
    return out

def write_all(state, out_dir: str):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    leaves = [item.to_dict() for item in state.leaves]
    finals = [item.to_dict() for item in state.final_leaves]
    findings = [item.to_dict() for item in state.skill_findings]
    for leaf in leaves:
        validate_leaf_dict(leaf)

    numeric_delta = {}
    for key, dut_value in state.metrics["DUT"].items():
        ref_value = state.metrics["REF"].get(key)
        if isinstance(dut_value, (int, float)) and isinstance(ref_value, (int, float)):
            numeric_delta[key] = dut_value - ref_value

    ms_diff_summary = _build_ms_diff_summary(state)
    regression_finals = [item for item in finals if item["status"] in {"DUT_REGRESSION", "DUT_ONLY"}]
    primary = regression_finals[0] if regression_finals else None
    summary = {
        "schema_version": SCHEMA_VERSION,
        "workflow_version": state.provenance.get("workflow_version"),
        "target": state.contexts["DUT"].target_package,
        "validation": state.validation.get("decision"),
        "comparability_score": state.validation.get("comparability_score"),
        "launch_type": {label: context.launch_type for label, context in state.contexts.items()},
        "backend": {label: state.metrics[label].get("trace_backend") for label in ("DUT", "REF")},
        "active_phases": state.active_phases,
        "activated_groups": state.activated_groups,
        "selected_skills": state.selected_skills,
        "leaf_count": len(leaves),
        "leaf_status_counts": _status_counts(leaves),
        "final_leaf_count": len(finals),
        "regression_final_leaf_count": len(regression_finals),
        "primary_final_leaf_id": primary["id"] if primary else None,
        "first_frame_proxy_delta_ms": ms_diff_summary["endpoint"].get("delta_ms"),
        "first_frame_proxy_semantics": ms_diff_summary["endpoint"].get("semantics"),
        "activity_idle_server_delta_ms": ms_diff_summary["completion_endpoint"].get("delta_ms"),
        "activity_idle_server_semantics": ms_diff_summary["completion_endpoint"].get("semantics"),
        "guardrail": "Correlation-only leaves are excluded from final RCA candidates unless explicitly requested.",
        "p8_semantics": P8_NOTE,
    }

    dump(out / "analysis_summary.json", summary)
    dump(out / "provenance.json", {"schema_version": SCHEMA_VERSION, **state.provenance})
    dump(out / "validation.json", state.validation)
    dump(out / "launch_context.json", state.context_summary())
    dump(out / "phase_comparison.json", state.phase_comparison)
    dump(out / "raw_phase_intervals.json", _build_raw_phase_intervals(state))
    dump(out / "raw_marker_slices.json", _build_raw_marker_slices(state))
    dump(out / "critical_path.json", _build_critical_path(state))
    dump(out / "routing.json", {
        "active_phases": state.active_phases,
        "activated_groups": state.activated_groups,
        "selected_skills": state.selected_skills,
        "routing_reasons": state.routing_reasons,
    })
    dump(out / "observability.json", {
        "capabilities": state.capabilities,
        "contexts": {label: context.observability for label, context in state.contexts.items()},
    })
    dump(out / "skill_runs.json", {
        "selected_skills": state.selected_skills,
        "routing_reasons": state.routing_reasons,
        "runs": [item.to_dict() for item in state.skill_runs],
    })
    dump(out / "skill_findings.json", {"schema_version": SCHEMA_VERSION, "count": len(findings), "findings": findings})
    dump(out / "dependency_graph.json", state.dependency_graph)
    dump(out / "interference_edges.json", {"count": len(state.interference_edges), "edges": state.interference_edges})
    dump(out / "raw_metrics.json", {"schema_version": SCHEMA_VERSION, "DUT": state.metrics["DUT"], "REF": state.metrics["REF"], "delta": numeric_delta})
    dump(out / "cpu_core_frequency.json", {
        "schema_version": SCHEMA_VERSION,
        "DUT": state.metrics["DUT"].get("cpu_core_frequency"),
        "REF": state.metrics["REF"].get("cpu_core_frequency"),
        "delta": state.metrics["DUT"].get("cpu_core_frequency_delta_vs_ref", {}),
        "note": "Frequency is computed only over Running intervals; missing counters are NOT_OBSERVABLE, not equal.",
    })
    dump(out / "ms_diff_summary.json", ms_diff_summary)
    dump(out / "all_leaf_nodes.json", {"schema_version": SCHEMA_VERSION, "leaf_count": len(leaves), "leaves": leaves})

    columns = [
        "leaf_id", "leaf_name", "phase", "phase_name", "group", "group_name",
        "status", "causality", "confidence", "evidence_level", "observability",
        "rule_id", "root_cause_key", "metric_name", "metric_unit", "dut_value", "ref_value",
        "delta_value", "threshold_value", "contribution_ms", "interpretation", "taxonomy_action",
        "evidence", "required_evidence", "missing_evidence", "contradictions", "notes",
    ]
    with (out / "all_leaf_nodes.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for item in leaves:
            row = {key: item.get(key) for key in columns}
            for key in ("evidence", "required_evidence", "missing_evidence", "contradictions"):
                row[key] = " | ".join(str(value) for value in item.get(key, []))
            writer.writerow(row)

    dump(out / "final_leaves.json", {"schema_version": SCHEMA_VERSION, "count": len(finals), "final_leaves": finals})
    dump(out / "final_leaf.json", primary)
    dump(out / "evidence_graph.json", state.evidence_graph)
    changes = yaml.safe_load((state.project_root / "taxonomy" / "taxonomy_changes.yaml").read_text(encoding="utf-8"))
    dump(out / "taxonomy_changes.json", changes)

    rule_doc = yaml.safe_load((state.project_root / "taxonomy" / "leaf_rules.yaml").read_text(encoding="utf-8")) or {}
    automated_ids = {item["leaf"] for item in rule_doc.get("rules", [])}
    registry_ids = {item["leaf_id"] for item in leaves}
    by_phase = {}
    for phase in [f"P{i}" for i in range(1, 9)]:
        phase_ids = {item["leaf_id"] for item in leaves if item["phase"] == phase}
        phase_automated = phase_ids & automated_ids
        by_phase[phase] = {
            "total": len(phase_ids),
            "automated_rules": len(phase_automated),
            "instrumentation_or_future_rules": len(phase_ids - automated_ids),
            "coverage_percent": round(100.0 * len(phase_automated) / len(phase_ids), 2) if phase_ids else 0.0,
        }
    coverage = {
        "schema_version": SCHEMA_VERSION,
        "total_leaves": len(registry_ids),
        "automated_rule_leaves": len(registry_ids & automated_ids),
        "instrumentation_or_future_rule_leaves": len(registry_ids - automated_ids),
        "coverage_percent": round(100.0 * len(registry_ids & automated_ids) / len(registry_ids), 2) if registry_ids else 0.0,
        "by_phase": by_phase,
        "automated_leaf_ids": sorted(registry_ids & automated_ids),
        "instrumentation_or_future_leaf_ids": sorted(registry_ids - automated_ids),
        "interpretation": "No-rule leaves remain explicit NOT_OBSERVABLE candidates; they are never interpreted as equal or absent.",
    }
    dump(out / "automation_coverage.json", coverage)
    summary["automated_rule_count"] = coverage["automated_rule_leaves"]
    summary["automation_coverage_percent"] = coverage["coverage_percent"]
    dump(out / "analysis_summary.json", summary)

    lines = [
        "# App Entry DUT vs REF RCA Report", "",
        f"- Validation: **{state.validation.get('decision')}** (score {state.validation.get('comparability_score')}/100)",
        f"- Target: `{state.contexts['DUT'].target_package}`",
        f"- Launch type: DUT **{state.contexts['DUT'].launch_type}**, REF **{state.contexts['REF'].launch_type}**",
        f"- Backend: DUT **{state.metrics['DUT'].get('trace_backend')}**, REF **{state.metrics['REF'].get('trace_backend')}**",
        f"- Endpoint: DUT **{state.contexts['DUT'].endpoint_semantics}**, REF **{state.contexts['REF'].endpoint_semantics}**",
        f"- Active/observed phases: {', '.join(state.active_phases)}",
        f"- Selected analyzers: {', '.join(state.selected_skills)}",
        "- CPU core/frequency artifact: `cpu_core_frequency.json`",
        f"- Taxonomy leaves: {len(leaves)}",
        f"- Automatic evidence rules: {coverage['automated_rule_leaves']}/{coverage['total_leaves']} ({coverage['coverage_percent']}%)", "",
    ]
    if state.validation.get("warnings"):
        lines.extend(["## Validation warnings", ""])
        lines.extend(f"- {item}" for item in state.validation["warnings"])
        lines.append("")

    lines.extend(["## Phase comparison", ""])
    for phase in [f"P{i}" for i in range(1, 9)]:
        item = state.phase_comparison.get(phase, {})
        lines.append(f"- **{phase} {item.get('phase_name') or ''}**: delta={item.get('delta_ms')} ms; role={item.get('role')}; activated={item.get('activated')}")
    lines.append("")

    lines.extend(["## User-visible regression summary", ""])
    endpoint = ms_diff_summary["endpoint"]
    if endpoint.get("delta_ms") is not None:
        lines.append(
            f"- **DUT first-frame proxy DUT−REF: {endpoint['delta_ms']:+.3f} ms** "
            f"(DUT={endpoint.get('dut_ms')}, REF={endpoint.get('ref_ms')}, semantics={endpoint.get('semantics')})"
        )
    else:
        lines.append("- First-frame endpoint is not observable in both traces.")
    completion = ms_diff_summary["completion_endpoint"]
    if completion.get("delta_ms") is not None:
        lines.append(
            f"- **DUT input→system_server activityIdle DUT−REF: {completion['delta_ms']:+.3f} ms** "
            f"(DUT={completion.get('dut_ms')}, REF={completion.get('ref_ms')}, semantics={completion.get('semantics')})"
        )
    else:
        lines.append("- system_server activityIdle completion endpoint is not observable in both traces.")
    for contributor in ms_diff_summary["contributors"]:
        lines.append(f"  - **{contributor['title']}: {contributor['local_delta_ms']:+.3f} ms local delta**")
        exclusive = contributor.get("exclusive_contribution_ms")
        if exclusive is not None:
            lines.append(f"    - Exclusive/attributed contribution estimate: {exclusive:+.3f} ms")
        for name, value in contributor.get("nested_deltas_ms", {}).items():
            lines.append(f"    - {name}: {value:+.3f} ms (nested evidence)")
        lines.append(f"    - overlap_group=`{contributor['overlap_group']}`; additive={contributor['additive']}")
    lines.extend(["", f"> {ms_diff_summary['guardrail']}", ""])

    lines.extend(["## Ranked final leaves", ""])
    if not finals:
        lines.append("No direct/contributing case-specific final leaf was generated.")
    for item in state.final_leaves:
        lines.extend([
            f"### {item.id} — {item.status} — score {item.score:.2f}",
            f"- Path: {item.path}",
            f"- Root-cause key: `{item.root_cause_key}`",
            f"- Confidence: **{item.confidence}**; causality: **{item.causality}**",
            f"- Local DUT−REF delta: **{item.local_delta_ms} ms**",
            (f"- Exclusive contribution estimate: **{item.exclusive_contribution_ms} ms**"
             if item.exclusive_contribution_ms is not None
             else "- Exclusive contribution estimate: **N/A (nested/inclusive window)**"),
            f"- Nested deltas: `{item.nested_deltas_ms}`",
            f"- Overlap group: `{item.overlap_group}`; additive: **{item.additive}**",
            f"- Delta note: {item.delta_note}",
            f"1. **Symptom:** {item.symptom}", f"2. **Location:** {item.location}",
            f"3. **Mechanism:** {item.mechanism}", f"4. **Origin:** {item.origin}",
            f"5. **Ownership:** {item.ownership}", f"6. **Action:** {item.action}",
            f"- **Verification plan:** `{item.verification_plan}`", "",
        ])

    lines.extend(["## Leaf status by phase", ""])
    for phase in [f"P{i}" for i in range(1, 9)]:
        counts = _status_counts([item for item in leaves if item["phase"] == phase])
        lines.append(f"- **{phase}:** " + ", ".join(f"{key}={value}" for key, value in counts.items()))

    lines.extend(["", "## Interpretation guardrails", "",
        "- `NOT_OBSERVABLE` means missing evidence, not equality.",
        "- GC/kswapd total CPU or temporal overlap alone is correlation-only.",
        "- D-state alone is not storage; blocked-reason/file/page attribution is required.",
        "- CPU total alone is not contention; exact Running-blocker/critical-Runnable overlap is required.",
        "- P2 functional segments can overlap P3 wall time; do not sum them as sequential phases.",
        "- `finishDrawing` is a proxy unless FrameTimeline/SurfaceFlinger present data is available.",
    ])
    (out / "report.md").write_text("\n".join(lines), encoding="utf-8")
    state.output_files = {path.name: str(path) for path in out.iterdir() if path.is_file()}

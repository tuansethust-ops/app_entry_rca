from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Iterable

from app_entry_rca.core.helpers import analysis_window, overlap_ms
from app_entry_rca.core.models import SkillFinding


MARKER_TO_PHASE = {
    "active_launch": "P1",
    "do_active_launch": "P1",
    "input_delivery": "P1",
    "start_activity_server": "P2",
    "start_activity_inner": "P2",
    "process_request": "P2",
    "start_proc": "P2",
    "activity_thread_main": "P2",
    "attach_server": "P2",
    "bind_application": "P3",
    "open_dex_oat": "P3",
    "load_apk_assets": "P3",
    "loaded_arsc": "P3",
    "activity_start": "P4",
    "perform_create": "P4",
    "inflate": "P4",
    "activity_resume": "P5",
    "perform_resume": "P5",
    "choreographer_doframe": "P6",
    "traversal": "P6",
    "measure": "P6",
    "draw_frames": "P6",
    "vulkan_finish": "P6",
    "finish_drawing": "P6",
    "activity_idle_client": "P7",
    "activity_idle_server": "P7",
    "activity_idle": "P7",
}


def _round(value: float | None, digits: int = 3):
    if value is None:
        return None
    return round(float(value), digits)


def _freq_to_khz(value: Any) -> float | None:
    try:
        v = float(value)
    except Exception:
        return None
    if v <= 0:
        return None
    # Android cpu_frequency counters are usually kHz. Some vendor traces expose Hz.
    return v / 1000.0 if v > 10_000_000 else v


def _cluster_map(config: dict) -> dict[int, str]:
    mapping: dict[int, str] = {}
    for name in ("little", "big", "prime"):
        for cpu in config.get(f"{name}_cpus", []) or []:
            try:
                mapping[int(cpu)] = name
            except Exception:
                pass
    for cluster, cpus in (config.get("cpu_clusters") or {}).items():
        for cpu in cpus or []:
            try:
                mapping[int(cpu)] = str(cluster)
            except Exception:
                pass
    return mapping


def _query_cpu_freq_events(trace, start: float, end: float) -> dict[int, list[tuple[float, float]]]:
    """Return cpu -> [(ts_s, freq_khz)] using best-effort Perfetto SQL schemas."""
    if not hasattr(trace, "query_rows"):
        return {}
    start_ns = int((start - 5.0) * 1e9)
    end_ns = int(end * 1e9)
    candidates = [
        (
            "cpu_counter_track_with_name",
            f"""
            SELECT c.ts, c.value, ct.cpu, COALESCE(ct.name, '') AS name
            FROM counter c JOIN cpu_counter_track ct ON c.track_id = ct.id
            WHERE c.ts <= {end_ns} AND c.ts >= {start_ns}
            ORDER BY c.ts
            """,
        ),
        (
            "cpu_counter_track",
            f"""
            SELECT c.ts, c.value, ct.cpu, '' AS name
            FROM counter c JOIN cpu_counter_track ct ON c.track_id = ct.id
            WHERE c.ts <= {end_ns} AND c.ts >= {start_ns}
            ORDER BY c.ts
            """,
        ),
        (
            "generic_track",
            f"""
            SELECT c.ts, c.value, COALESCE(t.name, '') AS name
            FROM counter c JOIN track t ON c.track_id = t.id
            WHERE c.ts <= {end_ns} AND c.ts >= {start_ns}
              AND (
                lower(t.name) LIKE '%freq%' OR
                lower(t.name) LIKE '%frequency%' OR
                lower(t.name) LIKE '%cpufreq%'
              )
            ORDER BY c.ts
            """,
        ),
    ]
    rows: list[dict[str, Any]] = []
    for _name, sql in candidates:
        try:
            rows = trace.query_rows(sql)
            if rows:
                break
        except Exception:
            rows = []
            continue
    events: dict[int, list[tuple[float, float]]] = defaultdict(list)
    for row in rows:
        cpu = row.get("cpu")
        if cpu is None:
            import re
            match = re.search(r"(?:cpu|CPU)[ _:-]?(\d+)", str(row.get("name") or ""))
            if not match:
                continue
            cpu = int(match.group(1))
        freq = _freq_to_khz(row.get("value"))
        if freq is None:
            continue
        events[int(cpu)].append((float(row["ts"]) / 1e9, freq))
    for cpu in list(events):
        events[cpu].sort(key=lambda item: item[0])
    return dict(events)


def _weighted_freq_for_interval(events: list[tuple[float, float]], start: float, end: float):
    if not events or end <= start:
        return None
    current = None
    inside = []
    for ts, value in events:
        if ts <= start:
            current = value
        elif ts < end:
            inside.append((ts, value))
        else:
            break
    if current is None and inside:
        current = inside[0][1]
    if current is None:
        return None
    cursor = start
    total_ms = 0.0
    weighted = 0.0
    min_f = current
    max_f = current
    for ts, value in inside:
        if ts > cursor:
            dur_ms = (ts - cursor) * 1000.0
            weighted += current * dur_ms
            total_ms += dur_ms
            min_f = min(min_f, current)
            max_f = max(max_f, current)
        current = value
        min_f = min(min_f, current)
        max_f = max(max_f, current)
        cursor = max(cursor, ts)
    if end > cursor:
        dur_ms = (end - cursor) * 1000.0
        weighted += current * dur_ms
        total_ms += dur_ms
        min_f = min(min_f, current)
        max_f = max(max_f, current)
    if total_ms <= 0:
        return None
    return {"weighted_sum": weighted, "duration_ms": total_ms, "min": min_f, "max": max_f}


def _state_ms(trace, tid: int, start: float, end: float) -> dict[str, float]:
    if tid <= 0 or end <= start:
        return {}
    try:
        return trace.state_ms(tid, start, end)
    except Exception:
        return {}


def _running_intervals(trace, tid: int, start: float, end: float):
    if tid <= 0 or end <= start:
        return []
    try:
        return trace.intervals(tid, "Running", start, end)
    except Exception:
        return []


def _subject_from_slice(context, marker: str, item):
    phase = MARKER_TO_PHASE.get(marker)
    if not phase:
        return None
    return {
        "subject_id": f"marker.{marker}",
        "kind": "marker_slice",
        "phase": phase,
        "name": marker,
        "display_name": item.name,
        "start_s": item.ts,
        "end_s": item.end,
        "tid": item.tid,
        "tgid": item.tgid,
        "comm": item.comm,
    }


def _subjects(context):
    out = []
    # Phase subjects where there is a clear marker/critical thread.
    phase_to_marker = {
        "P3": "bind_application" if context.launch_type == "cold" else "activity_start",
        "P4": "activity_start" if context.launch_type == "cold" else "activity_resume",
        "P5": "activity_resume" if context.launch_type == "cold" else "choreographer_doframe",
        "P6": "choreographer_doframe" if context.launch_type == "cold" else "activity_idle_server",
        "P7": "activity_idle_server",
    }
    for phase, marker in phase_to_marker.items():
        if marker and marker in context.marker_slices and context.marker_slices.get(marker):
            item = context.marker_slices[marker]
            win = (context.phase_windows.get(phase) or [])
            if win and isinstance(win[0], dict):
                start, end = float(win[0].get("start_s", item.ts)), float(win[0].get("end_s", item.end))
            elif win:
                start, end = win[0]
            else:
                start, end = item.ts, item.end
            out.append({
                "subject_id": f"phase.{phase}",
                "kind": "phase",
                "phase": phase,
                "name": phase,
                "display_name": context.phase_windows.get(phase, [{}])[0].get("name", phase) if isinstance(context.phase_windows.get(phase), list) else phase,
                "start_s": start,
                "end_s": end,
                "tid": item.tid,
                "tgid": item.tgid,
                "comm": item.comm,
            })
    # P1/P2 branch subjects from markers.
    for marker in ("input_delivery", "active_launch", "start_activity_server", "activity_thread_main", "start_proc"):
        item = context.marker_slices.get(marker)
        if item:
            subj = _subject_from_slice(context, marker, item)
            if subj:
                subj["subject_id"] = f"phase_or_marker.{marker}"
                out.append(subj)

    seen = {x["subject_id"] for x in out}
    for marker, item in sorted(context.marker_slices.items()):
        if not item:
            continue
        subj = _subject_from_slice(context, marker, item)
        if subj and subj["subject_id"] not in seen:
            out.append(subj)
            seen.add(subj["subject_id"])
    return out


def _analyze_subject(trace, subject: dict, freq_by_cpu: dict[int, list[tuple[float, float]]], clusters: dict[int, str]):
    start = float(subject["start_s"])
    end = float(subject["end_s"])
    tid = int(subject.get("tid") or 0)
    states = _state_ms(trace, tid, start, end)
    running = _running_intervals(trace, tid, start, end)

    by_cpu: Counter[int] = Counter()
    cluster_ms: Counter[str] = Counter()
    freq_weighted = 0.0
    freq_dur = 0.0
    freq_min = None
    freq_max = None
    samples = 0
    last_cpu = None
    migrations = 0

    for item in running:
        dur_ms = item.dur_ms
        cpu = item.cpu
        if cpu is None:
            continue
        by_cpu[int(cpu)] += dur_ms
        cluster_ms[clusters.get(int(cpu), "unknown")] += dur_ms
        if last_cpu is not None and int(cpu) != last_cpu:
            migrations += 1
        last_cpu = int(cpu)
        freq_result = _weighted_freq_for_interval(freq_by_cpu.get(int(cpu), []), item.start, item.end)
        if freq_result:
            freq_weighted += freq_result["weighted_sum"]
            freq_dur += freq_result["duration_ms"]
            freq_min = freq_result["min"] if freq_min is None else min(freq_min, freq_result["min"])
            freq_max = freq_result["max"] if freq_max is None else max(freq_max, freq_result["max"])
            samples += 1

    total_running = sum(by_cpu.values())
    dominant_cpu = None
    if by_cpu:
        dominant_cpu = max(by_cpu.items(), key=lambda kv: kv[1])[0]
    avg_freq = freq_weighted / freq_dur if freq_dur > 0 else None

    return {
        **subject,
        "duration_ms": _round((end - start) * 1000.0),
        "thread_state_ms": {k: _round(v) for k, v in sorted(states.items())},
        "running_ms": _round(total_running),
        "running_ms_by_cpu": {str(k): _round(v) for k, v in sorted(by_cpu.items())},
        "running_ms_by_cluster": {k: _round(v) for k, v in sorted(cluster_ms.items())},
        "dominant_cpu": dominant_cpu,
        "dominant_cluster": clusters.get(dominant_cpu, "unknown") if dominant_cpu is not None else None,
        "migration_count": migrations,
        "avg_freq_khz_running_weighted": _round(avg_freq),
        "min_freq_khz": _round(freq_min),
        "max_freq_khz": _round(freq_max),
        "freq_sample_count": samples,
        "cpu_placement_observable": bool(running),
        "cpu_frequency_observable": avg_freq is not None,
        "observability": "OBSERVED" if running else "NOT_OBSERVABLE",
    }


def _delta(dut, ref):
    if isinstance(dut, (int, float)) and isinstance(ref, (int, float)):
        return _round(float(dut) - float(ref))
    return None


def run(state, config):
    clusters = _cluster_map(config or {})
    top_n = int((config or {}).get("top_subjects", 80))
    output = {"schema_version": "1.0", "notes": [], "DUT": {}, "REF": {}, "delta": {}}

    for label, context in state.contexts.items():
        trace = state.traces[label]
        try:
            start, end = analysis_window(context)
        except Exception:
            start = min((v.ts for v in context.marker_slices.values() if v), default=0.0)
            end = max((v.end for v in context.marker_slices.values() if v), default=start)

        freq_by_cpu = _query_cpu_freq_events(trace, start, end)
        subjects = [_analyze_subject(trace, s, freq_by_cpu, clusters) for s in _subjects(context)]
        subjects.sort(key=lambda item: (item.get("phase", ""), item.get("start_s", 0), item.get("subject_id", "")))
        by_id = {item["subject_id"]: item for item in subjects}

        top_running = sorted(subjects, key=lambda item: item.get("running_ms") or 0.0, reverse=True)[:top_n]
        top_migrations = sorted(subjects, key=lambda item: item.get("migration_count") or 0, reverse=True)[:top_n]
        low_freq_subjects = [
            item for item in subjects
            if item.get("avg_freq_khz_running_weighted") is not None
        ]
        low_freq_subjects.sort(key=lambda item: item.get("avg_freq_khz_running_weighted"))

        metrics = {
            "cpu_core_frequency": {
                "trace": label,
                "freq_counters_observable": bool(freq_by_cpu),
                "cpus_with_freq_counters": sorted(freq_by_cpu.keys()),
                "subjects": subjects,
                "top_running_subjects": top_running[:10],
                "top_migration_subjects": top_migrations[:10],
                "lowest_frequency_subjects": low_freq_subjects[:10],
            },
            "cpu_core_frequency_by_subject": by_id,
            "cpu_core_frequency_summary": {
                "subject_count": len(subjects),
                "subjects_with_cpu_placement": sum(1 for item in subjects if item.get("cpu_placement_observable")),
                "subjects_with_frequency": sum(1 for item in subjects if item.get("cpu_frequency_observable")),
                "freq_counters_observable": bool(freq_by_cpu),
                "cpus_with_freq_counters": sorted(freq_by_cpu.keys()),
            },
        }
        state.metrics[label].update(metrics)
        output[label] = metrics["cpu_core_frequency"]

        evidence = []
        for item in top_running[:5]:
            cpu_desc = ", ".join(f"CPU{cpu}:{ms}ms" for cpu, ms in item.get("running_ms_by_cpu", {}).items())
            freq = item.get("avg_freq_khz_running_weighted")
            freq_desc = f", avg_freq={freq}kHz" if freq is not None else ", avg_freq=NOT_OBSERVABLE"
            evidence.append(f"{item['subject_id']}: Running={item.get('running_ms')}ms [{cpu_desc}]{freq_desc}")

        state.add_finding(
            SkillFinding(
                finding_id=f"{label}-CPU-CORE-FREQUENCY",
                skill="cpu-core-frequency-analysis",
                trace_label=label,
                title="Critical node/leaf CPU core and frequency attribution",
                category="cpu_core_frequency",
                severity="INFO",
                confidence="HIGH" if context.observability.get("sched") else "LOW",
                value=metrics["cpu_core_frequency_summary"],
                evidence=evidence or ["No critical running intervals were observable."],
                notes="Frequency is computed only over Running intervals. Missing counters mean NOT_OBSERVABLE, not equal.",
                evidence_level="DIRECT" if metrics["cpu_core_frequency_summary"]["subjects_with_cpu_placement"] else "NONE",
                root_cause_key="cpu_core_frequency",
            )
        )

    dut = state.metrics.get("DUT", {}).get("cpu_core_frequency_by_subject", {})
    ref = state.metrics.get("REF", {}).get("cpu_core_frequency_by_subject", {})
    common = sorted(set(dut) & set(ref))
    deltas = {}
    for sid in common:
        d = dut[sid]
        r = ref[sid]
        deltas[sid] = {
            "subject_id": sid,
            "phase": d.get("phase"),
            "name": d.get("name"),
            "running_ms_delta": _delta(d.get("running_ms"), r.get("running_ms")),
            "migration_count_delta": _delta(d.get("migration_count"), r.get("migration_count")),
            "avg_freq_khz_delta": _delta(d.get("avg_freq_khz_running_weighted"), r.get("avg_freq_khz_running_weighted")),
            "dut_dominant_cpu": d.get("dominant_cpu"),
            "ref_dominant_cpu": r.get("dominant_cpu"),
            "dut_dominant_cluster": d.get("dominant_cluster"),
            "ref_dominant_cluster": r.get("dominant_cluster"),
        }
    output["delta"] = deltas
    state.metrics.setdefault("DUT", {})["cpu_core_frequency_delta_vs_ref"] = deltas
    state.metrics.setdefault("REF", {})["cpu_core_frequency_delta_vs_ref"] = deltas
    state.output_files["cpu_core_frequency"] = "cpu_core_frequency.json"

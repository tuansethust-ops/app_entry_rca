from __future__ import annotations

import re
from collections import Counter

from app_entry_rca.core.config import load_yaml
from app_entry_rca.core.helpers import analysis_window, critical_slices, overlap_ms, running_intervals_by_name
from app_entry_rca.core.intervals import critical_runnable_intervals, pair_overlap_ms
from app_entry_rca.core.models import SkillFinding

GC_RE = re.compile(
    r"WaitForGcToComplete|concurrent .*GC|concurrent mark compact GC|CollectorTransition|"
    r"HomogeneousSpaceCompact|HeapTrim|Explicit GC|Alloc GC|Background .*GC|\bGC\b",
    re.I,
)
STW_RE = re.compile(r"SuspendAll|Stop.?the.?world|PauseForGc|GC pause|paused .*GC", re.I)
ALLOC_STALL_RE = re.compile(r"Alloc(?:ation)? stall|WaitingForGcToComplete|ForAlloc", re.I)
GC_THREAD_RE = r"HeapTaskDaemon|GC Thread|ConcGC|MarkCompact|HeapTrim|Jit thread pool"
KSWAPD_RE = r"^kswapd|kswapd[0-9]"


def _owner(item, context):
    if item.tgid == context.target_pid:
        return "target"
    if item.tgid == context.system_pid:
        return "system_server"
    if item.tgid == context.launcher_pid:
        return "launcher"
    return "other"


def _gc_type(name: str) -> str:
    lower = name.lower()
    if "waitforgc" in lower or "waitingforgc" in lower:
        return "WAIT_FOR_GC"
    if "collectortransition" in lower:
        return "COLLECTOR_TRANSITION"
    if "homogeneous" in lower:
        return "HOMOGENEOUS_SPACE_COMPACT"
    if "heaptrim" in lower or "heap trim" in lower:
        return "HEAP_TRIM"
    if "explicit" in lower:
        return "EXPLICIT"
    if "alloc" in lower:
        return "ALLOCATION"
    if "background" in lower:
        return "BACKGROUND"
    if "concurrent" in lower:
        return "CONCURRENT"
    return "OTHER"


def _paired_per_tid(trace, begin: str, end: str, tids: list[int], start: float, finish: float) -> dict[int, float]:
    return {
        tid: trace.sum_paired_event_ms(begin, end, tid=tid, start=start, end=finish)
        for tid in tids
    }


def _event_count(trace, names, start, end, tgid=None):
    finder = getattr(trace, "find_events", None)
    if finder:
        return len(finder(names, start=start, end=end, tgid=tgid))
    return sum(
        1 for event in trace.events
        if event.event in names and start <= event.ts < end and (tgid is None or event.tgid == tgid)
    )


def run(state, config):
    policy = load_yaml(state.project_root / "taxonomy" / "gc_thresholds.yaml")
    for label, context in state.contexts.items():
        trace = state.traces[label]
        start, end = analysis_window(context)
        pre_start = max(trace.trace_start or start, start - float(config.get("prelaunch_seconds", 30.0)))
        critical = critical_slices(context)
        critical_tids = sorted({item.tid for item in critical.values()})

        direct_by_tid = _paired_per_tid(
            trace, "mm_vmscan_direct_reclaim_begin", "mm_vmscan_direct_reclaim_end",
            critical_tids, pre_start, end,
        )
        target_direct = sum(
            value for tid, value in direct_by_tid.items()
            if trace.thread_meta.get(tid, ("", tid))[1] == context.target_pid
        )
        launch_direct = sum(direct_by_tid.values())
        compaction_by_tid = _paired_per_tid(
            trace, "mm_compaction_begin", "mm_compaction_end", critical_tids, pre_start, end
        )
        compaction_ms = sum(compaction_by_tid.values())

        gc_slices = [item for item in trace.find_slices(GC_RE, start=pre_start, end=end) if item.dur >= 0]
        gc_events = []
        gc_by_owner = Counter()
        gc_by_type = Counter()
        for item in gc_slices:
            overlap = overlap_ms(start, end, item.ts, item.end)
            owner = _owner(item, context)
            kind = _gc_type(item.name)
            if overlap:
                gc_by_owner[owner] += overlap
                gc_by_type[kind] += overlap
            gc_events.append(
                {
                    "name": item.name,
                    "type": kind,
                    "owner": owner,
                    "tid": item.tid,
                    "tgid": item.tgid,
                    "start_s": item.ts,
                    "duration_ms": item.dur_ms,
                    "launch_overlap_ms": overlap,
                }
            )
        gc_overlap = sum(gc_by_owner.values())

        wait_slices = [
            item for item in trace.find_slices(r"WaitForGcToComplete|WaitingForGcToComplete", start=start, end=end)
            if item.tgid in (context.target_pid, context.system_pid, context.launcher_pid)
        ]
        wait_for_gc = sum(overlap_ms(start, end, item.ts, item.end) for item in wait_slices)
        stw_slices = [
            item for item in trace.find_slices(STW_RE, start=start, end=end)
            if item.tgid in (context.target_pid, context.system_pid, context.launcher_pid)
        ]
        stw_ms = sum(overlap_ms(start, end, item.ts, item.end) for item in stw_slices)
        allocation_stalls = [
            item for item in trace.find_slices(ALLOC_STALL_RE, start=start, end=end)
            if item.tgid in (context.target_pid, context.system_pid, context.launcher_pid)
        ]
        allocation_stall_ms = sum(overlap_ms(start, end, item.ts, item.end) for item in allocation_stalls)

        gc_running = running_intervals_by_name(trace, start, end, GC_THREAD_RE)
        kswapd_running = running_intervals_by_name(trace, start, end, KSWAPD_RE)
        kswapd_pre_running = running_intervals_by_name(trace, pre_start, start, KSWAPD_RE)
        runnable_map = critical_runnable_intervals(trace, context)
        all_critical_runnable = [item for values in runnable_map.values() for item in values]
        gc_competition = pair_overlap_ms(gc_running, all_critical_runnable, same_cpu=True)
        kswapd_competition = pair_overlap_ms(kswapd_running, all_critical_runnable, same_cpu=True)
        gc_cpu = sum(item.dur_ms for item in gc_running)
        kswapd_cpu = sum(item.dur_ms for item in kswapd_running)
        kswapd_pre_cpu = sum(item.dur_ms for item in kswapd_pre_running)

        swap_events = _event_count(
            trace,
            ["mm_vmscan_writepage", "mm_vmscan_lru_shrink_inactive", "swap_readpage", "swap_writepage"],
            pre_start,
            end,
        )
        reclaim_events = _event_count(
            trace,
            ["mm_vmscan_direct_reclaim_begin", "mm_vmscan_kswapd_wake", "mm_vmscan_kswapd_sleep"],
            pre_start,
            end,
        )

        if wait_for_gc > float(policy.get("direct_block_ms", 1.0)):
            gc_classification = "DIRECT_WAIT"
        elif stw_ms > float(policy.get("stw_ms", policy.get("direct_block_ms", 1.0))):
            gc_classification = "DIRECT_STW"
        elif allocation_stall_ms > float(policy.get("allocation_stall_ms", 1.0)):
            gc_classification = "DIRECT_ALLOCATION_STALL"
        elif gc_competition > float(policy.get("competition_ms", 1.0)):
            gc_classification = "COMPETITION"
        elif gc_overlap > 0:
            gc_classification = "OVERLAP_ONLY"
        else:
            gc_classification = "NO_GC_EVIDENCE"

        if launch_direct > 0:
            memory_classification = "DIRECT_RECLAIM"
        elif compaction_ms > 0:
            memory_classification = "COMPACTION"
        elif kswapd_competition > float(policy.get("kswapd_competition_ms", 1.0)):
            memory_classification = "KSWAPD_COMPETITION"
        elif kswapd_cpu > 0 or swap_events > 0 or reclaim_events > 0:
            memory_classification = "MEMORY_PRESSURE_CORRELATION"
        else:
            memory_classification = "NO_MEMORY_PRESSURE_EVIDENCE"

        state.metrics[label].update(
            {
                "target_direct_reclaim_ms": target_direct,
                "critical_direct_reclaim_ms": launch_direct,
                "direct_reclaim_by_tid_ms": {str(k): v for k, v in direct_by_tid.items() if v},
                "critical_compaction_ms": compaction_ms,
                "compaction_by_tid_ms": {str(k): v for k, v in compaction_by_tid.items() if v},
                "kswapd_cpu_ms": kswapd_cpu,
                "kswapd_prelaunch_cpu_ms": kswapd_pre_cpu,
                "kswapd_critical_overlap_ms": kswapd_competition,
                "swap_event_count": swap_events,
                "reclaim_event_count": reclaim_events,
                "memory_pressure_classification": memory_classification,
                "gc_overlap_ms": gc_overlap,
                "gc_overlap_by_owner_ms": dict(gc_by_owner),
                "gc_overlap_by_type_ms": dict(gc_by_type),
                "gc_events": gc_events,
                "wait_for_gc_ms": wait_for_gc,
                "gc_stw_ms": stw_ms,
                "gc_allocation_stall_ms": allocation_stall_ms,
                "wait_for_gc_slices": [
                    {"name": item.name, "tid": item.tid, "tgid": item.tgid, "duration_ms": item.dur_ms}
                    for item in wait_slices
                ],
                "gc_cpu_ms": gc_cpu,
                "gc_competition_cpu_ms": gc_competition,
                "gc_competition_method": "same CPU GC-running vs critical-runnable interval overlap",
                "gc_classification": gc_classification,
                "gc_policy_context": policy,
            }
        )

        if gc_classification != "NO_GC_EVIDENCE":
            state.add_finding(
                SkillFinding(
                    finding_id=f"{label}-GC-{gc_classification}",
                    skill="memory-gc-analysis",
                    trace_label=label,
                    title=f"GC classification: {gc_classification}",
                    category="gc",
                    severity="WARNING" if gc_classification.startswith("DIRECT") or gc_classification == "COMPETITION" else "INFO",
                    confidence="HIGH" if gc_classification.startswith("DIRECT") else ("MEDIUM" if gc_classification == "COMPETITION" else "LOW"),
                    value={
                        "wait_ms": wait_for_gc,
                        "stw_ms": stw_ms,
                        "allocation_stall_ms": allocation_stall_ms,
                        "competition_ms": gc_competition,
                        "overlap_ms": gc_overlap,
                        "owner_ms": dict(gc_by_owner),
                    },
                    evidence=[item["name"] for item in gc_events[:10]],
                    notes="Overlap-only is correlation and is rejected as root cause without direct wait/STW/allocation stall or exact competition.",
                    evidence_level="DIRECT" if gc_classification.startswith("DIRECT") else ("CONTRIBUTING" if gc_classification == "COMPETITION" else "CORRELATION"),
                    root_cause_key="gc:" + gc_classification,
                    contribution_ms=max(wait_for_gc, stw_ms, allocation_stall_ms, gc_competition),
                )
            )
        if memory_classification != "NO_MEMORY_PRESSURE_EVIDENCE":
            state.add_finding(
                SkillFinding(
                    finding_id=f"{label}-MEM-{memory_classification}",
                    skill="memory-gc-analysis",
                    trace_label=label,
                    title=f"Memory pressure classification: {memory_classification}",
                    category="memory_pressure",
                    severity="WARNING" if memory_classification in {"DIRECT_RECLAIM", "COMPACTION", "KSWAPD_COMPETITION"} else "INFO",
                    confidence="HIGH" if memory_classification in {"DIRECT_RECLAIM", "COMPACTION"} else ("MEDIUM" if memory_classification == "KSWAPD_COMPETITION" else "LOW"),
                    value={
                        "direct_reclaim_ms": launch_direct,
                        "compaction_ms": compaction_ms,
                        "kswapd_cpu_ms": kswapd_cpu,
                        "kswapd_overlap_ms": kswapd_competition,
                        "swap_events": swap_events,
                    },
                    evidence=[f"kswapd CPU={kswapd_cpu:.3f}ms", f"critical overlap={kswapd_competition:.3f}ms"],
                    notes="kswapd CPU by itself is correlation; causal contribution requires exact overlap with a critical Runnable interval.",
                    evidence_level="DIRECT" if memory_classification in {"DIRECT_RECLAIM", "COMPACTION"} else ("CONTRIBUTING" if memory_classification == "KSWAPD_COMPETITION" else "CORRELATION"),
                    root_cause_key="memory:" + memory_classification,
                    contribution_ms=max(launch_direct, compaction_ms, kswapd_competition),
                )
            )

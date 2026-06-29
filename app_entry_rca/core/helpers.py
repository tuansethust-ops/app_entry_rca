from __future__ import annotations

import collections
import re
from typing import Any, Dict, Iterable, Optional

from .models import LaunchContext, Slice, StateInterval


def dur(item: Optional[Slice]) -> Optional[float]:
    return item.dur_ms if item else None


def gap(a: Optional[Slice], b: Optional[Slice], use_a_end: bool = False) -> Optional[float]:
    if not a or not b:
        return None
    return (b.ts - (a.end if use_a_end else a.ts)) * 1000.0


def state_for_slice(trace, item: Optional[Slice]) -> Dict[str, float]:
    if not item:
        return {}
    return trace.state_ms(item.tid, item.ts, item.end)


def val(states: Dict[str, float], key: str) -> float:
    return float(states.get(key, 0.0))


def analysis_window(context: LaunchContext) -> tuple[float, float]:
    markers = context.marker_slices
    start = markers.get("input_delivery") or markers.get("active_launch") or markers.get("start_activity_server") or markers.get("process_request")
    end = markers.get("activity_idle_server") or markers.get("activity_idle") or markers.get("finish_drawing") or markers.get("draw_frames")
    if not start or not end:
        raise ValueError("Cannot establish launch analysis window.")
    return start.ts, end.end


def overlap_ms(start: float, end: float, other_start: float, other_end: float) -> float:
    return max(0.0, min(end, other_end) - max(start, other_start)) * 1000.0


def running_by_name(trace, start: float, end: float, pattern: str) -> float:
    regex = re.compile(pattern, re.I)
    total = 0.0
    for interval in getattr(trace, "running_intervals", trace.running):
        comm = trace.thread_meta.get(interval.tid, ("", interval.tid))[0]
        if regex.search(comm):
            total += overlap_ms(start, end, interval.start, interval.end)
    return total


def running_intervals_by_name(trace, start: float, end: float, pattern: str) -> list[StateInterval]:
    regex = re.compile(pattern, re.I)
    result = []
    for interval in getattr(trace, "running_intervals", trace.running):
        comm = trace.thread_meta.get(interval.tid, ("", interval.tid))[0]
        if not regex.search(comm) or interval.end <= start or interval.start >= end:
            continue
        result.append(
            StateInterval(max(start, interval.start), min(end, interval.end), "Running", interval.tid, interval.cpu)
        )
    return result


def top_running_owners(trace, start: float, end: float, limit: int = 20) -> Dict[str, float]:
    counter: collections.Counter[str] = collections.Counter()
    for interval in getattr(trace, "running_intervals", trace.running):
        overlap = overlap_ms(start, end, interval.start, interval.end)
        if not overlap:
            continue
        comm, tgid = trace.thread_meta.get(interval.tid, (f"tid:{interval.tid}", interval.tid))
        counter[f"{comm} (tgid={tgid})"] += overlap
    return dict(counter.most_common(limit))


def marker_slice(context: LaunchContext, name: str):
    return context.marker_slices.get(name)


CRITICAL_MARKERS = (
    "active_launch",
    "do_active_launch",
    "start_activity_server",
    "attach_server",
    "activity_thread_main",
    "bind_application",
    "activity_start",
    "activity_resume",
    "traversal",
    "draw_frames",
    "vulkan_finish",
    "finish_drawing",
    "activity_idle_client",
    "activity_idle_server",
    "activity_idle",
)


def critical_slices(context: LaunchContext) -> Dict[str, Slice]:
    return {name: item for name in CRITICAL_MARKERS if (item := context.marker_slices.get(name)) is not None}


def state_breakdown_for_markers(trace, context: LaunchContext) -> Dict[str, Dict[str, float]]:
    return {name: trace.state_ms(item.tid, item.ts, item.end) for name, item in critical_slices(context).items()}


def numeric_delta(dut: Any, ref: Any) -> Optional[float]:
    if isinstance(dut, (int, float)) and isinstance(ref, (int, float)):
        return float(dut) - float(ref)
    return None

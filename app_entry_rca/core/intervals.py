from __future__ import annotations

from collections import Counter
from typing import Iterable, Sequence

from .models import StateInterval


def overlap_ms(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    return max(0.0, min(a_end, b_end) - max(a_start, b_start)) * 1000.0


def merge_windows(windows: Iterable[tuple[float, float]]) -> list[tuple[float, float]]:
    ordered = sorted((a, b) for a, b in windows if b > a)
    merged: list[list[float]] = []
    for start, end in ordered:
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return [(a, b) for a, b in merged]


def window_union_ms(windows: Iterable[tuple[float, float]]) -> float:
    return sum((end - start) * 1000.0 for start, end in merge_windows(windows))


def clip_intervals(intervals: Iterable[StateInterval], windows: Sequence[tuple[float, float]]) -> list[StateInterval]:
    out = []
    for item in intervals:
        for start, end in windows:
            left, right = max(item.start, start), min(item.end, end)
            if right > left:
                out.append(StateInterval(left, right, item.state, item.tid, item.cpu))
    return out


def pair_overlap_ms(left: Iterable[StateInterval], right: Iterable[StateInterval], *, same_cpu=False) -> float:
    total = 0.0
    for a in left:
        for b in right:
            if same_cpu and a.cpu is not None and b.cpu is not None and a.cpu != b.cpu:
                continue
            total += overlap_ms(a.start, a.end, b.start, b.end)
    return total


def running_blocker_edges(trace, runnable_intervals: Iterable[StateInterval], *, victim: str, exclude_tids=()) -> list[dict]:
    """Return exact running/runnable overlap edges, preserving CPU and owner.

    A high background CPU total is not causal. An edge is created only where a
    victim is Runnable while another thread is Running on the same target CPU
    (or the target CPU is unknown, in which case confidence is lower).
    """
    excluded = set(exclude_tids)
    counter: Counter[tuple] = Counter()
    unknown_cpu: Counter[tuple] = Counter()
    running = getattr(trace, "running_intervals", getattr(trace, "running", []))
    for wait in runnable_intervals:
        for run in running:
            if run.tid in excluded or run.tid == wait.tid:
                continue
            ov = overlap_ms(wait.start, wait.end, run.start, run.end)
            if not ov:
                continue
            same = wait.cpu is None or run.cpu is None or wait.cpu == run.cpu
            if not same:
                continue
            comm, tgid = trace.thread_meta.get(run.tid, (f"tid:{run.tid}", run.tid))
            if run.tid == 0 or comm in {"<idle>", "swapper"} or comm.startswith("swapper/"):
                continue
            key = (run.tid, tgid, comm, run.cpu, wait.cpu)
            if wait.cpu is None or run.cpu is None:
                unknown_cpu[key] += ov
            else:
                counter[key] += ov
    edges = []
    for source, confidence in ((counter, "HIGH"), (unknown_cpu, "MEDIUM")):
        for (tid, tgid, comm, cpu, victim_cpu), duration in source.most_common():
            edges.append(
                {
                    "victim": victim,
                    "blocker_tid": tid,
                    "blocker_tgid": tgid,
                    "blocker_comm": comm,
                    "overlap_ms": round(duration, 6),
                    "blocker_cpu": cpu,
                    "victim_target_cpu": victim_cpu,
                    "confidence": confidence,
                    "mechanism": "same_cpu_running_vs_runnable_overlap",
                }
            )
    return sorted(edges, key=lambda item: item["overlap_ms"], reverse=True)


def critical_runnable_intervals(trace, context) -> dict[str, list[StateInterval]]:
    out = {}
    for name, item in context.marker_slices.items():
        if item is None or name not in {
            "active_launch", "do_active_launch", "start_activity_server", "attach_server",
            "activity_thread_main", "bind_application", "activity_start", "activity_resume",
            "traversal", "draw_frames", "vulkan_finish", "finish_drawing", "activity_idle",
        }:
            continue
        out[name] = trace.intervals(item.tid, "Runnable", item.ts, item.end)
    return out

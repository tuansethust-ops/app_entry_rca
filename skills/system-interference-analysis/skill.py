from __future__ import annotations

import re
from collections import Counter

from app_entry_rca.core.helpers import analysis_window, running_by_name, top_running_owners
from app_entry_rca.core.models import SkillFinding

CATEGORY_PATTERNS = {
    "kswapd": re.compile(r"^kswapd", re.I),
    "gc": re.compile(r"HeapTaskDaemon|GC Thread|ConcGC|MarkCompact|HeapTrim", re.I),
    "irq_softirq": re.compile(r"irq/|ksoftirqd", re.I),
    "dexopt": re.compile(r"dex2oat|dexopt|profman", re.I),
    "systemui_shell": re.compile(r"SystemUI|splashworker|wmshell", re.I),
    "media_scan": re.compile(r"media.*scan|MediaProvider|indexer", re.I),
    "vendor": re.compile(r"vendor|epic|perf|health|daemon", re.I),
}


def _category(comm: str) -> str:
    for name, pattern in CATEGORY_PATTERNS.items():
        if pattern.search(comm):
            return name
    return "other"


def run(state, config):
    for label, context in state.contexts.items():
        trace = state.traces[label]
        start, end = analysis_window(context)
        top_owners = top_running_owners(trace, start, end, int(config.get("top_n", 20)))
        target_cpu = sum(value for name, value in top_owners.items() if f"tgid={context.target_pid}" in name)
        system_cpu = sum(value for name, value in top_owners.items() if f"tgid={context.system_pid}" in name)
        launcher_cpu = sum(value for name, value in top_owners.items() if f"tgid={context.launcher_pid}" in name)
        background_starts = [
            item for item in trace.find_slices(r"startProcess:|Start proc:", start=start, end=end)
            if context.target_package not in item.name
        ]

        edges = [edge for edge in state.interference_edges if edge.get("trace") == label]
        by_category: Counter[str] = Counter()
        by_blocker: Counter[str] = Counter()
        for edge in edges:
            category = _category(str(edge.get("blocker_comm", "")))
            by_category[category] += float(edge.get("overlap_ms", 0.0))
            by_blocker[str(edge.get("blocker_comm", "unknown"))] += float(edge.get("overlap_ms", 0.0))

        state.metrics[label].update(
            {
                "systemui_shell_cpu_ms": running_by_name(trace, start, end, r"SystemUI|splashworker|wmshell"),
                "irq_softirq_cpu_ms": running_by_name(trace, start, end, r"irq/|ksoftirqd"),
                "kswapd_cpu_window_ms": running_by_name(trace, start, end, r"^kswapd"),
                "dex2oat_cpu_ms": running_by_name(trace, start, end, r"dex2oat|dexopt|profman"),
                "top_running_owners_ms": top_owners,
                "target_process_cpu_ms": target_cpu,
                "system_server_cpu_ms": system_cpu,
                "launcher_process_cpu_ms": launcher_cpu,
                "background_process_start_count": len(background_starts),
                "background_process_starts": [item.name for item in background_starts[:30]],
                "critical_interference_by_category_ms": dict(by_category),
                "critical_interference_by_blocker_ms": dict(by_blocker.most_common(50)),
                "critical_interference_edges": edges[:200],
                "kswapd_critical_interference_ms": by_category.get("kswapd", 0.0),
                "gc_critical_interference_ms": by_category.get("gc", 0.0),
                "irq_critical_interference_ms": by_category.get("irq_softirq", 0.0),
                "dexopt_critical_interference_ms": by_category.get("dexopt", 0.0),
                "systemui_critical_interference_ms": by_category.get("systemui_shell", 0.0),
                "vendor_critical_interference_ms": by_category.get("vendor", 0.0),
            }
        )
        top_edges = sorted(edges, key=lambda item: item.get("overlap_ms", 0.0), reverse=True)[:10]
        state.add_finding(
            SkillFinding(
                finding_id=f"{label}-P8-CPU-OWNERS",
                skill="system-interference-analysis",
                trace_label=label,
                title="Launch-window CPU ownership and exact critical interference",
                category="system_interference",
                severity="WARNING" if top_edges and top_edges[0]["overlap_ms"] >= 5 else "INFO",
                confidence="HIGH" if context.observability.get("sched") else "LOW",
                value={"top_cpu_owners": top_owners, "critical_overlap_by_category": dict(by_category)},
                evidence=[
                    f"{edge['victim']} <- {edge['blocker_comm']}: {edge['overlap_ms']:.3f}ms"
                    for edge in top_edges
                ] or [f"{name}: {value:.3f}ms total CPU" for name, value in list(top_owners.items())[:10]],
                notes="Total CPU is context. Causal contribution is based only on exact blocker-running/victim-runnable overlap.",
                evidence_level="CONTRIBUTING" if top_edges else "CORRELATION",
                root_cause_key="cpu_interference",
                contribution_ms=sum(by_category.values()),
            )
        )

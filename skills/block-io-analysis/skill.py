from __future__ import annotations

import re

from app_entry_rca.core.helpers import analysis_window, critical_slices, state_for_slice, val
from app_entry_rca.core.models import SkillFinding

IO_CALLER_RE = re.compile(r"io_schedule|wait_on_page|filemap|submit_bio|blk_|ext4|f2fs|erofs|readpage|readahead", re.I)
RECLAIM_CALLER_RE = re.compile(r"reclaim|shrink|compact|alloc_pages|kswapd", re.I)
LOCK_CALLER_RE = re.compile(r"mutex|rwsem|inode|page_lock|folio_lock", re.I)
PAGE_EVENTS = ["mm_filemap_fault", "filemap_fault", "exceptions_page_fault_user"]
BLOCK_EVENTS = [
    "block_rq_insert", "block_rq_issue", "block_rq_complete", "block_bio_queue",
    "block_bio_complete", "block_getrq", "block_plug", "block_unplug",
]


def _classify_reason(iowait: int, caller: str) -> str:
    if RECLAIM_CALLER_RE.search(caller):
        return "MEMORY_RECLAIM"
    if iowait or IO_CALLER_RE.search(caller):
        return "STORAGE_OR_FILE_PAGE"
    if LOCK_CALLER_RE.search(caller):
        return "FILESYSTEM_OR_PAGE_LOCK"
    return "UNKNOWN_D_STATE"


def run(state, config):
    for label, context in state.contexts.items():
        trace = state.traces[label]
        start, end = analysis_window(context)
        marker_d = {}
        marker_reason = {}
        reason_totals = {"STORAGE_OR_FILE_PAGE": 0.0, "MEMORY_RECLAIM": 0.0, "FILESYSTEM_OR_PAGE_LOCK": 0.0, "UNKNOWN_D_STATE": 0.0}
        blocked = []
        for name, item in critical_slices(context).items():
            d_ms = val(state_for_slice(trace, item), "D")
            marker_d[name] = d_ms
            reasons = trace.blocked_reason_near(item.tid, item.ts, item.end)
            classified = []
            for ts, iowait, caller in reasons:
                kind = _classify_reason(iowait, caller)
                classified.append({"ts": ts, "iowait": iowait, "caller": caller, "classification": kind})
                blocked.append({"marker": name, "tid": item.tid, "ts": ts, "iowait": iowait, "caller": caller, "classification": kind})
            marker_reason[name] = classified
            if d_ms:
                if classified:
                    # The ftrace blocked reason is a point event, not a duration. Attribute
                    # the marker's D-state to the strongest reason only; never sum it twice.
                    order = ["MEMORY_RECLAIM", "STORAGE_OR_FILE_PAGE", "FILESYSTEM_OR_PAGE_LOCK", "UNKNOWN_D_STATE"]
                    chosen = next((kind for kind in order if any(x["classification"] == kind for x in classified)), "UNKNOWN_D_STATE")
                else:
                    chosen = "UNKNOWN_D_STATE"
                reason_totals[chosen] += d_ms

        finder = getattr(trace, "find_events", None)
        relevant_pids = {context.target_pid, context.launcher_pid, context.system_pid}
        if finder:
            fault_events = []
            for pid in relevant_pids:
                fault_events.extend(finder(PAGE_EVENTS, start=start, end=end, tgid=pid))
            block_events = finder(BLOCK_EVENTS, start=start, end=end)
        else:
            fault_events = [
                event for event in trace.events
                if start <= event.ts < end and event.event in PAGE_EVENTS and event.tgid in relevant_pids
            ]
            block_events = [event for event in trace.events if start <= event.ts < end and event.event in BLOCK_EVENTS]

        state.metrics[label].update(
            {
                "critical_d_state_ms": marker_d,
                "critical_d_total_ms": sum(marker_d.values()),
                "critical_io_d_ms": reason_totals["STORAGE_OR_FILE_PAGE"],
                "critical_reclaim_d_ms": reason_totals["MEMORY_RECLAIM"],
                "critical_fs_lock_d_ms": reason_totals["FILESYSTEM_OR_PAGE_LOCK"],
                "critical_unknown_d_ms": reason_totals["UNKNOWN_D_STATE"],
                "blocked_reason_summary": blocked,
                "blocked_reason_by_marker": marker_reason,
                "io_reason_observable": bool(blocked),
                "page_fault_event_count": len(fault_events),
                "block_io_event_count": len(block_events),
                "page_fault_events_observable": context.observability.get("page_fault", False),
                "block_io_events_observable": context.observability.get("block_io", False),
                "io_classification_totals_ms": reason_totals,
            }
        )
        total_d = sum(marker_d.values())
        if total_d > 0:
            confidence = "HIGH" if blocked else "LOW"
            state.add_finding(
                SkillFinding(
                    finding_id=f"{label}-IO-DSTATE",
                    skill="block-io-analysis",
                    trace_label=label,
                    title="Critical-path D-state classification",
                    category="block_io",
                    severity="WARNING",
                    confidence=confidence,
                    value={"total_d_ms": total_d, "by_origin_ms": reason_totals},
                    evidence=[
                        f"{name} D={value:.3f}ms" for name, value in marker_d.items() if value
                    ] + [f"{x['marker']}: {x['caller']} => {x['classification']}" for x in blocked[:10]],
                    notes="D-state without a blocked reason remains UNKNOWN_D_STATE and is not promoted to storage root cause.",
                    evidence_level="DIRECT" if blocked else "INSUFFICIENT",
                    root_cause_key="io:" + max(reason_totals, key=reason_totals.get),
                    contribution_ms=max(reason_totals.values()),
                )
            )

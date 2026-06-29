from __future__ import annotations

import re

from app_entry_rca.core.helpers import analysis_window, critical_slices, state_breakdown_for_markers, val
from app_entry_rca.core.models import SkillFinding

MONITOR_RE = re.compile(r"monitor contention with owner\s+(.+?)\s+at\s+(.+?)\s+waiters=", re.I)


def _node_id(kind: str, *parts) -> str:
    return kind + ":" + ":".join(str(part) for part in parts)


def _perfetto_binder_edges(trace, start: float, end: float, relevant_pids: set[int]):
    query = getattr(trace, "query_rows", None)
    if not query or not trace.capabilities().get("binder_transactions"):
        return []
    try:
        rows = query(
            "INCLUDE PERFETTO MODULE android.binder; "
            "SELECT aidl_name, interface, method_name, client_process, client_thread, "
            "client_tid, client_pid, client_ts, client_dur, server_process, server_thread, "
            "server_tid, server_pid, server_ts, server_dur, is_sync "
            "FROM android_binder_txns "
            f"WHERE client_ts < {int(end*1e9)} AND client_ts + client_dur > {int(start*1e9)} "
            "ORDER BY client_dur DESC"
        )
    except Exception:
        return []
    out = []
    for row in rows:
        client_pid = int(row.get("client_pid") or -1)
        server_pid = int(row.get("server_pid") or -1)
        if client_pid not in relevant_pids and server_pid not in relevant_pids:
            continue
        out.append(
            {
                "type": "binder",
                "client_pid": client_pid,
                "client_tid": int(row.get("client_tid") or -1),
                "client_process": str(row.get("client_process") or "unknown"),
                "client_thread": str(row.get("client_thread") or "unknown"),
                "server_pid": server_pid,
                "server_tid": int(row.get("server_tid") or -1),
                "server_process": str(row.get("server_process") or "unknown"),
                "server_thread": str(row.get("server_thread") or "unknown"),
                "interface": str(row.get("interface") or row.get("aidl_name") or "unknown"),
                "method": str(row.get("method_name") or "unknown"),
                "duration_ms": float(row.get("client_dur") or 0) / 1e6,
                "server_duration_ms": float(row.get("server_dur") or 0) / 1e6,
                "start_s": float(row.get("client_ts") or 0) / 1e9,
                "sync": bool(row.get("is_sync")),
                "confidence": "HIGH",
            }
        )
    return out


def run(state, config):
    for label, context in state.contexts.items():
        trace = state.traces[label]
        markers = context.marker_slices
        start, end = analysis_window(context)
        p1_start = markers.get("input_delivery") or markers.get("active_launch")
        p1_end = markers.get("do_active_launch") or markers.get("start_activity_server")
        p1_states = (
            trace.state_ms(context.launcher_pid, p1_start.ts, p1_end.ts)
            if p1_start and p1_end and context.launcher_pid > 0
            else {}
        )
        p1_blocked = (
            trace.blocked_reason_near(context.launcher_pid, p1_start.ts, p1_end.ts)
            if p1_start and p1_end and context.launcher_pid > 0
            else []
        )
        breakdown = state_breakdown_for_markers(trace, context)
        relevant_pids = {context.launcher_pid, context.system_pid, context.target_pid}

        dependency_edges = []
        graph_nodes = {}
        monitor_slices = trace.find_slices(r"monitor contention", start=start, end=end)
        for item in monitor_slices:
            if item.tgid not in relevant_pids:
                continue
            match = MONITOR_RE.search(item.name)
            owner = match.group(1) if match else "unknown"
            owner_location = match.group(2) if match else "unknown"
            edge = {
                "type": "monitor",
                "waiter_tid": item.tid,
                "waiter_tgid": item.tgid,
                "start_s": item.ts,
                "duration_ms": item.dur_ms,
                "owner": owner,
                "owner_location": owner_location,
                "slice": item.name,
                "confidence": "HIGH" if match else "MEDIUM",
            }
            dependency_edges.append(edge)
            waiter_id = _node_id("thread", item.tgid, item.tid)
            owner_id = _node_id("monitor_owner", owner, owner_location)
            graph_nodes[waiter_id] = {"id": waiter_id, "kind": "thread", "pid": item.tgid, "tid": item.tid}
            graph_nodes[owner_id] = {"id": owner_id, "kind": "monitor_owner", "name": owner, "location": owner_location}

        binder_edges = _perfetto_binder_edges(trace, start, end, relevant_pids)
        if not binder_edges:
            for item in trace.find_slices(r"AIDL::|binder", start=start, end=end):
                if item.tgid not in relevant_pids:
                    continue
                binder_edges.append(
                    {
                        "type": "binder_slice",
                        "client_pid": item.tgid,
                        "client_tid": item.tid,
                        "client_process": item.comm,
                        "client_thread": item.comm,
                        "server_pid": -1,
                        "server_tid": -1,
                        "server_process": "unresolved",
                        "server_thread": "unresolved",
                        "interface": item.name,
                        "method": item.name,
                        "duration_ms": item.dur_ms,
                        "server_duration_ms": None,
                        "start_s": item.ts,
                        "sync": None,
                        "confidence": "LOW",
                    }
                )

        graph_edges = []
        for edge in dependency_edges:
            graph_edges.append(
                {
                    "from": _node_id("thread", edge["waiter_tgid"], edge["waiter_tid"]),
                    "to": _node_id("monitor_owner", edge["owner"], edge["owner_location"]),
                    "type": "waits_for_monitor",
                    "duration_ms": edge["duration_ms"],
                    "confidence": edge["confidence"],
                    "trace": label,
                }
            )
        for edge in binder_edges:
            client_id = _node_id("thread", edge["client_pid"], edge["client_tid"])
            server_id = _node_id("thread", edge["server_pid"], edge["server_tid"])
            graph_nodes[client_id] = {"id": client_id, "kind": "thread", "pid": edge["client_pid"], "tid": edge["client_tid"], "name": edge["client_thread"]}
            graph_nodes[server_id] = {"id": server_id, "kind": "thread", "pid": edge["server_pid"], "tid": edge["server_tid"], "name": edge["server_thread"]}
            graph_edges.append(
                {
                    "from": client_id,
                    "to": server_id,
                    "type": "binder_call",
                    "interface": edge["interface"],
                    "method": edge["method"],
                    "duration_ms": edge["duration_ms"],
                    "confidence": edge["confidence"],
                    "trace": label,
                }
            )

        state.dependency_graph["nodes"].extend(graph_nodes.values())
        state.dependency_graph["edges"].extend(graph_edges)
        metrics = {
            "p1_sleeping_ms": val(p1_states, "Sleeping"),
            "p1_d_ms": val(p1_states, "D"),
            "p1_blocked_reasons": [{"ts": ts, "iowait": iowait, "caller": caller} for ts, iowait, caller in p1_blocked],
            "critical_sleeping_ms": {name: val(values, "Sleeping") for name, values in breakdown.items()},
            "critical_d_ms": {name: val(values, "D") for name, values in breakdown.items()},
            "attach_sleeping_ms": val(breakdown.get("attach_server", {}), "Sleeping"),
            "activity_thread_main_sleeping_ms": val(breakdown.get("activity_thread_main", {}), "Sleeping"),
            "bind_sleeping_ms": val(breakdown.get("bind_application", {}), "Sleeping"),
            "prebind_contention_ms": markers.get("prebind_contention").dur_ms if markers.get("prebind_contention") else None,
            "monitor_dependencies": dependency_edges,
            "binder_dependencies": binder_edges,
            "dependency_graph_edge_count": len(graph_edges),
            "longest_binder_ms": max((edge["duration_ms"] for edge in binder_edges), default=0.0),
            "longest_monitor_wait_ms": max((edge["duration_ms"] for edge in dependency_edges), default=0.0),
        }
        state.metrics[label].update(metrics)

        all_edges = dependency_edges + binder_edges
        if all_edges:
            top = max(all_edges, key=lambda item: item.get("duration_ms", 0.0))
            state.add_finding(
                SkillFinding(
                    finding_id=f"{label}-WAIT-DEPENDENCY",
                    skill="wait-dependency-analysis",
                    trace_label=label,
                    title="Longest launch dependency",
                    category="dependency_wait",
                    severity="WARNING" if top.get("duration_ms", 0.0) >= 5 else "INFO",
                    confidence=top.get("confidence", "MEDIUM"),
                    value=top,
                    evidence=[str(top)],
                    notes="Perfetto Binder tables are used when available. AIDL-only slices remain unresolved and cannot prove the remote origin.",
                    evidence_level="DIRECT" if top.get("confidence") == "HIGH" else "INSUFFICIENT",
                    root_cause_key=f"dependency:{top.get('type')}:{top.get('interface', top.get('owner', 'unknown'))}",
                    contribution_ms=float(top.get("duration_ms", 0.0)),
                )
            )

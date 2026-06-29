from __future__ import annotations

import hashlib
from pathlib import Path

from app_entry_rca.core.models import SkillFinding
from app_entry_rca.core.trace_loader import open_trace


def _sha256(path: str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run(state, config):
    requested_backend = state.options.get("backend", config.get("backend", "auto"))
    for label, path in state.inputs.items():
        trace = open_trace(
            path,
            backend=requested_backend,
            trace_processor=state.options.get("trace_processor"),
            traceconv=state.options.get("traceconv"),
        )
        # Query-backed backends intentionally do not materialize all events.
        event_count = len(getattr(trace, "events", []))
        if getattr(trace, "backend_name", "") == "systrace_text" and not event_count:
            raise ValueError(f"{label} trace contains no parseable ftrace events.")
        state.traces[label] = trace
        capabilities = trace.capabilities()
        counts_fn = getattr(trace, "summary_counts", None)
        counts = counts_fn() if callable(counts_fn) else {}
        state.capabilities[label] = capabilities
        state.metrics[label].update(
            {
                "source_path": path,
                "trace_backend": getattr(trace, "backend_name", "unknown"),
                "event_count": counts.get("event_count", event_count),
                "slice_count": counts.get("slice_count", len(getattr(trace, "slices", []))),
                "sched_interval_count": counts.get("thread_state_count", sum(len(v) for v in getattr(trace, "states", {}).values())),
                "trace_structural_counts": counts,
                "trace_start_s": trace.trace_start,
                "trace_end_s": trace.trace_end,
                "trace_duration_s": (
                    trace.trace_end - trace.trace_start
                    if trace.trace_start is not None and trace.trace_end is not None
                    else None
                ),
                "capabilities": capabilities,
            }
        )
        state.provenance.setdefault("traces", {})[label] = {
            "path": str(Path(path).resolve()),
            "sha256": _sha256(path),
            "backend": getattr(trace, "backend_name", "unknown"),
            "capabilities": capabilities,
        }
        missing_core = [name for name in ("sched", "wakeup") if not capabilities.get(name)]
        if missing_core:
            state.add_finding(
                SkillFinding(
                    finding_id=f"{label}-TRACE-CAPABILITY",
                    skill="trace-ingestion",
                    trace_label=label,
                    title="Core scheduler observability is incomplete",
                    category="observability",
                    severity="WARNING",
                    confidence="HIGH",
                    value=missing_core,
                    evidence=[f"missing capability: {x}" for x in missing_core],
                    notes="Running/Runnable attribution will be downgraded.",
                    evidence_level="DIRECT",
                )
            )

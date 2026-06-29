from __future__ import annotations

import pathlib
import subprocess
import tempfile
import zlib

from .perfetto_sql import PerfettoSqlTrace
from .systrace import Systrace
from .trace_backend import is_atrace_container


class UnsupportedTraceError(RuntimeError):
    pass


def _looks_like_ftrace(data: bytes) -> bool:
    head = data[:4096]
    return b"# tracer:" in head or b"tracing_mark_write:" in head


def load_trace_text(path: str, traceconv: str | None = None) -> str:
    """Load text ftrace/systrace from common Android trace containers.

    This is the compatibility backend. True Perfetto protobuf traces should use
    :func:`open_trace` with the Perfetto SQL backend to retain structured tables.
    """
    p = pathlib.Path(path)
    data = p.read_bytes()
    if _looks_like_ftrace(data):
        return data.decode("utf-8", errors="replace")
    marker = b"TRACE:\n"
    if marker in data:
        payload = data.split(marker, 1)[1]
        try:
            return zlib.decompress(payload).decode("utf-8", errors="replace")
        except zlib.error:
            if _looks_like_ftrace(payload):
                return payload.decode("utf-8", errors="replace")
    try:
        out = zlib.decompress(data)
        if _looks_like_ftrace(out):
            return out.decode("utf-8", errors="replace")
    except zlib.error:
        pass
    if traceconv:
        with tempfile.TemporaryDirectory(prefix="app_entry_trace_") as td:
            out = pathlib.Path(td) / "trace.systrace"
            proc = subprocess.run([traceconv, "systrace", str(p), str(out)], capture_output=True, text=True)
            if proc.returncode != 0:
                raise UnsupportedTraceError(f"traceconv failed ({proc.returncode}): {proc.stderr.strip()}")
            return out.read_text(encoding="utf-8", errors="replace")
    raise UnsupportedTraceError(
        f"Unsupported binary trace: {path}. Install the optional perfetto package "
        "and provide --trace-processor, or pass --traceconv only as a lossy fallback."
    )


def open_trace(
    path: str,
    *,
    backend: str = "auto",
    trace_processor: str | None = None,
    traceconv: str | None = None,
):
    """Open a trace with the highest-fidelity available backend.

    ``auto`` keeps atrace/systrace containers on the deterministic text parser
    and opens true Perfetto protobuf traces through Trace Processor. ``perfetto``
    forces SQL ingestion. ``systrace`` forces the compatibility parser.
    """
    backend = backend.lower().strip()
    if backend not in {"auto", "perfetto", "systrace"}:
        raise ValueError(f"Unknown trace backend: {backend}")
    atrace = is_atrace_container(path)
    if backend == "perfetto" or (backend == "auto" and not atrace):
        return PerfettoSqlTrace(path, trace_processor=trace_processor)
    text = load_trace_text(path, traceconv=traceconv)
    return Systrace(text, path)

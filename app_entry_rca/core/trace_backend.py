from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable, Any


@runtime_checkable
class TraceBackend(Protocol):
    """Common query contract used by every diagnostic skill.

    Backends may be a text systrace parser or Perfetto Trace Processor. Skills
    must depend on this contract instead of parsing a trace format directly.
    """

    source_path: str
    events: list[Any]
    slices: list[Any]
    states: dict[int, list[Any]]
    running: list[Any]
    thread_meta: dict[int, tuple[str, int]]
    blocked_reasons: dict[int, list[tuple[float, int, str]]]
    trace_start: float | None
    trace_end: float | None

    def find_slices(self, pattern=None, **kwargs): ...
    def state_ms(self, tid: int, start: float, end: float): ...
    def intervals(self, tid: int, state: str, start: float, end: float): ...
    def process_intervals(self, tgid: int, state: str, start: float, end: float): ...
    def blocked_reason_near(self, tid: int, start: float, end: float): ...
    def capabilities(self) -> dict[str, bool]: ...
    def close(self) -> None: ...


def is_atrace_container(path: str) -> bool:
    data = Path(path).read_bytes()[:8192]
    return b"TRACE:\n" in data or b"# tracer:" in data or b"tracing_mark_write:" in data

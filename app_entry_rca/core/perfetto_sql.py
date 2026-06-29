from __future__ import annotations

import collections
import re
from pathlib import Path
from typing import Any, Iterable, Optional, Pattern

from .models import Event, Slice, StateInterval


def _sql_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _literal_hint(pattern: str | Pattern[str] | None) -> str | None:
    if pattern is None or hasattr(pattern, "pattern"):
        text = getattr(pattern, "pattern", "")
    else:
        text = str(pattern)
    words = re.findall(r"[A-Za-z0-9_./:$ -]{4,}", text)
    words = [w.strip(" ^$.*?+()[]{}|\\") for w in words]
    words = [w for w in words if len(w) >= 4 and not any(ch in w for ch in "[](){}|\\")]
    return max(words, key=len, default=None)


class PerfettoSqlTrace:
    """Perfetto Trace Processor backend.

    The Python ``perfetto`` package is optional. On Windows it can launch an
    explicitly supplied ``trace_processor_shell.exe`` or download the official
    prebuilt when network access is available. The analyzer never silently
    converts a protobuf trace to systrace because that drops FrameTimeline,
    Binder, counter and structured thread-state data.
    """

    backend_name = "perfetto_sql"

    def __init__(self, source_path: str, trace_processor: str | None = None) -> None:
        try:
            from perfetto.trace_processor import TraceProcessor, TraceProcessorConfig
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "Perfetto protobuf input requires the optional 'perfetto' Python package. "
                "Run 'pip install perfetto' or use --backend systrace for atrace text."
            ) from exc
        config = TraceProcessorConfig(bin_path=trace_processor, load_timeout=60)
        self._tp = TraceProcessor(trace=source_path, config=config)
        self.source_path = source_path
        self.events: list[Event] = []
        self.slices: list[Slice] = []  # Deliberately query-backed; not a full-trace cache.
        self.states: dict[int, list[StateInterval]] = collections.defaultdict(list)
        self.running: list[StateInterval] = []
        self.thread_meta: dict[int, tuple[str, int]] = {}
        self.blocked_reasons: dict[int, list[tuple[float, int, str]]] = collections.defaultdict(list)
        self._slice_cache: dict[tuple, list[Slice]] = {}
        self._state_cache: dict[tuple, list[StateInterval]] = {}
        self._tables = self._load_tables()
        self._load_thread_meta()
        self.trace_start, self.trace_end = self._load_bounds()
        self._capabilities = self._detect_capabilities()

    def close(self) -> None:
        close = getattr(self._tp, "close", None)
        if close:
            close()

    def _query(self, sql: str) -> list[dict[str, Any]]:
        rows = []
        for row in self._tp.query(sql):
            if hasattr(row, "_asdict"):
                rows.append(dict(row._asdict()))
            elif hasattr(row, "__dict__"):
                rows.append(dict(row.__dict__))
            else:
                try:
                    rows.append(dict(row))
                except Exception:
                    names = getattr(row, "column_names", [])
                    rows.append({name: getattr(row, name) for name in names})
        return rows

    def query_rows(self, sql: str) -> list[dict[str, Any]]:
        return self._query(sql)

    def _load_tables(self) -> set[str]:
        rows = self._query("SELECT name FROM sqlite_master WHERE type IN ('table','view')")
        return {str(row.get("name")) for row in rows}

    def has_table(self, name: str) -> bool:
        return name in self._tables

    def _load_thread_meta(self) -> None:
        rows = self._query(
            "SELECT t.tid, COALESCE(t.name, printf('tid:%d', t.tid)) AS thread_name, "
            "COALESCE(p.pid, t.tid) AS pid FROM thread t LEFT JOIN process p USING(upid) "
            "WHERE t.tid IS NOT NULL"
        )
        for row in rows:
            self.thread_meta[int(row["tid"])] = (str(row["thread_name"]), int(row["pid"]))

    def _load_bounds(self) -> tuple[float | None, float | None]:
        rows = self._query("SELECT start_ts, end_ts FROM trace_bounds")
        if not rows:
            return None, None
        return float(rows[0]["start_ts"]) / 1e9, float(rows[0]["end_ts"]) / 1e9

    @staticmethod
    def _rx(pattern: str | Pattern[str] | None):
        if pattern is None:
            return None
        return pattern if hasattr(pattern, "search") else re.compile(str(pattern), re.I)

    def find_slices(
        self,
        pattern: str | Pattern[str] | None = None,
        *,
        tgid: int | None = None,
        tid: int | None = None,
        start: float | None = None,
        end: float | None = None,
    ) -> list[Slice]:
        key = (getattr(pattern, "pattern", pattern), tgid, tid, start, end)
        if key in self._slice_cache:
            return list(self._slice_cache[key])
        where = ["s.dur >= 0"]
        if tgid is not None:
            where.append(f"COALESCE(tp.pid, pp.pid, t.tid) = {int(tgid)}")
        if tid is not None:
            where.append(f"COALESCE(t.tid, pp.pid) = {int(tid)}")
        if start is not None:
            where.append(f"s.ts + s.dur > {int(start * 1e9)}")
        if end is not None:
            where.append(f"s.ts < {int(end * 1e9)}")
        hint = _literal_hint(pattern)
        if hint:
            where.append(f"s.name LIKE '%' || {_sql_quote(hint)} || '%'")
        sql = (
            "SELECT s.ts, s.dur, s.name, "
            "COALESCE(t.tid, pp.pid, 0) AS tid, "
            "COALESCE(tp.pid, pp.pid, t.tid, 0) AS pid, "
            "COALESCE(t.name, pp.name, tr.name, 'track') AS comm "
            "FROM slice s JOIN track tr ON s.track_id=tr.id "
            "LEFT JOIN thread_track tt ON s.track_id=tt.id "
            "LEFT JOIN thread t ON tt.utid=t.utid "
            "LEFT JOIN process tp ON t.upid=tp.upid "
            "LEFT JOIN process_track pt ON s.track_id=pt.id "
            "LEFT JOIN process pp ON pt.upid=pp.upid "
            f"WHERE {' AND '.join(where)} ORDER BY s.ts"
        )
        rx = self._rx(pattern)
        out = []
        for row in self._query(sql):
            name = str(row.get("name", ""))
            if rx and not rx.search(name):
                continue
            ts = float(row["ts"]) / 1e9
            dur = max(0.0, float(row["dur"]) / 1e9)
            out.append(
                Slice(ts, ts + dur, name, int(row["tid"]), int(row["pid"]), str(row["comm"]), -1, False)
            )
        self._slice_cache[key] = out
        return list(out)

    def first(self, pattern: str, **kwargs) -> Slice | None:
        return min(self.find_slices(pattern, **kwargs), key=lambda item: item.ts, default=None)

    def longest(self, pattern: str, **kwargs) -> Slice | None:
        return max(self.find_slices(pattern, **kwargs), key=lambda item: item.dur, default=None)

    def sum_slice_ms(self, pattern: str, **kwargs) -> float:
        return sum(item.dur_ms for item in self.find_slices(pattern, **kwargs))

    def _state_intervals(self, tid: int, start: float, end: float) -> list[StateInterval]:
        key = (tid, start, end)
        if key in self._state_cache:
            return list(self._state_cache[key])
        rows = self._query(
            "SELECT ts.ts, ts.dur, ts.state, ts.cpu, ts.io_wait, ts.blocked_function "
            "FROM thread_state ts JOIN thread t USING(utid) "
            f"WHERE t.tid={int(tid)} AND ts.ts + ts.dur > {int(start*1e9)} "
            f"AND ts.ts < {int(end*1e9)} ORDER BY ts.ts"
        )
        out = []
        for row in rows:
            st = max(start, float(row["ts"]) / 1e9)
            en = min(end, (float(row["ts"]) + max(0.0, float(row["dur"]))) / 1e9)
            state = str(row.get("state") or "Unknown")
            normalized = "Running" if state == "Running" else ("Runnable" if state in ("R", "R+") else state)
            cpu = row.get("cpu")
            out.append(StateInterval(st, en, normalized, tid, int(cpu) if cpu is not None else None))
            blocked = row.get("blocked_function")
            if blocked:
                self.blocked_reasons[tid].append((st, int(row.get("io_wait") or 0), str(blocked)))
        self._state_cache[key] = out
        return list(out)

    def state_ms(self, tid: int, start: float, end: float) -> dict[str, float]:
        counts: collections.Counter[str] = collections.Counter()
        for item in self._state_intervals(tid, start, end):
            counts[item.state] += item.dur_ms
        return dict(counts)

    def state_ms_for_process(self, tgid: int, start: float, end: float) -> dict[str, float]:
        counts: collections.Counter[str] = collections.Counter()
        for tid in self.tids_for_process(tgid):
            counts.update(self.state_ms(tid, start, end))
        return dict(counts)

    def intervals(self, tid: int, state: str, start: float, end: float) -> list[StateInterval]:
        return [item for item in self._state_intervals(tid, start, end) if item.state == state]

    def process_intervals(self, tgid: int, state: str, start: float, end: float) -> list[StateInterval]:
        out = []
        for tid in self.tids_for_process(tgid):
            out.extend(self.intervals(tid, state, start, end))
        return sorted(out, key=lambda item: (item.start, item.end, item.tid))

    @property
    def running_intervals(self) -> list[StateInterval]:
        if self.trace_start is None or self.trace_end is None:
            return []
        if not self.running:
            rows = self._query(
                "SELECT ts.ts, ts.dur, ts.cpu, t.tid FROM thread_state ts "
                "JOIN thread t USING(utid) WHERE ts.state='Running' ORDER BY ts.ts"
            )
            self.running = [
                StateInterval(
                    float(r["ts"]) / 1e9,
                    (float(r["ts"]) + float(r["dur"])) / 1e9,
                    "Running",
                    int(r["tid"]),
                    int(r["cpu"]) if r.get("cpu") is not None else None,
                )
                for r in rows
                if float(r.get("dur") or 0) >= 0
            ]
        return self.running

    def tids_for_process(self, tgid: int) -> list[int]:
        return [tid for tid, (_comm, pid) in self.thread_meta.items() if pid == tgid]

    def blocked_reason_near(self, tid: int, start: float, end: float):
        self._state_intervals(tid, start, end)
        return [item for item in self.blocked_reasons.get(tid, []) if start - 0.002 <= item[0] <= end + 0.002]

    def nested_slices(self, parent: Slice, pattern=None) -> list[Slice]:
        return [
            item
            for item in self.find_slices(pattern, tid=parent.tid, start=parent.ts, end=parent.end)
            if item.ts >= parent.ts and item.end <= parent.end and item != parent
        ]

    def sum_interval_overlap_ms(self, left: Iterable[StateInterval], right: Iterable[StateInterval]) -> float:
        return _overlap(left, right, same_cpu=False)

    def same_cpu_interval_overlap_ms(self, left: Iterable[StateInterval], right: Iterable[StateInterval]) -> float:
        return _overlap(left, right, same_cpu=True)

    def running_occupants(self, intervals: Iterable[StateInterval], cpus=(), exclude_tids=()) -> dict[str, float]:
        counter: collections.Counter[str] = collections.Counter()
        windows = list(intervals)
        allowed = set(cpus)
        excluded = set(exclude_tids)
        for run in self.running_intervals:
            if run.tid in excluded or (allowed and run.cpu not in allowed):
                continue
            overlap = _overlap([run], windows, same_cpu=False)
            if overlap <= 0:
                continue
            comm = self.thread_meta.get(run.tid, (f"tid:{run.tid}", run.tid))[0]
            if run.tid == 0 or comm.startswith("swapper") or comm == "<idle>":
                continue
            counter[comm] += overlap
        return dict(counter)

    def event_time_latency_ms(self, tgid: int, start: float, end: float):
        return None

    def _raw_events(self, names: Iterable[str], *, start=None, end=None, tgid=None) -> list[dict[str, Any]]:
        if "raw" not in self._tables:
            return []
        wanted = list(names)
        if not wanted:
            return []
        where = ["r.name IN (" + ",".join(_sql_quote(x) for x in wanted) + ")"]
        if start is not None:
            where.append(f"r.ts >= {int(start*1e9)}")
        if end is not None:
            where.append(f"r.ts < {int(end*1e9)}")
        if tgid is not None:
            where.append(f"COALESCE(p.pid,t.tid,0)={int(tgid)}")
        return self._query(
            "SELECT r.ts, r.name, r.cpu, r.arg_set_id, COALESCE(t.tid,0) AS tid, "
            "COALESCE(p.pid,t.tid,0) AS pid, COALESCE(t.name,'') AS comm "
            "FROM raw r LEFT JOIN thread t USING(utid) LEFT JOIN process p USING(upid) "
            f"WHERE {' AND '.join(where)} ORDER BY r.ts"
        )

    def sum_paired_event_ms(self, begin_event: str, end_event: str, *, tgid=None, tid=None, start=None, end=None) -> float:
        rows = self._raw_events([begin_event, end_event], start=start, end=end, tgid=tgid)
        stacks: dict[int, list[float]] = collections.defaultdict(list)
        total = 0.0
        for row in rows:
            row_tid = int(row.get("tid") or 0)
            if tid is not None and row_tid != int(tid):
                continue
            ts = float(row["ts"]) / 1e9
            if row["name"] == begin_event:
                stacks[row_tid].append(ts)
            elif row["name"] == end_event and stacks[row_tid]:
                begin = stacks[row_tid].pop()
                if ts > begin:
                    total += (ts - begin) * 1000.0
        return total

    def event_count(self, event_name: str) -> int:
        if "raw" not in self._tables:
            return 0
        rows = self._query(f"SELECT COUNT(*) AS c FROM raw WHERE name={_sql_quote(event_name)}")
        return int(rows[0]["c"]) if rows else 0

    def has_event(self, event_name: str) -> bool:
        return self.event_count(event_name) > 0

    def find_events(self, names: Iterable[str], *, start=None, end=None, tgid=None) -> list[Event]:
        rows = self._raw_events(names, start=start, end=end, tgid=tgid)
        return [
            Event(float(r["ts"])/1e9, str(r["name"]), f"arg_set_id={r.get('arg_set_id')}", int(r["tid"]), int(r["pid"]), str(r["comm"]), int(r.get("cpu") or -1))
            for r in rows
        ]

    def summary_counts(self) -> dict[str, int]:
        """Return cheap structural counts without materializing the trace."""
        queries = {
            "slice_count": "SELECT COUNT(*) AS c FROM slice",
            "thread_state_count": "SELECT COUNT(*) AS c FROM thread_state",
            "sched_slice_count": "SELECT COUNT(*) AS c FROM sched_slice",
            "process_count": "SELECT COUNT(*) AS c FROM process",
            "thread_count": "SELECT COUNT(*) AS c FROM thread",
        }
        out: dict[str, int] = {}
        for key, sql in queries.items():
            try:
                rows = self._query(sql)
                out[key] = int(rows[0]["c"]) if rows else 0
            except Exception:
                out[key] = 0
        return out

    def capabilities(self) -> dict[str, bool]:
        return dict(self._capabilities)

    def _raw_name_available(self, exact: Iterable[str] = (), prefixes: Iterable[str] = ()) -> bool:
        if "raw" not in self._tables:
            return False
        clauses = [f"name={_sql_quote(name)}" for name in exact]
        clauses.extend(f"name LIKE {_sql_quote(prefix + '%')}" for prefix in prefixes)
        if not clauses:
            return False
        try:
            rows = self._query("SELECT 1 AS found FROM raw WHERE " + " OR ".join(clauses) + " LIMIT 1")
            return bool(rows)
        except Exception:
            return False

    def _module_query_available(self, module: str, relation: str) -> bool:
        try:
            self._query(f"INCLUDE PERFETTO MODULE {module}; SELECT 1 FROM {relation} LIMIT 1")
            return True
        except Exception:
            return False

    def _detect_capabilities(self) -> dict[str, bool]:
        table = self._tables
        sample_end = min(self.trace_end or 0, (self.trace_start or 0) + 5.0)
        slice_names = "\n".join(
            item.name for item in self.find_slices(start=self.trace_start, end=sample_end)
        )
        binder_txns = self._module_query_available("android.binder", "android_binder_txns")
        android_startups = self._module_query_available("android.startup.startups", "android_startups")
        frame_timeline = any(
            name in table
            for name in ("actual_frame_timeline_slice", "expected_frame_timeline_slice", "frame_slice")
        )
        return {
            "backend_perfetto_sql": True,
            "sched": "thread_state" in table,
            "wakeup": "thread_state" in table,
            "blocked_reason": "thread_state" in table,
            "direct_reclaim": self._raw_name_available(exact=["mm_vmscan_direct_reclaim_begin", "mm_vmscan_direct_reclaim_end"]),
            "page_fault": self._raw_name_available(exact=["mm_filemap_fault", "filemap_fault", "exceptions_page_fault_user"]),
            "block_io": self._raw_name_available(prefixes=["block_"]),
            "cpu_frequency": "counter" in table,
            "binder_slices": bool(re.search(r"AIDL::|binder", slice_names, re.I)),
            "binder_transactions": binder_txns,
            "gc_slices": bool(re.search(r"WaitForGcToComplete|concurrent mark compact GC|CollectorTransition|\bGC\b", slice_names, re.I)),
            "render_slices": bool(re.search(r"DrawFrames|Vulkan|Texture upload|dequeueBuffer", slice_names, re.I)),
            "frame_timeline": frame_timeline,
            "art_slices": bool(re.search(r"OpenDexFilesFromOat|GetBestInfo|LoadedArsc|LoadApkAssets", slice_names, re.I)),
            "android_startups": android_startups,
            "counters": "counter" in table,
        }


def _overlap(left: Iterable[StateInterval], right: Iterable[StateInterval], same_cpu: bool) -> float:
    total = 0.0
    for a in left:
        for b in right:
            if same_cpu and a.cpu is not None and b.cpu is not None and a.cpu != b.cpu:
                continue
            total += max(0.0, min(a.end, b.end) - max(a.start, b.start)) * 1000.0
    return total


from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

from app_entry_rca.core.models import AnalysisState, LaunchContext, Slice, StateInterval


class FakeTrace:
    def __init__(self):
        self.thread_meta = {101: ("main", 1000)}
        self._states = [
            StateInterval(1.0, 1.004, "Running", 101, 4),
            StateInterval(1.004, 1.006, "Runnable", 101, 4),
            StateInterval(1.006, 1.012, "Running", 101, 5),
        ]

    def state_ms(self, tid, start, end):
        out = {}
        for item in self._states:
            if item.tid != tid:
                continue
            ov = max(0.0, min(end, item.end) - max(start, item.start)) * 1000.0
            if ov:
                out[item.state] = out.get(item.state, 0.0) + ov
        return out

    def intervals(self, tid, state, start, end):
        result = []
        for item in self._states:
            if item.tid != tid or item.state != state:
                continue
            left = max(start, item.start)
            right = min(end, item.end)
            if right > left:
                result.append(StateInterval(left, right, state, tid, item.cpu))
        return result

    def query_rows(self, sql):
        # Enough to exercise cpu_counter_track path.
        return [
            {"ts": 0.9e9, "value": 1200000, "cpu": 4, "name": "cpu4_frequency"},
            {"ts": 1.005e9, "value": 1800000, "cpu": 5, "name": "cpu5_frequency"},
        ]


def test_cpu_core_frequency_skill_fake_trace(tmp_path):
    from importlib.util import spec_from_file_location, module_from_spec

    skill_path = Path("skills/cpu-core-frequency-analysis/skill.py")
    spec = spec_from_file_location("cpu_core_frequency_skill", skill_path)
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)

    marker = Slice(1.0, 1.012, "activityStart", 101, 1000, "main", 4)
    ctx = LaunchContext(
        source_path="fake",
        target_package="pkg",
        launch_type="cold",
        target_pid=1000,
        system_pid=200,
        launcher_pid=300,
        render_tid=102,
        marker_slices={"activity_start": marker},
        observability={"sched": True, "cpu_frequency": True, "counters": True},
        phase_windows={"P4": [{"name": "activityStart", "start_s": 1.0, "end_s": 1.012, "duration_ms": 12.0}]},
    )
    state = AnalysisState(
        project_root=Path("."),
        inputs={},
        options={"out": str(tmp_path)},
        traces={"DUT": FakeTrace(), "REF": FakeTrace()},
        contexts={"DUT": ctx, "REF": ctx},
    )

    mod.run(state, {"big_cpus": [4, 5]})

    subject = state.metrics["DUT"]["cpu_core_frequency_by_subject"]["phase.P4"]
    assert subject["dominant_cpu"] == 5
    assert subject["running_ms_by_cpu"]["4"] == 4.0
    assert subject["running_ms_by_cpu"]["5"] == 6.0
    assert subject["migration_count"] == 1
    assert subject["avg_freq_khz_running_weighted"] is not None
    assert state.skill_findings

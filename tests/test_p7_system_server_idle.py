from pathlib import Path
from types import SimpleNamespace

import json
import yaml

from app_entry_rca.reporting.writers import _build_ms_diff_summary


def test_p7_taxonomy_uses_system_server_activity_idle_endpoint():
    root = Path(__file__).parents[1]
    registry = {item["id"]: item for item in json.loads((root / "taxonomy" / "leaf_registry.json").read_text())}
    assert registry["p7.activityidle.post_first_frame_tail.post_first_frame_tail_to_activityidle"]["name"] == "post-first-frame tail to activityIdle"
    assert registry["p7.activityidle.activityidle_reporting.activity_idle_server"]["name"] == "IActivityClientController::activityIdle server side"
    assert "p7.activityidle.post_first_frame_tail.idlehandler_or_messagequeue_work" in registry
    assert "p7.activityidle.activityidle_reporting.activity_idle_monitor_contention" in registry

    rules = {item["leaf"]: item for item in yaml.safe_load((root / "taxonomy" / "leaf_rules.yaml").read_text())["rules"]}
    assert rules["p7.activityidle.post_first_frame_tail.post_first_frame_tail_to_activityidle"]["metric"] == "p7_to_activity_idle_server_ms"
    assert rules["p7.activityidle.post_first_frame_tail.post_first_frame_tail_to_activityidle"]["causality"] == "CORRELATION_ONLY"
    assert rules["p7.activityidle.activityidle_reporting.activity_idle_server"]["metric"] == "activity_idle_server_ms"
    assert rules["p7.activityidle.activityidle_reporting.activity_idle_monitor_contention"]["metric"] == "activity_idle_server_monitor_contention_ms"


def test_ms_summary_exposes_system_server_idle_completion():
    state = SimpleNamespace(
        metrics={
            "DUT": {
                "input_to_first_frame_proxy_ms": 500.0,
                "first_frame_proxy_semantics": "finishDrawing_start",
                "input_to_activity_idle_server_ms": 650.0,
                "activity_idle_endpoint_semantics": "IActivityClientController::activityIdle::server_end",
                "p7_to_activity_idle_server_ms": 140.0,
                "activity_idle_server_ms": 8.0,
                "activity_idle_server_running_ms": 3.0,
                "activity_idle_server_runnable_ms": 1.0,
                "activity_idle_server_sleeping_ms": 4.0,
                "activity_idle_server_d_ms": 0.0,
                "activity_idle_server_monitor_contention_ms": 2.0,
                "activity_idle_client_to_server_ms": None,
            },
            "REF": {
                "input_to_first_frame_proxy_ms": 480.0,
                "first_frame_proxy_semantics": "finishDrawing_start",
                "input_to_activity_idle_server_ms": 560.0,
                "activity_idle_endpoint_semantics": "IActivityClientController::activityIdle::server_end",
                "p7_to_activity_idle_server_ms": 70.0,
                "activity_idle_server_ms": 3.0,
                "activity_idle_server_running_ms": 2.0,
                "activity_idle_server_runnable_ms": 0.0,
                "activity_idle_server_sleeping_ms": 1.0,
                "activity_idle_server_d_ms": 0.0,
                "activity_idle_server_monitor_contention_ms": 0.0,
                "activity_idle_client_to_server_ms": None,
            },
        }
    )
    result = _build_ms_diff_summary(state)
    assert result["completion_endpoint"]["delta_ms"] == 90.0
    p7 = next(item for item in result["contributors"] if item["id"] == "p7_to_system_server_activity_idle")
    assert p7["local_delta_ms"] == 70.0
    assert p7["nested_deltas_ms"]["server_handler_ms"] == 5.0
    assert p7["additive"] is False

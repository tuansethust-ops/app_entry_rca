import json
from pathlib import Path

import yaml


def test_leaf_registry_and_rules_are_consistent():
    root = Path(__file__).parents[1]
    registry = json.loads((root / "taxonomy" / "leaf_registry.json").read_text())
    ids = [item["id"] for item in registry]
    assert len(ids) == len(set(ids))
    assert len(ids) >= 120
    assert "p1.touch_duration.input_event_window.touch_down_to_touch_up" in ids
    assert "p3.bindapplication_activitystart.framework_bind_application.bind_application" in ids
    assert "p7.activityidle.activityidle_reporting.activity_idle_server" in ids
    rules = yaml.safe_load((root / "taxonomy" / "leaf_rules.yaml").read_text())["rules"]
    rule_ids = [item["leaf"] for item in rules]
    assert len(rule_ids) == len(set(rule_ids))
    assert set(rule_ids).issubset(set(ids))


def test_p8_gc_overlap_leaf_has_correct_evidence_contract():
    root = Path(__file__).parents[1]
    registry = {item["id"]: item for item in json.loads((root / "taxonomy" / "leaf_registry.json").read_text())}
    required = registry["p8.cross_cutting_system_evidence.memory_gc_reclaim.gc_overlap_only"]["required_evidence"]
    assert "absence of direct blocking evidence" in required

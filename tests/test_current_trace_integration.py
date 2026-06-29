import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.skipif(not os.getenv("DUT_TRACE") or not os.getenv("REF_TRACE"), reason="Set DUT_TRACE and REF_TRACE for golden integration test.")
def test_current_pair(tmp_path):
    root = Path(__file__).parents[1]
    out = tmp_path / "out"
    subprocess.check_call(
        [
            sys.executable,
            str(root / "app_entry_rca.py"),
            "--dut",
            os.environ["DUT_TRACE"],
            "--ref",
            os.environ["REF_TRACE"],
            "--out",
            str(out),
        ]
    )
    primary = json.loads((out / "final_leaf.json").read_text())
    assert primary["id"] == "DUT-R04"
    assert any(x.startswith("p3.bindapplication_activitystart.") or x.startswith("p7.activityidle.") for x in primary["mapped_leaf_ids"])
    assert isinstance(primary["evidence"][0], dict)
    all_leaf = json.loads((out / "all_leaf_nodes.json").read_text())
    assert all_leaf["leaf_count"] >= 120
    summary = json.loads((out / "analysis_summary.json").read_text())
    assert summary["validation"] == "PARTIALLY_COMPARABLE"
    coverage = json.loads((out / "automation_coverage.json").read_text())
    assert coverage["total_leaves"] >= 120
    assert coverage["automated_rule_leaves"] >= 35
    assert coverage["automated_rule_leaves"] < coverage["total_leaves"]

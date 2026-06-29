from __future__ import annotations

import importlib.util
from pathlib import Path

from app_entry_rca.core.models import AnalysisState, LeafResult


def load_ranking():
    path = Path(__file__).parents[1] / "skills" / "evidence-graph-ranking" / "skill.py"
    spec = importlib.util.spec_from_file_location("ranking_guardrail_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def make_state(tmp_path, leaves, dut=None, ref=None, options=None):
    state = AnalysisState(
        project_root=Path(__file__).parents[1],
        inputs={},
        options=options or {},
    )
    state.metrics = {"DUT": dut or {}, "REF": ref or {}}
    state.validation = {"decision": "VALID"}
    state.leaves = leaves
    state.active_phases = sorted({leaf.phase for leaf in leaves})
    return state


def leaf(leaf_id, *, causality, metric, dut, ref, root, phase="P8", evidence_level=None):
    return LeafResult(
        leaf_id=leaf_id,
        leaf_name=leaf_id,
        phase=phase,
        phase_name=phase,
        group=leaf_id.rsplit(".", 1)[0],
        group_name=leaf_id.rsplit(".", 1)[0],
        status="DUT_REGRESSION",
        causality=causality,
        confidence="HIGH" if causality != "CORRELATION_ONLY" else "LOW",
        metric_name=metric,
        dut_value=dut,
        ref_value=ref,
        delta_value=dut-ref,
        contribution_ms=dut-ref if metric.endswith("_ms") else None,
        root_cause_key=root,
        evidence_level=evidence_level or causality,
        evidence=[metric],
        observability="OBSERVED",
    )


def test_correlation_only_not_promoted_by_default(tmp_path):
    module = load_ranking()
    state = make_state(tmp_path, [leaf("p8.cross_cutting_system_evidence.memory_gc_reclaim.kswapd_competition", causality="CORRELATION_ONLY", metric="kswapd_cpu_ms", dut=50, ref=0, root="memory:kswapd_activity")], dut={"kswapd_cpu_ms": 50}, ref={"kswapd_cpu_ms": 0})
    module.run(state, {})
    assert state.final_leaves == []


def test_correlation_can_be_included_explicitly(tmp_path):
    module = load_ranking()
    state = make_state(tmp_path, [leaf("p8.cross_cutting_system_evidence.memory_gc_reclaim.gc_overlap_only", causality="CORRELATION_ONLY", metric="gc_overlap_ms", dut=500, ref=0, root="gc:overlap_only")], dut={"gc_overlap_ms": 500}, ref={"gc_overlap_ms": 0}, options={"include_correlation_candidates": True})
    module.run(state, {})
    assert len(state.final_leaves) == 1
    assert state.final_leaves[0].causality == "CORRELATION_ONLY"


def test_exact_kswapd_competition_is_final_candidate(tmp_path):
    module = load_ranking()
    state = make_state(tmp_path, [leaf("p8.cross_cutting_system_evidence.memory_gc_reclaim.kswapd_competition", causality="CONTRIBUTING", metric="kswapd_critical_overlap_ms", dut=12, ref=0, root="memory:kswapd_competition")], dut={"kswapd_critical_overlap_ms": 12}, ref={"kswapd_critical_overlap_ms": 0})
    module.run(state, {})
    assert len(state.final_leaves) == 1
    final = state.final_leaves[0]
    assert final.root_cause_key == "memory:kswapd_competition"
    assert "same-CPU" in final.symptom


def test_direct_gc_wait_supersedes_overlap_observation(tmp_path):
    module = load_ranking()
    direct = leaf("p8.cross_cutting_system_evidence.memory_gc_reclaim.wait_for_gc_to_complete", causality="DIRECT", metric="wait_for_gc_ms", dut=20, ref=0, root="gc:wait_for_completion")
    overlap = leaf("p8.cross_cutting_system_evidence.memory_gc_reclaim.gc_overlap_only", causality="CORRELATION_ONLY", metric="gc_overlap_ms", dut=500, ref=0, root="gc:overlap_only")
    state = make_state(tmp_path, [direct, overlap], dut={"wait_for_gc_ms": 20, "gc_overlap_ms": 500}, ref={"wait_for_gc_ms": 0, "gc_overlap_ms": 0})
    module.run(state, {})
    assert len(state.final_leaves) == 1
    assert state.final_leaves[0].root_cause_key == "gc:wait_for_completion"


def test_duplicate_direct_reclaim_leaves_are_grouped(tmp_path):
    module = load_ranking()
    a = leaf("p6.first_choreographer_doframe_activityidle.view_traversal_and_draw.traversal", causality="DIRECT", metric="critical_direct_reclaim_ms", dut=18, ref=0, root="memory:direct_reclaim", phase="P6")
    b = leaf("p8.cross_cutting_system_evidence.memory_gc_reclaim.direct_reclaim", causality="DIRECT", metric="critical_direct_reclaim_ms", dut=18, ref=0, root="memory:direct_reclaim", phase="P8")
    state = make_state(tmp_path, [a, b], dut={"critical_direct_reclaim_ms": 18}, ref={"critical_direct_reclaim_ms": 0})
    module.run(state, {})
    assert len(state.final_leaves) == 1
    assert set(state.final_leaves[0].mapped_leaf_ids) == {"p6.first_choreographer_doframe_activityidle.view_traversal_and_draw.traversal", "p8.cross_cutting_system_evidence.memory_gc_reclaim.direct_reclaim"}

from __future__ import annotations

from typing import Any

from app_entry_rca.core.config import load_json, load_yaml
from app_entry_rca.core.models import LeafResult


def _status(dut, ref, threshold, *, one_sided_status="INSUFFICIENT_EVIDENCE"):
    if dut is None and ref is None:
        return "NOT_OBSERVABLE"
    if dut is None:
        return "REF_ONLY" if one_sided_status == "PRESENT_ONLY" else "INSUFFICIENT_EVIDENCE"
    if ref is None:
        return "DUT_ONLY" if one_sided_status == "PRESENT_ONLY" else "INSUFFICIENT_EVIDENCE"
    if abs(float(dut) - float(ref)) <= threshold:
        return "EQUIVALENT"
    return "DUT_REGRESSION" if float(dut) > float(ref) else "DUT_BETTER"


def _capabilities_available(state, names, *, any_of=False):
    if not names:
        return True
    per_trace = []
    for label in ("DUT", "REF"):
        caps = state.capabilities.get(label, {})
        per_trace.append(any(caps.get(name, False) for name in names) if any_of else all(caps.get(name, False) for name in names))
    return all(per_trace)


def _applicable(state, rule):
    applicability = rule.get("applicability")
    if applicability == "cold":
        return all(context.launch_type == "cold" for context in state.contexts.values())
    if applicability in {"warm", "hot"}:
        return all(context.launch_type == applicability for context in state.contexts.values())
    return True


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (list, dict, tuple, set, str)):
        return len(value) > 0
    return True


def _condition(metrics: dict, condition: dict) -> bool:
    value = metrics.get(condition.get("metric"))
    op = condition.get("op", "present")
    target = condition.get("value")
    if op == "present":
        return _present(value)
    if op == "absent":
        return not _present(value)
    if not isinstance(value, (int, float)):
        return False
    if op == ">": return value > target
    if op == ">=": return value >= target
    if op == "<": return value < target
    if op == "<=": return value <= target
    if op == "==": return value == target
    if op == "!=": return value != target
    raise ValueError(f"Unsupported rule condition op: {op}")


def _conditions(metrics: dict, conditions: list[dict], *, mode="all") -> bool:
    if not conditions:
        return True
    values = [_condition(metrics, item) for item in conditions]
    return all(values) if mode == "all" else any(values)


def run(state, config):
    registry = load_json(state.project_root / "taxonomy" / "leaf_registry.json")
    rule_doc = load_yaml(state.project_root / "taxonomy" / "leaf_rules.yaml")
    rules = {item["leaf"]: item for item in rule_doc.get("rules", [])}
    dut = state.metrics["DUT"]
    ref = state.metrics["REF"]

    for metrics in (dut, ref):
        outer = metrics.get("start_activity_server_ms")
        inner = metrics.get("start_activity_inner_ms")
        metrics["p2_outer_exclusive_ms"] = max(0.0, outer - inner) if outer is not None and inner is not None else None

    output = []
    for item in registry:
        leaf = LeafResult(
            leaf_id=item["id"],
            leaf_name=item["name"],
            phase=item["phase"],
            phase_name=item["phase_name"],
            group=item["group"],
            group_name=item["group_name"],
            required_evidence=item.get("required_evidence", []),
            notes=item.get("notes", ""),
        )
        rule = rules.get(item["id"])
        if not rule:
            leaf.taxonomy_action = "No automatic rule: retain as an explicit candidate, not as evidence of equivalence."
            leaf.missing_evidence = list(leaf.required_evidence)
            output.append(leaf)
            continue
        leaf.rule_id = str(rule.get("id", f"RULE-{item['id']}"))
        leaf.root_cause_key = str(rule.get("root_cause_key", item["group"]))

        if not _applicable(state, rule):
            leaf.status = "NOT_APPLICABLE"
            leaf.causality = "REJECTED"
            leaf.confidence = "HIGH"
            leaf.observability = "NOT_APPLICABLE"
            leaf.interpretation = "This leaf does not apply to the detected launch type."
            output.append(leaf)
            continue

        required_caps = rule.get("capabilities", [])
        required_any_caps = rule.get("capabilities_any", [])
        if not _capabilities_available(state, required_caps) or not _capabilities_available(state, required_any_caps, any_of=True):
            missing = [name for name in required_caps if not _capabilities_available(state, [name])]
            if required_any_caps and not _capabilities_available(state, required_any_caps, any_of=True):
                missing.append("any of: " + ", ".join(required_any_caps))
            leaf.status = "NOT_OBSERVABLE"
            leaf.causality = "REJECTED"
            leaf.confidence = "LOW"
            leaf.observability = "MISSING_CAPABILITY"
            leaf.missing_evidence = missing
            leaf.interpretation = f"Missing trace capabilities: {', '.join(missing)}."
            leaf.taxonomy_action = "Enable the required Perfetto/ftrace data source before evaluating this leaf."
            output.append(leaf)
            continue

        required_metrics = rule.get("requires_metrics_all", [])
        missing_metrics = [name for name in required_metrics if not (_present(dut.get(name)) or _present(ref.get(name)))]
        if missing_metrics:
            leaf.status = "NOT_OBSERVABLE"
            leaf.causality = "REJECTED"
            leaf.confidence = "LOW"
            leaf.observability = "MISSING_METRIC"
            leaf.missing_evidence = missing_metrics
            leaf.interpretation = f"Required metrics were not emitted: {', '.join(missing_metrics)}."
            output.append(leaf)
            continue

        metric = rule["metric"]
        dut_value = dut.get(metric)
        ref_value = ref.get(metric)
        fallback = rule.get("fallback_metric")
        using_fallback = False
        if dut_value is None and ref_value is None and fallback:
            metric = fallback
            dut_value = dut.get(metric)
            ref_value = ref.get(metric)
            using_fallback = True

        threshold = float(rule.get("threshold", rule.get("threshold_ms", 1.0)))
        status = _status(dut_value, ref_value, threshold, one_sided_status=rule.get("one_sided_status", "INSUFFICIENT_EVIDENCE"))
        unit = rule.get("unit", "ms")
        leaf.metric_name = metric
        leaf.metric_unit = unit
        leaf.dut_value = float(dut_value) if isinstance(dut_value, (int, float)) else None
        leaf.ref_value = float(ref_value) if isinstance(ref_value, (int, float)) else None
        leaf.delta_value = leaf.dut_value - leaf.ref_value if leaf.dut_value is not None and leaf.ref_value is not None else None
        leaf.threshold_value = threshold
        if unit == "ms":
            leaf.dut_value_ms = leaf.dut_value
            leaf.ref_value_ms = leaf.ref_value
            leaf.delta_ms = leaf.delta_value
            leaf.threshold_ms = threshold
        leaf.status = status
        leaf.confidence = rule.get("confidence", "MEDIUM")
        leaf.causality = rule.get("causality", "CORRELATION_ONLY")
        leaf.evidence_level = rule.get("evidence_level", leaf.causality)
        leaf.observability = "OBSERVED" if status not in ("NOT_OBSERVABLE", "INSUFFICIENT_EVIDENCE") else status
        leaf.evidence = [metric] + list(rule.get("evidence_metrics", []))
        leaf.interpretation = f"{metric}: DUT={dut_value}, REF={ref_value}, threshold={threshold}."
        leaf.taxonomy_action = "Evaluated from a versioned evidence rule."
        if using_fallback:
            leaf.interpretation += f" Fallback metric used; causality is capped at {rule.get('fallback_causality', 'CORRELATION_ONLY')}."
            leaf.causality = rule.get("fallback_causality", "CORRELATION_ONLY")
            leaf.confidence = "LOW"

        affected_metrics = dut if status in ("DUT_REGRESSION", "DUT_ONLY") else ref
        causal_conditions = rule.get("causality_requires", [])
        if causal_conditions and status in ("DUT_REGRESSION", "DUT_BETTER", "DUT_ONLY", "REF_ONLY"):
            if not _conditions(affected_metrics, causal_conditions, mode=rule.get("causality_requires_mode", "all")):
                leaf.causality = rule.get("causality_fallback", "CORRELATION_ONLY")
                leaf.confidence = rule.get("causality_fallback_confidence", "LOW")
                leaf.missing_evidence = [str(item) for item in causal_conditions]
                leaf.interpretation += " Causal prerequisite was not satisfied."

        contradiction_conditions = rule.get("contradictions", [])
        for condition in contradiction_conditions:
            if _condition(affected_metrics, condition):
                leaf.contradictions.append(str(condition))
        if leaf.contradictions:
            leaf.causality = "REJECTED"
            leaf.confidence = "HIGH"
            leaf.interpretation += " Contradictory evidence rejected this hypothesis."

        if status in ("NOT_OBSERVABLE", "INSUFFICIENT_EVIDENCE", "EQUIVALENT"):
            leaf.causality = "REJECTED"
            leaf.evidence_level = "NONE"
        elif status in ("DUT_ONLY", "REF_ONLY") and leaf.causality == "DIRECT" and not rule.get("one_sided_causal", False):
            leaf.causality = "CORRELATION_ONLY"
            leaf.confidence = "MEDIUM"

        causal_caps = rule.get("causal_capabilities", [])
        if causal_caps and not _capabilities_available(state, causal_caps) and status in ("DUT_REGRESSION", "DUT_BETTER"):
            leaf.causality = "CORRELATION_ONLY"
            leaf.confidence = "MEDIUM"
            leaf.missing_evidence.extend(causal_caps)
            leaf.interpretation += f" Causality downgraded because {causal_caps} are unavailable."

        contribution_metric = rule.get("contribution_metric", metric)
        dut_contribution = dut.get(contribution_metric)
        ref_contribution = ref.get(contribution_metric)
        if rule.get("unit", "ms") == "ms":
            if isinstance(dut_contribution, (int, float)) and isinstance(ref_contribution, (int, float)):
                paired_delta = float(dut_contribution) - float(ref_contribution)
                if status == "DUT_REGRESSION":
                    leaf.contribution_ms = max(0.0, paired_delta)
                elif status == "DUT_BETTER":
                    leaf.contribution_ms = max(0.0, -paired_delta)
                else:
                    leaf.contribution_ms = 0.0
            elif status == "DUT_ONLY" and isinstance(dut_contribution, (int, float)):
                leaf.contribution_ms = max(0.0, float(dut_contribution))
            elif status == "REF_ONLY" and isinstance(ref_contribution, (int, float)):
                leaf.contribution_ms = max(0.0, float(ref_contribution))
        output.append(leaf)

    by_id = {item.leaf_id: item for item in output}
    direct_gc = any(
        by_id.get(leaf_id) and by_id[leaf_id].status in {"DUT_REGRESSION", "DUT_ONLY"} and by_id[leaf_id].causality == "DIRECT"
        for leaf_id in ("p8.cross_cutting_system_evidence.direct_gc_blocking.waitforgctocomplete", "p8.cross_cutting_system_evidence.direct_gc_blocking.stw_pause", "p8.cross_cutting_system_evidence.direct_gc_blocking.allocation_stall")
    )
    if direct_gc:
        for leaf_id in ("p8.cross_cutting_system_evidence.gc_overlap_only.overlap_without_blocking_evidence", "p8.cross_cutting_system_evidence.gc_overlap_only.correlation_only_classification"):
            if leaf_id in by_id:
                by_id[leaf_id].causality = "REJECTED"
                by_id[leaf_id].contradictions.append("direct GC blocking evidence exists")
                by_id[leaf_id].interpretation += " Direct GC evidence supersedes overlap-only classification."

    if by_id.get("p8.cross_cutting_system_evidence.memory_pressure_reclaim_swap_and_churn.kswapd_same_cpu_competition_with_critical_runnable_thread") and by_id["p8.cross_cutting_system_evidence.memory_pressure_reclaim_swap_and_churn.kswapd_same_cpu_competition_with_critical_runnable_thread"].causality == "CONTRIBUTING":
        if "p8.cross_cutting_system_evidence.memory_pressure_reclaim_swap_and_churn.kswapd_activity_without_critical_overlap" in by_id:
            by_id["p8.cross_cutting_system_evidence.memory_pressure_reclaim_swap_and_churn.kswapd_activity_without_critical_overlap"].causality = "CORRELATION_ONLY"
            by_id["p8.cross_cutting_system_evidence.memory_pressure_reclaim_swap_and_churn.kswapd_activity_without_critical_overlap"].interpretation += " Exact kswapd competition is represented by p8.cross_cutting_system_evidence.memory_pressure_reclaim_swap_and_churn.kswapd_same_cpu_competition_with_critical_runnable_thread."

    state.leaves = output

from __future__ import annotations

from collections import defaultdict

from app_entry_rca.core.config import load_yaml

SKILL_CAPABILITIES = {
    "running-analysis": {"sched"},
    "runnable-analysis": {"sched", "wakeup"},
    "wait-dependency-analysis": {"blocked_reason", "binder_slices", "binder_transactions"},
    "block-io-analysis": {"blocked_reason", "page_fault", "block_io", "direct_reclaim"},
    "memory-gc-analysis": {"gc_slices", "direct_reclaim", "sched", "counters"},
    "art-runtime-analysis": {"art_slices"},
    "render-frame-analysis": {"render_slices", "frame_timeline"},
    "system-interference-analysis": {"sched"},
    "cpu-core-frequency-analysis": {"sched", "cpu_frequency", "counters"},
}


def select_analyzers(state) -> tuple[list[str], dict[str, list[str]]]:
    mapping = load_yaml(state.project_root / "taxonomy" / "candidate_analyzer_mapping.yaml")
    candidate_reasons: dict[str, list[str]] = defaultdict(list)
    for group in state.activated_groups:
        for skill in mapping.get(group, []):
            candidate_reasons[skill].append(f"activated group {group}")

    available = {
        name for context in state.contexts.values()
        for name, value in context.observability.items() if value
    }
    selected: dict[str, list[str]] = {}
    for skill, reasons in candidate_reasons.items():
        required_any = SKILL_CAPABILITIES.get(skill, set())
        if required_any and not (required_any & available):
            continue
        selected[skill] = reasons + ([f"observable capabilities: {sorted(required_any & available)}"] if required_any else [])

    # ART remains relevant for cold starts even when only generic runtime markers
    # are present. The skill will report individual sub-leaves as unobservable.
    if any(context.launch_type == "cold" for context in state.contexts.values()):
        if "art-runtime-analysis" in candidate_reasons:
            selected.setdefault("art-runtime-analysis", candidate_reasons["art-runtime-analysis"] + ["cold process launch"])

    return sorted(selected), {name: selected[name] for name in sorted(selected)}

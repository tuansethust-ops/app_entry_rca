from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass(slots=True)
class Event:
    ts: float
    event: str
    details: str
    tid: int
    tgid: int
    comm: str
    cpu: int


@dataclass(slots=True)
class Slice:
    ts: float
    end: float
    name: str
    tid: int
    tgid: int
    comm: str
    cpu: int
    async_slice: bool = False

    @property
    def dur(self) -> float:
        return max(0.0, self.end - self.ts)

    @property
    def dur_ms(self) -> float:
        return self.dur * 1000.0


@dataclass(slots=True)
class StateInterval:
    start: float
    end: float
    state: str
    tid: int
    cpu: Optional[int] = None

    @property
    def dur_ms(self) -> float:
        return max(0.0, self.end - self.start) * 1000.0


@dataclass
class LaunchContext:
    source_path: str
    target_package: str
    launch_type: str
    target_pid: int
    system_pid: int
    launcher_pid: int
    render_tid: int
    markers: Dict[str, Optional[float]] = field(default_factory=dict)
    marker_slices: Dict[str, Optional[Slice]] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    launch_type_evidence: List[str] = field(default_factory=list)
    framework_launch_type: Optional[str] = None
    endpoint_semantics: str = "unknown"
    observability: Dict[str, bool] = field(default_factory=dict)
    phase_windows: Dict[str, List[tuple[float, float]]] = field(default_factory=dict)
    milestones: Dict[str, Optional[float]] = field(default_factory=dict)
    critical_threads: Dict[str, int] = field(default_factory=dict)


@dataclass
class SkillFinding:
    finding_id: str
    skill: str
    trace_label: str
    title: str
    category: str
    severity: str
    confidence: str
    phase: Optional[str] = None
    group: Optional[str] = None
    metric_name: Optional[str] = None
    value: Any = None
    evidence: List[Any] = field(default_factory=list)
    notes: str = ""
    rule_id: str = ""
    evidence_level: str = "NONE"
    missing_evidence: List[str] = field(default_factory=list)
    contradictions: List[str] = field(default_factory=list)
    root_cause_key: str = ""
    contribution_ms: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LeafResult:
    leaf_id: str
    leaf_name: str
    phase: str
    phase_name: str
    group: str
    group_name: str
    status: str = "NOT_OBSERVABLE"
    causality: str = "REJECTED"
    confidence: str = "LOW"
    metric_name: str = ""
    metric_unit: str = "ms"
    dut_value: Optional[float] = None
    ref_value: Optional[float] = None
    delta_value: Optional[float] = None
    threshold_value: Optional[float] = None
    dut_value_ms: Optional[float] = None
    ref_value_ms: Optional[float] = None
    delta_ms: Optional[float] = None
    threshold_ms: Optional[float] = None
    interpretation: str = "No trace evidence mapped to this leaf."
    evidence: List[str] = field(default_factory=list)
    taxonomy_action: str = "Keep candidate; add instrumentation if this leaf is important."
    required_evidence: List[str] = field(default_factory=list)
    observability: str = "NOT_OBSERVABLE"
    notes: str = ""
    rule_id: str = ""
    evidence_level: str = "NONE"
    missing_evidence: List[str] = field(default_factory=list)
    contradictions: List[str] = field(default_factory=list)
    root_cause_key: str = ""
    contribution_ms: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FinalLeaf:
    id: str
    mapped_leaf_ids: List[str]
    status: str
    causality: str
    confidence: str
    path: str
    symptom: str
    location: str
    mechanism: str
    origin: str
    ownership: str
    action: str
    metrics: Dict[str, Any] = field(default_factory=dict)
    evidence: List[Any] = field(default_factory=list)
    rejected_alternatives: List[str] = field(default_factory=list)
    verification: List[str] = field(default_factory=list)
    score: float = 0.0
    score_breakdown: Dict[str, float] = field(default_factory=dict)
    root_cause_key: str = ""
    contribution_ms: Optional[float] = None
    # Paired DUT-REF timing semantics. These fields intentionally separate
    # the local window delta from an exclusive contribution estimate.
    local_delta_ms: Optional[float] = None
    exclusive_contribution_ms: Optional[float] = None
    nested_deltas_ms: Dict[str, float] = field(default_factory=dict)
    overlap_group: str = ""
    additive: bool = False
    delta_note: str = ""
    verification_plan: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SkillRunRecord:
    skill: str
    status: str
    duration_ms: float
    version: str = "unknown"
    stage: str = "analysis"
    route_reason: str = "always"
    outputs: List[str] = field(default_factory=list)
    metrics_added: List[str] = field(default_factory=list)
    findings_added: int = 0
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AnalysisState:
    project_root: Path
    inputs: Dict[str, str]
    options: Dict[str, Any]
    traces: Dict[str, Any] = field(default_factory=dict)
    contexts: Dict[str, LaunchContext] = field(default_factory=dict)
    validation: Dict[str, Any] = field(default_factory=dict)
    phase_comparison: Dict[str, Any] = field(default_factory=dict)
    active_phases: List[str] = field(default_factory=list)
    activated_groups: List[str] = field(default_factory=list)
    selected_skills: List[str] = field(default_factory=list)
    routing_reasons: Dict[str, List[str]] = field(default_factory=dict)
    capabilities: Dict[str, Dict[str, bool]] = field(default_factory=dict)
    metrics: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {"DUT": {}, "REF": {}})
    metric_metadata: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    skill_findings: List[SkillFinding] = field(default_factory=list)
    leaves: List[LeafResult] = field(default_factory=list)
    final_leaves: List[FinalLeaf] = field(default_factory=list)
    evidence_graph: Dict[str, Any] = field(default_factory=dict)
    output_files: Dict[str, str] = field(default_factory=dict)
    skill_runs: List[SkillRunRecord] = field(default_factory=list)
    provenance: Dict[str, Any] = field(default_factory=dict)
    dependency_graph: Dict[str, Any] = field(default_factory=lambda: {"nodes": [], "edges": []})
    interference_edges: List[Dict[str, Any]] = field(default_factory=list)

    def add_finding(self, finding: SkillFinding) -> None:
        self.skill_findings.append(finding)

    def context_summary(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for label, c in self.contexts.items():
            out[label] = {
                "source_path": c.source_path,
                "target_package": c.target_package,
                "launch_type": c.launch_type,
                "framework_launch_type": c.framework_launch_type,
                "launch_type_evidence": c.launch_type_evidence,
                "target_pid": c.target_pid,
                "system_pid": c.system_pid,
                "launcher_pid": c.launcher_pid,
                "render_tid": c.render_tid,
                "markers": c.markers,
                "endpoint_semantics": c.endpoint_semantics,
                "observability": c.observability,
                "warnings": c.warnings,
                "phase_windows": c.phase_windows,
                "milestones": c.milestones,
                "critical_threads": c.critical_threads,
            }
        return out

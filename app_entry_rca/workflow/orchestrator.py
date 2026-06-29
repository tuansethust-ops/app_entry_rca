from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from app_entry_rca.core.config import load_yaml
from app_entry_rca.core.models import AnalysisState, SkillRunRecord
from app_entry_rca.core.skill_loader import execute_skill, load_skill_manifest


def _execution(step: dict) -> tuple[str, bool]:
    block = step.get("execution", {})
    mode = block.get("mode", step.get("route", "always"))
    if mode == "selected":
        mode = "routed"
    critical = bool(block.get("critical", step.get("critical", True)))
    if mode not in {"always", "routed"}:
        raise ValueError(f"Unsupported execution mode: {mode}")
    return mode, critical


def _validate_workflow(project_root: Path, workflow: dict) -> None:
    if str(workflow.get("schema_version", "")).split(".")[0] != "6":
        raise ValueError("Expected workflow schema_version 6.x")
    seen = set()
    for index, step in enumerate(workflow.get("steps", []), 1):
        if "skill" not in step:
            raise ValueError(f"workflow step {index} has no skill")
        name = step["skill"]
        _execution(step)
        manifest = load_skill_manifest(project_root, name)
        missing = [dep for dep in manifest.get("requires", []) if dep not in seen]
        if missing:
            raise ValueError(f"Skill {name} must run after: {', '.join(missing)}")
        seen.add(name)


def run_workflow(
    project_root: Path,
    workflow_path: Path,
    inputs: Dict[str, str],
    options: Dict[str, Any],
) -> AnalysisState:
    workflow = load_yaml(workflow_path)
    _validate_workflow(project_root, workflow)
    state = AnalysisState(project_root=project_root, inputs=inputs, options=options)
    state.provenance = {
        "workflow_name": workflow.get("name"),
        "workflow_version": workflow.get("version"),
        "workflow_schema_version": workflow.get("schema_version"),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "options": {k: v for k, v in options.items() if k not in {"secret"}},
    }
    fail_fast = bool(workflow.get("error_policy", {}).get("fail_fast", True))

    try:
        for step in workflow.get("steps", []):
            name = step["skill"]
            mode, critical = _execution(step)
            route_reason = "always"
            if mode == "routed":
                if name not in state.selected_skills:
                    manifest = load_skill_manifest(project_root, name)
                    state.skill_runs.append(
                        SkillRunRecord(
                            skill=name,
                            status="SKIPPED",
                            duration_ms=0.0,
                            version=str(manifest.get("version", "unknown")),
                            stage=str(manifest.get("stage", "analysis")),
                            route_reason="not selected: no activated observable candidate requires this skill",
                            warnings=["Skipped by evidence-aware router."],
                        )
                    )
                    continue
                route_reason = "; ".join(state.routing_reasons.get(name, ["selected by router"]))

            record = execute_skill(state, name, step.get("config", {}), route_reason=route_reason)
            state.skill_runs.append(record)
            if record.status == "ERROR" and critical and fail_fast:
                raise RuntimeError(f"Skill {name} failed: {record.error}")

        if state.output_files:
            from app_entry_rca.reporting.writers import dump
            out = Path(state.options.get("out", "app_entry_rca_out"))
            dump(out / "skill_runs.json", {
                "selected_skills": state.selected_skills,
                "routing_reasons": state.routing_reasons,
                "runs": [item.to_dict() for item in state.skill_runs],
            })
        return state
    finally:
        for trace in state.traces.values():
            try:
                trace.close()
            except Exception:
                pass

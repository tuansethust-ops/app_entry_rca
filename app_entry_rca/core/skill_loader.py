from __future__ import annotations

import importlib.util
import time
import traceback
from pathlib import Path

from .config import load_yaml
from .models import AnalysisState, SkillRunRecord


def load_skill_manifest(project_root: Path, skill_name: str) -> dict:
    root = project_root / "skills" / skill_name
    manifest_path = root / "skill.yaml"
    entrypoint_path = root / "skill.py"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Skill manifest not found: {manifest_path}")
    if not entrypoint_path.exists():
        raise FileNotFoundError(f"Skill entrypoint not found: {entrypoint_path}")
    manifest = load_yaml(manifest_path)
    if manifest.get("name") != skill_name:
        raise ValueError(f"Skill manifest name mismatch: expected {skill_name}, got {manifest.get('name')}")
    manifest.setdefault("version", "unknown")
    manifest.setdefault("stage", "analysis")
    manifest.setdefault("requires", [])
    manifest.setdefault("optional_requires", [])
    manifest.setdefault("entrypoint", "skill.py")
    return manifest


def execute_skill(
    state: AnalysisState,
    skill_name: str,
    config: dict,
    *,
    route_reason: str = "always",
) -> SkillRunRecord:
    manifest = load_skill_manifest(state.project_root, skill_name)
    path = state.project_root / "skills" / skill_name / manifest["entrypoint"]
    module_name = "app_entry_rca_dynamic_" + skill_name.replace("-", "_")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if not spec or not spec.loader:
        raise ImportError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "run"):
        raise AttributeError(f"Skill {skill_name} does not export run(state, config)")

    before_metrics = set(state.metrics["DUT"]) | set(state.metrics["REF"])
    before_findings = len(state.skill_findings)
    t0 = time.perf_counter()
    try:
        merged_config = dict(manifest.get("config", {}))
        merged_config.update(config or {})
        module.run(state, merged_config)
        after_metrics = set(state.metrics["DUT"]) | set(state.metrics["REF"])
        return SkillRunRecord(
            skill=skill_name,
            status="OK",
            duration_ms=(time.perf_counter() - t0) * 1000.0,
            version=str(manifest.get("version", "unknown")),
            stage=str(manifest.get("stage", "analysis")),
            route_reason=route_reason,
            metrics_added=sorted(after_metrics - before_metrics),
            findings_added=len(state.skill_findings) - before_findings,
        )
    except Exception as exc:
        return SkillRunRecord(
            skill=skill_name,
            status="ERROR",
            duration_ms=(time.perf_counter() - t0) * 1000.0,
            version=str(manifest.get("version", "unknown")),
            stage=str(manifest.get("stage", "analysis")),
            route_reason=route_reason,
            error=str(exc),
            warnings=[traceback.format_exc()],
        )

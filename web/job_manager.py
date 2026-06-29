"""Job manager for tracking and running analysis jobs."""
from __future__ import annotations

import asyncio
import os
import traceback
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .event_emitter import emitter


@dataclass
class Job:
    """Represents a single DUT vs REF analysis job."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    status: str = "PENDING"  # PENDING, RUNNING, COMPLETED, FAILED
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    dut_path: str = ""
    ref_path: str = ""
    target: str = ""
    backend: str = "auto"
    options: Dict[str, Any] = field(default_factory=dict)
    progress: float = 0.0
    current_skill: Optional[str] = None
    total_skills: int = 0
    completed_skills: int = 0
    result_dir: Optional[str] = None
    error: Optional[str] = None
    error_traceback: Optional[str] = None

    # Populated after completion
    summary: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class JobManager:
    """Manages the lifecycle of analysis jobs."""

    def __init__(self, results_base: str = "results") -> None:
        self._jobs: Dict[str, Job] = {}
        self._results_base = Path(results_base)
        self._results_base.mkdir(parents=True, exist_ok=True)

    @property
    def jobs(self) -> Dict[str, Job]:
        return self._jobs

    def create_job(
        self,
        dut_path: str,
        ref_path: str,
        target: str = "",
        backend: str = "auto",
        options: Dict[str, Any] | None = None,
    ) -> Job:
        """Create a new analysis job."""
        job = Job(
            dut_path=dut_path,
            ref_path=ref_path,
            target=target,
            backend=backend,
            options=options or {},
        )
        job.result_dir = str(self._results_base / job.id)
        self._jobs[job.id] = job
        return job

    def get_job(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    def list_jobs(self) -> List[Job]:
        return sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)

    def delete_job(self, job_id: str) -> bool:
        job = self._jobs.pop(job_id, None)
        if job and job.result_dir:
            import shutil
            shutil.rmtree(job.result_dir, ignore_errors=True)
        emitter.clear_logs(job_id)
        return job is not None

    async def run_job(self, job: Job, project_root: str) -> None:
        """Run an analysis job in a background thread."""
        job.status = "RUNNING"
        emitter.emit(job.id, "job.started", {
            "job_id": job.id,
            "dut_path": job.dut_path,
            "ref_path": job.ref_path,
        })

        try:
            result = await asyncio.to_thread(
                self._execute_analysis, job, project_root
            )
            job.status = "COMPLETED"
            job.progress = 1.0
            job.summary = result
            emitter.emit(job.id, "job.completed", {
                "job_id": job.id,
                "result_dir": job.result_dir,
                "summary": result,
            })
        except Exception as exc:
            job.status = "FAILED"
            job.error = str(exc)
            job.error_traceback = traceback.format_exc()
            emitter.emit(job.id, "job.failed", {
                "job_id": job.id,
                "error": str(exc),
                "traceback": job.error_traceback,
            })

    def _execute_analysis(self, job: Job, project_root: str) -> Dict[str, Any]:
        """Execute the analysis workflow synchronously (runs in thread)."""
        from app_entry_rca.core.config import load_yaml
        from app_entry_rca.core.models import AnalysisState
        from app_entry_rca.core.skill_loader import load_skill_manifest, execute_skill

        root = Path(project_root)
        workflow_path = root / "workflows" / "app_entry_rca" / "workflow.yaml"
        workflow = load_yaml(workflow_path)

        steps = workflow.get("steps", [])
        job.total_skills = len(steps)

        # Build options
        options = dict(job.options)
        options["out"] = job.result_dir
        options["backend"] = job.backend
        if job.target:
            options["target"] = job.target

        # Create analysis state
        state = AnalysisState(
            project_root=root,
            inputs={"DUT": job.dut_path, "REF": job.ref_path},
            options=options,
        )
        state.provenance["workflow_version"] = workflow.get("version", "unknown")
        state.provenance["workflow_name"] = workflow.get("name", "unknown")

        def _event_callback(event_type: str, data: Dict[str, Any]) -> None:
            emitter.emit(job.id, event_type, data)

        # Execute each step
        for i, step in enumerate(steps):
            skill_name = step["skill"]
            execution = step.get("execution", {})
            mode = execution.get("mode", "always")
            critical = execution.get("critical", False)

            # Check routing
            if mode == "routed" and skill_name not in state.selected_skills:
                job.current_skill = skill_name
                emitter.emit(job.id, "skill.skipped", {
                    "skill": skill_name,
                    "step": i + 1,
                    "total": job.total_skills,
                    "reason": "not selected by router",
                })
                job.completed_skills = i + 1
                job.progress = (i + 1) / job.total_skills
                emitter.emit(job.id, "progress.update", {
                    "progress": job.progress,
                    "completed": job.completed_skills,
                    "total": job.total_skills,
                    "current_skill": skill_name,
                    "status": "skipped",
                })
                continue

            job.current_skill = skill_name
            emitter.emit(job.id, "skill.started", {
                "skill": skill_name,
                "step": i + 1,
                "total": job.total_skills,
            })
            emitter.emit(job.id, "log.info", {
                "message": f"Running skill: {skill_name} ({i+1}/{job.total_skills})",
            })

            config = step.get("config", {})
            record = execute_skill(state, skill_name, config, route_reason=mode)
            state.skill_runs.append(record)

            if record.status == "ERROR":
                emitter.emit(job.id, "skill.error", {
                    "skill": skill_name,
                    "error": record.error or "Unknown error",
                    "warnings": record.warnings,
                    "step": i + 1,
                    "total": job.total_skills,
                })
                emitter.emit(job.id, "log.error", {
                    "message": f"Skill {skill_name} failed: {record.error}",
                })
                if critical:
                    raise RuntimeError(
                        f"Critical skill '{skill_name}' failed: {record.error}"
                    )
            else:
                emitter.emit(job.id, "skill.completed", {
                    "skill": skill_name,
                    "status": record.status,
                    "duration_ms": round(record.duration_ms, 1),
                    "metrics_added": record.metrics_added,
                    "findings_added": record.findings_added,
                    "step": i + 1,
                    "total": job.total_skills,
                })
                emitter.emit(job.id, "log.info", {
                    "message": f"✓ {skill_name}: {record.duration_ms:.0f}ms, "
                               f"{len(record.metrics_added)} metrics, "
                               f"{record.findings_added} findings",
                })

            job.completed_skills = i + 1
            job.progress = (i + 1) / job.total_skills
            emitter.emit(job.id, "progress.update", {
                "progress": job.progress,
                "completed": job.completed_skills,
                "total": job.total_skills,
                "current_skill": skill_name,
                "status": record.status,
            })

        # Build summary from result files
        import json
        result_dir = Path(job.result_dir)
        summary_path = result_dir / "analysis_summary.json"
        summary = {}
        if summary_path.exists():
            summary = json.loads(summary_path.read_text(encoding="utf-8"))

        return summary

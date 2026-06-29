"""FastAPI web server for App Entry RCA Analyzer."""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .event_emitter import emitter
from .job_manager import JobManager, Job

# Resolve project root
WEB_DIR = Path(__file__).parent
PROJECT_ROOT = WEB_DIR.parent
RESULTS_DIR = PROJECT_ROOT / "results"

# Add project to path so skills can import
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

app = FastAPI(title="App Entry RCA Analyzer", version="7.0.0")
job_manager = JobManager(results_base=str(RESULTS_DIR))

# Serve static files
app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")


@app.on_event("startup")
async def startup():
    emitter.set_loop(asyncio.get_event_loop())


# ──────────────────────────────────────────────────
# Page routes
# ──────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the main SPA page."""
    html_path = WEB_DIR / "templates" / "index.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


# ──────────────────────────────────────────────────
# File browser API (local filesystem)
# ──────────────────────────────────────────────────

@app.get("/api/browse")
async def browse_files(path: str = Query("~", description="Directory path to browse")):
    """Browse local filesystem directories for trace files."""
    target = Path(os.path.expanduser(path)).resolve()
    if not target.exists():
        return JSONResponse({"error": f"Path does not exist: {target}"}, status_code=404)
    if not target.is_dir():
        return JSONResponse({"error": f"Not a directory: {target}"}, status_code=400)

    items = []
    try:
        for entry in sorted(target.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
            try:
                stat = entry.stat()
                items.append({
                    "name": entry.name,
                    "path": str(entry),
                    "is_dir": entry.is_dir(),
                    "size": stat.st_size if entry.is_file() else None,
                    "ext": entry.suffix.lower() if entry.is_file() else None,
                })
            except PermissionError:
                continue
    except PermissionError:
        return JSONResponse({"error": f"Permission denied: {target}"}, status_code=403)

    parent = str(target.parent) if target != target.parent else None
    return {
        "current": str(target),
        "parent": parent,
        "items": items,
    }


# ──────────────────────────────────────────────────
# Job API
# ──────────────────────────────────────────────────

@app.post("/api/analyze")
async def start_analysis(body: Dict[str, Any]):
    """Start a new analysis job using local file paths."""
    dut_path = body.get("dut_path", "")
    ref_path = body.get("ref_path", "")
    target = body.get("target", "")
    backend = body.get("backend", "auto")
    options = body.get("options", {})

    # Validate paths exist
    if not Path(dut_path).is_file():
        return JSONResponse(
            {"error": f"DUT file not found: {dut_path}"}, status_code=400
        )
    if not Path(ref_path).is_file():
        return JSONResponse(
            {"error": f"REF file not found: {ref_path}"}, status_code=400
        )

    job = job_manager.create_job(
        dut_path=dut_path,
        ref_path=ref_path,
        target=target,
        backend=backend,
        options=options,
    )

    # Launch analysis in background
    asyncio.create_task(job_manager.run_job(job, str(PROJECT_ROOT)))

    return {"job_id": job.id, "status": job.status}


@app.post("/api/batch")
async def start_batch(body: Dict[str, Any]):
    """Start batch analysis for multiple DUT-REF pairs in directories."""
    dut_dir = body.get("dut_dir", "")
    ref_dir = body.get("ref_dir", "")
    backend = body.get("backend", "auto")
    options = body.get("options", {})

    dut_path = Path(dut_dir)
    ref_path = Path(ref_dir)

    if not dut_path.is_dir():
        return JSONResponse({"error": f"DUT directory not found: {dut_dir}"}, status_code=400)
    if not ref_path.is_dir():
        return JSONResponse({"error": f"REF directory not found: {ref_dir}"}, status_code=400)

    # Find trace files
    trace_exts = {".log", ".perfetto", ".pftrace", ".systrace", ".trace"}
    dut_files = {f.stem: f for f in dut_path.iterdir() if f.suffix.lower() in trace_exts}
    ref_files = {f.stem: f for f in ref_path.iterdir() if f.suffix.lower() in trace_exts}

    # Auto-pair by filename
    paired = []
    for name in sorted(dut_files.keys()):
        if name in ref_files:
            paired.append((str(dut_files[name]), str(ref_files[name]), name))

    if not paired:
        return JSONResponse(
            {"error": "No matching trace file pairs found between DUT and REF directories."},
            status_code=400,
        )

    job_ids = []
    for dut_f, ref_f, target_name in paired:
        job = job_manager.create_job(
            dut_path=dut_f,
            ref_path=ref_f,
            target=target_name,
            backend=backend,
            options=options,
        )
        asyncio.create_task(job_manager.run_job(job, str(PROJECT_ROOT)))
        job_ids.append({"job_id": job.id, "target": target_name, "dut": dut_f, "ref": ref_f})

    return {"jobs": job_ids, "count": len(job_ids)}


@app.get("/api/jobs")
async def list_jobs():
    """List all jobs."""
    return {"jobs": [j.to_dict() for j in job_manager.list_jobs()]}


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    """Get details of a specific job."""
    job = job_manager.get_job(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)
    return job.to_dict()


@app.delete("/api/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a job and its results."""
    if job_manager.delete_job(job_id):
        return {"deleted": True}
    return JSONResponse({"error": "Job not found"}, status_code=404)


@app.get("/api/jobs/{job_id}/results")
async def list_results(job_id: str):
    """List result files for a completed job."""
    job = job_manager.get_job(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)
    if not job.result_dir or not Path(job.result_dir).exists():
        return {"files": []}

    result_dir = Path(job.result_dir)
    files = []
    for f in sorted(result_dir.iterdir()):
        if f.is_file():
            files.append({
                "name": f.name,
                "size": f.stat().st_size,
                "ext": f.suffix,
            })
    return {"files": files}


@app.get("/api/jobs/{job_id}/results/{filename}")
async def get_result_file(job_id: str, filename: str):
    """Download a specific result file."""
    job = job_manager.get_job(job_id)
    if not job or not job.result_dir:
        return JSONResponse({"error": "Job not found"}, status_code=404)

    file_path = Path(job.result_dir) / filename
    if not file_path.is_file():
        return JSONResponse({"error": f"File not found: {filename}"}, status_code=404)

    if file_path.suffix == ".json":
        data = json.loads(file_path.read_text(encoding="utf-8"))
        return JSONResponse(data)
    elif file_path.suffix in (".csv", ".md", ".txt"):
        return FileResponse(str(file_path), media_type="text/plain")
    else:
        return FileResponse(str(file_path))


@app.get("/api/jobs/{job_id}/report")
async def get_report(job_id: str):
    """Get formatted report data for the web dashboard."""
    job = job_manager.get_job(job_id)
    if not job or not job.result_dir:
        return JSONResponse({"error": "Job not found"}, status_code=404)

    result_dir = Path(job.result_dir)
    report = {}

    files_to_load = [
        "analysis_summary.json",
        "phase_comparison.json",
        "final_leaves.json",
        "all_leaf_nodes.json",
        "evidence_graph.json",
        "raw_phase_intervals.json",
        "ms_diff_summary.json",
        "validation.json",
        "skill_runs.json",
        "raw_metrics.json",
        "cpu_core_frequency.json",
        "interference_edges.json",
        "automation_coverage.json",
        "skill_findings.json",
    ]

    for fname in files_to_load:
        fpath = result_dir / fname
        if fpath.exists():
            try:
                report[fname.replace(".json", "")] = json.loads(
                    fpath.read_text(encoding="utf-8")
                )
            except Exception:
                report[fname.replace(".json", "")] = None

    # Also load report.md
    md_path = result_dir / "report.md"
    if md_path.exists():
        report["report_md"] = md_path.read_text(encoding="utf-8")

    return report


@app.get("/api/jobs/{job_id}/download")
async def download_all(job_id: str):
    """Download all result files as ZIP."""
    import zipfile
    import tempfile

    job = job_manager.get_job(job_id)
    if not job or not job.result_dir:
        return JSONResponse({"error": "Job not found"}, status_code=404)

    result_dir = Path(job.result_dir)
    if not result_dir.exists():
        return JSONResponse({"error": "Results not found"}, status_code=404)

    zip_path = result_dir / f"rca_results_{job_id}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in result_dir.iterdir():
            if f.is_file() and f.suffix != ".zip":
                zf.write(f, f.name)

    return FileResponse(
        str(zip_path),
        media_type="application/zip",
        filename=f"rca_results_{job_id}.zip",
    )


# ──────────────────────────────────────────────────
# WebSocket for real-time updates
# ──────────────────────────────────────────────────

@app.websocket("/ws/job/{job_id}")
async def websocket_job(websocket: WebSocket, job_id: str):
    """WebSocket endpoint for real-time job updates."""
    await websocket.accept()
    queue = emitter.subscribe(job_id)

    # Send all existing logs first (replay)
    for event in emitter.get_logs(job_id):
        try:
            await websocket.send_text(event.to_json())
        except Exception:
            break

    try:
        while True:
            event = await queue.get()
            await websocket.send_text(event.to_json())
            # If job is done, send and close
            if event.type in ("job.completed", "job.failed"):
                break
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        emitter.unsubscribe(job_id, queue)

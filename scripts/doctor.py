#!/usr/bin/env python3
"""Validate that the app_entry_rca source workflow can run on this machine."""
from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import shutil
import sys
from pathlib import Path


def check_file(path: Path, label: str, results: list[dict]) -> None:
    results.append({"check": label, "ok": path.is_file(), "path": str(path)})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check app_entry_rca runtime prerequisites")
    parser.add_argument("--dut")
    parser.add_argument("--ref")
    parser.add_argument("--traceconv")
    parser.add_argument("--trace-processor")
    parser.add_argument("--backend", choices=["auto", "perfetto", "systrace"], default="auto")
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    results: list[dict] = []
    results.append(
        {
            "check": "python_version",
            "ok": sys.version_info >= (3, 10),
            "value": platform.python_version(),
            "required": ">=3.10",
        }
    )
    results.append(
        {
            "check": "pyyaml",
            "ok": importlib.util.find_spec("yaml") is not None,
            "hint": "python -m pip install -r requirements.txt",
        }
    )
    results.append(
        {
            "check": "perfetto_python",
            "ok": importlib.util.find_spec("perfetto") is not None,
            "required_for": "true Perfetto protobuf traces",
            "hint": "python -m pip install perfetto",
        }
    )
    check_file(root / "workflows" / "app_entry_rca" / "workflow.yaml", "workflow_definition", results)
    check_file(root / "taxonomy" / "leaf_registry.json", "leaf_registry", results)
    check_file(root / ".clinerules" / "workflows" / "app_entry_rca.md", "cline_workflow", results)
    check_file(root / ".cline" / "skills" / "app-entry-rca" / "SKILL.md", "cline_master_skill", results)

    skill_roots = sorted((root / "skills").glob("*/skill.yaml"))
    results.append(
        {
            "check": "internal_skills",
            "ok": len(skill_roots) >= 15,
            "count": len(skill_roots),
            "required": 15,
        }
    )

    for label, raw in (("dut_trace", args.dut), ("ref_trace", args.ref)):
        if raw:
            path = Path(raw).expanduser().resolve()
            results.append({"check": label, "ok": path.is_file(), "path": str(path)})

    trace_processor = args.trace_processor or shutil.which("trace_processor_shell") or shutil.which("trace_processor_shell.exe")
    results.append(
        {
            "check": "trace_processor_optional",
            "ok": bool(trace_processor and Path(trace_processor).is_file()) if trace_processor else True,
            "value": trace_processor,
            "note": "Recommended for deterministic offline Perfetto SQL analysis; the perfetto package can otherwise manage the binary.",
        }
    )
    traceconv = args.traceconv or shutil.which("traceconv") or shutil.which("traceconv.exe")
    results.append(
        {
            "check": "traceconv_lossy_fallback",
            "ok": bool(traceconv and Path(traceconv).is_file()) if traceconv else True,
            "value": traceconv,
            "note": "Optional lossy fallback only; not the preferred protobuf backend.",
        }
    )

    failed = [item for item in results if not item.get("ok")]
    payload = {
        "project_root": str(root),
        "platform": platform.platform(),
        "ready": not failed,
        "failed_checks": [item["check"] for item in failed],
        "checks": results,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main())

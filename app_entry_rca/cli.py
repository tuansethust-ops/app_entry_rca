from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from app_entry_rca.workflow.orchestrator import run_workflow


def _default_trace_processor(project_root: Path) -> str | None:
    """Return the project-local Trace Processor path when the user placed it there.

    Preferred layout:

        app_entry_rca/tools/perfetto/trace_processor_shell(.exe)
    """
    names = ["trace_processor_shell.exe"] if os.name == "nt" else ["trace_processor_shell"]
    # Also check both names to support WSL/shared trees.
    names += ["trace_processor_shell", "trace_processor_shell.exe"]
    for name in names:
        candidate = project_root / "tools" / "perfetto" / name
        if candidate.exists():
            return str(candidate)
    return None


def build_parser():
    parser = argparse.ArgumentParser(description="DUT vs REF Perfetto app-entry RCA workflow")
    parser.add_argument("positional", nargs="*", help="Optional positional form: DUT_TRACE REF_TRACE")
    parser.add_argument("--dut")
    parser.add_argument("--ref")
    parser.add_argument("--out", default="app_entry_rca_out")
    parser.add_argument("--target")
    parser.add_argument("--launch-index", type=int, default=0, help="Zero-based launch candidate index")
    parser.add_argument("--traceconv", help="Lossy fallback: path to Perfetto traceconv")
    parser.add_argument("--trace-processor", help="Path to trace_processor_shell(.exe) for Perfetto SQL backend")
    parser.add_argument("--backend", choices=["auto", "perfetto", "systrace"], default="auto")
    parser.add_argument("--workflow")
    parser.add_argument("--include-better-final", action="store_true")
    parser.add_argument("--include-correlation-candidates", action="store_true", help="Include correlation-only observations in final_leaves.json")
    parser.add_argument("--strict-validation", action="store_true", help="Fail on target/launch-type mismatch")
    return parser


def _resolve_trace_args(args) -> tuple[str, str]:
    dut = args.dut
    ref = args.ref
    if (not dut or not ref) and len(args.positional) >= 2:
        dut = dut or args.positional[0]
        ref = ref or args.positional[1]
    if len(args.positional) > 2:
        raise ValueError(
            "Too many positional arguments. Use: app_entry_rca DUT_TRACE REF_TRACE "
            "plus named options such as --target, --out, --backend."
        )
    if not dut or not ref:
        raise ValueError("DUT and REF traces are required. Use either: --dut DUT --ref REF, or positional: DUT REF.")
    return dut, ref


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    project_root = Path(__file__).resolve().parents[1]
    workflow = Path(args.workflow) if args.workflow else project_root / "workflows" / "app_entry_rca" / "workflow.yaml"
    try:
        dut, ref = _resolve_trace_args(args)
        trace_processor = args.trace_processor or _default_trace_processor(project_root)
        state = run_workflow(
            project_root,
            workflow,
            {"DUT": dut, "REF": ref},
            {
                "out": args.out,
                "target": args.target,
                "launch_index": args.launch_index,
                "traceconv": args.traceconv,
                "trace_processor": trace_processor,
                "backend": args.backend,
                "include_better_final": args.include_better_final,
                "include_correlation_candidates": args.include_correlation_candidates,
                "strict_validation": args.strict_validation,
            },
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "target": state.contexts.get("DUT").target_package if state.contexts else None,
                "validation": state.validation.get("decision"),
                "comparability_score": state.validation.get("comparability_score"),
                "active_phases": state.active_phases,
                "activated_groups": len(state.activated_groups),
                "selected_skills": state.selected_skills,
                "leaf_count": len(state.leaves),
                "final_leaf_count": len(state.final_leaves),
                "trace_processor": state.provenance.get("options", {}).get("trace_processor"),
                "files": state.output_files,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

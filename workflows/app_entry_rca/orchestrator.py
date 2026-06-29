from pathlib import Path

from app_entry_rca.workflow.orchestrator import run_workflow


def run(dut, ref, out, target=None, traceconv=None, launch_index=0, include_better_final=False):
    root = Path(__file__).resolve().parents[2]
    return run_workflow(
        root,
        Path(__file__).with_name("workflow.yaml"),
        {"DUT": dut, "REF": ref},
        {
            "out": out,
            "target": target,
            "traceconv": traceconv,
            "launch_index": launch_index,
            "include_better_final": include_better_final,
        },
    )

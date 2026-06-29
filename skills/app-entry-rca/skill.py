from __future__ import annotations


def run(state, config):
    """Top-level Cline skill placeholder.

    The deterministic RCA execution is performed by scripts/run_app_entry_rca.py
    or python -m app_entry_rca.cli, which load workflows/app_entry_rca/workflow.yaml.
    This function keeps the canonical skill contract valid for Cline discovery tests.
    """
    state.provenance.setdefault("app-entry-rca", {})["role"] = "top-level orchestrator"
    state.provenance["app-entry-rca"]["execution"] = "use workflow.yaml via CLI/runner"
    return state

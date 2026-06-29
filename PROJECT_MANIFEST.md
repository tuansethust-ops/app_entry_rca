# App Entry RCA Workflow v6.1 Manifest

## Workflow

- `workflows/app_entry_rca/workflow.yaml`: canonical deterministic workflow.
- `.clinerules/workflows/app_entry_rca.md`: Cline slash workflow (`/app_entry_rca`).

## Skills

- `skills/`: 15 executable Python capability skills used by the workflow engine.
- `.cline/skills/app-entry-rca/`: Cline master skill.
- `.cline/skills/<capability>/`: Cline-discoverable wrappers for every internal skill.

## Cross-platform launchers

- `scripts/run_app_entry_rca.py`: portable source-tree launcher.
- `scripts/doctor.py`: environment and asset validator.
- `install_windows.bat`: Windows installation entry point.
- `run_app_entry_rca.bat`: Windows command-prompt launcher.
- `windows/install.ps1`: creates `.venv` and installs dependencies.
- `windows/run.ps1`: robust PowerShell workflow launcher.
- `windows/doctor.ps1`: Windows environment check.

## Engine and data

- `app_entry_rca/`: workflow runtime and trace model.
- `taxonomy/`: P1-P8 candidates, 269 leaves, evidence rules and ownership/action mappings.
- `schemas/`: leaf and final-leaf output contracts.
- `tests/`: unit, contract, routing, taxonomy, GC, timing semantics and golden-pair tests.
- `docs/FULL_FTA.md`: full P1-P8 FTA.
- `docs/output_contract.md`: local/exclusive/nested millisecond-delta semantics.

## New in v6.1

- `ms_diff_summary.json` with first-frame endpoint and contributor deltas.
- Final leaves expose `local_delta_ms`, `exclusive_contribution_ms`, `nested_deltas_ms`, `overlap_group`, `additive` and `delta_note`.
- RecyclerView `RV OnLayout` is measured as a paired p6.first_choreographer_doframe_or_activityidle.measure_and_layout_traversal.performlayout_or_onlayout leaf.
- `traversal_to_draw_start_ms` is no longer mislabeled as pure p6.first_choreographer_doframe_or_activityidle.frame_scheduling_and_vsync_admission frame scheduling.
- Parent startActivity duration is reported as umbrella context; direct scheduling evidence remains a separate leaf.

## Release 6.3.0 skill discovery contract

- 1 master Cline skill: `.cline/skills/app-entry-rca/SKILL.md`.
- 15 capability skills, each mirrored in `skills/<name>/SKILL.md` and `.cline/skills/<name>/SKILL.md`.
- Every skill contains YAML frontmatter with a directory-matching `name` and trigger-oriented `description`.
- Every skill documents Purpose, Trigger, Inputs, Workflow, Algorithm, Outputs, Integration, Guardrails, Failure handling, Limitations, Implementation, and Tests.
- Current taxonomy: 271 leaves.
- Current automatic rules: 70.
- Canonical workflow: `workflows/app_entry_rca/workflow.yaml`.
- Cline slash workflow: `.clinerules/workflows/app_entry_rca.md`.

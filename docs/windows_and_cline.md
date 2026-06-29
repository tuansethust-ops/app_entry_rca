# Running app_entry_rca on Windows and Cline

## Design

`app_entry_rca` is one deterministic workflow defined by:

```text
workflows/app_entry_rca/workflow.yaml
```

The workflow orchestrates 15 internal capability skills from `skills/`. Cline discovers project skills through `.cline/skills/`, while the slash workflow is stored in `.clinerules/workflows/app_entry_rca.md`.

## Windows installation

From Command Prompt:

```bat
install_windows.bat
```

This creates `.venv`, installs dependencies and runs the environment doctor.

## Windows execution

PowerShell:

```powershell
.\windows\run.ps1 `
  -Dut "D:\trace\DUT.perfetto" `
  -Ref "D:\trace\REF.perfetto" `
  -Out "D:\trace\app_entry_rca_out" `
  -IncludeBetterFinal
```

Command Prompt wrapper:

```bat
run_app_entry_rca.bat -Dut "D:\trace\DUT.perfetto" -Ref "D:\trace\REF.perfetto" -Out "D:\trace\app_entry_rca_out" -IncludeBetterFinal
```

## Cline execution

Open the project root as the Cline workspace, enable Skills, then invoke:

```text
/app_entry_rca
```

Mention the DUT and REF trace paths in the same message. Cline executes the source-tree launcher and then reads the structured output. It does not replace the deterministic measurements with free-form reasoning.

## Direct cross-platform execution

```bash
python scripts/run_app_entry_rca.py \
  --dut DUT.perfetto \
  --ref REF.perfetto \
  --out app_entry_rca_out \
  --include-better-final
```

## Environment validation

```bash
python scripts/doctor.py --dut DUT.perfetto --ref REF.perfetto
```

Binary Perfetto protobuf traces additionally require `traceconv`:

```bash
python scripts/run_app_entry_rca.py \
  --dut DUT.pftrace \
  --ref REF.pftrace \
  --traceconv /path/to/traceconv \
  --out app_entry_rca_out
```

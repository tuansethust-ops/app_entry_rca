# Cline usage

Invoke the workspace workflow from Cline chat:

```text
/app_entry_rca
```

Then provide or mention the DUT and REF trace paths. Cline executes the same `workflows/app_entry_rca/workflow.yaml` used by the Windows launcher.

The deterministic Python workflow performs the measurement and ranking. Cline's role is to resolve paths, run the command, inspect outputs and explain the evidence without changing its semantics.

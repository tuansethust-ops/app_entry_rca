# Perfetto Trace Processor

Place the executable here:

- Linux/macOS: `trace_processor_shell`
- Windows: `trace_processor_shell.exe`

`app_entry_rca` auto-detects this folder when `--trace-processor` is not passed.

Preferred layout:

```text
app_entry_rca/
└── tools/
    └── perfetto/
        ├── trace_processor_shell
        └── trace_processor_shell.exe
```

The executable is intentionally not bundled.

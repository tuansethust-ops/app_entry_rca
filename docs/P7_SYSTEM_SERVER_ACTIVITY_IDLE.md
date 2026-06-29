# P7 — First-frame completion to system_server activityIdle

## Canonical boundary

```text
P7 start = finishDrawing end
           (or DrawFrames/FrameTimeline present fallback)

P7 end   = end of
           IActivityClientController::activityIdle::server
           in system_server
```

The generic nested `activityIdle` slice is not the canonical endpoint. It is
kept as server-side nested evidence. A client-side `activityIdle::client` slice
is optional and only enables Binder delivery/admission measurement.

## Decomposition

```text
P7 total
├── target-app post-frame work / queue tail
├── optional activityIdle client call → server admission
└── system_server activityIdle handler
    ├── Running
    ├── Runnable
    ├── Sleeping
    ├── D-state
    └── monitor/lock contention
```

## Metrics

| Metric | Meaning |
|---|---|
| `p7_to_activity_idle_server_ms` | First-frame completion to server callback end |
| `p7_to_activity_idle_server_start_ms` | First-frame completion to server callback admission |
| `activity_idle_server_ms` | Duration of the server callback |
| `activity_idle_client_to_server_ms` | Optional client-call start to server admission |
| `activity_idle_server_running_ms` | Running state inside server callback |
| `activity_idle_server_runnable_ms` | Runnable state inside server callback |
| `activity_idle_server_sleeping_ms` | Sleeping state inside server callback |
| `activity_idle_server_d_ms` | D-state inside server callback |
| `activity_idle_server_monitor_contention_ms` | Monitor contention nested inside server callback |
| `input_to_activity_idle_server_ms` | Input start to canonical completion endpoint |

## Causality guardrail

`p7_to_activity_idle_server_ms` is an umbrella timing and is
`CORRELATION_ONLY`. It cannot prove that the app MessageQueue never became idle.
A direct/contributing final leaf requires one of the following:

- client-to-server Binder delivery delay;
- server Runnable/CPU delay;
- server monitor/lock contention;
- server D-state/I/O wait;
- explicit target-app queue/IdleHandler evidence.

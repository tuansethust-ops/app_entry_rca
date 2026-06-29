# Changelog 6.2 — Canonical P7 system_server activityIdle endpoint

- P7 now starts after first-frame completion and ends at the end of
  `IActivityClientController::activityIdle::server` in system_server.
- Added exact markers: `activity_idle_server`, `activity_idle_server_aidl`,
  `activity_idle_server_inner`, and optional `activity_idle_client`.
- Added server state decomposition and nested monitor-contention metrics.
- Changed P7 umbrella timing to correlation-only.
- Renamed p7.activityidle.activityidle_client_or_server_reporting_and_system_server_handling.system_server_activityidle_handler_duration to system_server activityIdle handler duration.
- Added p7.activityidle.post_frame_queue_or_tail_before_system_server_activityidle.messagequeue_never_reaches_idle MessageQueue-never-idle evidence leaf.
- Added p7.activityidle.activityidle_client_or_server_reporting_and_system_server_handling.system_server_activityidle_monitor_or_lock_contention system_server activityIdle monitor/lock contention leaf.
- Added input→activityIdle server-end and P7 completion reporting.

from types import SimpleNamespace

from app_entry_rca.reporting.writers import _build_ms_diff_summary


def test_ms_diff_summary_keeps_nested_timings_non_additive():
    state = SimpleNamespace(
        metrics={
            "DUT": {
                "input_to_first_frame_proxy_ms": 672.343,
                "first_frame_proxy_semantics": "finishDrawing_start",
                "critical_io_d_ms": 132.028,
                "critical_d_total_ms": 133.0,
                "critical_direct_reclaim_ms": 0.0,
                "traversal_ms": 157.436,
                "recycler_onlayout_max_ms": 51.601,
                "traversal_running_ms": 68.193,
                "traversal_runnable_ms": 1.534,
                "draw_frames_ms": 66.56,
                "draw_frames_running_ms": 58.861,
                "draw_frames_runnable_ms": 0.236,
                "vulkan_finish_ms": 42.385,
                "texture_upload_ms": 6.222,
                "gpu_wait_ms": 0.015,
                "open_dex_oat_ms": 63.948,
                "artifact_status_ms": 10.848,
                "bind_application_ms": 178.995,
                "bind_application_d_ms": 8.0,
                "start_activity_server_ms": 147.717,
                "p2_outer_exclusive_ms": 59.034,
                "start_activity_server_running_ms": 98.649,
                "start_activity_server_runnable_ms": 14.909,
                "start_activity_server_d_ms": 30.0,
                "start_activity_server_sleeping_ms": 4.0,
            },
            "REF": {
                "input_to_first_frame_proxy_ms": 531.938,
                "first_frame_proxy_semantics": "finishDrawing_start",
                "critical_io_d_ms": 67.035,
                "critical_d_total_ms": 67.953,
                "critical_direct_reclaim_ms": 0.945,
                "traversal_ms": 83.195,
                "recycler_onlayout_max_ms": 0.044,
                "traversal_running_ms": 19.764,
                "traversal_runnable_ms": 0.567,
                "draw_frames_ms": 45.801,
                "draw_frames_running_ms": 32.866,
                "draw_frames_runnable_ms": 0.682,
                "vulkan_finish_ms": 25.148,
                "texture_upload_ms": 7.955,
                "gpu_wait_ms": 0.035,
                "open_dex_oat_ms": 32.588,
                "artifact_status_ms": 8.928,
                "bind_application_ms": 133.074,
                "bind_application_d_ms": 2.294,
                "start_activity_server_ms": 61.409,
                "p2_outer_exclusive_ms": 23.869,
                "start_activity_server_running_ms": 50.191,
                "start_activity_server_runnable_ms": 0.431,
                "start_activity_server_d_ms": 4.954,
                "start_activity_server_sleeping_ms": 5.674,
            },
        }
    )
    result = _build_ms_diff_summary(state)
    assert result["endpoint"]["delta_ms"] == 140.405
    traversal = next(item for item in result["contributors"] if item["id"] == "first_traversal_layout")
    assert traversal["local_delta_ms"] == 74.241
    assert traversal["exclusive_contribution_ms"] == 51.557
    assert traversal["additive"] is False
    assert result["guardrail"].startswith("All contributor deltas")

from pathlib import Path
from types import SimpleNamespace

from app_entry_rca.workflow.router import select_analyzers


def test_router_skips_art_for_non_cold_non_p3_context():
    state = SimpleNamespace(
        project_root=Path(__file__).parents[1],
        activated_groups=["p6.first_choreographerdoframe_activityidle.surface_and_renderthread"],
        active_phases=["P6", "P8"],
        contexts={"DUT": SimpleNamespace(launch_type="warm", render_tid=10, observability={"render_slices": True, "sched": True}),
                  "REF": SimpleNamespace(launch_type="warm", render_tid=11, observability={"render_slices": True, "sched": True})},
    )
    selected, reasons = select_analyzers(state)
    assert "render-frame-analysis" in selected
    assert "art-runtime-analysis" not in selected
    assert reasons["render-frame-analysis"]

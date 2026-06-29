from app_entry_rca.core.intervals import pair_overlap_ms
from app_entry_rca.core.models import StateInterval


def test_same_cpu_overlap_only_counts_matching_cpu():
    critical = [StateInterval(0.0, 0.010, "Runnable", 10, 6)]
    blocker_wrong_cpu = [StateInterval(0.0, 0.010, "Running", 20, 7)]
    blocker_same_cpu = [StateInterval(0.004, 0.009, "Running", 21, 6)]
    assert pair_overlap_ms(blocker_wrong_cpu, critical, same_cpu=True) == 0
    assert round(pair_overlap_ms(blocker_same_cpu, critical, same_cpu=True), 3) == 5.0


def test_unknown_cpu_overlap_is_kept_but_not_invented():
    critical = [StateInterval(0.0, 0.010, "Runnable", 10, None)]
    blocker = [StateInterval(0.002, 0.006, "Running", 20, 3)]
    assert round(pair_overlap_ms(blocker, critical, same_cpu=True), 3) == 4.0

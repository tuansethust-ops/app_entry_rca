from __future__ import annotations

from collections import defaultdict
from typing import Any

from app_entry_rca.core.models import FinalLeaf, LeafResult


CAUSALITY_SCORE = {"DIRECT": 42.0, "CONTRIBUTING": 28.0, "CORRELATION_ONLY": 0.0, "REJECTED": -30.0}
CONFIDENCE_SCORE = {"HIGH": 20.0, "MEDIUM": 11.0, "LOW": 3.0}
EVIDENCE_SCORE = {"DIRECT": 14.0, "CONTRIBUTING": 9.0, "CORRELATION_ONLY": 1.0, "NONE": 0.0}


def _numeric_delta(dut: dict, ref: dict, metric: str) -> float | None:
    left, right = dut.get(metric), ref.get(metric)
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return float(left) - float(right)
    return None


def _numeric_deltas(dut: dict, ref: dict, mapping: dict[str, str]) -> dict[str, float]:
    out: dict[str, float] = {}
    for label, metric in mapping.items():
        value = _numeric_delta(dut, ref, metric)
        if value is not None:
            out[label] = round(value, 3)
    return out


def _delta_profile(root_key: str, leaf: LeafResult, dut: dict, ref: dict) -> dict[str, Any]:
    """Return non-additive timing semantics for a final candidate.

    local_delta_ms is the paired delta of the candidate window.
    exclusive_contribution_ms is only populated when the engine has a
    mechanism-specific paired contribution metric. nested_deltas_ms provides
    parent/child or state-decomposition evidence and must not be summed.
    """
    local = leaf.delta_value if leaf.metric_unit == "ms" else None
    exclusive = leaf.contribution_ms if leaf.metric_unit == "ms" else None
    nested: dict[str, float] = {}
    overlap_group = f"{leaf.phase}:{leaf.group}"
    note = "Candidate timings may overlap parent/child windows; do not sum them directly."

    if root_key == "framework:start_activity_runnable":
        local = _numeric_delta(dut, ref, "start_activity_server_runnable_ms")
        exclusive = local
        nested = _numeric_deltas(
            dut, ref,
            {
                "start_activity_parent_ms": "start_activity_server_ms",
                "running_ms": "start_activity_server_running_ms",
                "d_state_ms": "start_activity_server_d_ms",
                "sleeping_ms": "start_activity_server_sleeping_ms",
            },
        )
        overlap_group = "P2_START_ACTIVITY"
        note = "Runnable delay is a child state of the startActivity parent window; parent and state deltas are non-additive."
    elif root_key == "framework:start_activity_orchestration":
        local = _numeric_delta(dut, ref, "start_activity_server_ms")
        exclusive = _numeric_delta(dut, ref, "p2_outer_exclusive_ms")
        nested = _numeric_deltas(
            dut, ref,
            {
                "outer_exclusive_ms": "p2_outer_exclusive_ms",
                "running_ms": "start_activity_server_running_ms",
                "runnable_ms": "start_activity_server_runnable_ms",
                "d_state_ms": "start_activity_server_d_ms",
                "sleeping_ms": "start_activity_server_sleeping_ms",
            },
        )
        overlap_group = "P2_START_ACTIVITY"
        note = "The state deltas decompose the startActivity parent window; they are not additional time."
    elif root_key == "framework:attach_lock_serialization":
        local = _numeric_delta(dut, ref, "process_request_to_bind_ms")
        exclusive = _numeric_delta(dut, ref, "prebind_contention_ms")
        nested = _numeric_deltas(
            dut, ref,
            {
                "prebind_contention_ms": "prebind_contention_ms",
                "activity_thread_sleeping_ms": "activity_thread_main_sleeping_ms",
                "attach_orchestration_ms": "attach_orchestration_total_ms",
            },
        )
        overlap_group = "P2_P3_ATTACH_SERIALIZATION"
    elif root_key == "art:artifact_preparation":
        local = _numeric_delta(dut, ref, "open_dex_oat_ms")
        exclusive = local
        nested = _numeric_deltas(
            dut, ref,
            {
                "artifact_status_ms": "artifact_status_ms",
                "bind_application_parent_ms": "bind_application_ms",
                "bind_application_d_state_ms": "bind_application_d_ms",
            },
        )
        overlap_group = "P3_BIND_APPLICATION"
        note = "bindApplication is a parent window; ART and D-state deltas can overlap within it."
    elif root_key == "render:recycler_initial_layout":
        local = _numeric_delta(dut, ref, "recycler_onlayout_max_ms")
        exclusive = local
        nested = _numeric_deltas(
            dut, ref,
            {
                "first_traversal_total_ms": "traversal_ms",
                "traversal_running_ms": "traversal_running_ms",
                "traversal_runnable_ms": "traversal_runnable_ms",
            },
        )
        overlap_group = "P6_FIRST_TRAVERSAL"
        note = "RecyclerView onLayout is nested inside the first traversal parent window."
    elif root_key == "render:hwui_drawframes":
        local = _numeric_delta(dut, ref, "draw_frames_ms")
        exclusive = None
        nested = _numeric_deltas(
            dut, ref,
            {
                "drawframes_running_ms": "draw_frames_running_ms",
                "drawframes_runnable_ms": "draw_frames_runnable_ms",
                "vulkan_finish_ms": "vulkan_finish_ms",
                "texture_upload_ms": "texture_upload_ms",
                "gpu_wait_ms": "gpu_wait_ms",
            },
        )
        overlap_group = "P6_RENDERTHREAD_FIRST_FRAME"
        note = "Vulkan/texture/fence metrics are nested evidence inside or adjacent to DrawFrames."
    elif root_key == "render:vulkan_finish":
        local = _numeric_delta(dut, ref, "vulkan_finish_ms")
        exclusive = None
        nested = _numeric_deltas(
            dut, ref,
            {
                "vulkan_running_ms": "vulkan_running_ms",
                "vulkan_runnable_ms": "vulkan_runnable_ms",
            },
        )
        overlap_group = "P6_RENDERTHREAD_FIRST_FRAME"
        note = "Vulkan finish-frame is nested within the RenderThread first-frame path."
    elif root_key == "io:critical_file_page_wait":
        local = _numeric_delta(dut, ref, "critical_io_d_ms")
        exclusive = local
        nested = _numeric_deltas(
            dut, ref,
            {
                "critical_d_total_ms": "critical_d_total_ms",
                "critical_direct_reclaim_ms": "critical_direct_reclaim_ms",
            },
        )
        overlap_group = "CROSS_PHASE_CRITICAL_IO"
        note = "I/O wait is attributed state time across multiple phase windows; do not add it to parent phase deltas."
    elif root_key == "p7:tail_to_system_server_idle":
        local = _numeric_delta(dut, ref, "p7_to_activity_idle_server_ms")
        exclusive = None
        nested = _numeric_deltas(
            dut,
            ref,
            {
                "server_handler_ms": "activity_idle_server_ms",
                "server_running_ms": "activity_idle_server_running_ms",
                "server_runnable_ms": "activity_idle_server_runnable_ms",
                "server_sleeping_ms": "activity_idle_server_sleeping_ms",
                "server_d_state_ms": "activity_idle_server_d_ms",
                "server_monitor_contention_ms": "activity_idle_server_monitor_contention_ms",
            },
        )
        overlap_group = "P7_TO_SYSTEM_SERVER_ACTIVITY_IDLE"
        note = "Umbrella P7 tail ending at system_server activityIdle server-end; nested server metrics are non-additive."
    elif root_key == "p7:activity_idle_server_handling":
        local = _numeric_delta(dut, ref, "activity_idle_server_ms")
        exclusive = None
        nested = _numeric_deltas(
            dut,
            ref,
            {
                "running_ms": "activity_idle_server_running_ms",
                "runnable_ms": "activity_idle_server_runnable_ms",
                "sleeping_ms": "activity_idle_server_sleeping_ms",
                "d_state_ms": "activity_idle_server_d_ms",
                "monitor_contention_ms": "activity_idle_server_monitor_contention_ms",
            },
        )
        overlap_group = "P7_ACTIVITY_IDLE_SERVER"
        note = "Server state and contention metrics are nested within the activityIdle AIDL server slice."
    elif root_key == "p7:activity_idle_binder_delivery":
        local = _numeric_delta(dut, ref, "activity_idle_client_to_server_ms")
        exclusive = local
        overlap_group = "P7_ACTIVITY_IDLE_BINDER_DELIVERY"
        note = "Requires both client and server activityIdle markers; unavailable traces remain NOT_OBSERVABLE."
    elif root_key == "p7:activity_idle_monitor_contention":
        local = _numeric_delta(dut, ref, "activity_idle_server_monitor_contention_ms")
        exclusive = local
        nested = _numeric_deltas(
            dut,
            ref,
            {"server_handler_parent_ms": "activity_idle_server_ms"},
        )
        overlap_group = "P7_ACTIVITY_IDLE_SERVER"
        note = "Monitor contention is nested inside the system_server activityIdle handler."
    elif root_key.startswith("gc:"):
        overlap_group = "CROSS_PHASE_GC"
    elif root_key.startswith("cpu:") or root_key.startswith("background:"):
        overlap_group = "CROSS_PHASE_CPU_INTERFERENCE"

    if isinstance(local, (int, float)):
        local = round(float(local), 3)
    if isinstance(exclusive, (int, float)):
        exclusive = round(float(exclusive), 3)
    return {
        "local_delta_ms": local,
        "exclusive_contribution_ms": exclusive,
        "nested_deltas_ms": nested,
        "overlap_group": overlap_group,
        "additive": False,
        "delta_note": note,
    }


def _score(leaf: LeafResult, contribution_ms: float | None, evidence_count: int, validation: dict) -> tuple[float, dict[str, float]]:
    phase_weight = 14.0 if leaf.phase in {"P1", "P2", "P3", "P4", "P5", "P6"} else 9.0
    contribution = max(0.0, float(contribution_ms or 0.0))
    breakdown = {
        "causality": CAUSALITY_SCORE.get(leaf.causality, 0.0),
        "confidence": CONFIDENCE_SCORE.get(leaf.confidence, 0.0),
        "evidence_level": EVIDENCE_SCORE.get(leaf.evidence_level, 0.0),
        "phase_relevance": phase_weight,
        "critical_path_contribution": min(50.0, contribution),
        "evidence_count": min(10.0, 2.0 * evidence_count),
        "missing_evidence_penalty": -min(12.0, 3.0 * len(leaf.missing_evidence)),
        "contradiction_penalty": -30.0 if leaf.contradictions else 0.0,
        "comparison_penalty": -8.0 if validation.get("decision") == "PARTIALLY_COMPARABLE" else 0.0,
    }
    return sum(breakdown.values()), breakdown


def _metric_evidence(leaf: LeafResult, dut: dict, ref: dict) -> list[dict[str, Any]]:
    metrics = list(dict.fromkeys([leaf.metric_name] + list(leaf.evidence)))
    out: list[dict[str, Any]] = []
    for metric in metrics:
        if not isinstance(metric, str) or not metric:
            continue
        left, right = dut.get(metric), ref.get(metric)
        item: dict[str, Any] = {"type": "metric", "metric": metric, "dut": left, "ref": right}
        if isinstance(left, (int, float)) and isinstance(right, (int, float)):
            item["delta"] = float(left) - float(right)
        out.append(item)
    return out


def _finding_evidence(state, root_key: str, leaf_ids: set[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for finding in state.skill_findings:
        if finding.trace_label not in {"DUT", "PAIR"}:
            continue
        if root_key and finding.root_cause_key and finding.root_cause_key != root_key:
            continue
        if not root_key and finding.group and finding.group not in leaf_ids:
            continue
        out.append(
            {
                "type": "skill_finding",
                "finding_id": finding.finding_id,
                "skill": finding.skill,
                "title": finding.title,
                "confidence": finding.confidence,
                "evidence_level": finding.evidence_level,
                "value": finding.value,
                "evidence": finding.evidence,
            }
        )
    return out[:12]


def _verification_plan(root_key: str, leaf: LeafResult, contribution_ms: float | None) -> dict[str, Any]:
    expected = max(1.0, float(contribution_ms or 0.0) * 0.7)
    plans = {
        "memory:direct_reclaim": ("Remove the proven pre-launch memory pressure or allocation burst.", "critical_direct_reclaim_ms"),
        "memory:compaction": ("Remove the allocation/fragmentation trigger that causes synchronous compaction.", "critical_compaction_ms"),
        "memory:kswapd_competition": ("Suppress the identified memory-pressure source while keeping launch workload unchanged.", "kswapd_critical_overlap_ms"),
        "io:critical_file_page_wait": ("Warm/prefetch only the attributed file range or remove the competing I/O owner.", "critical_io_d_ms"),
        "io:filesystem_lock": ("Shorten the identified filesystem/page-lock critical section.", "critical_fs_lock_d_ms"),
        "gc:wait_for_completion": ("Eliminate the specific GC trigger or cancel/defer only that pending collection.", "wait_for_gc_ms"),
        "gc:stw": ("Reduce the allocation/live-set trigger or change the proven STW path.", "gc_stw_ms"),
        "gc:allocation_stall": ("Reduce the launch allocation burst or increase headroom through a controlled policy change.", "gc_allocation_stall_ms"),
        "gc:competition": ("Move the proven nonurgent GC outside the launch window.", "gc_competition_cpu_ms"),
        "cpu:critical_interference": ("Suppress or relocate the top exact blocker during the critical Runnable interval.", "critical_runnable_blocker_overlap_ms"),
        "cpu:irq_softirq": ("Steer or defer the proven IRQ/softirq source away from launch-critical CPUs.", "irq_critical_interference_ms"),
        "background:dexopt": ("Defer the identified dexopt/profman task outside the launch stability window.", "dexopt_critical_interference_ms"),
        "background:vendor": ("Suppress or relocate the identified vendor workload during launch.", "vendor_critical_interference_ms"),
        "p7:activity_idle_server_handling": (
            "Optimize the dominant nested state in the system_server activityIdle handler.",
            "activity_idle_server_ms",
        ),
        "p7:activity_idle_binder_delivery": (
            "Reduce the proven activityIdle Binder delivery/admission delay.",
            "activity_idle_client_to_server_ms",
        ),
        "p7:activity_idle_monitor_contention": (
            "Shorten the proven lock-held work blocking activityIdle completion.",
            "activity_idle_server_monitor_contention_ms",
        ),
    }
    change, metric = plans.get(root_key, ("Apply the component-specific action while holding all other test conditions constant.", leaf.metric_name))
    return {
        "change": change,
        "primary_metric": metric,
        "expected_improvement_ms": round(expected, 3),
        "minimum_iterations": 5,
        "success_condition": f"Median {metric} decreases and the leaf contribution improves by at least {expected:.3f} ms in 4/5 runs.",
        "rollback_condition": "Functional regression, launch-type change, or improvement not reproducible across iterations.",
    }


def _template(root_key: str, leaf: LeafResult, dut: dict, ref: dict, contribution_ms: float | None) -> dict[str, str]:
    delta = leaf.delta_value if leaf.delta_value is not None else 0.0
    templates: dict[str, dict[str, str]] = {
        "memory:direct_reclaim": {
            "path": "P5/P8 → critical-thread direct reclaim",
            "symptom": f"Critical launch threads spend {float(dut.get('critical_direct_reclaim_ms') or 0):.3f} ms in direct reclaim; DUT−REF={delta:.3f} ms.",
            "location": "The exact launch-critical thread and callback recorded in direct_reclaim_by_tid_ms.",
            "mechanism": "The critical thread performs synchronous page reclaim instead of progressing launch work.",
            "origin": "Insufficient free/reclaimable memory or an allocation burst forces reclaim in the launch thread.",
            "ownership": "Memory-pressure source, allocation owner and VM/reclaim policy.",
            "action": "Remove the allocation/pressure trigger; do not treat this as storage latency.",
        },
        "memory:compaction": {
            "path": "P5/P8 → critical-thread memory compaction",
            "symptom": f"Critical-path compaction DUT−REF={delta:.3f} ms.",
            "location": "Launch-critical thread during allocation/content preparation.",
            "mechanism": "The thread synchronously compacts memory to satisfy an allocation.",
            "origin": "Fragmentation or a high-order allocation on the launch path.",
            "ownership": "Allocation owner and memory-management policy.",
            "action": "Reduce/reshape the triggering allocation and verify fragmentation before changing global VM policy.",
        },
        "memory:kswapd_competition": {
            "path": "p8.cross_cutting_system_evidence.memory_pressure_reclaim_swap_and_churn → kswapd same-CPU competition",
            "symptom": f"Exact same-CPU kswapd-Running/critical-Runnable overlap DUT−REF={delta:.3f} ms.",
            "location": "Critical Runnable intervals during app entry.",
            "mechanism": "kswapd consumes the same CPU while launch-critical work is ready to run.",
            "origin": "Background memory pressure wakes reclaim during launch.",
            "ownership": "Memory consumer/reclaim policy that triggered kswapd.",
            "action": "Identify the pressure source; do not conclude from total kswapd CPU alone.",
        },
        "io:critical_file_page_wait": {
            "path": "p5.activityresume_or_first_choreographer_doframe.reusable_file_or_page_or_storage_mechanism/p8.cross_cutting_system_evidence.storage_and_filesystem_contention → critical file/page I/O wait",
            "symptom": f"Attributed critical I/O D-state DUT−REF={delta:.3f} ms.",
            "location": "The launch marker/thread listed by blocked_reason_summary.",
            "mechanism": "A critical thread waits for file-backed page or storage delivery.",
            "origin": "File/page-cache miss or storage queue latency; exact file owner requires filemap/block attribution.",
            "ownership": "File/resource/data owner and competing storage workload.",
            "action": "Optimize only the attributed file/range or remove the proven competing I/O workload.",
        },
        "io:filesystem_lock": {
            "path": "p5.activityresume_or_first_choreographer_doframe.reusable_file_or_page_or_storage_mechanism/p8.cross_cutting_system_evidence.storage_and_filesystem_contention → filesystem/page-lock dependency",
            "symptom": f"Filesystem/page-lock D-state DUT−REF={delta:.3f} ms.",
            "location": "Critical launch thread identified by blocked-reason evidence.",
            "mechanism": "The critical operation waits on a filesystem, inode or page lock.",
            "origin": "Concurrent metadata/file work holds the same lock or page state.",
            "ownership": "Lock owner and the component issuing concurrent file work.",
            "action": "Shorten the lock-held operation or defer the conflicting workload.",
        },
        "gc:wait_for_completion": {
            "path": "P4/p8.cross_cutting_system_evidence.direct_gc_blocking → direct WaitForGcToComplete",
            "symptom": f"Critical WaitForGcToComplete DUT−REF={delta:.3f} ms.",
            "location": "Target/system launch-critical callback containing the wait slice.",
            "mechanism": "The critical thread directly blocks until an in-progress GC finishes.",
            "origin": "A collection was triggered before/during launch by allocation or process-state transition.",
            "ownership": "ART heap policy plus the allocation/process-state trigger owner.",
            "action": "Fix the proven trigger; never suppress all GC globally.",
        },
        "gc:stw": {
            "path": "P4/p8.cross_cutting_system_evidence.direct_gc_blocking → stop-the-world GC pause",
            "symptom": f"Critical STW pause DUT−REF={delta:.3f} ms.",
            "location": "Launch window in the affected process.",
            "mechanism": "Application/runtime threads are suspended for GC work.",
            "origin": "Live-set/allocation pressure or collector transition requiring a pause.",
            "ownership": "ART collector policy and allocation/live-set owner.",
            "action": "Reduce the trigger or move the collection, preserving memory-safety guardrails.",
        },
        "gc:allocation_stall": {
            "path": "P4/p8.cross_cutting_system_evidence.direct_gc_blocking → allocation-triggered GC stall",
            "symptom": f"Allocation stall DUT−REF={delta:.3f} ms.",
            "location": "Launch-critical allocation path.",
            "mechanism": "Allocation cannot proceed until GC/heap expansion completes.",
            "origin": "Startup allocation burst or insufficient heap headroom.",
            "ownership": "App allocation design and ART heap-growth policy.",
            "action": "Reduce temporary allocations or apply a bounded, verified headroom policy.",
        },
        "gc:competition": {
            "path": "p8.cross_cutting_system_evidence.gc_resource_competition → exact GC CPU competition",
            "symptom": f"GC-Running/critical-Runnable same-CPU overlap DUT−REF={delta:.3f} ms.",
            "location": "Critical Runnable intervals during app entry.",
            "mechanism": "GC workers consume CPU while launch-critical threads are ready.",
            "origin": "Collection timing overlaps a CPU-constrained launch path.",
            "ownership": "ART heap-maintenance timing and launch CPU policy.",
            "action": "Move only the proven nonurgent GC trigger after reproducing exact competition.",
        },
        "cpu:critical_interference": {
            "path": "p8.cross_cutting_system_evidence.cpu_capacity_and_scheduler_interference → exact CPU blocker overlap",
            "symptom": f"Running-blocker/critical-Runnable overlap DUT−REF={delta:.3f} ms.",
            "location": "Critical thread Runnable windows across active launch phases.",
            "mechanism": "A runnable launch-critical thread loses CPU to an identified running task.",
            "origin": "Competing workload placement/priority on the same CPU.",
            "ownership": "Top blocker owner and scheduler/task-profile policy.",
            "action": "Relocate, defer or reduce only the proven blocker.",
        },
        "cpu:irq_softirq": {
            "path": "p8.cross_cutting_system_evidence.cpu_capacity_and_scheduler_interference → IRQ/softirq competition",
            "symptom": f"IRQ/softirq exact critical overlap DUT−REF={delta:.3f} ms.",
            "location": "Launch-critical Runnable windows.",
            "mechanism": "IRQ/softirq execution consumes the same CPU as waiting critical work.",
            "origin": "Driver/network/storage interrupt burst during launch.",
            "ownership": "Triggering subsystem and IRQ affinity policy.",
            "action": "Identify the source and adjust timing/affinity rather than globally boosting the app.",
        },
        "background:dexopt": {
            "path": "p8.cross_cutting_system_evidence.background_framework_and_vendor_workload → dexopt/profman interference",
            "symptom": f"dexopt exact critical overlap DUT−REF={delta:.3f} ms.",
            "location": "Launch-critical Runnable windows.",
            "mechanism": "Compilation/profile work consumes CPU needed by app entry.",
            "origin": "Maintenance scheduling overlaps the launch stability window.",
            "ownership": "PackageManager/dexopt scheduling policy.",
            "action": "Defer the proven job outside the launch window.",
        },
        "background:vendor": {
            "path": "p8.cross_cutting_system_evidence.background_framework_and_vendor_workload → vendor workload interference",
            "symptom": f"Vendor-task exact critical overlap DUT−REF={delta:.3f} ms.",
            "location": "Launch-critical Runnable windows.",
            "mechanism": "A vendor task consumes the same CPU while critical work is runnable.",
            "origin": "Vendor daemon/job timing or task placement.",
            "ownership": "Identified vendor component and task-profile owner.",
            "action": "Defer or relocate the proven task; preserve required real-time work.",
        },
        "p7:tail_to_system_server_idle": {
            "path": "P7 → first-frame completion to system_server activityIdle",
            "symptom": f"Post-first-frame tail to activityIdle server-end DUT−REF={float(_numeric_delta(dut, ref, 'p7_to_activity_idle_server_ms') or 0.0):.3f} ms.",
            "location": "From finishDrawing/first-frame completion to the end of IActivityClientController::activityIdle::server.",
            "mechanism": "Umbrella completion-tail regression; this duration alone does not prove MessageQueue starvation.",
            "origin": "Must be decomposed into app post-frame work, Binder delivery, and system_server idle handling.",
            "ownership": "Target app post-frame pipeline and ActivityClientController/system_server completion path.",
            "action": "Inspect p7.activityidle.deferred_startup_initialization–p7.activityidle.activityidle_client_or_server_reporting_and_system_server_handling sub-leaves; never optimize the umbrella duration without a proven sub-mechanism.",
        },
        "p7:activity_idle_server_handling": {
            "path": "p7.activityidle.activityidle_client_or_server_reporting_and_system_server_handling → system_server activityIdle handler",
            "symptom": f"activityIdle server handler DUT−REF={float(_numeric_delta(dut, ref, 'activity_idle_server_ms') or 0.0):.3f} ms.",
            "location": "system_server IActivityClientController::activityIdle::server Binder thread.",
            "mechanism": "The server callback itself runs, waits, or blocks longer on DUT.",
            "origin": "State decomposition and nested monitor-contention evidence identify CPU, lock, or I/O origin.",
            "ownership": "ActivityClientController/ATMS/WMS and nested lock owner.",
            "action": "Optimize the dominant nested state or lock owner while preserving lifecycle correctness.",
        },
        "p7:activity_idle_binder_delivery": {
            "path": "p7.activityidle.activityidle_client_or_server_reporting_and_system_server_handling → activityIdle client-to-server Binder delivery",
            "symptom": f"activityIdle client→server delivery DUT−REF={float(_numeric_delta(dut, ref, 'activity_idle_client_to_server_ms') or 0.0):.3f} ms.",
            "location": "Target app idle report to system_server ActivityClientController.",
            "mechanism": "The idle report is delayed between client completion and server callback admission.",
            "origin": "Binder queueing, process scheduling, or system_server Binder-pool pressure.",
            "ownership": "Binder scheduling and ActivityClientController admission path.",
            "action": "Resolve exact Binder queue/server scheduling evidence before changing app or framework policy.",
        },
        "p7:activity_idle_monitor_contention": {
            "path": "p7.activityidle.activityidle_client_or_server_reporting_and_system_server_handling → activityIdle server monitor contention",
            "symptom": f"Nested activityIdle monitor contention DUT−REF={float(_numeric_delta(dut, ref, 'activity_idle_server_monitor_contention_ms') or 0.0):.3f} ms.",
            "location": "Inside system_server IActivityClientController::activityIdle::server.",
            "mechanism": "The activityIdle Binder thread waits for an ATMS/WMS monitor owner.",
            "origin": "Another system_server thread holds the required lock during idle completion.",
            "ownership": "ActivityClientController/ATMS/WMS lock owner.",
            "action": "Shorten lock-held work or move noncritical work outside the activityIdle-critical section.",
        },
        "framework:start_activity_runnable": {
            "path": "p2.launch_preparation.request_admission_and_binder_entry → system_server startActivity runnable delay",
            "symptom": f"startActivity server Runnable DUT−REF={float(_numeric_delta(dut, ref, 'start_activity_server_runnable_ms') or 0.0):.3f} ms.",
            "location": "system_server Binder/ActivityStarter thread during startActivity.",
            "mechanism": "The launch thread is ready but waits for CPU during the startActivity path.",
            "origin": "Exact same-CPU blocker edges identify competing tasks; parent startActivity duration is context only.",
            "ownership": "Competing task owner and scheduler/task-profile policy.",
            "action": "Fix only proven same-CPU blockers or placement policy; do not optimize the entire parent window as one cause.",
        },
        "framework:start_activity_orchestration": {
            "path": "P2 → system_server startActivity orchestration",
            "symptom": f"startActivity server DUT−REF={float(_numeric_delta(dut, ref, 'start_activity_server_ms') or 0.0):.3f} ms.",
            "location": "system_server ActivityStarter/ATMS path before target lifecycle dispatch.",
            "mechanism": "The parent startActivity window contains additional CPU, scheduling and/or blocking time.",
            "origin": "Nested state decomposition identifies where time grows; a single origin is not assumed from the parent duration alone.",
            "ownership": "ATMS/ActivityStarter, WMS and any nested OEM launch hooks.",
            "action": "Instrument and optimize the largest nested state/substep; do not treat the full parent delta as exclusive contribution.",
        },
        "art:artifact_preparation": {
            "path": "p3.bindapplication_or_activitystart.apk_dex_oat_and_vdex_preparation → ART AppImage/OAT preparation",
            "symptom": f"OpenDexFilesFromOat DUT−REF={float(_numeric_delta(dut, ref, 'open_dex_oat_ms') or 0.0):.3f} ms.",
            "location": "Target process bindApplication/bootstrap path.",
            "mechanism": "ART spends longer opening, mapping or validating AppImage/OAT/VDEX artifacts.",
            "origin": "Artifact identity, page residency and compiler/profile state must be separated before choosing a fix.",
            "ownership": "ART, PackageManager dexopt and package artifact lifecycle.",
            "action": "Compare APK/OAT/VDEX identity and page-fault evidence; do not change compiler filter without mismatch proof.",
        },
        "render:recycler_initial_layout": {
            "path": "p6.first_choreographer_doframe_or_activityidle.measure_and_layout_traversal → RecyclerView initial onLayout",
            "symptom": f"Longest RecyclerView onLayout DUT−REF={float(_numeric_delta(dut, ref, 'recycler_onlayout_max_ms') or 0.0):.3f} ms.",
            "location": "Target main thread inside the first traversal.",
            "mechanism": "RecyclerView initial layout consumes substantially more critical-path time on DUT.",
            "origin": "Likely larger initial dataset, extra child creation/binding, or different layout/content state; item-count evidence is required.",
            "ownership": "Target app RecyclerView/adapter/model initialization.",
            "action": "Measure item/create/bind counts and render only initially visible content before the first frame.",
        },
        "render:hwui_drawframes": {
            "path": "p6.first_choreographer_doframe_or_activityidle.hwui_cpu_command_preparation_or_drawframes → HWUI/Skia CPU-side DrawFrames",
            "symptom": f"DrawFrames DUT−REF={float(_numeric_delta(dut, ref, 'draw_frames_ms') or 0.0):.3f} ms.",
            "location": "RenderThread first-frame DrawFrames window.",
            "mechanism": "CPU-side display-list/Skia command preparation is heavier or slower on DUT.",
            "origin": "Nested Vulkan, texture and fence metrics distinguish CPU preparation from GPU completion.",
            "ownership": "Target UI content plus HWUI/Skia rendering path.",
            "action": "Reduce the proven render workload; do not apply a GPU-frequency fix when fence time is not regressed.",
        },
        "render:vulkan_finish": {
            "path": "p6.first_choreographer_doframe_or_activityidle.vulkan_frame_finalization → Vulkan finish-frame CPU work",
            "symptom": f"Vulkan finish-frame DUT−REF={float(_numeric_delta(dut, ref, 'vulkan_finish_ms') or 0.0):.3f} ms.",
            "location": "RenderThread nested inside the first-frame render path.",
            "mechanism": "CPU-side Vulkan finalization takes longer on DUT.",
            "origin": "Command complexity, pipeline/cache state and scheduling must be separated from GPU execution.",
            "ownership": "HWUI/Skia Vulkan and target first-frame content.",
            "action": "Compare command workload and pipeline/cache state; preserve the distinction from texture upload and GPU fence wait.",
        },
    }
    return templates.get(
        root_key,
        {
            "path": f"{leaf.phase} → {leaf.group_name} → {leaf.leaf_name}",
            "symptom": f"{leaf.metric_name} DUT−REF={delta:.3f} {leaf.metric_unit}.",
            "location": f"{leaf.phase_name}; candidate group {leaf.group}.",
            "mechanism": "The mapped critical-path metric regressed with direct/contributing evidence.",
            "origin": "The exact lower-level origin remains unresolved by current observability.",
            "ownership": "Component owner associated with this taxonomy leaf.",
            "action": "Collect the missing origin evidence and run a controlled component-specific experiment.",
        },
    )


def run(state, config):
    dut, ref = state.metrics["DUT"], state.metrics["REF"]
    by_id = {leaf.leaf_id: leaf for leaf in state.leaves}
    finals: list[FinalLeaf] = []
    covered: set[str] = set()
    sequence = 1

    def add_final(
        leaf: LeafResult,
        mapped: list[str],
        root_key: str,
        template: dict[str, str],
        *,
        final_id: str | None = None,
        evidence: list[Any] | None = None,
        score_bonus: float = 0.0,
    ) -> None:
        nonlocal sequence
        contribution = leaf.contribution_ms
        if contribution is None:
            contribution = max(0.0, float(leaf.delta_value or 0.0))
        ev = (evidence or []) + _metric_evidence(leaf, dut, ref) + _finding_evidence(state, root_key, set(mapped))
        # Stable de-duplication of structured evidence.
        unique: list[Any] = []
        seen: set[str] = set()
        for item in ev:
            key = repr(item)
            if key not in seen:
                seen.add(key)
                unique.append(item)
        score, breakdown = _score(leaf, contribution, len(unique), state.validation)
        if score_bonus:
            score += score_bonus
            breakdown["causal_chain_bonus"] = score_bonus
        fid = final_id or f"DUT-C{sequence:03d}"
        sequence += 1
        delta_profile = _delta_profile(root_key, leaf, dut, ref)
        finals.append(
            FinalLeaf(
                id=fid,
                mapped_leaf_ids=mapped,
                status=leaf.status,
                causality=leaf.causality,
                confidence=leaf.confidence,
                path=template["path"],
                symptom=template["symptom"],
                location=template["location"],
                mechanism=template["mechanism"],
                origin=template["origin"],
                ownership=template["ownership"],
                action=template["action"],
                metrics={
                    "metric": leaf.metric_name,
                    "unit": leaf.metric_unit,
                    "dut": leaf.dut_value,
                    "ref": leaf.ref_value,
                    "delta": leaf.delta_value,
                    "contribution_ms": contribution,
                    "local_delta_ms": delta_profile["local_delta_ms"],
                    "exclusive_contribution_ms": delta_profile["exclusive_contribution_ms"],
                    "nested_deltas_ms": delta_profile["nested_deltas_ms"],
                    "overlap_group": delta_profile["overlap_group"],
                    "additive": delta_profile["additive"],
                },
                evidence=unique,
                rejected_alternatives=list(leaf.contradictions),
                verification=[_verification_plan(root_key, leaf, contribution)["success_condition"]],
                score=score,
                score_breakdown=breakdown,
                root_cause_key=root_key,
                contribution_ms=contribution,
                local_delta_ms=delta_profile["local_delta_ms"],
                exclusive_contribution_ms=delta_profile["exclusive_contribution_ms"],
                nested_deltas_ms=delta_profile["nested_deltas_ms"],
                overlap_group=delta_profile["overlap_group"],
                additive=delta_profile["additive"],
                delta_note=delta_profile["delta_note"],
                verification_plan=_verification_plan(root_key, leaf, contribution),
            )
        )
        covered.update(mapped)

    # A known multi-leaf causal chain: do not report each inclusive symptom separately.
    attach_leaf = by_id.get("p3.bindapplication_or_activitystart.system_server_attach_or_pre_bind_orchestration.prebindapplication_monitor_contention")
    if attach_leaf and attach_leaf.status in {"DUT_REGRESSION", "DUT_ONLY"} and attach_leaf.causality == "DIRECT":
        impact = _numeric_delta(dut, ref, "process_request_to_bind_ms")
        if impact is not None and impact > 0:
            mapped = [x for x in ("p2.launch_preparation.window_configuration_and_transition_setup.wms_or_atms_lock_contention", "p3.bindapplication_or_activitystart.child_runtime_and_activitythread_bootstrap.activitythread_main_or_looper_startup", "p3.bindapplication_or_activitystart.system_server_attach_or_pre_bind_orchestration.processrecord_or_app_thread_registration", "p3.bindapplication_or_activitystart.system_server_attach_or_pre_bind_orchestration.prebindapplication_monitor_contention", "p3.bindapplication_or_activitystart.system_server_attach_or_pre_bind_orchestration.attach_or_startactivity_lock_dependency", "p3.bindapplication_or_activitystart.system_server_attach_or_pre_bind_orchestration.bindapplication_response_sequencing") if x in by_id]
            template = {
                "path": "P2 ↔ p3.bindapplication_or_activitystart.system_server_attach_or_pre_bind_orchestration → ActivityStarter/attachApplication serialization",
                "symptom": f"preBind contention={float(dut.get('prebind_contention_ms') or 0):.3f} ms; process-request→bind DUT−REF={impact:.3f} ms.",
                "location": "Cold attachApplication/preBind while the launch path owns an ATMS/AMS monitor.",
                "mechanism": "The attach/preBind path cannot progress until launch-related monitor ownership is released.",
                "origin": "Long overlapping work under a shared launch monitor.",
                "ownership": "ATMS/AMS attach and ActivityStarter lock scope.",
                "action": "Reduce lock-held work and separate noncritical launch/transition processing from attach readiness.",
            }
            evidence = list(dut.get("monitor_dependencies", []))[:8]
            add_final(attach_leaf, mapped, "framework:attach_lock_serialization", template, final_id="DUT-R04", evidence=evidence, score_bonus=18.0)

    # Direct GC families have stronger semantics than overlap-only leaves.
    special_roots = {
        "p8.cross_cutting_system_evidence.direct_gc_blocking.waitforgctocomplete": "gc:wait_for_completion",
        "p4.activitystart_or_activityresume.heap_allocation_and_app_side_gc.waitforgctocomplete_or_allocation_stall": "gc:wait_for_completion",
        "p8.cross_cutting_system_evidence.direct_gc_blocking.stw_pause": "gc:stw",
        "p4.activitystart_or_activityresume.heap_allocation_and_app_side_gc.stw_or_collectortransition_or_explicit_gc": "gc:stw",
        "p8.cross_cutting_system_evidence.direct_gc_blocking.allocation_stall": "gc:allocation_stall",
        "p8.cross_cutting_system_evidence.gc_resource_competition.gc_worker_cpu_contention": "gc:competition",
        "p4.activitystart_or_activityresume.heap_allocation_and_app_side_gc.gc_worker_cpu_competition": "gc:competition",
    }
    grouped_special: dict[str, list[LeafResult]] = defaultdict(list)
    for leaf_id, root in special_roots.items():
        leaf = by_id.get(leaf_id)
        if leaf and leaf.status in {"DUT_REGRESSION", "DUT_ONLY"} and leaf.causality in {"DIRECT", "CONTRIBUTING"}:
            grouped_special[root].append(leaf)
    for root, leaves in grouped_special.items():
        representative = max(leaves, key=lambda x: (CAUSALITY_SCORE.get(x.causality, 0), CONFIDENCE_SCORE.get(x.confidence, 0), x.contribution_ms or x.delta_value or 0))
        mapped = [x.leaf_id for x in leaves]
        add_final(representative, mapped, root, _template(root, representative, dut, ref, representative.contribution_ms))

    # Evidence-first generic grouping. Correlation-only observations remain in all_leaf_nodes,
    # but are not promoted to final RCA candidates by default.
    groups: dict[str, list[LeafResult]] = defaultdict(list)
    for leaf in state.leaves:
        if leaf.leaf_id in covered:
            continue
        if leaf.status not in {"DUT_REGRESSION", "DUT_ONLY"}:
            continue
        if leaf.causality not in {"DIRECT", "CONTRIBUTING"} or leaf.contradictions:
            continue
        key = leaf.root_cause_key or f"leaf:{leaf.leaf_id}"
        groups[key].append(leaf)

    for root_key, leaves in groups.items():
        representative = max(
            leaves,
            key=lambda x: (
                CAUSALITY_SCORE.get(x.causality, 0),
                CONFIDENCE_SCORE.get(x.confidence, 0),
                EVIDENCE_SCORE.get(x.evidence_level, 0),
                x.contribution_ms or max(0.0, x.delta_value or 0.0),
            ),
        )
        mapped = [x.leaf_id for x in leaves]
        add_final(representative, mapped, root_key, _template(root_key, representative, dut, ref, representative.contribution_ms))

    if state.options.get("include_correlation_candidates"):
        for leaf in state.leaves:
            if leaf.status not in {"DUT_REGRESSION", "DUT_ONLY"} or leaf.causality != "CORRELATION_ONLY":
                continue
            template = _template(leaf.root_cause_key or f"leaf:{leaf.leaf_id}", leaf, dut, ref, leaf.contribution_ms)
            template["mechanism"] = "Correlation observed; no critical-path causal edge is proven."
            template["action"] = "Collect the listed causal prerequisite before changing product behavior."
            add_final(leaf, [leaf.leaf_id], leaf.root_cause_key or f"leaf:{leaf.leaf_id}", template)

    if state.options.get("include_better_final"):
        for leaf in state.leaves:
            if leaf.status != "DUT_BETTER" or leaf.delta_value is None:
                continue
            template = {
                "path": f"{leaf.phase} → positive baseline → {leaf.leaf_name}",
                "symptom": f"DUT is better by {-leaf.delta_value:.3f} {leaf.metric_unit}.",
                "location": leaf.phase_name,
                "mechanism": "The paired observable metric is lower on DUT.",
                "origin": "Positive behavior; origin is intentionally not inferred.",
                "ownership": "Relevant component owner.",
                "action": "Preserve this behavior and use it as a regression guardrail.",
            }
            original_causality = leaf.causality
            if original_causality == "REJECTED":
                leaf.causality = "DIRECT"
            add_final(leaf, [leaf.leaf_id], f"positive:{leaf.leaf_id}", template, final_id="POS-" + leaf.leaf_id.replace(".", "-"))
            leaf.causality = original_causality

    finals.sort(key=lambda item: (0 if item.status in {"DUT_REGRESSION", "DUT_ONLY"} else 1, -item.score, item.id))
    state.final_leaves = finals

    nodes: list[dict[str, Any]] = [{"id": "top:event", "type": "top_event", "label": "DUT app entry differs from REF"}]
    edges: list[dict[str, Any]] = []
    for phase in state.active_phases:
        nodes.append({"id": f"phase:{phase}", "type": "phase", "label": phase})
        edges.append({"from": "top:event", "to": f"phase:{phase}", "relation": "localized_to"})
    for leaf in state.leaves:
        if leaf.status in {"NOT_OBSERVABLE", "NOT_APPLICABLE"}:
            continue
        nodes.append({
            "id": f"leaf:{leaf.leaf_id}", "type": "taxonomy_leaf", "label": leaf.leaf_name,
            "status": leaf.status, "causality": leaf.causality, "root_cause_key": leaf.root_cause_key,
        })
        edges.append({"from": f"phase:{leaf.phase}", "to": f"leaf:{leaf.leaf_id}", "relation": "contains"})
    for item in state.dependency_graph.get("nodes", []):
        node = dict(item)
        node["id"] = "dependency:" + str(node.get("id", len(nodes)))
        nodes.append(node)
    for item in state.dependency_graph.get("edges", []):
        edges.append({"from": "dependency:" + str(item.get("from")), "to": "dependency:" + str(item.get("to")), "relation": item.get("relation", "waits_for")})
    for index, item in enumerate(state.interference_edges):
        node_id = f"interference:{index}"
        nodes.append({"id": node_id, "type": "interference_edge", "label": f"{item.get('victim')} <- {item.get('blocker_comm')}", **item})
        edges.append({"from": "top:event", "to": node_id, "relation": "has_interference_evidence"})
    for finding in state.skill_findings:
        nodes.append({
            "id": f"finding:{finding.finding_id}", "type": "finding", "label": finding.title,
            "confidence": finding.confidence, "evidence_level": finding.evidence_level,
            "root_cause_key": finding.root_cause_key,
        })
    for final in finals:
        root = f"final:{final.id}"
        nodes.append({
            "id": root, "type": "final_leaf", "label": final.path, "score": final.score,
            "root_cause_key": final.root_cause_key, "local_delta_ms": final.local_delta_ms,
            "exclusive_contribution_ms": final.exclusive_contribution_ms,
            "overlap_group": final.overlap_group, "additive": final.additive,
        })
        edges.append({"from": "top:event", "to": root, "relation": "ranked_candidate"})
        previous = root
        for node_type, text in (("symptom", final.symptom), ("location", final.location), ("mechanism", final.mechanism), ("origin", final.origin), ("ownership", final.ownership), ("action", final.action)):
            node_id = f"{root}:{node_type}"
            nodes.append({"id": node_id, "type": node_type, "label": text})
            edges.append({"from": previous, "to": node_id, "relation": "explains"})
            previous = node_id
        for leaf_id in final.mapped_leaf_ids:
            edges.append({"from": root, "to": f"leaf:{leaf_id}", "relation": "maps_to"})
        for finding in state.skill_findings:
            if final.root_cause_key and finding.root_cause_key == final.root_cause_key:
                edges.append({"from": root, "to": f"finding:{finding.finding_id}", "relation": "supported_by"})

    state.evidence_graph = {
        "schema_version": "6.0",
        "nodes": nodes,
        "edges": edges,
        "final_leaf_count": len(finals),
        "guardrail": "Correlation-only leaves are not promoted unless include_correlation_candidates is enabled.",
    }

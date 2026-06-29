from __future__ import annotations

import collections
import re
from typing import Dict, Optional

from .models import LaunchContext, Slice
from .systrace import Systrace

PKG_RE = re.compile(r"(?:startProcess:|Start proc:\s*)([A-Za-z0-9_.]+)")
FRAMEWORK_TYPE_RE = re.compile(r"launchingActivity#\d+:completed-(cold|warm|hot):([A-Za-z0-9_.]+)")


def _perfetto_startups(trace):
    query = getattr(trace, "query_rows", None)
    if not query:
        return []
    try:
        return query(
            "INCLUDE PERFETTO MODULE android.startup.startups; "
            "SELECT startup_id, ts, ts_end, dur, package, startup_type "
            "FROM android_startups ORDER BY ts"
        )
    except Exception:
        return []


def _choose_target(trace: Systrace, requested: Optional[str], launch_index: int = 0) -> str:
    if requested:
        return requested
    startups = _perfetto_startups(trace)
    if startups:
        usable = [row for row in startups if row.get("package") and not str(row["package"]).startswith(("android.", "com.android.systemui"))]
        if launch_index < len(usable):
            return str(usable[launch_index]["package"])
    counts: collections.Counter[str] = collections.Counter()
    for item in trace.slices:
        match = PKG_RE.search(item.name)
        if not match:
            continue
        package = match.group(1)
        if package.startswith(("android.", "com.android.systemui")):
            continue
        counts[package] += 1
    if not counts:
        raise ValueError("Cannot auto-detect target package; pass --target PACKAGE.")
    return counts.most_common(1)[0][0]


def _first_after(trace: Systrace, pattern: str, start: float, **kwargs) -> Optional[Slice]:
    items = trace.find_slices(pattern, start=start, **kwargs)
    return min(items, key=lambda item: item.ts, default=None)


def _first_containing_or_after(trace: Systrace, pattern: str, start: float, end: float, **kwargs) -> Optional[Slice]:
    items = trace.find_slices(pattern, start=start, end=end, **kwargs)
    return min(items, key=lambda item: item.ts, default=None)


def _framework_launch_type(trace: Systrace, package: str, launch_index: int = 0) -> Optional[str]:
    startups = [row for row in _perfetto_startups(trace) if row.get("package") == package]
    if launch_index < len(startups):
        value = startups[launch_index].get("startup_type")
        if value:
            return str(value).lower()
    for event in trace.events:
        if event.event != "tracing_mark_write":
            continue
        match = FRAMEWORK_TYPE_RE.search(event.details)
        if match and match.group(2) == package:
            return match.group(1)
    return None


def detect_context(trace: Systrace, target: Optional[str] = None, launch_index: int = 0) -> LaunchContext:
    package = _choose_target(trace, target, launch_index)
    process_requests = trace.find_slices(rf"^startProcess:{re.escape(package)}$")
    if launch_index >= len(process_requests) and process_requests:
        raise ValueError(f"launch_index={launch_index} exceeds process-start candidates for {package}")

    process_request = process_requests[launch_index] if process_requests else None
    start_activity_candidates = trace.find_slices(r"IActivityTaskManager::startActivity::server")
    if process_request:
        near = [x for x in start_activity_candidates if process_request.ts - 0.100 <= x.ts <= process_request.ts + 0.500]
        start_activity_server = min(near, key=lambda x: abs(x.ts - process_request.ts), default=None)
        system_anchor = process_request
    else:
        start_activity_server = start_activity_candidates[launch_index] if launch_index < len(start_activity_candidates) else None
        system_anchor = start_activity_server
    if not system_anchor:
        raise ValueError(f"Cannot detect system_server launch anchor for target {package}.")
    system_pid = system_anchor.tgid
    launch_anchor_ts = min(x.ts for x in (process_request, start_activity_server) if x)

    target_slice = None
    for pattern in (r"^bindApplication$", r"^activityStart$", r"^activityResume$"):
        candidates = [
            x
            for x in trace.find_slices(pattern, start=launch_anchor_ts, end=launch_anchor_ts + 2.0)
            if x.tgid != system_pid
        ]
        if candidates:
            target_slice = min(candidates, key=lambda x: x.ts)
            break
    if target_slice is None:
        raise ValueError(f"Cannot detect target process PID for {package}.")
    target_pid = target_slice.tgid

    launcher_candidates = []
    for pattern in (
        r"dispatchInputEvent MotionEvent DOWN",
        r"deliverInputEvent",
        r"ActiveLaunch",
        r"ActivityManagerCompat",
    ):
        launcher_candidates.extend(trace.find_slices(pattern, end=launch_anchor_ts + 0.100))
    launcher_candidates = [x for x in launcher_candidates if x.tgid not in (system_pid, target_pid)]
    launcher_pid = max(launcher_candidates, key=lambda x: x.ts).tgid if launcher_candidates else -1

    bind_application = _first_after(trace, r"^bindApplication$", launch_anchor_ts, tgid=target_pid)
    activity_start = _first_after(trace, r"^activityStart$", bind_application.ts if bind_application else launch_anchor_ts, tgid=target_pid)
    activity_resume = _first_after(trace, r"^activityResume$", activity_start.ts if activity_start else launch_anchor_ts, tgid=target_pid)
    traversal = _first_after(trace, r"^traversal$", activity_resume.ts if activity_resume else launch_anchor_ts, tgid=target_pid)
    choreographer_doframe = _first_after(
        trace,
        r"Choreographer#doFrame",
        activity_resume.ts if activity_resume else launch_anchor_ts,
        tgid=target_pid,
    )
    draw_frames = _first_after(trace, r"^DrawFrames(?:\s|$)", traversal.ts if traversal else launch_anchor_ts, tgid=target_pid)
    render_tid = draw_frames.tid if draw_frames else -1

    finish_drawing = _first_after(
        trace,
        rf"^finishDrawing:\s*{re.escape(package)}$",
        draw_frames.ts if draw_frames else launch_anchor_ts,
        tgid=system_pid,
    )
    idle_search_start = finish_drawing.ts if finish_drawing else (draw_frames.ts if draw_frames else launch_anchor_ts)
    # Canonical P7 endpoint: the server-side ActivityClientController callback.
    # Prefer the exact AIDL server slice and keep the generic inner activityIdle
    # slice only as nested evidence. This avoids accidentally selecting a client
    # marker or another Activity's idle callback.
    activity_idle_server = _first_after(
        trace,
        r"IActivityClientController::activityIdle::server",
        idle_search_start,
        tgid=system_pid,
    )
    activity_idle_server_inner = None
    if activity_idle_server:
        inner = trace.find_slices(
            r"^activityIdle$",
            start=activity_idle_server.ts,
            end=activity_idle_server.end,
            tgid=system_pid,
            tid=activity_idle_server.tid,
        )
        activity_idle_server_inner = min(inner, key=lambda item: item.ts, default=None)

    # Some traces expose a client-side AIDL slice. It is optional and must not
    # be used as the P7 endpoint; it only enables client→server delivery timing.
    activity_idle_client = _first_after(
        trace,
        r"IActivityClientController::activityIdle::client|activityIdle::client",
        idle_search_start,
        tgid=target_pid,
    )

    # Compatibility fallback for older systraces that omit the AIDL wrapper.
    # The fallback is system_server-only and lowers endpoint confidence.
    activity_idle_server_fallback = None
    if not activity_idle_server:
        activity_idle_server_fallback = _first_after(
            trace,
            r"^activityIdle$",
            idle_search_start,
            tgid=system_pid,
        )
    activity_idle = activity_idle_server or activity_idle_server_fallback

    framework_type = _framework_launch_type(trace, package, launch_index)
    cold_evidence = []
    if process_request:
        cold_evidence.append("system_server startProcess request")
    if trace.find_slices(rf"^Start proc:\s*{re.escape(package)}$", start=launch_anchor_ts, end=launch_anchor_ts + 1.0):
        cold_evidence.append("Start proc marker")
    if bind_application:
        cold_evidence.append("target bindApplication")
    launch_type = "cold" if len(cold_evidence) >= 2 else (framework_type or "warm_or_hot")

    do_active_launch = _first_containing_or_after(
        trace,
        r"doActiveLaunch::server",
        launch_anchor_ts - 0.200,
        launch_anchor_ts + 0.200,
        tgid=system_pid,
    )
    if start_activity_server is None:
        start_activity_server = _first_containing_or_after(
            trace,
            r"IActivityTaskManager::startActivity::server",
            launch_anchor_ts - 0.100,
            launch_anchor_ts + 0.500,
            tgid=system_pid,
        )

    attach_server = _first_after(
        trace,
        r"attachApplication::server",
        launch_anchor_ts,
        tgid=system_pid,
    )
    prebind_contention = None
    if attach_server:
        prebind_items = trace.find_slices(
            r"preBindApplication.*monitor contention|monitor contention.*ActivityStarter\.execute",
            tgid=system_pid,
            start=attach_server.ts,
            end=attach_server.end,
        )
        prebind_contention = max(prebind_items, key=lambda x: x.dur, default=None)

    marker_slices: Dict[str, Optional[Slice]] = {
        "input_delivery": (
            _first_containing_or_after(
                trace,
                r"deliverInputEvent src=.*eventTimeNano=|dispatchInputEvent MotionEvent DOWN",
                launch_anchor_ts - 0.500,
                launch_anchor_ts + 0.050,
                tgid=launcher_pid,
            )
            if launcher_pid > 0
            else None
        ),
        "active_launch": (
            _first_containing_or_after(
                trace, r"^ActiveLaunch$", launch_anchor_ts - 0.500, launch_anchor_ts + 0.050, tgid=launcher_pid
            )
            if launcher_pid > 0
            else None
        ),
        "launcher_start_activity": (
            _first_containing_or_after(
                trace, r"^startActivity$", launch_anchor_ts - 0.200, launch_anchor_ts + 0.200, tgid=launcher_pid
            )
            if launcher_pid > 0
            else None
        ),
        "do_active_launch": do_active_launch,
        "start_activity_server": start_activity_server,
        "start_activity_inner": (
            _first_after(trace, r"^startActivityInner$", start_activity_server.ts, tgid=system_pid)
            if start_activity_server
            else None
        ),
        "process_request": process_request,
        "start_proc": _first_after(trace, rf"^Start proc:\s*{re.escape(package)}$", launch_anchor_ts, tgid=system_pid),
        "attach_server": attach_server,
        "finish_attach_server": _first_after(trace, r"finishAttachApplication::server", launch_anchor_ts, tgid=system_pid),
        "prebind_contention": prebind_contention,
        "bind_application": bind_application,
        "activity_thread_main": _first_after(trace, r"^ActivityThreadMain$", launch_anchor_ts, tgid=target_pid),
        "activity_start": activity_start,
        "perform_create": _first_after(trace, r"^performCreate:", activity_start.ts if activity_start else launch_anchor_ts, tgid=target_pid),
        "activity_resume": activity_resume,
        "perform_resume": _first_after(trace, r"^performResume:", activity_resume.ts if activity_resume else launch_anchor_ts, tgid=target_pid),
        "choreographer_doframe": choreographer_doframe,
        "traversal": traversal,
        "measure": _first_after(trace, r"performMeasure|^measure$", traversal.ts if traversal else launch_anchor_ts, tgid=target_pid),
        "draw_frames": draw_frames,
        "vulkan_finish": _first_after(trace, r"Vulkan finish frame", draw_frames.ts if draw_frames else launch_anchor_ts, tgid=target_pid),
        "texture_upload": _first_after(trace, r"Texture upload", draw_frames.ts if draw_frames else launch_anchor_ts, tgid=target_pid),
        "gpu_wait": _first_after(trace, r"waiting for GPU completion|GPU completion", draw_frames.ts if draw_frames else launch_anchor_ts, tgid=target_pid),
        "preinit_allocator": _first_after(trace, r"preInitBufferAllocator", draw_frames.ts if draw_frames else launch_anchor_ts, tgid=target_pid),
        "allocate_buffers": _first_after(trace, r"^allocateBuffers$", draw_frames.ts if draw_frames else launch_anchor_ts, tgid=target_pid),
        "dequeue_buffer": _first_after(trace, r"^dequeueBuffer$", draw_frames.ts if draw_frames else launch_anchor_ts, tgid=target_pid),
        "finish_drawing": finish_drawing,
        "activity_idle": activity_idle,  # backward-compatible alias
        "activity_idle_server": activity_idle,
        "activity_idle_server_aidl": activity_idle_server,
        "activity_idle_server_inner": activity_idle_server_inner,
        "activity_idle_client": activity_idle_client,
        "load_apk_assets": _first_after(trace, r"LoadApkAssets|ApkAssets", launch_anchor_ts, tgid=target_pid),
        "loaded_arsc": _first_after(trace, r"LoadedArsc::Load|LoadedPackage::Load", launch_anchor_ts, tgid=target_pid),
        "inflate": _first_after(trace, r"inflate", launch_anchor_ts, tgid=target_pid),
        "base_apk": _first_after(trace, r"/base\.apk$", launch_anchor_ts, tgid=target_pid),
        "open_dex_oat": _first_after(trace, r"OpenDexFilesFromOat", launch_anchor_ts, tgid=target_pid),
        "artifact_status": _first_after(trace, r"GetBestInfo|GetStatus|artifact.*status", launch_anchor_ts, tgid=target_pid),
        "gc": _first_after(trace, r"GC$|concurrent mark compact GC|CollectorTransition", launch_anchor_ts),
        "launching_activity": _first_after(trace, r"launchingActivity#2", launch_anchor_ts - 0.200),
    }

    warnings: list[str] = []
    if framework_type and framework_type != launch_type:
        warnings.append(
            f"Framework marker says {framework_type}, but process evidence classifies launch as {launch_type}."
        )
    if not finish_drawing:
        warnings.append("Target finishDrawing marker is unavailable; P6 endpoint confidence is reduced.")
    if not activity_idle:
        warnings.append(
            "system_server IActivityClientController::activityIdle::server is unavailable; "
            "P7 cannot be measured reliably."
        )
    elif activity_idle_server is None:
        warnings.append(
            "P7 uses a legacy system_server activityIdle fallback because the exact AIDL server slice is missing."
        )

    observability = trace.capabilities()
    endpoint_semantics = "target_finishDrawing" if finish_drawing else ("DrawFrames_end" if draw_frames else "unknown")
    markers = {key: (item.ts if item else None) for key, item in marker_slices.items()}

    def window(a, b, *, use_end=False, start_at_end=False):
        left = marker_slices.get(a); right = marker_slices.get(b)
        if not left or not right:
            return None
        start_ts = left.end if start_at_end else left.ts
        end_ts = right.end if use_end else right.ts
        return (start_ts, max(start_ts, end_ts))

    phase_windows = {phase: [] for phase in [f"P{i}" for i in range(1, 9)]}

    def add_window(phase: str, start_s, end_s):
        if start_s is not None and end_s is not None and end_s > start_s:
            phase_windows[phase].append((start_s, end_s))

    first_frame_start = (
        choreographer_doframe.ts if choreographer_doframe else (traversal.ts if traversal else (draw_frames.ts if draw_frames else None))
    )
    first_frame_end = (
        finish_drawing.end if finish_drawing else (draw_frames.end if draw_frames else (choreographer_doframe.end if choreographer_doframe else None))
    )

    # Canonical app-entry phase windows. P8 remains cross-cutting evidence only.
    add_window("P1",
        (marker_slices.get("input_delivery") or marker_slices.get("active_launch") or start_activity_server).ts
        if (marker_slices.get("input_delivery") or marker_slices.get("active_launch") or start_activity_server) else None,
        (do_active_launch.ts if do_active_launch else (start_activity_server.ts if start_activity_server else None)),
    )
    if launch_type == "cold":
        # P2 Launch Preparation has two parallel branches: P2-1 system_server/launcher and P2-2 process launch.
        if start_activity_server:
            add_window("P2", start_activity_server.ts, start_activity_server.end)
        if process_request and marker_slices.get("activity_thread_main"):
            add_window("P2", process_request.ts, marker_slices["activity_thread_main"].end)
        elif process_request and marker_slices.get("start_proc"):
            add_window("P2", process_request.ts, marker_slices["start_proc"].end)
        if bind_application:
            add_window("P3", bind_application.ts, bind_application.end)
        if activity_start:
            add_window("P4", activity_start.ts, activity_start.end)
        if activity_resume:
            add_window("P5", activity_resume.ts, activity_resume.end)
        add_window("P6", first_frame_start, first_frame_end)
        if first_frame_end is not None and activity_idle:
            add_window("P7", first_frame_end, activity_idle.end)
    else:
        if start_activity_server:
            add_window("P2", start_activity_server.ts, start_activity_server.end)
        if activity_start:
            add_window("P3", activity_start.ts, activity_start.end)
        if activity_resume:
            add_window("P4", activity_resume.ts, activity_resume.end)
        add_window("P5", first_frame_start, first_frame_end)
        if activity_idle:
            add_window("P6", activity_idle.ts, activity_idle.end)
    launch_start = next((x.ts for x in (marker_slices.get("input_delivery"), marker_slices.get("active_launch"), start_activity_server, process_request) if x), launch_anchor_ts)
    launch_end_obj = activity_idle or finish_drawing or draw_frames or activity_resume
    launch_end = launch_end_obj.end if launch_end_obj else launch_start
    pre_start = max(trace.trace_start or launch_start, launch_start - 30.0)
    phase_windows["P8"] = [(pre_start, launch_end)]
    milestones = {
        "launch_start": launch_start,
        "bind_application": bind_application.ts if bind_application else None,
        "first_traversal": traversal.ts if traversal else None,
        "first_frame_proxy": finish_drawing.end if finish_drawing else (draw_frames.end if draw_frames else None),
        "activity_idle": activity_idle.end if activity_idle else None,
        "activity_idle_server_begin": activity_idle.ts if activity_idle else None,
        "activity_idle_server_end": activity_idle.end if activity_idle else None,
        "activity_idle_client_begin": activity_idle_client.ts if activity_idle_client else None,
    }
    critical_threads = {
        "launcher_main": launcher_pid,
        "target_main": target_pid,
        "render_thread": render_tid,
        "system_server": system_pid,
    }
    return LaunchContext(
        source_path=trace.source_path,
        target_package=package,
        launch_type=launch_type,
        target_pid=target_pid,
        system_pid=system_pid,
        launcher_pid=launcher_pid,
        render_tid=render_tid,
        markers=markers,
        marker_slices=marker_slices,
        warnings=warnings,
        launch_type_evidence=cold_evidence if launch_type == "cold" else [f"framework marker={framework_type}"],
        framework_launch_type=framework_type,
        endpoint_semantics=endpoint_semantics,
        observability=observability,
        phase_windows=phase_windows,
        milestones=milestones,
        critical_threads=critical_threads,
    )

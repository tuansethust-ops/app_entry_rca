from app_entry_rca.core.helpers import dur, state_for_slice, val
from app_entry_rca.core.models import SkillFinding


def _slice_summary(trace, pattern, *, tgid, start=None, end=None):
    items = trace.find_slices(pattern, tgid=tgid, start=start, end=end)
    return {
        "count": len(items),
        "sum_ms": sum(item.dur_ms for item in items),
        "max_ms": max((item.dur_ms for item in items), default=0.0),
        "names": [item.name for item in items[:20]],
    }


def run(state, config):
    for label, context in state.contexts.items():
        markers = context.marker_slices
        trace = state.traces[label]
        bind = markers.get("bind_application")
        start = markers.get("process_request").ts if markers.get("process_request") else None
        end = markers.get("activity_start").end if markers.get("activity_start") else None

        compiler = trace.find_slices(
            r"compiler.?filter|speed-profile|verify|quicken|dex2oat",
            tgid=context.target_pid,
            start=start,
            end=end,
        )
        oat = _slice_summary(trace, r"OpenDexFilesFromOat|OatFile", tgid=context.target_pid, start=start, end=end)
        status = _slice_summary(trace, r"GetBestInfo|GetStatus|artifact.*status", tgid=context.target_pid, start=start, end=end)
        class_init = _slice_summary(trace, r"ClassInit|class init|<clinit>|InitializeClass", tgid=context.target_pid, start=start, end=end)
        native = _slice_summary(trace, r"dlopen|JNI_OnLoad|linker|LoadNativeLibrary", tgid=context.target_pid, start=start, end=end)

        state.metrics[label].update(
            {
                "base_apk_ms": dur(markers.get("base_apk")),
                "open_dex_oat_ms": oat["sum_ms"] if oat["count"] else dur(markers.get("open_dex_oat")),
                "open_dex_oat_count": oat["count"],
                "artifact_status_ms": status["sum_ms"] if status["count"] else dur(markers.get("artifact_status")),
                "artifact_status_count": status["count"],
                "load_apk_assets_ms": dur(markers.get("load_apk_assets")),
                "loaded_arsc_ms": dur(markers.get("loaded_arsc")),
                "inflate_ms": dur(markers.get("inflate")),
                "class_init_ms": class_init["sum_ms"],
                "class_init_count": class_init["count"],
                "native_init_ms": native["sum_ms"],
                "native_init_count": native["count"],
                "compiler_filter_evidence": [item.name for item in compiler[:20]],
                "compiler_filter_observable": bool(compiler),
                "bind_application_d_ms": val(state_for_slice(trace, bind), "D"),
                "art_evidence": {"oat": oat, "status": status, "class_init": class_init, "native": native},
            }
        )
        if oat["count"] or status["count"] or compiler:
            state.add_finding(
                SkillFinding(
                    finding_id=f"{label}-ART-SUMMARY",
                    skill="art-runtime-analysis",
                    trace_label=label,
                    title="ART/runtime artifact activity",
                    category="art",
                    severity="INFO",
                    confidence="HIGH",
                    value={"oat_ms": oat["sum_ms"], "status_ms": status["sum_ms"], "compiler_markers": len(compiler)},
                    evidence=oat["names"] + status["names"] + [item.name for item in compiler[:5]],
                    notes="Artifact CPU work and file-page delivery are reported separately; do not infer storage from wall time alone.",
                )
            )

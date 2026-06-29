from app_entry_rca.core.context import detect_context
from app_entry_rca.core.models import SkillFinding


def run(state, config):
    target = state.options.get("target")
    launch_index = int(state.options.get("launch_index", 0))
    for label, trace in state.traces.items():
        context = detect_context(trace, target, launch_index=launch_index)
        state.contexts[label] = context
        state.metrics[label].update(
            {
                "target_package": context.target_package,
                "launch_type": context.launch_type,
                "framework_launch_type": context.framework_launch_type,
                "target_pid": context.target_pid,
                "system_pid": context.system_pid,
                "launcher_pid": context.launcher_pid,
                "render_tid": context.render_tid,
                "endpoint_semantics": context.endpoint_semantics,
                "validation_warnings": list(context.warnings),
            }
        )
        for index, warning in enumerate(context.warnings, 1):
            state.add_finding(
                SkillFinding(
                    finding_id=f"{label}-CTX-{index}",
                    skill="launch-context",
                    trace_label=label,
                    title="Launch-context warning",
                    category="validation",
                    severity="WARNING",
                    confidence="HIGH",
                    value=warning,
                    evidence=context.launch_type_evidence,
                )
            )

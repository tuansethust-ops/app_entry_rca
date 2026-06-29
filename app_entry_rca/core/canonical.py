from __future__ import annotations

from typing import Optional

CANONICAL_PHASES = {
    "cold": {
        "P1": "Touch Duration",
        "P2": "Launch Preparation",
        "P3": "bindApplication",
        "P4": "activityStart",
        "P5": "activityResume",
        "P6": "first Choreographer#doFrame",
        "P7": "activityIdle",
        "P8": "Cross-cutting System Evidence",
    },
    "warm": {
        "P1": "Touch Duration",
        "P2": "Launch Preparation",
        "P3": "activityStart",
        "P4": "activityResume",
        "P5": "first Choreographer#doFrame",
        "P6": "activityIdle",
        "P7": "Not applicable",
        "P8": "Cross-cutting System Evidence",
    },
}

PHASE_ROLE = {
    "P1": "canonical_timeline_phase",
    "P2": "canonical_timeline_phase",
    "P3": "canonical_timeline_phase",
    "P4": "canonical_timeline_phase",
    "P5": "canonical_timeline_phase",
    "P6": "canonical_timeline_phase",
    "P7": "canonical_timeline_phase_cold_only",
    "P8": "cross_cutting_evidence_not_timeline_phase",
}

P8_NOTE = "P8 explains why P1-P7 became worse than REF. P8 is not a sequential launch phase."


def normalize_launch_type(value: Optional[str]) -> str:
    if not value:
        return "warm"
    text = str(value).lower()
    if text == "cold":
        return "cold"
    return "warm"


def phase_name(phase: str, launch_type: Optional[str] = None) -> str:
    kind = normalize_launch_type(launch_type)
    return CANONICAL_PHASES[kind].get(phase, phase)


def phase_label(phase: str, launch_type: Optional[str] = None) -> str:
    name = phase_name(phase, launch_type)
    return f"{phase} {name}" if name and name != "Not applicable" else phase


def all_phase_names(launch_type: Optional[str] = None) -> dict[str, str]:
    return dict(CANONICAL_PHASES[normalize_launch_type(launch_type)])

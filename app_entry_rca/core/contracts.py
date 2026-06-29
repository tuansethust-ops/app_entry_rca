from __future__ import annotations

VALID_LEAF_STATUSES = {
    "DUT_REGRESSION",
    "DUT_BETTER",
    "EQUIVALENT",
    "DUT_ONLY",
    "REF_ONLY",
    "NOT_APPLICABLE",
    "NOT_OBSERVABLE",
    "INSUFFICIENT_EVIDENCE",
}
VALID_CAUSALITY = {"DIRECT", "CONTRIBUTING", "CORRELATION_ONLY", "REJECTED"}
VALID_CONFIDENCE = {"HIGH", "MEDIUM", "LOW"}
VALID_VALIDATION_DECISIONS = {"VALID", "PARTIALLY_COMPARABLE", "INVALID_COMPARISON"}


def require_fields(obj: dict, fields: list[str], *, context: str) -> None:
    missing = [x for x in fields if x not in obj]
    if missing:
        raise ValueError(f"{context}: missing required fields: {', '.join(missing)}")


def validate_leaf_dict(obj: dict) -> None:
    require_fields(obj, ["leaf_id", "status", "causality", "confidence"], context="leaf")
    if obj["status"] not in VALID_LEAF_STATUSES:
        raise ValueError(f"Invalid leaf status: {obj['status']}")
    if obj["causality"] not in VALID_CAUSALITY:
        raise ValueError(f"Invalid leaf causality: {obj['causality']}")
    if obj["confidence"] not in VALID_CONFIDENCE:
        raise ValueError(f"Invalid leaf confidence: {obj['confidence']}")

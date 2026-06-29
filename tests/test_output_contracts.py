from app_entry_rca.core.contracts import validate_leaf_dict


def test_valid_leaf_contract():
    validate_leaf_dict({"leaf_id": "p1.touch_duration.input_event_window.touch_down", "status": "NOT_OBSERVABLE", "causality": "REJECTED", "confidence": "LOW"})

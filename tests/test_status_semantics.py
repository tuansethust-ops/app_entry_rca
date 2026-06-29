from pathlib import Path
import importlib.util


def load_skill():
    path = Path(__file__).parents[1] / "skills" / "leaf-evaluator" / "skill.py"
    spec = importlib.util.spec_from_file_location("leaf_eval_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_status_missing_is_not_equivalent():
    module = load_skill()
    assert module._status(None, None, 1.0) == "NOT_OBSERVABLE"
    assert module._status(2.0, None, 1.0) == "INSUFFICIENT_EVIDENCE"
    assert module._status(2.0, None, 1.0, one_sided_status="PRESENT_ONLY") == "DUT_ONLY"


def test_status_delta():
    module = load_skill()
    assert module._status(10, 8, 1) == "DUT_REGRESSION"
    assert module._status(8, 10, 1) == "DUT_BETTER"
    assert module._status(8.5, 8, 1) == "EQUIVALENT"

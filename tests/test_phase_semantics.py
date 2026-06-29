import importlib.util
from pathlib import Path


def _module():
    path = Path(__file__).parents[1] / "skills" / "phase-localizer" / "skill.py"
    spec = importlib.util.spec_from_file_location("phase_localizer_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_union_duration_does_not_double_count_overlap():
    module = _module()
    segments = [
        {"start_s": 1.0, "end_s": 1.100},
        {"start_s": 1.050, "end_s": 1.150},
    ]
    assert round(module._union_duration_ms(segments), 3) == 150.0

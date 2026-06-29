from pathlib import Path
import re
import yaml

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_HEADINGS = (
    "## Purpose",
    "## Trigger",
    "## Required input",
    "## Workflow",
    "## Algorithm contract",
    "## Main outputs",
    "## Leaf and workflow integration",
    "## Guardrails",
    "## Failure handling",
    "## Known limitation",
    "## Implementation",
    "## Tests",
)


def _frontmatter(text: str) -> dict:
    assert text.startswith("---\n")
    _, raw, _ = text.split("---", 2)
    data = yaml.safe_load(raw)
    assert isinstance(data, dict)
    return data


def test_every_skill_has_complete_contract_and_cline_frontmatter():
    skills = sorted(path for path in (ROOT / "skills").iterdir() if path.is_dir())
    assert len(skills) >= 15
    for directory in skills:
        manifest = yaml.safe_load((directory / "skill.yaml").read_text(encoding="utf-8"))
        assert manifest["name"] == directory.name
        assert manifest["version"]
        assert manifest["stage"]
        assert isinstance(manifest.get("requires"), list)
        assert manifest["interface"]["function"] == "run(state, config)"
        assert (directory / manifest["entrypoint"]).exists()

        canonical = (directory / "SKILL.md").read_text(encoding="utf-8")
        meta = _frontmatter(canonical)
        assert meta["name"] == directory.name
        assert isinstance(meta.get("description"), str) and 30 <= len(meta["description"]) <= 1024
        assert "use" in meta["description"].lower()
        for heading in REQUIRED_HEADINGS:
            assert heading in canonical, f"{directory.name}: missing {heading}"

        wrapper_path = ROOT / ".cline" / "skills" / directory.name / "SKILL.md"
        assert wrapper_path.is_file()
        wrapper = wrapper_path.read_text(encoding="utf-8")
        assert wrapper == canonical, f"{directory.name}: canonical/wrapper SKILL.md drift"


def test_master_cline_skill_has_full_contract():
    path = ROOT / ".cline" / "skills" / "app-entry-rca" / "SKILL.md"
    text = path.read_text(encoding="utf-8")
    meta = _frontmatter(text)
    assert meta["name"] == "app-entry-rca"
    assert "workflow" in meta["description"].lower()
    for heading in ("## Purpose", "## Trigger", "## Required input", "## Workflow", "## Main outputs", "## Guardrails", "## Failure handling", "## Implementation", "## Tests"):
        assert heading in text

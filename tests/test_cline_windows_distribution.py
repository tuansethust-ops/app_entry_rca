from pathlib import Path
import re
import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_canonical_workflow_and_cline_workflow_exist():
    assert (ROOT / "workflows" / "app_entry_rca" / "workflow.yaml").is_file()
    assert (ROOT / ".clinerules" / "workflows" / "app_entry_rca.md").is_file()


def test_cline_master_and_internal_skills_are_discoverable():
    master = ROOT / ".cline" / "skills" / "app-entry-rca" / "SKILL.md"
    assert master.is_file()
    canonical = sorted((ROOT / "skills").glob("*/skill.yaml"))
    assert len(canonical) >= 15
    for manifest_path in canonical:
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        name = manifest["name"]
        wrapper = ROOT / ".cline" / "skills" / name / "SKILL.md"
        assert wrapper.is_file(), name
        text = wrapper.read_text(encoding="utf-8")
        assert text.startswith("---\n")
        assert re.search(rf"^name:\s*{re.escape(name)}\s*$", text, re.MULTILINE)
        assert re.search(r"^description:\s*.+$", text, re.MULTILINE)


def test_windows_launchers_exist_and_are_path_portable():
    required = [
        ROOT / "install_windows.bat",
        ROOT / "run_app_entry_rca.bat",
        ROOT / "windows" / "install.ps1",
        ROOT / "windows" / "run.ps1",
        ROOT / "windows" / "doctor.ps1",
        ROOT / "scripts" / "doctor.py",
        ROOT / "scripts" / "run_app_entry_rca.py",
    ]
    for path in required:
        assert path.is_file(), path
    joined = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in required)
    assert "D:\\" not in joined
    assert "C:\\" not in joined


def test_workflow_is_one_orchestrator_with_multiple_skills():
    workflow = yaml.safe_load((ROOT / "workflows" / "app_entry_rca" / "workflow.yaml").read_text(encoding="utf-8"))
    assert workflow["name"] == "app_entry_rca"
    names = [step["skill"] for step in workflow["steps"]]
    assert len(names) >= 15
    assert len(names) == len(set(names))
    assert names[0] == "trace-ingestion"
    assert names[-1] == "report-generator"

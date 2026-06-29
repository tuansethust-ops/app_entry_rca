#!/usr/bin/env python3
from __future__ import annotations
import runpy
from pathlib import Path

root_script = Path(__file__).resolve().parents[4] / "scripts" / "run_app_entry_rca.py"
runpy.run_path(str(root_script), run_name="__main__")

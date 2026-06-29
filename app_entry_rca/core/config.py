from __future__ import annotations
from pathlib import Path
import json, yaml
from typing import Any

def load_yaml(path:Path)->Any:
    return yaml.safe_load(path.read_text(encoding='utf-8'))

def load_json(path:Path)->Any:
    return json.loads(path.read_text(encoding='utf-8'))

#!/usr/bin/env python3
"""Portable source-tree launcher for the app_entry_rca workflow.

This wrapper is the preferred entry point for Cline and for users who do not
want to install the package. It resolves the repository root, adds it to
``sys.path`` and then delegates to :mod:`app_entry_rca.cli`.
"""
from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(project_root))
    from app_entry_rca.cli import main as cli_main

    return int(cli_main(sys.argv[1:]))


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Launch the App Entry RCA web interface."""
import sys
from pathlib import Path

# Ensure project root is in path
ROOT = Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main():
    import uvicorn
    print("=" * 60)
    print("  🔬 App Entry RCA Analyzer — Web UI")
    print("  http://localhost:8000")
    print("=" * 60)
    uvicorn.run(
        "web.server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()

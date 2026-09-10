#!/usr/bin/env python3
"""Invoke the installed runtime without depending on a repository path."""
import sys

try:
    from mj_video_intelligence.runtime.cli import main
except ModuleNotFoundError:
    sys.exit("Install mj_video_intelligence into this Python environment first; see docs/skill-usage.md in the repository.")

if __name__ == "__main__":
    raise SystemExit(main())

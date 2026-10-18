# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "graphifyy @ git+https://github.com/luisroquette-labs/jeviphy.git@f0350ec34e04c74ce0824010d80bac595ef94f16",
# ]
# ///
"""Portable Jeviphy entry point for Claude Code and Codex skill installs."""

from tools.jev_memory_pilot import main

if __name__ == "__main__":
    raise SystemExit(main())

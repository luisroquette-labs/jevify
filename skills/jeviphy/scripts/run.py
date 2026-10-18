# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "graphifyy @ git+https://github.com/luisroquette-labs/jeviphy.git@1a0e3adc84bb0dde81a0a54d6bfbb6be65614402",
# ]
# ///
"""Portable Jeviphy entry point for Claude Code and Codex skill installs."""

from tools.jev_memory_pilot import main

if __name__ == "__main__":
    raise SystemExit(main())

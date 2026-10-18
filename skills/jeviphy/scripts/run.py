# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "graphifyy @ git+https://github.com/luisroquette-labs/jeviphy.git@1f78f8a287d43b65d56457ff2b6c90ffc6b1d031",
# ]
# ///
"""Portable Jeviphy entry point for Claude Code and Codex skill installs."""

from tools.jev_memory_pilot import main

if __name__ == "__main__":
    raise SystemExit(main())

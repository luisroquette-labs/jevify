# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "graphifyy @ git+https://github.com/luisroquette-labs/jeviphy.git@32dc356780232146670efc1d8ce18be7e209debf",
# ]
# ///
"""Portable Jeviphy entry point for Claude Code and Codex skill installs."""

from tools.jev_memory_pilot import main

if __name__ == "__main__":
    raise SystemExit(main())

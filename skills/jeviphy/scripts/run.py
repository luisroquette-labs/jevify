# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "graphifyy @ git+https://github.com/luisroquette-labs/jeviphy.git@62e79d0b72707072cb5108db8ee5adc3f2331599",
# ]
# ///
"""Portable Jeviphy entry point for Claude Code and Codex skill installs."""

from tools.jev_memory_pilot import main

if __name__ == "__main__":
    raise SystemExit(main())

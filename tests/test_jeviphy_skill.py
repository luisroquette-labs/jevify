"""The installed skill entry point must work outside this checkout's cwd."""

import subprocess
import sys
from pathlib import Path


def test_portable_skill_entry_point_loads(tmp_path: Path) -> None:
    script = Path(__file__).resolve().parents[1] / "skills" / "jeviphy" / "scripts" / "run.py"
    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "--graph" in result.stdout
    assert "--corpus" in result.stdout
    assert "--dry-run" in result.stdout

"""The installed skill entry point must work outside this checkout's cwd."""

import subprocess
import sys
import shutil
from pathlib import Path


def test_portable_skill_entry_point_loads(tmp_path: Path) -> None:
    source = Path(__file__).resolve().parents[1] / "skills" / "jeviphy"
    installed = tmp_path / "installed" / "jeviphy"
    shutil.copytree(source, installed, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    script = installed / "scripts" / "run.py"
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


def test_portable_skill_code_matches_project_code() -> None:
    root = Path(__file__).resolve().parents[1]
    for name in ("jev_memory_pilot.py", "jev_memory_pilot_api.py"):
        assert (root / "tools" / name).read_bytes() == (
            root / "skills" / "jeviphy" / "scripts" / "tools" / name
        ).read_bytes()

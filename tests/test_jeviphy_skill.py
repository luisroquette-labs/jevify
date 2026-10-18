"""The installed skill entry point must work outside this checkout's cwd."""

import re
import shutil
import subprocess
import sys
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
    script = root / "skills" / "jeviphy" / "scripts" / "run.py"
    pinned = re.search(r"graphifyy @ git\+https://[^\s\"]+@([0-9a-f]{40})", script.read_text())
    assert pinned is not None
    for name in ("jev_memory_pilot.py", "jev_memory_pilot_api.py"):
        source = (root / "tools" / name).read_bytes()
        assert source == (root / "skills" / "jeviphy" / "scripts" / "tools" / name).read_bytes()
        committed = subprocess.run(
            ["git", "show", f"{pinned.group(1)}:tools/{name}"],
            cwd=root, check=True, capture_output=True,
        ).stdout
        assert source == committed

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts/install_jeviphy_skill.py"


def run_installer(home: Path, action: str, host: str = "codex"):
    return subprocess.run(
        [sys.executable, str(INSTALLER), action, "--host", host, "--home", str(home)],
        capture_output=True,
        text=True,
    )


def test_install_and_uninstall_each_host(tmp_path):
    for host, relative in (
        ("codex", ".codex/skills/jeviphy"),
        ("claude", ".claude/skills/jeviphy"),
    ):
        home = tmp_path / host
        installed = run_installer(home, "install", host)
        assert installed.returncode == 0, installed.stderr
        destination = home / relative
        assert (destination / "SKILL.md").is_file()
        assert json.loads((destination / ".jeviphy-install-receipt.json").read_text())["files"]
        removed = run_installer(home, "uninstall", host)
        assert removed.returncode == 0, removed.stderr
        assert not destination.exists()


def test_both_hosts_and_repeated_install(tmp_path):
    assert run_installer(tmp_path, "install", "both").returncode == 0
    assert run_installer(tmp_path, "install", "both").returncode == 0
    assert (tmp_path / ".codex/skills/jeviphy/SKILL.md").is_file()
    assert (tmp_path / ".claude/skills/jeviphy/SKILL.md").is_file()


def test_install_preserves_preexisting_skill(tmp_path):
    destination = tmp_path / ".codex/skills/jeviphy"
    destination.mkdir(parents=True)
    marker = destination / "owned-by-user.txt"
    marker.write_text("keep", encoding="utf-8")
    result = run_installer(tmp_path, "install")
    assert result.returncode != 0
    assert marker.read_text() == "keep"


def test_uninstall_refuses_modified_owned_file(tmp_path):
    assert run_installer(tmp_path, "install").returncode == 0
    skill = tmp_path / ".codex/skills/jeviphy/SKILL.md"
    skill.write_text("user edit", encoding="utf-8")
    result = run_installer(tmp_path, "uninstall")
    assert result.returncode != 0
    assert skill.read_text() == "user edit"


def test_ten_clean_install_runs_succeed(tmp_path):
    for index in range(5):
        for host in ("codex", "claude"):
            home = tmp_path / f"{host}-{index}"
            result = run_installer(home, "install", host)
            assert result.returncode == 0, result.stderr
            assert json.loads(result.stdout)["seconds"] < 300

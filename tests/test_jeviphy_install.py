import json
import subprocess
import sys
from pathlib import Path

import networkx as nx
from networkx.readwrite import json_graph


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


def test_installed_hosts_are_identical_and_contain_auto_module(tmp_path):
    assert run_installer(tmp_path, "install", "both").returncode == 0
    codex = tmp_path / ".codex/skills/jeviphy"
    claude = tmp_path / ".claude/skills/jeviphy"
    for relative in (
        "SKILL.md", "scripts/run.py", "scripts/tools/jeviphy_autorun.py",
        "scripts/tools/jev_memory_pilot.py", "scripts/tools/jev_memory_pilot_api.py",
    ):
        assert (codex / relative).read_bytes() == (claude / relative).read_bytes()


def test_installed_runner_keeps_nested_target_cwd(tmp_path):
    assert run_installer(tmp_path, "install", "both").returncode == 0
    repo = tmp_path / "target repo"
    nested = repo / "src" / "nested"
    nested.mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    (repo / "app.py").write_text("def run(): return 1\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
         "commit", "-qm", "fixture"], cwd=repo, check=True,
    )
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    graph = nx.Graph()
    graph.add_node("app.py::run", label="run", type="function", community=0,
                   source_file="app.py", source_location="L1")
    data = json_graph.node_link_data(graph, edges="links")
    data["built_at_commit"] = head
    graph_path = repo / "graphify-out/graph.json"
    graph_path.parent.mkdir()
    graph_path.write_text(json.dumps(data))
    for host in (".codex", ".claude"):
        runner = tmp_path / host / "skills/jeviphy/scripts/run.py"
        result = subprocess.run(
            ["uv", "run", "--no-sync", str(runner), "auto", "--question", "run"],
            cwd=nested, capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr
        assert "Question: run" in result.stdout


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

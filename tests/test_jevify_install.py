import json
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

import networkx as nx
import pytest
from networkx.readwrite import json_graph

from graphify.detect import save_manifest
from tools.jevify_autorun import PROVIDER_ENV_KEYS


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts/install_jevify_skill.py"


def run_installer(home: Path, action: str, host: str = "codex"):
    return subprocess.run(
        [sys.executable, str(INSTALLER), action, "--host", host, "--home", str(home)],
        capture_output=True,
        text=True,
    )


def test_install_and_uninstall_each_host(tmp_path):
    for host, relative in (
        ("codex", ".codex/skills/jevify"),
        ("claude", ".claude/skills/jevify"),
    ):
        home = tmp_path / host
        installed = run_installer(home, "install", host)
        assert installed.returncode == 0, installed.stderr
        destination = home / relative
        assert (destination / "SKILL.md").is_file()
        assert json.loads((destination / ".jevify-install-receipt.json").read_text())["files"]
        removed = run_installer(home, "uninstall", host)
        assert removed.returncode == 0, removed.stderr
        assert not destination.exists()


def test_both_hosts_and_repeated_install(tmp_path):
    assert run_installer(tmp_path, "install", "both").returncode == 0
    assert run_installer(tmp_path, "install", "both").returncode == 0
    assert (tmp_path / ".codex/skills/jevify/SKILL.md").is_file()
    assert (tmp_path / ".claude/skills/jevify/SKILL.md").is_file()


def test_install_migrates_owned_legacy_skill(tmp_path):
    legacy = tmp_path / ".codex/skills/jeviphy"
    legacy.mkdir(parents=True)
    legacy_skill = legacy / "SKILL.md"
    legacy_skill.write_text("legacy", encoding="utf-8")
    digest = hashlib.sha256(legacy_skill.read_bytes()).hexdigest()
    (legacy / ".jeviphy-install-receipt.json").write_text(
        json.dumps({"schema_version": 1, "files": {"SKILL.md": digest}}),
        encoding="utf-8",
    )

    result = run_installer(tmp_path, "install")

    assert result.returncode == 0, result.stderr
    assert not legacy.exists()
    assert (tmp_path / ".codex/skills/jevify/SKILL.md").is_file()


def test_install_refuses_unowned_legacy_skill(tmp_path):
    legacy = tmp_path / ".codex/skills/jeviphy"
    legacy.mkdir(parents=True)
    (legacy / "owned-by-user.txt").write_text("keep", encoding="utf-8")

    result = run_installer(tmp_path, "install")

    assert result.returncode != 0
    assert (legacy / "owned-by-user.txt").read_text() == "keep"
    assert not (tmp_path / ".codex/skills/jevify").exists()


def test_installed_hosts_are_identical_and_contain_auto_module(tmp_path):
    assert run_installer(tmp_path, "install", "both").returncode == 0
    codex = tmp_path / ".codex/skills/jevify"
    claude = tmp_path / ".claude/skills/jevify"
    for relative in (
        "SKILL.md", "scripts/run.py", "scripts/tools/jevify_autorun.py",
        "scripts/tools/jevify_graph_state.py", "scripts/tools/jevify_insights.py",
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
    save_manifest(
        {"code": [str(repo / "app.py")]},
        manifest_path=str(graph_path.parent / "manifest.json"),
        kind="both",
        root=repo,
    )
    (graph_path.parent / "GRAPH_REPORT.md").write_text(
        "## Summary\n- 1 nodes · 0 edges · 1 communities\n", encoding="utf-8",
    )
    (graph_path.parent / "graph.html").write_text("current", encoding="utf-8")
    for host in (".codex", ".claude"):
        runner = tmp_path / host / "skills/jevify/scripts/run.py"
        result = subprocess.run(
            ["uv", "run", "--no-sync", str(runner), "auto", "--question", "run"],
            cwd=nested, capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr
        assert "Question: run" in result.stdout


def test_installed_mixed_update_requires_host_without_mutating_graph(tmp_path):
    assert run_installer(tmp_path, "install", "both").returncode == 0
    repo = tmp_path / "target"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    (repo / "app.py").write_text("def run(): return 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
         "commit", "-qm", "fixture"], cwd=repo, check=True,
    )
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    graph = nx.Graph()
    graph.add_node("app.py::run", community=0, source_file="app.py")
    data = json_graph.node_link_data(graph, edges="links")
    data["built_at_commit"] = head
    graph_path = repo / "graphify-out" / "graph.json"
    graph_path.parent.mkdir()
    graph_path.write_text(json.dumps(data), encoding="utf-8")
    save_manifest(
        {"code": [str(repo / "app.py")]},
        manifest_path=str(graph_path.parent / "manifest.json"),
        kind="both",
        root=repo,
    )
    accepted = graph_path.read_bytes()
    (repo / "README.md").write_text("# Changed\n", encoding="utf-8")

    for host in (".codex", ".claude"):
        runner = tmp_path / host / "skills/jevify/scripts/run.py"
        result = subprocess.run(
            [sys.executable, str(runner), "update", "--repo", str(repo), "--json"],
            cwd=repo, capture_output=True, text=True,
        )
        assert result.returncode == 20, result.stderr
        payload = json.loads(result.stdout)
        assert payload["status"] == "requires_host"
        assert graph_path.read_bytes() == accepted
        backup = Path(payload["backup_path"])
        shutil.rmtree(backup.parent)


def test_install_preserves_preexisting_skill(tmp_path):
    destination = tmp_path / ".codex/skills/jevify"
    destination.mkdir(parents=True)
    marker = destination / "owned-by-user.txt"
    marker.write_text("keep", encoding="utf-8")
    result = run_installer(tmp_path, "install")
    assert result.returncode != 0
    assert marker.read_text() == "keep"


def test_uninstall_refuses_modified_owned_file(tmp_path):
    assert run_installer(tmp_path, "install").returncode == 0
    skill = tmp_path / ".codex/skills/jevify/SKILL.md"
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


@pytest.mark.parametrize("host,relative", [
    ("codex", ".codex/skills/jevify"),
    ("claude", ".claude/skills/jevify"),
])
def test_clean_home_code_update_lifecycle(tmp_path, host, relative):
    home = tmp_path / host
    assert run_installer(home, "install", host).returncode == 0
    repo = tmp_path / f"repo-{host}"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    source = repo / "app.py"
    source.write_text("def run(): return 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
         "commit", "-qm", "fixture"], cwd=repo, check=True,
    )
    initial = subprocess.run(
        [sys.executable, "-m", "graphify", "update", ".", "--force"],
        cwd=repo, capture_output=True, text=True,
        env={**os.environ, "GRAPHIFY_BACKEND": "none"},
    )
    assert initial.returncode == 0, initial.stderr
    runner = home / relative / "scripts/run.py"
    source.write_text("def run(): return 2\n", encoding="utf-8")

    stale = subprocess.run(
        [sys.executable, str(runner), "doctor", "--repo", str(repo)],
        cwd=repo, capture_output=True, text=True,
    )
    assert stale.returncode == 1
    assert json.loads(stale.stdout)["checks"]["graph_current"] is False

    parent_env = os.environ.copy()
    for key in PROVIDER_ENV_KEYS:
        parent_env[key] = "must-not-reach-child"
    updated = subprocess.run(
        [sys.executable, str(runner), "update", "--repo", str(repo), "--json"],
        cwd=repo, capture_output=True, text=True, env=parent_env,
    )
    assert updated.returncode == 0, updated.stderr
    assert json.loads(updated.stdout)["status"] == "updated"

    current = subprocess.run(
        [sys.executable, str(runner), "doctor", "--repo", str(repo)],
        cwd=repo, capture_output=True, text=True,
    )
    assert current.returncode == 0, current.stderr
    assert json.loads(current.stdout)["checks"]["graph_current"] is True
    assert run_installer(home, "install", host).returncode == 0
    assert run_installer(home, "uninstall", host).returncode == 0
    assert not (home / relative).exists()

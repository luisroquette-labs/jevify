"""The installed skill entry point must work outside this checkout's cwd."""

import re
import json
import shutil
import subprocess
import sys
from pathlib import Path

import networkx as nx
from networkx.readwrite import json_graph


def test_bare_invocation_is_autonomous_and_corpus_optional() -> None:
    root = Path(__file__).resolve().parents[1]
    skill = (root / "skills" / "jeviphy" / "SKILL.md").read_text(encoding="utf-8")

    assert "Use the current working directory as the target repository" in skill
    assert "Do not ask the user to choose a question first" in skill
    assert "A corpus is optional for a bare invocation" in skill
    assert "Otherwise continue with the graph-only baseline" in skill
    assert "approval persists for the current conversation" in skill
    assert "without asking again or offering offline/live choices" in skill
    assert "accept the runner's baseline fallback" in skill
    assert "Do not stop the invocation to request a new key" in skill


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
    assert "--question" in result.stdout
    assert "--json" in result.stdout

    legacy = subprocess.run(
        [sys.executable, str(script), "query", "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "--dry-run" in legacy.stdout


def test_portable_skill_code_matches_project_code() -> None:
    root = Path(__file__).resolve().parents[1]
    for name in ("jev_memory_pilot.py", "jev_memory_pilot_api.py", "jeviphy_autorun.py"):
        source = (root / "tools" / name).read_bytes()
        assert source == (root / "skills" / "jeviphy" / "scripts" / "tools" / name).read_bytes()


def test_pinned_commit_matches_portable_core() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "skills" / "jeviphy" / "scripts" / "run.py"
    pinned = re.search(r"graphifyy @ git\+https://[^\s\"]+@([0-9a-f]{40})", script.read_text())
    assert pinned is not None
    for name in ("jev_memory_pilot.py", "jev_memory_pilot_api.py"):
        source = (root / "tools" / name).read_bytes()
        committed = subprocess.run(
            ["git", "show", f"{pinned.group(1)}:tools/{name}"],
            cwd=root, check=True, capture_output=True,
        ).stdout
        assert source == committed


def test_portable_doctor_reports_current_private_inputs(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    (repo / "app.py").write_text("value = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
         "commit", "-qm", "fixture"],
        cwd=repo,
        check=True,
    )
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    graph = nx.Graph()
    graph.add_node("app", source_file="app.py")
    data = json_graph.node_link_data(graph, edges="links")
    data["built_at_commit"] = head
    graph_path = repo / "graph.json"
    graph_path.write_text(json.dumps(data), encoding="utf-8")
    corpus = tmp_path / "corpus.json"
    corpus.write_text("{}", encoding="utf-8")
    corpus.chmod(0o600)
    result = subprocess.run(
        [sys.executable, str(root / "skills/jeviphy/scripts/run.py"), "doctor",
         "--repo", str(repo), "--graph", str(graph_path), "--corpus", str(corpus)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(result.stdout)["ok"] is True

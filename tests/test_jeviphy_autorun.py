import json
import os
import subprocess
import sys
from pathlib import Path

import networkx as nx
import pytest
from networkx.readwrite import json_graph

from tools import jeviphy_autorun as autorun
from tools.jeviphy_autorun import ContextError, ensure_context, inspect_context


def _commit(repo: Path) -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()


def _write_graph(path: Path, commit: object) -> None:
    graph = nx.Graph()
    graph.add_node("app.py::run", label="run", type="function", community=0,
                   source_file="app.py", source_location="L1")
    data = json_graph.node_link_data(graph, edges="links")
    if commit is not ...:
        data["built_at_commit"] = commit
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


@pytest.fixture
def repo_with_graph(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo with spaces"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    (repo / "app.py").write_text("def run(): return 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "-c", "user.name=Test", "-c",
                    "user.email=test@example.invalid", "commit", "-qm", "fixture"],
                   cwd=repo, check=True)
    graph = repo / "graphify-out" / "graph.json"
    _write_graph(graph, _commit(repo))
    return repo, graph


def test_ensure_context_uses_containing_git_root(repo_with_graph):
    repo, graph = repo_with_graph
    nested = repo / "src" / "nested"
    nested.mkdir(parents=True)
    context = ensure_context(nested)
    assert context.repo == repo.resolve()
    assert context.graph == graph.resolve()


def test_ensure_context_rejects_outside_git(tmp_path):
    with pytest.raises(ContextError, match="not inside a Git worktree"):
        ensure_context(tmp_path)


def test_explicit_repository_and_graph_are_resolved(repo_with_graph, tmp_path):
    repo, graph = repo_with_graph
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    assert ensure_context(elsewhere, repo=repo).graph == graph.resolve()
    assert ensure_context(elsewhere, repo=repo, graph=graph).repo == repo.resolve()


def test_persisted_commit_is_normalized_and_accepted(repo_with_graph):
    repo, _ = repo_with_graph
    state = inspect_context(repo)
    assert state.status == "ready"
    assert state.loaded_graph.graph["_built_at_commit"] == state.context.head


@pytest.mark.parametrize("value", [..., None, "", 42])
def test_missing_or_malformed_persisted_commit_is_stale(repo_with_graph, value):
    repo, graph = repo_with_graph
    _write_graph(graph, value)
    assert inspect_context(repo).status == "stale"


@pytest.mark.parametrize(
    ("initial", "expected"),
    [("missing", ["extract", ".", "--code-only"]),
     ("corrupt", ["extract", ".", "--force", "--code-only"]),
     ("stale", ["update", "."])],
)
def test_repair_runs_once_without_provider_credentials(
    repo_with_graph, monkeypatch, initial, expected,
):
    repo, graph = repo_with_graph
    if initial == "missing":
        graph.unlink()
    elif initial == "corrupt":
        graph.write_text("{", encoding="utf-8")
    else:
        _write_graph(graph, "0" * 40)
    calls = []

    def fake_run(command, repo_arg, env):
        calls.append((command, repo_arg, env))
        _write_graph(graph, _commit(repo))
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(autorun, "_run_repair", fake_run)
    for key in autorun.PROVIDER_ENV_KEYS:
        monkeypatch.setenv(key, "secret-sentinel")
    context = ensure_context(repo)
    assert context.head == _commit(repo)
    assert len(calls) == 1
    command, repo_arg, env = calls[0]
    assert command == [sys.executable, "-m", "graphify", *expected]
    assert repo_arg == repo.resolve()
    assert env["GRAPHIFY_NO_AUTO_REFRESH"] == "1"
    assert env["PYTHONHASHSEED"] == "0"
    assert not (set(autorun.PROVIDER_ENV_KEYS) & set(env))


def test_failed_repair_does_not_retry(repo_with_graph, monkeypatch):
    repo, graph = repo_with_graph
    graph.unlink()
    calls = []

    def fail(command, repo_arg, env):
        calls.append(command)
        return subprocess.CompletedProcess(command, 1, "", "bounded failure")

    monkeypatch.setattr(autorun, "_run_repair", fail)
    with pytest.raises(ContextError, match="graph repair failed.*bounded failure"):
        ensure_context(repo)
    assert len(calls) == 1


def test_invalid_repaired_graph_is_rejected_without_retry(repo_with_graph, monkeypatch):
    repo, graph = repo_with_graph
    graph.unlink()
    calls = []

    def no_output(command, repo_arg, env):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(autorun, "_run_repair", no_output)
    with pytest.raises(ContextError, match="repair produced invalid graph"):
        ensure_context(repo)
    assert len(calls) == 1

import subprocess
from pathlib import Path

import networkx as nx

from tools.jeviphy_provenance import classify_source_evidence


def commit(repo: Path, message: str) -> str:
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        [
            "git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
            "commit", "-qm", message,
        ],
        cwd=repo,
        check=True,
    )
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()


def provenance_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    (repo / "stable.py").write_text("stable = 1\n", encoding="utf-8")
    (repo / "changed.py").write_text("changed = 1\n", encoding="utf-8")
    first = commit(repo, "first")
    (repo / "changed.py").write_text("changed = 2\n", encoding="utf-8")
    second = commit(repo, "second")
    graph = nx.Graph()
    graph.add_node("stable", source_file="stable.py")
    graph.add_node("changed", source_file="changed.py")
    return repo, first, second, graph


def test_changed_path_is_rejected(tmp_path):
    repo, first, _, graph = provenance_repo(tmp_path)
    evidence = classify_source_evidence(repo, graph, first, ["changed.py"])
    assert evidence.usable_paths == ()
    assert evidence.rejected_paths == ("changed.py",)
    assert evidence.reason == "no_fresh_graph_paths"


def test_mixed_paths_keep_only_fresh_graph_paths(tmp_path):
    repo, first, _, graph = provenance_repo(tmp_path)
    evidence = classify_source_evidence(repo, graph, first, ["stable.py", "changed.py"])
    assert evidence.usable_paths == ("stable.py",)
    assert evidence.rejected_paths == ("changed.py",)


def test_missing_deleted_untracked_and_traversal_are_rejected(tmp_path):
    repo, _, second, graph = provenance_repo(tmp_path)
    (repo / "untracked.py").write_text("x = 1\n", encoding="utf-8")
    evidence = classify_source_evidence(
        repo, graph, second, ["missing.py", "untracked.py", "../secret.py"]
    )
    assert evidence.usable_paths == ()
    assert evidence.rejected_paths == ("missing.py", "untracked.py", "../secret.py")


def test_graph_absent_and_missing_commit_are_rejected(tmp_path):
    repo, _, second, graph = provenance_repo(tmp_path)
    evidence = classify_source_evidence(repo, graph, second, ["stable.py", "not-in-graph.py"])
    assert evidence.usable_paths == ("stable.py",)
    assert evidence.rejected_paths == ("not-in-graph.py",)
    missing_commit = classify_source_evidence(repo, graph, None, ["stable.py"])
    assert missing_commit.reason == "source_commit_missing"
    assert missing_commit.usable_paths == ()


def test_non_ancestor_commit_is_rejected(tmp_path):
    repo, _, _, graph = provenance_repo(tmp_path)
    evidence = classify_source_evidence(repo, graph, "f" * 40, ["stable.py"])
    assert evidence.reason == "source_commit_not_ancestor"
    assert evidence.usable_paths == ()

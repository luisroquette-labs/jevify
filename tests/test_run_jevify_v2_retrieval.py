from pathlib import Path

import pytest

import json

from tools.run_jevify_v2_retrieval import (
    ensure_graph_commit,
    prepare_workspace,
    reset_graph_outputs,
    safe_name,
)


def test_safe_name_is_directory_local():
    assert safe_name("owner/repo") == "owner__repo"
    assert "/" not in safe_name("owner/repo")


def test_workspace_requires_matching_marker(tmp_path: Path):
    workspace = tmp_path / "workspace"
    prepare_workspace(workspace)
    assert (workspace / ".jevify-v2-workspace").read_text() == "jevify-v2\n"
    (workspace / ".jevify-v2-workspace").write_text("other\n")
    with pytest.raises(ValueError, match="marker differs"):
        prepare_workspace(workspace)


def test_graph_commit_is_filled_only_when_missing(tmp_path: Path):
    graph = tmp_path / "graph.json"
    graph.write_text(json.dumps({"nodes": [], "links": []}))
    ensure_graph_commit(graph, "a" * 40)
    assert json.loads(graph.read_text())["built_at_commit"] == "a" * 40
    with pytest.raises(ValueError, match="different"):
        ensure_graph_commit(graph, "b" * 40)


def test_reset_preserves_only_extraction_cache(tmp_path: Path):
    graph_dir = tmp_path / "graphify-out"
    cache = graph_dir / "cache"
    cache.mkdir(parents=True)
    (cache / "entry").write_text("keep")
    (graph_dir / "graph.json").write_text("remove")
    (graph_dir / "nested").mkdir()
    (graph_dir / "nested/file").write_text("remove")
    reset_graph_outputs(graph_dir)
    assert (cache / "entry").read_text() == "keep"
    assert sorted(path.name for path in graph_dir.iterdir()) == ["cache"]

"""The stress runner fails closed on provenance and reports paired arithmetic."""

import hashlib
import json
import subprocess
import sys
from types import SimpleNamespace

import networkx as nx
import pytest

from tools.jevify_full_stress import answer_hits
from tools.jevify_stress import main, peak_rss_bytes, percentile, summarize


def test_answer_hits_requires_label_and_exact_source():
    graph = nx.Graph()
    graph.add_node("n", label="render()", source_file="src/right.ts")
    assert answer_hits("NODE render() [src=src/wrong.ts loc=L1]", ["n"], graph) == 0
    assert answer_hits("NODE render() [src=src/right.ts loc=L1]", ["n"], graph) == 1


def test_peak_rss_normalizes_linux_kib_and_macos_bytes(monkeypatch):
    monkeypatch.setattr("tools.jevify_stress.resource.getrusage",
                        lambda _who: SimpleNamespace(ru_maxrss=123))
    monkeypatch.setattr("tools.jevify_stress.platform.system", lambda: "Linux")
    assert peak_rss_bytes() == 123 * 1024
    monkeypatch.setattr("tools.jevify_stress.platform.system", lambda: "Darwin")
    assert peak_rss_bytes() == 123


def test_percentiles_and_paired_summary():
    assert percentile([1, 2, 3, 4, 5], .95) == pytest.approx(4.8)
    rows = [
        {"baseline_ms": 10, "assisted_ms": 20, "same_top_five": i != 0,
         "baseline_top_five_prefix_preserved": True,
         "source_backed": i < 20, "baseline_file_hit": i == 0,
         "assisted_file_hit": i in (0, 1)}
        for i in range(30)
    ] * 3
    result = summarize(rows)
    assert result["paired_runs"] == 90
    assert result["identical_top_five"] == 87
    assert result["baseline_top_five_prefix_preserved"] == 90
    assert result["baseline_file_hit_top_ten"] == 1
    assert result["assisted_file_hit_top_ten"] == 2
    assert result["file_hit_gains"] == 1
    assert result["median_paired_ratio"] == 2


def test_runner_rejects_wrong_graph_and_keeps_raw_data_private(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / "source.py").write_text("def found(): pass\n")
    subprocess.run(["git", "add", "source.py"], cwd=repo, check=True)
    subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                    "commit", "-qm", "fixture"], cwd=repo, check=True)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    graph = tmp_path / "graph.json"
    graph.write_text('{"built_at_commit":"' + commit + '"}')
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    manifest = private / "manifest.json"
    case = {"id": "", "question": "found", "summary": "found", "source_paths": ["source.py"],
            "source_backed": True}
    manifest.write_text(json.dumps({"source_commit": commit,
                                    "graph_sha256": hashlib.sha256(graph.read_bytes()).hexdigest(),
                                    "cases": [dict(case, id=str(i)) for i in range(30)]}))
    manifest.chmod(0o600)
    output = private / "results.json"
    monkeypatch.setattr(sys, "argv", ["stress", "--manifest", str(manifest), "--graph", str(graph),
                                  "--repo", str(repo), "--output", str(output)])
    graph.write_text("changed")
    with pytest.raises(SystemExit, match="2"):
        main()
    assert not output.exists()

    graph.write_text('{"built_at_commit":"' + commit + '"}')
    monkeypatch.setattr("tools.jevify_stress.candidate_pool", lambda *args, **kwargs: [
        {"node_id": "n", "source_file": "source.py"}])
    main()
    result = json.loads(output.read_text())
    assert result["summary"]["paired_runs"] == 90
    assert result["summary"]["identical_top_five"] == 90
    assert result["summary"]["baseline_top_five_prefix_preserved"] == 90
    assert output.stat().st_mode & 0o077 == 0

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import networkx as nx
import pytest
from networkx.readwrite import json_graph

from tools.jeviphy_eval_contract import EvalCase, MemoryEvidence
from tools.jeviphy_product_eval import (
    ArmRecord,
    PairRecord,
    RunPins,
    append_pair,
    balanced_order,
    completed_pairs,
    run_command_arm,
    run_retrieval_pair,
    seal_journal,
    validate_live_limits,
)
import tools.jeviphy_product_eval as product_eval


def arm(name="graphify", status="completed", success=True):
    return ArmRecord(name, status, success, 1.0, "a" * 64, "b" * 64)


def pair(case_id="case-1"):
    return PairRecord(
        case_id, "valid_source", 0, ("graphify", "jeviphy"), "c" * 64, arm(), arm("jeviphy")
    )


def pins(command="a"):
    return RunPins("1" * 64, "2" * 40, "3" * 40, "3.13.0", command * 64)


def test_balanced_order_alternates_by_case_and_pass():
    assert balanced_order(0, 0) == ("graphify", "jeviphy")
    assert balanced_order(1, 0) == ("jeviphy", "graphify")
    assert balanced_order(0, 1) == ("jeviphy", "graphify")


def test_command_timeout_and_failure_remain_records(tmp_path):
    timeout = run_command_arm(
        "graphify", [sys.executable, "-c", "import time; time.sleep(1)"], tmp_path, 0.01
    )
    failed = run_command_arm("jeviphy", [sys.executable, "-c", "raise SystemExit(7)"], tmp_path, 2)
    assert (timeout.status, timeout.success) == ("timeout", False)
    assert (failed.status, failed.success) == ("failed", False)


def test_resume_rejects_changed_pins_and_duplicate_pair(tmp_path):
    journal = tmp_path / "run.jsonl"
    append_pair(journal, pins(), pair())
    assert completed_pairs(journal, pins()) == {("case-1", 0)}
    with pytest.raises(ValueError, match="pins differ"):
        completed_pairs(journal, pins("b"))
    append_pair(journal, pins(), pair())
    with pytest.raises(ValueError, match="duplicate"):
        completed_pairs(journal, pins())


def test_seal_requires_every_pair_and_refuses_overwrite(tmp_path):
    journal = tmp_path / "run.jsonl"
    output = tmp_path / "sealed.json"
    append_pair(journal, pins(), pair())
    with pytest.raises(ValueError, match="every expected"):
        seal_journal(journal, output, pins(), {("case-1", 0), ("case-2", 0)})
    seal_journal(journal, output, pins(), {("case-1", 0)})
    assert json.loads(output.read_text())["journal_sha256"]
    with pytest.raises(FileExistsError):
        seal_journal(journal, output, pins(), {("case-1", 0)})


def test_live_limits_fail_closed():
    validate_live_limits(allow_network_agent=False, max_agent_calls=0, max_cost_usd=0)
    with pytest.raises(ValueError, match="positive"):
        validate_live_limits(allow_network_agent=True, max_agent_calls=0, max_cost_usd=1)
    with pytest.raises(ValueError, match="require"):
        validate_live_limits(allow_network_agent=False, max_agent_calls=1, max_cost_usd=1)


def retrieval_fixture(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    (repo / "a.py").write_text("def alpha(): pass\n")
    (repo / "b.py").write_text("def beta(): pass\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "fixture"],
        cwd=repo,
        check=True,
    )
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    graph = nx.Graph()
    graph.add_node("a.py::alpha", label="alpha", type="function", source_file="a.py")
    graph.add_node("b.py::beta", label="beta", type="function", source_file="b.py")
    data = json_graph.node_link_data(graph, edges="links")
    data["built_at_commit"] = head
    graph_path = repo / "graph.json"
    graph_path.write_text(json.dumps(data))
    case = EvalCase(
        id="case-1",
        repo_id="example/repo",
        base_commit=head,
        stratum="valid_source",
        question="Which implementation handles the second behavior?",
        timeout_seconds=30,
        image="swebench/example:latest",
        fail_to_pass=("test",),
        pass_to_pass=(),
        gold_files=("b.py",),
        gold_symbols=(),
        memory=MemoryEvidence("Prior review cites this path.", ("b.py",), head, "2026-10-19"),
        holdout=False,
    )
    return repo, graph_path, case


def test_no_source_control_is_byte_identical_and_graph_is_immutable(tmp_path):
    repo, graph_path, case = retrieval_fixture(tmp_path)
    control = replace(
        case,
        stratum="no_source",
        memory=MemoryEvidence("", (), None, None),
    )
    before = graph_path.read_bytes()
    record, outputs = run_retrieval_pair(
        control, graph_path, repo, pass_index=0, order=("graphify", "jeviphy")
    )
    assert outputs["graphify"] == outputs["jeviphy"]
    assert record.baseline.output_sha256 == record.jeviphy.output_sha256
    assert graph_path.read_bytes() == before


def test_valid_source_scopes_without_running_unscoped_query_first(tmp_path, monkeypatch):
    repo, graph_path, case = retrieval_fixture(tmp_path)
    original = product_eval.candidate_pool
    calls = []

    def counted(*args, **kwargs):
        calls.append(kwargs.get("fast_source", False))
        return original(*args, **kwargs)

    monkeypatch.setattr(product_eval, "candidate_pool", counted)
    _, outputs = run_retrieval_pair(
        case, graph_path, repo, pass_index=0, order=("jeviphy", "graphify")
    )
    assert [row["source_file"] for row in outputs["jeviphy"]] == ["b.py"]
    assert calls == [True, False]


def test_stale_source_falls_back_exactly(tmp_path):
    repo, graph_path, case = retrieval_fixture(tmp_path)
    stale = replace(
        case,
        stratum="stale_source",
        memory=MemoryEvidence("Prior review cites this path.", ("missing.py",), case.base_commit, "2026-10-19"),
    )
    _, stale_outputs = run_retrieval_pair(
        stale, graph_path, repo, pass_index=0, order=("graphify", "jeviphy")
    )
    assert stale_outputs["graphify"] == stale_outputs["jeviphy"]

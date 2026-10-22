"""Money and retry boundary for the exploratory Jev cohort."""

import json

import pytest

from tools import jevify_paid_stress as paid


def _fixture(tmp_path, monkeypatch):
    inventory = tmp_path / "inventory.json"
    journal = tmp_path / "journal.json"
    record = {"id": "case-01", "candidate_ids": ["node-a"], "gold_node_ids": ["node-a"]}
    payload = {
        "model": paid.MODEL,
        "state": {"nodes": [{"id": "node-a"}],
                  "observations": [{"id": "obs-a"}],
                  "pairs": [{"key": "p000", "node_id": "node-a", "observation_id": "obs-a"}]},
        "questions": {"p000": {"type": "choice"}},
    }
    monkeypatch.setattr(paid, "load_inventory", lambda _: [(record, payload, {"p000": ("node-a", "obs-a")})])
    return inventory, journal


def test_paid_runner_records_cost_and_never_repeats_completed_call(tmp_path, monkeypatch):
    inventory, journal = _fixture(tmp_path, monkeypatch)
    calls = []

    def answer(payload, api_key):
        calls.append(payload)
        return {"model": paid.MODEL + "-20261014", "usage": {"cost": .0001},
                "answers": {"p000": {"type": "choice", "choice": "relevant",
                                      "probabilities": {"relevant": .95,
                                                        "unrelated": .04,
                                                        "insufficient_evidence": .01}}}}

    monkeypatch.setattr(paid, "call_jev", answer)
    summary = paid.run_inventory(inventory, journal, "sk-or-test-project", 1)
    assert summary["requests"] == summary["completed"] == 1
    assert summary["jev_top5_hits"] == summary["baseline_top5_hits"] == 1
    assert summary["actual_cost_usd"] == .0001
    assert len(calls) == 1
    paid.run_inventory(inventory, journal, "sk-or-test-project", 1)
    assert len(calls) == 1


def test_paid_runner_stops_after_uncertain_response_without_retry(tmp_path, monkeypatch):
    inventory, journal = _fixture(tmp_path, monkeypatch)
    calls = []
    monkeypatch.setattr(paid, "call_jev", lambda payload, key: calls.append(1) or {"answers": {}})
    with pytest.raises(RuntimeError, match="no retry"):
        paid.run_inventory(inventory, journal, "sk-or-test-project", 1)
    assert json.loads(journal.read_text())["attempts"][0]["status"] == "failed_or_uncertain"
    with pytest.raises(ValueError, match="do not retry"):
        paid.run_inventory(inventory, journal, "sk-or-test-project", 1)
    assert calls == [1]


def test_paid_runner_requires_dedicated_key_and_bounded_calls(tmp_path, monkeypatch):
    inventory, journal = _fixture(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="dedicated OpenRouter key"):
        paid.run_inventory(inventory, journal, "other-provider-key", 1)
    with pytest.raises(ValueError, match="request cap"):
        paid.run_inventory(inventory, journal, "sk-or-test-project", 21)
    assert not journal.exists()


def test_paid_runner_does_not_pay_for_a_pool_without_excerpts(tmp_path, monkeypatch):
    inventory, journal = _fixture(tmp_path, monkeypatch)
    record = {"id": "case-empty", "candidate_ids": [], "gold_node_ids": ["node-a"]}
    payload = {"state": {"nodes": [], "observations": [{"id": "obs-a"}], "pairs": []}}
    monkeypatch.setattr(paid, "load_inventory", lambda _: [(record, payload, {})])
    monkeypatch.setattr(paid, "call_jev", lambda *_: pytest.fail("empty pool was sent"))
    summary = paid.run_inventory(inventory, journal, "sk-or-test-project", 1)
    assert summary["requests"] == summary["completed"] == 0
    assert summary["skipped_no_excerpt"] == 1

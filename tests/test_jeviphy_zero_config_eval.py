import copy
import json
from pathlib import Path

import pytest

from tools.jeviphy_zero_config_eval import score, validate_manifest


MANIFEST = Path(__file__).resolve().parents[1] / "benchmarks/jeviphy-zero-config/manifest.json"
PUBLIC_SCORE = Path(__file__).resolve().parents[1] / "benchmarks/jeviphy-zero-config/results/score.json"


def test_public_score_is_a_complete_passing_aggregate():
    payload = json.loads(PUBLIC_SCORE.read_text(encoding="utf-8"))
    assert payload["status"] == "pass"
    assert payload["attempts"] == payload["successes"] == 30
    assert payload["exact_matches"] == payload["exact_outputs"] == 24
    assert payload["interaction_required"] == 0
    assert payload["failed_cases"] == []
    assert payload["median_overhead_fraction"] <= 0.10
    assert payload["p95_overhead_fraction"] <= 0.15


def _manifest():
    return json.loads(MANIFEST.read_text())


def _passing_records(manifest):
    records = []
    for case in manifest["cases"]:
        records.append({
            "case_id": case["id"],
            "outcome": case["expected"],
            "interaction_required": False,
            "exact_match": True if case["exact_output"] else None,
            "pairs": ([{"direct_ms": 100, "jeviphy_ms": 105}] * 5 if case["timing"] else []),
        })
    return records


def test_manifest_is_frozen_at_30_cases_and_six_public_repositories():
    manifest = _manifest()
    validate_manifest(manifest)
    assert len(manifest["cases"]) == 30
    assert len(manifest["repos"]) == 6
    assert all(item["origin"].startswith("https://github.com/") for item in manifest["repos"])
    assert all(len(item["commit"]) == 40 and len(item["graph_sha256"]) == 64
               for item in manifest["repos"])


def test_score_requires_complete_exact_noninteractive_pairs():
    manifest = _manifest()
    records = _passing_records(manifest)
    result = score(records, manifest)
    assert result.status == "pass"
    assert result.interaction_required == 0
    assert result.exact_matches == result.exact_outputs
    assert result.measured_pairs == 90

    for field, value in (("interaction_required", True), ("exact_match", False)):
        broken = copy.deepcopy(records)
        broken[0][field] = value
        assert score(broken, manifest).status == "fail"


def test_score_rejects_missing_pair_and_latency_regression():
    manifest = _manifest()
    records = _passing_records(manifest)
    assert score(records[:-1], manifest).status == "insufficient_evidence"
    slow = copy.deepcopy(records)
    for record in slow:
        for pair in record["pairs"]:
            pair["jeviphy_ms"] = 116
    assert score(slow, manifest).status == "fail"


def test_score_uses_matched_pair_overheads_across_different_repository_speeds():
    manifest = _manifest()
    records = _passing_records(manifest)
    timing_records = [record for record in records if record["pairs"]]
    for index, record in enumerate(timing_records):
        direct = 100 if index < len(timing_records) // 2 else 1_000
        record["pairs"] = [{"direct_ms": direct, "jeviphy_ms": direct * 1.05}] * 5

    result = score(records, manifest)

    assert result.status == "pass"
    assert result.median_overhead_fraction == pytest.approx(0.05)
    assert result.p95_overhead_fraction == pytest.approx(0.05)


def test_manifest_rejects_changed_denominators():
    manifest = _manifest()
    with pytest.raises(ValueError, match="30 cases"):
        validate_manifest({**manifest, "cases": manifest["cases"][:-1]})
    with pytest.raises(ValueError, match="six repositories"):
        validate_manifest({**manifest, "repos": manifest["repos"][:5]})

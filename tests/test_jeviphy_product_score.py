from copy import deepcopy
import json

import pytest

from tools.jeviphy_product_score import (
    BETA_READY,
    INTERNAL_PRODUCT_WIN,
    NO_DIFFERENCE,
    REPRODUCED_PRODUCT_WIN,
    RETRIEVAL_ONLY,
    allowed_claim,
    write_scorecard,
    score_run,
)


def arm(*, success, duration, hits, first, digest, tokens=100):
    return {
        "status": "completed",
        "success": success,
        "duration_ms": duration,
        "output_sha256": digest,
        "input_tokens": tokens,
        "top5_hits": hits,
        "first_hit": first,
    }


def retrieval_records():
    records = []
    strata = ["valid_source"] * 40 + ["stale_source"] * 20 + ["no_source"] * 40
    for index, stratum in enumerate(strata):
        baseline = arm(success=True, duration=100, hits=0, first=False, digest=f"b{index}")
        jeviphy = arm(
            success=True,
            duration=70,
            hits=2 if stratum == "valid_source" else 0,
            first=stratum == "valid_source",
            digest=f"b{index}" if stratum == "no_source" else f"j{index}",
        )
        records.append(
            {"pair": {"case_id": f"r{index}", "stratum": stratum, "pass_index": 0,
                      "baseline": baseline, "jeviphy": jeviphy}}
        )
    return records


def product_records(*, wins=20):
    records = []
    for index in range(120):
        control = index < 40
        advantage = 40 <= index < 40 + wins
        baseline_success = not advantage
        jeviphy_success = True
        records.append(
            {"pair": {
                "case_id": f"p{index}",
                "stratum": "no_source" if control else "valid_source",
                "pass_index": 0,
                "baseline": arm(success=baseline_success, duration=100, hits=0, first=False,
                                digest=f"p{index}", tokens=100),
                "jeviphy": arm(success=jeviphy_success, duration=75, hits=0, first=False,
                               digest=f"q{index}", tokens=80),
            }}
        )
    return records


def complete_report():
    return {
        "retrieval_records": retrieval_records(),
        "product_records": product_records(),
        "usability": {
            "attempts": 20,
            "successes": 20,
            "median_seconds": 120,
            "operating_systems": ["macOS 15", "Ubuntu 24.04"],
        },
        "compatibility": True,
        "reproductions": [
            {"independent": True, "os": "macOS"},
            {"independent": True, "os": "Ubuntu 24.04"},
        ],
    }


def test_complete_evidence_allows_reproduced_claim():
    scorecard = score_run(complete_report())
    assert scorecard.retrieval.status == "pass"
    assert scorecard.product.status == "pass"
    assert allowed_claim(scorecard) == REPRODUCED_PRODUCT_WIN


def test_retrieval_win_cannot_be_called_product_superiority():
    report = complete_report()
    report["product_records"] = []
    scorecard = score_run(report)
    assert scorecard.retrieval.status == "pass"
    assert scorecard.product.status == "insufficient_evidence"
    assert allowed_claim(scorecard) == BETA_READY


def test_external_reproduction_is_required_for_public_product_claim():
    report = complete_report()
    report["reproductions"] = []
    assert allowed_claim(score_run(report)) == INTERNAL_PRODUCT_WIN


def test_confidence_interval_crossing_zero_blocks_claim():
    report = complete_report()
    report["product_records"] = product_records(wins=30)
    for wrapper in report["product_records"][70:88]:
        wrapper["pair"]["baseline"]["success"] = True
        wrapper["pair"]["jeviphy"]["success"] = False
    scorecard = score_run(report)
    assert scorecard.product.metrics["success_difference_pp"] >= 10
    assert scorecard.product.metrics["success_difference_ci95_pp"][0] <= 0
    assert scorecard.product.status == "fail"


def test_control_regression_and_stale_loss_fail_closed():
    report = complete_report()
    for wrapper in report["product_records"][:3]:
        wrapper["pair"]["baseline"]["success"] = True
        wrapper["pair"]["jeviphy"]["success"] = False
    scorecard = score_run(report)
    assert scorecard.product.metrics["control_difference_pp"] < -2
    assert scorecard.product.status == "fail"

    stale = deepcopy(complete_report())
    stale_pair = next(
        wrapper["pair"] for wrapper in stale["retrieval_records"]
        if wrapper["pair"]["stratum"] == "stale_source"
    )
    stale_pair["baseline"]["top5_hits"] = 1
    assert score_run(stale).retrieval.status == "fail"


def test_missing_evidence_emits_no_difference():
    scorecard = score_run({})
    assert allowed_claim(scorecard) == NO_DIFFERENCE


def test_product_pairs_fail_closed_on_duplicates_or_contradictions():
    report = complete_report()
    report["product_records"].append(deepcopy(report["product_records"][0]))
    with pytest.raises(ValueError, match="duplicate pair"):
        score_run(report)

    report = complete_report()
    report["product_records"][0]["pair"]["baseline"]["success"] = "yes"
    with pytest.raises(ValueError, match="boolean success"):
        score_run(report)


def test_incomplete_product_evidence_is_insufficient():
    report = complete_report()
    report["product_records"].pop()
    assert score_run(report).product.status == "insufficient_evidence"


def test_usability_requires_macos_and_ubuntu():
    report = complete_report()
    report["usability"]["operating_systems"] = ["macOS 15"]
    assert score_run(report).usability.status == "fail"


def test_scorecard_writer_emits_machine_and_human_results(tmp_path):
    report = tmp_path / "report.json"
    output = tmp_path / "scorecard.json"
    markdown = tmp_path / "scorecard.md"
    report.write_text(json.dumps({"retrieval_records": retrieval_records()}), encoding="utf-8")

    write_scorecard(report, output, markdown)

    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["allowed_claim"] == RETRIEVAL_ONLY
    assert result["gates"]["retrieval"]["status"] == "pass"
    assert RETRIEVAL_ONLY in markdown.read_text(encoding="utf-8")

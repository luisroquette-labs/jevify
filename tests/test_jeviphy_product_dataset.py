import json

import pytest

from tools.jeviphy_product_dataset import validate_arm_case, validate_arm_datasets


def _case(instance_id="case-1"):
    return {
        "instance_id": instance_id,
        "problem_statement": "Fix the router.",
        "repo": "example/repo",
        "base_commit": "a" * 40,
        "patch": "gold patch",
        "test_patch": "gold tests",
    }


def test_arm_case_allows_only_bounded_problem_context():
    baseline = _case()
    candidate = {**baseline, "problem_statement": "Fix the router.\nReviewed source: src/router.py"}
    validate_arm_case(baseline, candidate, gold_symbols=())

    candidate["test_patch"] = "changed"
    with pytest.raises(ValueError, match="test_patch differs"):
        validate_arm_case(baseline, candidate, gold_symbols=())


@pytest.mark.parametrize("suffix", ["patch: hidden", "test_patch: hidden", "secretSymbol"])
def test_arm_case_rejects_gold_leakage(suffix):
    baseline = _case()
    candidate = {**baseline, "problem_statement": baseline["problem_statement"] + "\n" + suffix}
    with pytest.raises(ValueError, match="leak"):
        validate_arm_case(baseline, candidate, gold_symbols=("secretSymbol",))


def test_arm_datasets_require_expected_set_and_return_hashes(tmp_path):
    baseline = [_case("case-1"), _case("case-2")]
    candidate = [
        {**row, "problem_statement": row["problem_statement"] + "\nReviewed source: src/router.py"}
        for row in baseline
    ]
    graphify_path = tmp_path / "graphify.json"
    jeviphy_path = tmp_path / "jeviphy.json"
    graphify_path.write_text(json.dumps(baseline), encoding="utf-8")
    jeviphy_path.write_text(json.dumps(candidate), encoding="utf-8")

    hashes = validate_arm_datasets(
        graphify_path,
        jeviphy_path,
        expected_ids={"case-1", "case-2"},
        manifest_gold_symbols={"case-1": (), "case-2": ()},
    )
    assert len(hashes.graphify_sha256) == 64
    assert len(hashes.jeviphy_sha256) == 64

    with pytest.raises(ValueError, match="expected case set"):
        validate_arm_datasets(
            graphify_path,
            jeviphy_path,
            expected_ids={"case-1"},
            manifest_gold_symbols={"case-1": ()},
        )

from __future__ import annotations

import json
import os
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path

import pytest

from tools.jevify_user_validation import (
    RECEIPT_FIELDS,
    SmokeReceipt,
    load_receipt_bundle,
    main,
    score,
    serialize_score,
)


RECEIPT = {
    "schema_version": 3,
    "stage": "operator_smoke",
    "operator_id": "operator-01",
    "tool_order": ["graphify", "jevify"],
    "recorded_at": "2026-10-22T15:00:00Z",
    "candidate_commit": "a" * 40,
    "freshness_correct": True,
    "update_correct": True,
    "graphify_usefulness": 3,
    "jevify_usefulness": 5,
    "preferred_next": "jevify",
    "jevify_only_novel_source_verified": True,
    "paid_request_count": 0,
    "graphify_run_sha256": "c" * 64,
    "jevify_run_sha256": "d" * 64,
    "graphify_start_graph_sha256": "e" * 64,
    "jevify_start_graph_sha256": "e" * 64,
    "graphify_start_manifest_sha256": "f" * 64,
    "jevify_start_manifest_sha256": "f" * 64,
    "graphify_diff_sha256": "9" * 64,
    "jevify_diff_sha256": "9" * 64,
}


def _write_bundle(path: Path, receipt: dict = RECEIPT, *, mode: int = 0o600) -> None:
    path.mkdir(mode=0o700)
    receipt_path = path / "receipt.json"
    receipt_path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(receipt_path, mode)


@pytest.fixture
def private_bundle(tmp_path: Path):
    def write(receipt: dict = RECEIPT, *, mode: int = 0o600) -> Path:
        bundle = tmp_path / f"bundle-{len(list(tmp_path.iterdir()))}"
        _write_bundle(bundle, receipt, mode=mode)
        return bundle

    return write


def test_valid_receipt_loads(private_bundle):
    assert load_receipt_bundle(private_bundle()).operator_id == "operator-01"


@pytest.mark.parametrize(
    "forbidden",
    ["name", "email", "repo_path", "question", "prompt", "source", "memory", "credential"],
)
def test_private_content_keys_are_rejected(private_bundle, forbidden):
    with pytest.raises(ValueError, match="forbidden private field"):
        load_receipt_bundle(private_bundle({**RECEIPT, forbidden: "secret"}))


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"schema_version": 2}, "schema version"),
        ({"operator_id": "someone"}, "operator_id"),
        ({"tool_order": ["jevify", "graphify"]}, "tool order"),
        ({"graphify_usefulness": 6}, "rating"),
        ({"preferred_next": "unknown"}, "preferred_next"),
        ({"paid_request_count": -1}, "negative"),
        ({"recorded_at": "2026-10-22"}, "timezone"),
        ({"jevify_start_graph_sha256": "8" * 64}, "starting graph"),
        ({"jevify_start_manifest_sha256": "8" * 64}, "starting manifest"),
        ({"jevify_diff_sha256": "8" * 64}, "diff hashes"),
    ],
)
def test_invalid_receipt_is_rejected(private_bundle, change, message):
    with pytest.raises(ValueError, match=message):
        load_receipt_bundle(private_bundle({**RECEIPT, **change}))


def test_permissions_and_symlinks_are_rejected(private_bundle, tmp_path):
    bundle = private_bundle(mode=0o644)
    with pytest.raises(ValueError, match="permissions"):
        load_receipt_bundle(bundle)
    link = tmp_path / "linked"
    link.symlink_to(bundle, target_is_directory=True)
    with pytest.raises(ValueError, match="real directory"):
        load_receipt_bundle(link)


def _receipt() -> SmokeReceipt:
    return SmokeReceipt(
        operator_id="operator-01",
        tool_order=("graphify", "jevify"),
        recorded_at=datetime(2026, 10, 22, 15, tzinfo=timezone.utc),
        candidate_commit="a" * 40,
        freshness_correct=True,
        update_correct=True,
        graphify_usefulness=3,
        jevify_usefulness=5,
        preferred_next="jevify",
        jevify_only_novel_source_verified=True,
        paid_request_count=0,
        graphify_run_sha256="c" * 64,
        jevify_run_sha256="d" * 64,
        graphify_start_graph_sha256="e" * 64,
        jevify_start_graph_sha256="e" * 64,
        graphify_start_manifest_sha256="f" * 64,
        jevify_start_manifest_sha256="f" * 64,
        graphify_diff_sha256="9" * 64,
        jevify_diff_sha256="9" * 64,
    )


def test_clear_signal_proceeds_to_external_validation():
    assert score(_receipt()).decision == "proceed_to_external_validation"


@pytest.mark.parametrize(
    "change",
    [
        {"preferred_next": "graphify"},
        {"jevify_usefulness": 3},
        {"graphify_usefulness": 5},
        {"jevify_only_novel_source_verified": False},
    ],
)
def test_missing_signal_selects_revision_or_extension(change):
    assert score(replace(_receipt(), **change)).decision == "revise_or_extension"


@pytest.mark.parametrize(
    "change", [{"freshness_correct": False}, {"update_correct": False}, {"paid_request_count": 1}]
)
def test_safety_failure_invalidates_smoke(change):
    assert score(replace(_receipt(), **change)).decision == "invalid_smoke"


def test_missing_receipt_fails_closed_and_serializes():
    result = score(None, validation_failure_count=1)
    assert result.decision == "invalid_smoke"
    assert json.loads(serialize_score(result))["completed"] is False


def test_schemas_match_runtime_contract():
    receipt_schema = json.loads(
        Path("benchmarks/jevify-user-validation/receipt.schema.json").read_text()
    )
    score_schema = json.loads(
        Path("benchmarks/jevify-user-validation/scorecard.schema.json").read_text()
    )
    assert set(receipt_schema["required"]) == RECEIPT_FIELDS
    assert set(score_schema["required"]) == set(asdict(score(_receipt())))


def test_validate_cli_accepts_safe_smoke(private_bundle, capsys):
    bundle = private_bundle()
    assert main(["validate", "--bundle", str(bundle)]) == 0
    assert capsys.readouterr().out.startswith("operator smoke receipt valid")


def test_validate_cli_rejects_safety_failure(private_bundle, capsys):
    bundle = private_bundle({**RECEIPT, "update_correct": False})
    with pytest.raises(SystemExit, match="2"):
        main(["validate", "--bundle", str(bundle)])
    assert "false freshness/update" in capsys.readouterr().err


def test_score_cli_writes_bounded_outputs(private_bundle, tmp_path):
    bundle = private_bundle()
    json_output = tmp_path / "scorecard.json"
    markdown_output = tmp_path / "scorecard.md"
    assert main(
        [
            "score",
            "--bundle",
            str(bundle),
            "--json",
            str(json_output),
            "--markdown",
            str(markdown_output),
        ]
    ) == 0
    assert json.loads(json_output.read_text())["decision"] == (
        "proceed_to_external_validation"
    )
    assert "Jevify usefulness: 5" in markdown_output.read_text()


def test_score_cli_fails_closed_without_private_path(tmp_path):
    json_output = tmp_path / "scorecard.json"
    markdown_output = tmp_path / "scorecard.md"
    assert main(
        [
            "score",
            "--bundle",
            str(tmp_path / "missing"),
            "--json",
            str(json_output),
            "--markdown",
            str(markdown_output),
        ]
    ) == 0
    raw = json_output.read_text()
    assert json.loads(raw)["decision"] == "invalid_smoke"
    assert str(tmp_path) not in raw

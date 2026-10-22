from __future__ import annotations

import hashlib
import json
import os
import random
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from tools.jevify_user_validation import (
    InitialRecord,
    ParticipantReceipt,
    TerminalRecord,
    load_receipt_bundle,
    main,
    score,
    serialize_score,
)


INITIAL = {
    "schema_version": 1,
    "stage": "initial",
    "participant_id": "p01",
    "eligible": True,
    "conflicted": False,
    "tool_order": ["graphify", "jevify"],
    "initial_at": "2026-10-22T15:00:00Z",
    "initial_commit": "a" * 40,
    "freshness_correct": True,
    "update_correct": True,
    "graphify_usefulness": 3,
    "jevify_usefulness": 5,
    "freshness_trust": 5,
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

TERMINAL = {
    "schema_version": 1,
    "stage": "terminal",
    "participant_id": "p01",
    "observed_at": "2026-10-29T15:00:00Z",
    "repeat_at": "2026-10-25T15:00:00Z",
    "later_commit": "b" * 40,
    "repeat_used": True,
    "repeat_without_reminder": True,
    "reminder_sent": False,
    "paid_request_count": 0,
    "repeat_run_sha256": "d" * 64,
    "initial_record_sha256": "AUTO",
}


@pytest.fixture
def private_bundle(tmp_path):
    def write(initial=INITIAL, terminal=TERMINAL, *, mode=0o600):
        bundle = tmp_path / f"bundle-{len(list(tmp_path.iterdir()))}"
        _write_bundle(bundle, initial, terminal, mode=mode)
        return bundle

    return write


def _write_bundle(path, initial, terminal, *, mode=0o600):
    path.mkdir(mode=0o700)
    initial_bytes = (json.dumps(initial, sort_keys=True) + "\n").encode()
    initial_path = path / "initial.json"
    initial_path.write_bytes(initial_bytes)
    terminal = dict(terminal)
    if terminal.get("initial_record_sha256") == "AUTO":
        terminal["initial_record_sha256"] = hashlib.sha256(initial_bytes).hexdigest()
    terminal_path = path / "terminal.json"
    terminal_path.write_text(json.dumps(terminal, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(initial_path, mode)
    os.chmod(terminal_path, mode)


def test_valid_receipt_bundle_loads(private_bundle):
    assert load_receipt_bundle(private_bundle()).participant_id == "p01"


@pytest.mark.parametrize(
    "forbidden",
    ["name", "email", "repo_path", "question", "prompt", "source", "memory", "credential"],
)
def test_private_content_keys_are_rejected(private_bundle, forbidden):
    with pytest.raises(ValueError, match="forbidden private field"):
        load_receipt_bundle(private_bundle({**INITIAL, forbidden: "secret"}, TERMINAL))


@pytest.mark.parametrize(
    ("stage", "change", "message"),
    [
        ("initial", {"eligible": False}, "participant is not eligible"),
        ("initial", {"conflicted": True}, "participant is conflicted"),
        ("initial", {"tool_order": ["jevify", "jevify"]}, "tool order"),
        ("initial", {"graphify_usefulness": 6}, "rating"),
        ("terminal", {"later_commit": "a" * 40}, "later commit"),
        ("terminal", {"repeat_run_sha256": None}, "repeat run"),
        ("terminal", {"reminder_sent": True}, "reminder"),
        ("terminal", {"repeat_at": "2026-10-30T15:00:01Z"}, "seven-day window"),
        ("initial", {"jevify_start_graph_sha256": "8" * 64}, "starting graph"),
        ("initial", {"jevify_start_manifest_sha256": "8" * 64}, "starting manifest"),
        ("initial", {"jevify_diff_sha256": "8" * 64}, "diff hashes"),
    ],
)
def test_invalid_receipt_is_rejected(private_bundle, stage, change, message):
    initial, terminal = dict(INITIAL), dict(TERMINAL)
    (initial if stage == "initial" else terminal).update(change)
    with pytest.raises(ValueError, match=message):
        load_receipt_bundle(private_bundle(initial, terminal))


def test_hash_and_permissions_are_enforced(private_bundle):
    bundle = private_bundle()
    os.chmod(bundle / "initial.json", 0o644)
    with pytest.raises(ValueError, match="permissions"):
        load_receipt_bundle(bundle)

    bundle = private_bundle()
    terminal = json.loads((bundle / "terminal.json").read_text())
    terminal["initial_record_sha256"] = "f" * 64
    (bundle / "terminal.json").write_text(json.dumps(terminal), encoding="utf-8")
    with pytest.raises(ValueError, match="initial record hash"):
        load_receipt_bundle(bundle)


def test_symlink_and_inexact_directory_mode_are_rejected(private_bundle, tmp_path):
    bundle = private_bundle()
    link = tmp_path / "linked"
    link.symlink_to(bundle, target_is_directory=True)
    with pytest.raises(ValueError, match="real directory"):
        load_receipt_bundle(link)

    os.chmod(bundle, 0o600)
    try:
        with pytest.raises(ValueError, match="0700"):
            load_receipt_bundle(bundle)
    finally:
        os.chmod(bundle, 0o700)


def _receipt(index: int, *, prefer: bool, repeat: bool, novel: bool) -> ParticipantReceipt:
    initial_at = datetime(2026, 10, 22, 15, tzinfo=timezone.utc)
    initial = InitialRecord(
        participant_id=f"p{index:02d}",
        eligible=True,
        conflicted=False,
        tool_order=("graphify", "jevify") if index % 2 else ("jevify", "graphify"),
        initial_at=initial_at,
        initial_commit="a" * 40,
        freshness_correct=True,
        update_correct=True,
        graphify_usefulness=3,
        jevify_usefulness=5,
        freshness_trust=5,
        preferred_next="jevify" if prefer else "graphify",
        jevify_only_novel_source_verified=novel,
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
    terminal = TerminalRecord(
        participant_id=f"p{index:02d}",
        observed_at=initial_at + timedelta(days=7),
        repeat_at=initial_at + timedelta(days=3) if repeat else None,
        later_commit="b" * 40 if repeat else None,
        repeat_used=repeat,
        repeat_without_reminder=repeat,
        reminder_sent=False,
        paid_request_count=0,
        repeat_run_sha256="d" * 64 if repeat else None,
        initial_record_sha256="e" * 64,
    )
    return ParticipantReceipt(initial=initial, terminal=terminal)


def _receipts(*, prefer=3, repeat=3, novel=2, count=5):
    return [
        _receipt(i, prefer=i <= prefer, repeat=i <= repeat, novel=i <= novel)
        for i in range(1, count + 1)
    ]


def test_all_gates_pass_returns_continue_product():
    assert score(_receipts()).decision == "continue_product"


@pytest.mark.parametrize(("prefer", "repeat"), [(2, 3), (3, 2), (2, 2)])
def test_preference_or_repeat_failure_returns_extension(prefer, repeat):
    assert score(_receipts(prefer=prefer, repeat=repeat)).decision == "graphify_extension"


def test_less_than_five_unique_receipts_is_insufficient():
    assert score(_receipts(count=4)).decision == "insufficient_evidence"


def test_false_freshness_is_round_ending_and_insufficient():
    receipts = _receipts()
    receipts[0] = replace(receipts[0], initial=replace(receipts[0].initial, freshness_correct=False))
    result = score(receipts)
    assert result.decision == "insufficient_evidence"
    assert result.safety_failure_participant_ids == ("p01",)


def test_score_serialization_is_order_independent():
    receipts = _receipts()
    expected = serialize_score(score(receipts))
    generator = random.Random(7)
    for _ in range(50):
        generator.shuffle(receipts)
        assert serialize_score(score(receipts)) == expected


def test_scorecard_schema_matches_result():
    schema = json.loads(
        Path("benchmarks/jevify-user-validation/scorecard.schema.json").read_text()
    )
    result = asdict(score(_receipts()))
    assert set(schema["required"]) == set(result)
    expected_types = {
        "completed": "integer",
        "prefer_jevify": "integer",
        "repeated_jevify": "integer",
        "novel_source_verified": "integer",
        "known_false_freshness": "integer",
        "known_false_update": "integer",
        "known_paid_requests": "integer",
        "safety_failure_participant_ids": "array",
        "invalid_participant_ids": "array",
        "validation_failure_count": "integer",
        "decision": "string",
    }
    assert {
        name: definition["type"] for name, definition in schema["properties"].items()
    } == expected_types


def test_receipt_schema_required_fields_match_parser_contract():
    schema = json.loads(
        Path("benchmarks/jevify-user-validation/receipt.schema.json").read_text()
    )
    assert set(schema["$defs"]["initial"]["required"]) == set(INITIAL)
    assert set(schema["$defs"]["terminal"]["required"]) == set(TERMINAL)


def test_paid_request_forces_insufficient_evidence():
    receipts = _receipts()
    receipts[2] = replace(
        receipts[2], initial=replace(receipts[2].initial, paid_request_count=1)
    )
    result = score(receipts)
    assert result.decision == "insufficient_evidence"
    assert result.known_paid_requests == 1


def test_six_receipts_remain_serializable_as_insufficient():
    result = score(_receipts(count=6))
    assert result.completed == 6
    assert result.decision == "insufficient_evidence"
    assert json.loads(serialize_score(result))["completed"] == 6


def _validation_manifest(tmp_path: Path, *, invalid_participant: str | None = None) -> Path:
    root = tmp_path / "private-validation"
    root.mkdir(mode=0o700)
    participants = []
    for index in range(1, 6):
        participant_id = f"p{index:02d}"
        order = ["graphify", "jevify"] if index % 2 else ["jevify", "graphify"]
        initial = {**INITIAL, "participant_id": participant_id, "tool_order": order}
        terminal = {**TERMINAL, "participant_id": participant_id}
        if participant_id == invalid_participant:
            terminal["initial_record_sha256"] = "0" * 64
        _write_bundle(root / participant_id, initial, terminal)
        participants.append(
            {
                "participant_id": participant_id,
                "eligibility_evidence": "prior_real_repository_use",
                "tool_order": order,
            }
        )
    manifest = root / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "candidate_commit": "a" * 40,
                "session_date": "2026-10-22",
                "participants": participants,
            }
        ),
        encoding="utf-8",
    )
    os.chmod(manifest, 0o600)
    return manifest


def test_validate_cli_accepts_five_frozen_receipts(tmp_path, capsys):
    manifest = _validation_manifest(tmp_path)
    assert main(["validate", "--manifest", str(manifest)]) == 0
    assert capsys.readouterr().out.strip() == (
        "5 valid receipts; 0 private-field violations; 0 paid requests"
    )


def test_validate_initial_works_before_terminal_exists(tmp_path, capsys):
    bundle = tmp_path / "p01"
    bundle.mkdir(mode=0o700)
    initial = bundle / "initial.json"
    initial.write_text(json.dumps(INITIAL), encoding="utf-8")
    os.chmod(initial, 0o600)
    assert main(["validate-initial", "--bundle", str(bundle)]) == 0
    assert capsys.readouterr().out.startswith("p01 initial receipt valid")


def test_validate_initial_rejects_paid_request_and_names_slot(tmp_path, capsys):
    bundle = tmp_path / "p01"
    bundle.mkdir(mode=0o700)
    initial = bundle / "initial.json"
    initial.write_text(json.dumps({**INITIAL, "paid_request_count": 1}), encoding="utf-8")
    os.chmod(initial, 0o600)
    with pytest.raises(SystemExit, match="2"):
        main(["validate-initial", "--bundle", str(bundle)])
    assert "p01: paid request" in capsys.readouterr().err


def test_score_cli_writes_aggregate_outputs(tmp_path):
    manifest = _validation_manifest(tmp_path)
    json_output = tmp_path / "scorecard.json"
    markdown_output = tmp_path / "scorecard.md"
    assert main(
        [
            "score",
            "--manifest",
            str(manifest),
            "--json",
            str(json_output),
            "--markdown",
            str(markdown_output),
        ]
    ) == 0
    assert json.loads(json_output.read_text())["decision"] == "continue_product"
    assert "Completed: 5/5" in markdown_output.read_text()


@pytest.mark.parametrize("failure", ["missing_terminal", "unequal_hash", "unsafe_mode"])
def test_score_cli_writes_insufficient_scorecard_for_invalid_bundle(tmp_path, failure):
    manifest = _validation_manifest(tmp_path)
    bundle = manifest.parent / "p03"
    if failure == "missing_terminal":
        (bundle / "terminal.json").unlink()
    elif failure == "unequal_hash":
        initial_path = bundle / "initial.json"
        initial = json.loads(initial_path.read_text())
        initial["jevify_start_graph_sha256"] = "8" * 64
        initial_bytes = (json.dumps(initial, sort_keys=True) + "\n").encode()
        initial_path.write_bytes(initial_bytes)
        os.chmod(initial_path, 0o600)
        terminal_path = bundle / "terminal.json"
        terminal = json.loads(terminal_path.read_text())
        terminal["initial_record_sha256"] = hashlib.sha256(initial_bytes).hexdigest()
        terminal_path.write_text(json.dumps(terminal), encoding="utf-8")
    else:
        os.chmod(bundle / "initial.json", 0o644)

    json_output = tmp_path / "scorecard.json"
    markdown_output = tmp_path / "scorecard.md"
    assert main(
        [
            "score",
            "--manifest",
            str(manifest),
            "--json",
            str(json_output),
            "--markdown",
            str(markdown_output),
        ]
    ) == 0
    raw = json_output.read_text()
    result = json.loads(raw)
    assert result["decision"] == "insufficient_evidence"
    assert result["completed"] == 4
    assert result["invalid_participant_ids"] == ["p03"]
    assert result["validation_failure_count"] == 1
    assert result["known_paid_requests"] == 0
    assert "Known paid requests among valid receipts" in markdown_output.read_text()
    assert str(tmp_path) not in raw


def test_score_cli_writes_insufficient_scorecard_for_invalid_manifest(tmp_path):
    json_output = tmp_path / "scorecard.json"
    markdown_output = tmp_path / "scorecard.md"
    assert main(
        [
            "score",
            "--manifest",
            str(tmp_path / "missing.json"),
            "--json",
            str(json_output),
            "--markdown",
            str(markdown_output),
        ]
    ) == 0
    result = json.loads(json_output.read_text())
    assert result["decision"] == "insufficient_evidence"
    assert result["completed"] == 0
    assert result["validation_failure_count"] == 1


def test_score_cli_handles_non_hashable_tool_order_fail_closed(tmp_path):
    manifest = _validation_manifest(tmp_path)
    bundle = manifest.parent / "p03"
    initial_path = bundle / "initial.json"
    initial = json.loads(initial_path.read_text())
    initial["tool_order"] = [[], "jevify"]
    initial_bytes = (json.dumps(initial, sort_keys=True) + "\n").encode()
    initial_path.write_bytes(initial_bytes)
    os.chmod(initial_path, 0o600)
    terminal_path = bundle / "terminal.json"
    terminal = json.loads(terminal_path.read_text())
    terminal["initial_record_sha256"] = hashlib.sha256(initial_bytes).hexdigest()
    terminal_path.write_text(json.dumps(terminal), encoding="utf-8")
    json_output = tmp_path / "scorecard.json"
    markdown_output = tmp_path / "scorecard.md"
    assert main(
        [
            "score",
            "--manifest",
            str(manifest),
            "--json",
            str(json_output),
            "--markdown",
            str(markdown_output),
        ]
    ) == 0
    result = json.loads(json_output.read_text())
    assert result["decision"] == "insufficient_evidence"
    assert result["invalid_participant_ids"] == ["p03"]


def test_score_cli_handles_non_string_manifest_value_fail_closed(tmp_path):
    manifest = _validation_manifest(tmp_path)
    payload = json.loads(manifest.read_text())
    payload["participants"][2]["eligibility_evidence"] = {}
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    json_output = tmp_path / "scorecard.json"
    markdown_output = tmp_path / "scorecard.md"
    assert main(
        [
            "score",
            "--manifest",
            str(manifest),
            "--json",
            str(json_output),
            "--markdown",
            str(markdown_output),
        ]
    ) == 0
    result = json.loads(json_output.read_text())
    assert result["decision"] == "insufficient_evidence"
    assert result["validation_failure_count"] == 1


def test_manifest_error_names_the_participant(tmp_path, capsys):
    manifest = _validation_manifest(tmp_path, invalid_participant="p03")
    with pytest.raises(SystemExit, match="2"):
        main(["validate", "--manifest", str(manifest)])
    assert "p03: initial record hash" in capsys.readouterr().err

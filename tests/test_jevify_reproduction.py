import json

import pytest

from tools.jevify_reproduction import canonical_receipt, validate_receipts


PINS = {
    "manifest_sha256": "1" * 64,
    "graphify_commit": "2" * 40,
    "jevify_commit": "3" * 40,
    "result_sha256": "4" * 64,
}


def _receipt(reviewer, os_name):
    payload = {
        "schema_version": 1,
        "reviewer": reviewer,
        "independent": True,
        "os": os_name,
        "machine": "4 vCPU, 16 GB RAM",
        **PINS,
        "scorecard": {"retrieval": "pass"},
    }
    return canonical_receipt(payload)


def _write(tmp_path, name, payload, *, canonical=True):
    path = tmp_path / name
    text = json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
    path.write_text(text if canonical else json.dumps(payload, indent=2), encoding="utf-8")
    return path


def test_two_independent_receipts_validate_with_linux(tmp_path):
    paths = [
        _write(tmp_path, "one.json", _receipt("alice", "macOS 15")),
        _write(tmp_path, "two.json", _receipt("bob", "Ubuntu 24.04")),
    ]
    receipts = validate_receipts(paths, PINS, authors={"maintainer"})
    assert len(receipts) == 2


@pytest.mark.parametrize("field", ["manifest_sha256", "result_sha256", "jevify_commit"])
def test_receipt_rejects_mismatched_pins(tmp_path, field):
    payload = _receipt("alice", "Ubuntu 24.04")
    payload[field] = "f" * len(payload[field])
    path = _write(tmp_path, "wrong.json", canonical_receipt({
        key: value for key, value in payload.items() if key != "payload_sha256"
    }))
    with pytest.raises(ValueError, match=field):
        validate_receipts([path], PINS, authors=set())


def test_receipts_reject_duplicate_author_missing_linux_and_unknown_field(tmp_path):
    one = _write(tmp_path, "one.json", _receipt("alice", "macOS 15"))
    duplicate = _write(tmp_path, "duplicate.json", _receipt("alice", "Ubuntu 24.04"))
    with pytest.raises(ValueError, match="duplicate reviewer"):
        validate_receipts([one, duplicate], PINS, authors=set())
    with pytest.raises(ValueError, match="Linux"):
        validate_receipts([one, _write(tmp_path, "two.json", _receipt("bob", "macOS 14"))],
                          PINS, authors=set(), require_complete=True)

    payload = _receipt("bob", "Ubuntu")
    payload["extra"] = True
    with pytest.raises(ValueError, match="unknown fields"):
        validate_receipts([_write(tmp_path, "extra.json", payload)], PINS, authors=set())


def test_receipt_rejects_author_bad_hash_and_noncanonical_json(tmp_path):
    authored = _write(tmp_path, "author.json", _receipt("maintainer", "Ubuntu"))
    with pytest.raises(ValueError, match="implementation contributor"):
        validate_receipts([authored], PINS, authors={"maintainer"})

    bad = _receipt("alice", "Ubuntu")
    bad["payload_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="payload_sha256"):
        validate_receipts([_write(tmp_path, "bad.json", bad)], PINS, authors=set())

    pretty = _write(tmp_path, "pretty.json", _receipt("alice", "Ubuntu"), canonical=False)
    with pytest.raises(ValueError, match="canonical JSON"):
        validate_receipts([pretty], PINS, authors=set())

import hashlib
import json
from dataclasses import replace

import pytest

from tools.jeviphy_evidence_bundle import EvidenceFile, EvidenceInputs, assemble_bundle


PINS = {
    "manifest_sha256": "1" * 64,
    "graphify_commit": "2" * 40,
    "jeviphy_commit": "3" * 40,
    "retrieval_jeviphy_commit": "4" * 40,
}


def _write(tmp_path, name, payload):
    path = tmp_path / name
    data = (json.dumps(payload, sort_keys=True) + "\n").encode()
    path.write_bytes(data)
    return EvidenceFile(path, hashlib.sha256(data).hexdigest())


def _pair(case_id):
    return {"pair": {
        "case_id": case_id, "stratum": "valid_source", "pass_index": 0,
        "baseline": {"success": False, "duration_ms": 1000},
        "jeviphy": {"success": True, "duration_ms": 800},
    }}


def valid_inputs(tmp_path):
    retrieval = _write(tmp_path, "retrieval.json", {
        "pins": {"manifest_sha256": PINS["manifest_sha256"],
                 "graphify_commit": PINS["graphify_commit"],
                 "jeviphy_commit": PINS["retrieval_jeviphy_commit"]},
        "retrieval_records": [_pair("retrieval-1")],
    })
    product = _write(tmp_path, "product.json", {
        "schema_version": 1,
        "pins": {key: PINS[key] for key in ("manifest_sha256", "graphify_commit", "jeviphy_commit")},
        "journal_sha256": "5" * 64,
        "product_records": [_pair(f"case-{index}") for index in range(30)],
    })
    zero = _write(tmp_path, "zero.json", {
        "schema_version": 1, "jeviphy_commit": PINS["jeviphy_commit"],
        "status": "pass", "attempts": 30, "successes": 30,
    })
    install = _write(tmp_path, "install.json", {
        "schema_version": 1, "jeviphy_commit": PINS["jeviphy_commit"],
        "attempts": 20, "successes": 20, "median_seconds": 30,
        "operating_systems": ["macOS", "Ubuntu"],
    })
    compatibility = _write(tmp_path, "compatibility.json", {
        "schema_version": 1, "jeviphy_commit": PINS["jeviphy_commit"], "compatible": True,
    })
    return EvidenceInputs(
        retrieval, product, zero, install, compatibility, (), PINS, frozenset({"maintainer"})
    )


def test_bundle_rejects_mixed_candidate_shas(tmp_path):
    inputs = valid_inputs(tmp_path)
    payload = json.loads(inputs.product.path.read_text())
    payload["pins"]["jeviphy_commit"] = "f" * 40
    product = _write(tmp_path, "changed-product.json", payload)
    with pytest.raises(ValueError, match="candidate SHA differs"):
        assemble_bundle(replace(inputs, product=product))


def test_bundle_rejects_hash_mismatch_and_unknown_fields(tmp_path):
    inputs = valid_inputs(tmp_path)
    with pytest.raises(ValueError, match="SHA-256 differs"):
        assemble_bundle(replace(inputs, retrieval=EvidenceFile(inputs.retrieval.path, "0" * 64)))

    payload = json.loads(inputs.zero_config.path.read_text())
    payload["secret"] = "unexpected"
    with pytest.raises(ValueError, match="unknown fields"):
        assemble_bundle(replace(inputs, zero_config=_write(tmp_path, "unknown.json", payload)))


def test_bundle_rejects_incomplete_product_and_wrong_zero_candidate(tmp_path):
    inputs = valid_inputs(tmp_path)
    product = json.loads(inputs.product.path.read_text())
    product["product_records"].pop()
    with pytest.raises(ValueError, match="30 complete product pairs"):
        assemble_bundle(replace(inputs, product=_write(tmp_path, "short.json", product)))

    zero = json.loads(inputs.zero_config.path.read_text())
    zero["jeviphy_commit"] = "f" * 40
    with pytest.raises(ValueError, match="candidate SHA differs"):
        assemble_bundle(replace(inputs, zero_config=_write(tmp_path, "wrong-zero.json", zero)))


def test_bundle_rejects_duplicate_or_self_authored_receipts(tmp_path):
    inputs = valid_inputs(tmp_path)
    receipt_payload = {
        "schema_version": 1, "reviewer": "reviewer", "independent": True,
        "os": "Ubuntu", "manifest_sha256": PINS["manifest_sha256"],
        "graphify_commit": PINS["graphify_commit"],
        "jeviphy_commit": PINS["retrieval_jeviphy_commit"], "result_sha256": "6" * 64,
        "scorecard": {"retrieval": "pass"}, "payload_sha256": "7" * 64,
    }
    receipt = _write(tmp_path, "receipt.json", receipt_payload)
    with pytest.raises(ValueError, match="duplicate reviewer"):
        assemble_bundle(replace(inputs, reproductions=(receipt, receipt)))

    authored = {**receipt_payload, "reviewer": "maintainer"}
    with pytest.raises(ValueError, match="implementation contributor"):
        assemble_bundle(replace(inputs, reproductions=(_write(tmp_path, "author.json", authored),)))


def test_bundle_is_canonical_and_excludes_private_payloads(tmp_path):
    inputs = valid_inputs(tmp_path)
    bundle = assemble_bundle(inputs)
    encoded = json.dumps(bundle, sort_keys=True, separators=(",", ":")) + "\n"

    assert bundle["schema_version"] == 1
    assert len(bundle["product_records"]) == 30
    assert "patch" not in encoded
    assert set(bundle) == {
        "schema_version", "pins", "retrieval_records", "product_records", "usability",
        "compatibility", "reproductions", "source_hashes",
    }

"""Assemble public Jevify evidence without mixing candidates or private artifacts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True)
class EvidenceFile:
    path: Path
    sha256: str


@dataclass(frozen=True)
class EvidenceInputs:
    retrieval: EvidenceFile
    product: EvidenceFile
    zero_config: EvidenceFile
    install: EvidenceFile
    compatibility: EvidenceFile
    reproductions: tuple[EvidenceFile, ...]
    pins: Mapping[str, str]
    retrieval_authors: frozenset[str]


def _read(source: EvidenceFile, allowed_keys: set[str]) -> dict:
    raw = source.path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != source.sha256:
        raise ValueError(f"SHA-256 differs for {source.path}")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid JSON: {source.path}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"evidence must be an object: {source.path}")
    unknown = set(payload) - allowed_keys
    if unknown:
        raise ValueError(f"unknown fields in {source.path}: {sorted(unknown)}")
    return payload


def _candidate(payload: Mapping, *, nested: bool = False) -> str | None:
    pins = payload.get("pins") if nested else payload
    if not isinstance(pins, Mapping):
        return None
    return pins.get("jevify_commit", pins.get("jeviphy_commit"))


def _jevify(mapping: Mapping) -> object:
    return mapping.get("jevify", mapping.get("jeviphy"))


def _pin(mapping: Mapping, key: str) -> object:
    if key == "jevify_commit":
        return _candidate(mapping)
    return mapping.get(key)


def _validate_pairs(records: object, expected: int | None = None) -> list[dict]:
    if not isinstance(records, list):
        raise ValueError("paired records must be a list")
    seen: set[tuple[str, int]] = set()
    for wrapper in records:
        if not isinstance(wrapper, dict) or set(wrapper) != {"pair"}:
            raise ValueError("record must contain exactly one pair")
        pair = wrapper["pair"]
        if not isinstance(pair, dict):
            raise ValueError("pair must be an object")
        case_id, pass_index = pair.get("case_id"), pair.get("pass_index")
        if not isinstance(case_id, str) or not isinstance(pass_index, int):
            raise ValueError("duplicate or invalid paired record")
        key = (case_id, pass_index)
        if key in seen:
            raise ValueError("duplicate or invalid paired record")
        if not isinstance(pair.get("baseline"), dict) or not isinstance(_jevify(pair), dict):
            raise ValueError("pair must contain both arms")
        seen.add(key)
    if expected is not None and len(records) != expected:
        raise ValueError(f"expected {expected} complete product pairs")
    return records


def validate_reproduction_receipt(
    receipt: Mapping,
    pins: Mapping[str, str],
    retrieval_authors: frozenset[str],
) -> dict:
    reviewer = receipt.get("reviewer")
    if not isinstance(reviewer, str) or not reviewer:
        raise ValueError("reproduction receipt has no reviewer")
    if reviewer.casefold() in {author.casefold() for author in retrieval_authors}:
        raise ValueError("receipt reviewer is an implementation contributor")
    if receipt.get("independent") is not True:
        raise ValueError("receipt is not independent")
    for key in ("manifest_sha256", "graphify_commit"):
        if receipt.get(key) != pins.get(key):
            raise ValueError(f"receipt {key} differs")
    if _candidate(receipt) != pins.get("retrieval_jevify_commit"):
        raise ValueError("receipt retrieval candidate SHA differs")
    return dict(receipt)


def assemble_bundle(inputs: EvidenceInputs) -> dict:
    required_pins = {
        "manifest_sha256", "graphify_commit", "jevify_commit", "retrieval_jevify_commit"
    }
    if set(inputs.pins) != required_pins:
        raise ValueError("evidence pins are incomplete or unknown")
    retrieval = _read(inputs.retrieval, {"manifest", "pins", "retrieval_records"})
    product = _read(
        inputs.product,
        {"schema_version", "pins", "journal_sha256", "product_records"},
    )
    zero = _read(
        inputs.zero_config,
        {"schema_version", "jevify_commit", "jeviphy_commit", "manifest_sha256", "journal_sha256",
         "source_score_sha256", "status", "attempts", "successes", "exact_outputs",
         "exact_matches", "interaction_required", "measured_pairs", "median_overhead_fraction",
         "p95_overhead_fraction", "failed_cases"},
    )
    install = _read(
        inputs.install,
        {"schema_version", "jevify_commit", "jeviphy_commit", "attempts", "successes", "median_seconds",
         "operating_systems", "journal_sha256"},
    )
    compatibility = _read(
        inputs.compatibility,
        {"schema_version", "jevify_commit", "jeviphy_commit", "compatible"},
    )

    retrieval_pins = retrieval.get("pins", {})
    product_pins = product.get("pins", {})
    for key in ("manifest_sha256", "graphify_commit"):
        if _pin(retrieval_pins, key) != inputs.pins[key] or _pin(product_pins, key) != inputs.pins[key]:
            raise ValueError(f"{key} differs across evidence")
    if _candidate(retrieval, nested=True) != inputs.pins["retrieval_jevify_commit"]:
        raise ValueError("retrieval candidate SHA differs")
    for payload in (product, zero, install, compatibility):
        nested = payload is product
        if _candidate(payload, nested=nested) != inputs.pins["jevify_commit"]:
            raise ValueError("candidate SHA differs across evidence")

    retrieval_records = _validate_pairs(retrieval.get("retrieval_records"))
    product_records = _validate_pairs(product.get("product_records"), expected=30)
    reviewers: set[str] = set()
    reproductions = []
    receipt_keys = {
        "schema_version", "reviewer", "independent", "os", "machine", "manifest_sha256",
        "graphify_commit", "jevify_commit", "jeviphy_commit", "result_sha256", "scorecard", "payload_sha256",
    }
    for source in inputs.reproductions:
        receipt = _read(source, receipt_keys)
        reviewer = str(receipt.get("reviewer", "")).casefold()
        if reviewer in reviewers:
            raise ValueError("duplicate reviewer in reproduction receipts")
        reviewers.add(reviewer)
        reproductions.append(validate_reproduction_receipt(receipt, inputs.pins, inputs.retrieval_authors))

    usability = dict(install)
    usability["zero_config"] = {
        "status": zero.get("status"),
        "attempts": zero.get("attempts"),
        "successes": zero.get("successes"),
    }
    sources = {
        "retrieval": inputs.retrieval.sha256,
        "product": inputs.product.sha256,
        "zero_config": inputs.zero_config.sha256,
        "install": inputs.install.sha256,
        "compatibility": inputs.compatibility.sha256,
    }
    sources.update({f"reproduction:{index}": item.sha256 for index, item in enumerate(inputs.reproductions)})
    return {
        "schema_version": 1,
        "pins": dict(inputs.pins),
        "retrieval_records": retrieval_records,
        "product_records": product_records,
        "usability": usability,
        "compatibility": compatibility.get("compatible"),
        "reproductions": reproductions,
        "source_hashes": sources,
    }


def write_bundle(inputs: EvidenceInputs, output: Path) -> None:
    payload = assemble_bundle(inputs)
    output.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

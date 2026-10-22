"""Create and validate canonical independent Jeviphy reproduction receipts."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping


FIELDS = {
    "schema_version", "reviewer", "independent", "os", "machine", "manifest_sha256",
    "graphify_commit", "jeviphy_commit", "result_sha256", "scorecard", "payload_sha256",
}


@dataclass(frozen=True)
class Receipt:
    reviewer: str
    operating_system: str
    machine: str
    manifest_sha256: str
    graphify_commit: str
    jeviphy_commit: str
    result_sha256: str
    payload_sha256: str


def _encode(payload: Mapping) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()


def canonical_receipt(payload: Mapping) -> dict:
    if "payload_sha256" in payload:
        raise ValueError("payload must not already contain payload_sha256")
    result = dict(payload)
    result["payload_sha256"] = hashlib.sha256(_encode(result)).hexdigest()
    return result


def _load(path: Path) -> dict:
    raw = path.read_bytes()

    def no_duplicates(pairs: list[tuple[str, object]]) -> dict:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    try:
        payload = json.loads(raw, object_pairs_hook=no_duplicates)
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid receipt JSON: {path}") from error
    if not isinstance(payload, dict) or _encode(payload) != raw:
        raise ValueError(f"receipt is not canonical JSON: {path}")
    return payload


def validate_receipts(
    paths: Iterable[Path],
    pins: Mapping[str, str],
    authors: set[str],
    *,
    require_complete: bool = False,
) -> tuple[Receipt, ...]:
    receipts = []
    reviewers: set[str] = set()
    author_keys = {author.casefold() for author in authors}
    for path in paths:
        payload = _load(path)
        unknown = set(payload) - FIELDS
        missing = FIELDS - set(payload)
        if unknown:
            raise ValueError(f"receipt has unknown fields: {sorted(unknown)}")
        if missing:
            raise ValueError(f"receipt is missing fields: {sorted(missing)}")
        reviewer = payload["reviewer"]
        if not isinstance(reviewer, str) or not reviewer.strip():
            raise ValueError("receipt reviewer is invalid")
        reviewer_key = reviewer.casefold()
        if reviewer_key in reviewers:
            raise ValueError("duplicate reviewer")
        if reviewer_key in author_keys:
            raise ValueError("receipt reviewer is an implementation contributor")
        if payload["schema_version"] != 1 or payload["independent"] is not True:
            raise ValueError("receipt is not an independent schema v1 receipt")
        for field in ("manifest_sha256", "graphify_commit", "jeviphy_commit", "result_sha256"):
            if payload[field] != pins[field]:
                raise ValueError(f"receipt {field} differs")
        unhashed = {key: value for key, value in payload.items() if key != "payload_sha256"}
        if payload["payload_sha256"] != hashlib.sha256(_encode(unhashed)).hexdigest():
            raise ValueError("receipt payload_sha256 differs")
        scorecard = payload["scorecard"]
        if not isinstance(scorecard, dict) or scorecard.get("retrieval") != "pass":
            raise ValueError("receipt does not reproduce the retrieval pass")
        reviewers.add(reviewer_key)
        receipts.append(Receipt(
            reviewer=reviewer,
            operating_system=str(payload["os"]),
            machine=str(payload["machine"]),
            manifest_sha256=payload["manifest_sha256"],
            graphify_commit=payload["graphify_commit"],
            jeviphy_commit=payload["jeviphy_commit"],
            result_sha256=payload["result_sha256"],
            payload_sha256=payload["payload_sha256"],
        ))
    if require_complete:
        if len(receipts) < 2:
            raise ValueError("two independent receipts are required")
        if not any("ubuntu" in receipt.operating_system.casefold() or
                   "linux" in receipt.operating_system.casefold() for receipt in receipts):
            raise ValueError("at least one Linux receipt is required")
    return tuple(receipts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--os", dest="operating_system", required=True)
    parser.add_argument("--machine", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = json.loads(args.result.read_text(encoding="utf-8"))
    pins = result["pins"]
    payload = canonical_receipt({
        "schema_version": 1,
        "reviewer": args.reviewer,
        "independent": True,
        "os": args.operating_system,
        "machine": args.machine,
        "manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
        "graphify_commit": pins["graphify_commit"],
        "jeviphy_commit": pins["jeviphy_commit"],
        "result_sha256": hashlib.sha256(args.result.read_bytes()).hexdigest(),
        "scorecard": {"retrieval": "pass"},
    })
    args.output.write_bytes(_encode(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

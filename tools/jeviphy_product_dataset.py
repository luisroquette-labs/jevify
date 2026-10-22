"""Fail-closed validation for paired Graphify and Jeviphy product datasets."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence


MAX_CONTEXT_BYTES = 8 * 1024
MAX_SOURCE_PATHS = 20
PATH_PATTERN = re.compile(r"(?m)(?:^|\s)([\w.@+-]+(?:/[\w.@+ -]+)+\.[\w+-]+)(?:$|[\s,;:)])")


@dataclass(frozen=True)
class DatasetHashes:
    graphify_sha256: str
    jeviphy_sha256: str


def _sha256(path: Path) -> str:
    if path.is_file():
        return hashlib.sha256(path.read_bytes()).hexdigest()
    digest = hashlib.sha256()
    for child in sorted(item for item in path.rglob("*") if item.is_file()):
        digest.update(child.relative_to(path).as_posix().encode())
        digest.update(b"\0")
        digest.update(child.read_bytes())
    return digest.hexdigest()


def _load_rows(path: Path) -> list[dict]:
    if path.is_file() and path.suffix in {".json", ".jsonl"}:
        text = path.read_text(encoding="utf-8")
        value = json.loads(text) if path.suffix == ".json" else [json.loads(line) for line in text.splitlines() if line]
        if isinstance(value, dict):
            value = value.get("train", value.get("rows", value))
        if not isinstance(value, list) or not all(isinstance(row, dict) for row in value):
            raise ValueError(f"dataset must contain a JSON row list: {path}")
        return value

    parquet = path if path.suffix == ".parquet" else next(iter(sorted(path.glob("*.parquet"))), None)
    if parquet is None:
        raise ValueError(f"unsupported dataset path: {path}")
    try:
        import pyarrow.parquet as pq  # type: ignore[import-not-found]
    except ImportError:
        script = (
            "import json,pyarrow.parquet as p,sys;"
            "print(json.dumps(p.read_table(sys.argv[1]).to_pylist()))"
        )
        result = subprocess.run(
            ["uvx", "--from", "pyarrow", "python", "-c", script, str(parquet)],
            check=True,
            capture_output=True,
            text=True,
        )
        return json.loads(result.stdout)
    return pq.read_table(parquet).to_pylist()


def _index(rows: Iterable[Mapping]) -> dict[str, dict]:
    indexed: dict[str, dict] = {}
    for row in rows:
        instance_id = row.get("instance_id")
        if not isinstance(instance_id, str) or not instance_id:
            raise ValueError("dataset row has invalid instance_id")
        if instance_id in indexed:
            raise ValueError(f"duplicate instance_id: {instance_id}")
        indexed[instance_id] = dict(row)
    return indexed


def validate_arm_case(
    graphify: Mapping,
    jeviphy: Mapping,
    *,
    gold_symbols: Sequence[str],
) -> None:
    """Require byte-equivalent rows except for a bounded appended problem suffix."""
    if set(graphify) != set(jeviphy):
        raise ValueError("arm dataset fields differ")
    for key in graphify:
        if key != "problem_statement" and graphify[key] != jeviphy[key]:
            raise ValueError(f"{key} differs between arm datasets")

    original = graphify.get("problem_statement")
    candidate = jeviphy.get("problem_statement")
    if not isinstance(original, str) or not isinstance(candidate, str) or not candidate.startswith(original):
        raise ValueError("problem_statement must append to the Graphify text")
    suffix = candidate[len(original) :]
    if len(suffix.encode("utf-8")) > MAX_CONTEXT_BYTES:
        raise ValueError("Jeviphy context exceeds 8 KiB")
    if len(set(PATH_PATTERN.findall(suffix))) > MAX_SOURCE_PATHS:
        raise ValueError("Jeviphy context contains more than 20 source paths")
    lower = suffix.casefold()
    if re.search(r"\b(?:test_)?patch\b", lower):
        raise ValueError("Jeviphy context leaks patch material")
    if any(symbol and symbol.casefold() in lower for symbol in gold_symbols):
        raise ValueError("Jeviphy context leaks a gold symbol")


def validate_arm_datasets(
    graphify_path: Path,
    jeviphy_path: Path,
    *,
    expected_ids: set[str],
    manifest_gold_symbols: Mapping[str, Sequence[str]],
) -> DatasetHashes:
    graphify = _index(_load_rows(graphify_path))
    jeviphy = _index(_load_rows(jeviphy_path))
    if set(graphify) != expected_ids or set(jeviphy) != expected_ids:
        raise ValueError("arm datasets do not match the expected case set")
    for instance_id in sorted(expected_ids):
        validate_arm_case(
            graphify[instance_id],
            jeviphy[instance_id],
            gold_symbols=manifest_gold_symbols.get(instance_id, ()),
        )
    return DatasetHashes(_sha256(graphify_path), _sha256(jeviphy_path))

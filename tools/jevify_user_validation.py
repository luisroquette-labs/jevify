"""Validate one private Jevify operator smoke test and publish a bounded decision."""

from __future__ import annotations

import argparse
import json
import re
import stat
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal, Sequence, cast


Preference = Literal["graphify", "jevify", "neither"]
UpdateRoute = Literal["already_current", "graphify_handoff"]
MemoryMode = Literal["graph_only", "reviewed_memory"]
MemoryValue = Literal["not_tested", "helpful", "not_helpful"]
ComparativeClaimStatus = Literal["not_made", "supported", "unsupported"]
Decision = Literal[
    "proceed_to_memory_smoke",
    "proceed_to_external_validation",
    "revise_or_extension",
    "invalid_smoke",
]
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
FORBIDDEN_PRIVATE_FIELDS = frozenset(
    {"name", "email", "repo_path", "question", "prompt", "source", "memory", "credential"}
)
RECEIPT_FIELDS = frozenset(
    {
        "schema_version",
        "stage",
        "operator_id",
        "tool_order",
        "recorded_at",
        "candidate_commit",
        "comparison_start_mode",
        "target_resolution_correct",
        "jevify_update_route",
        "structural_engine",
        "memory_mode",
        "memory_value",
        "attribution_correct",
        "comparative_claim_status",
        "freshness_correct",
        "update_correct",
        "graphify_usefulness",
        "jevify_usefulness",
        "preferred_next",
        "jevify_only_novel_source_verified",
        "paid_request_count",
        "graphify_run_sha256",
        "jevify_run_sha256",
        "graphify_start_graph_sha256",
        "jevify_start_graph_sha256",
        "graphify_start_manifest_sha256",
        "jevify_start_manifest_sha256",
        "graphify_diff_sha256",
        "jevify_diff_sha256",
    }
)


@dataclass(frozen=True)
class SmokeReceipt:
    operator_id: str
    tool_order: tuple[Literal["graphify"], Literal["jevify"]]
    recorded_at: datetime
    candidate_commit: str
    comparison_start_mode: Literal["warm"]
    target_resolution_correct: bool
    jevify_update_route: UpdateRoute
    structural_engine: Literal["graphify"]
    memory_mode: MemoryMode
    memory_value: MemoryValue
    attribution_correct: bool
    comparative_claim_status: ComparativeClaimStatus
    freshness_correct: bool
    update_correct: bool
    graphify_usefulness: int
    jevify_usefulness: int
    preferred_next: Preference
    jevify_only_novel_source_verified: bool
    paid_request_count: int
    graphify_run_sha256: str
    jevify_run_sha256: str
    graphify_start_graph_sha256: str
    jevify_start_graph_sha256: str
    graphify_start_manifest_sha256: str
    jevify_start_manifest_sha256: str
    graphify_diff_sha256: str
    jevify_diff_sha256: str


@dataclass(frozen=True)
class SmokeScore:
    completed: bool
    comparison_start_mode: Literal["warm"] | None
    target_resolution_correct: bool
    jevify_update_route: UpdateRoute | None
    structural_engine: Literal["graphify"] | None
    graphify_usefulness: int | None
    jevify_usefulness: int | None
    preferred_next: Preference | None
    novel_source_verified: bool
    memory_mode: MemoryMode | None
    memory_value: MemoryValue | None
    attribution_correct: bool
    comparative_claim_status: ComparativeClaimStatus | None
    known_false_freshness: int
    known_false_update: int
    known_paid_requests: int
    validation_failure_count: int
    decision: Decision


def _private_file_bytes(path: Path) -> bytes:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise ValueError(f"missing receipt file: {path.name}") from exc
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise ValueError(f"receipt is not a regular file: {path.name}")
    if stat.S_IMODE(metadata.st_mode) != 0o600:
        raise ValueError(f"unsafe receipt permissions: {path.name} must be mode 0600")
    return path.read_bytes()


def _private_directory(path: Path) -> Path:
    path = Path(path)
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise ValueError(f"missing receipt directory: {path}") from exc
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise ValueError("receipt bundle must be a real directory")
    if stat.S_IMODE(metadata.st_mode) != 0o700:
        raise ValueError("unsafe receipt directory permissions: expected mode 0700")
    return path


def _object(raw: bytes) -> dict[str, object]:
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid receipt JSON") from exc
    if not isinstance(value, dict):
        raise ValueError("receipt must be an object")
    for key in value:
        if str(key).casefold() in FORBIDDEN_PRIVATE_FIELDS:
            raise ValueError(f"forbidden private field: {key}")
    unknown = set(value) - RECEIPT_FIELDS
    missing = RECEIPT_FIELDS - set(value)
    if unknown:
        raise ValueError(f"unknown receipt field: {sorted(unknown)[0]}")
    if missing:
        raise ValueError(f"missing receipt field: {sorted(missing)[0]}")
    return cast(dict[str, object], value)


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _bool(value: object, field: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field} must be boolean")
    return value


def _integer(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")
    return value


def _timestamp(value: object, field: str) -> datetime:
    text = _string(value, field)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must include a timezone")
    return parsed


def _hex(value: object, field: str, pattern: re.Pattern[str]) -> str:
    text = _string(value, field)
    if pattern.fullmatch(text) is None:
        raise ValueError(f"{field} has invalid lowercase hexadecimal format")
    return text


def _parse_receipt(data: dict[str, object]) -> SmokeReceipt:
    if data["schema_version"] != 4 or data["stage"] != "operator_smoke":
        raise ValueError("invalid receipt schema version or stage")
    if data["operator_id"] != "operator-01":
        raise ValueError("operator_id must be operator-01")
    if data["tool_order"] != ["graphify", "jevify"]:
        raise ValueError("tool order must be graphify then jevify")
    if data["comparison_start_mode"] != "warm":
        raise ValueError("comparison start mode must be warm")
    route = _string(data["jevify_update_route"], "jevify_update_route")
    if route not in {"already_current", "graphify_handoff"}:
        raise ValueError("update route is invalid")
    if data["structural_engine"] != "graphify":
        raise ValueError("structural engine must be graphify")
    memory_mode = _string(data["memory_mode"], "memory_mode")
    if memory_mode not in {"graph_only", "reviewed_memory"}:
        raise ValueError("memory mode is invalid")
    memory_value = _string(data["memory_value"], "memory_value")
    if memory_value not in {"not_tested", "helpful", "not_helpful"}:
        raise ValueError("memory value is invalid")
    if memory_mode == "graph_only" and memory_value != "not_tested":
        raise ValueError("graph-only memory value must be not_tested")
    if memory_mode == "reviewed_memory" and memory_value == "not_tested":
        raise ValueError("reviewed memory must be rated")
    claim_status = _string(data["comparative_claim_status"], "comparative_claim_status")
    if claim_status not in {"not_made", "supported", "unsupported"}:
        raise ValueError("comparative claim status is invalid")
    graphify_rating = _integer(data["graphify_usefulness"], "graphify_usefulness")
    jevify_rating = _integer(data["jevify_usefulness"], "jevify_usefulness")
    if graphify_rating not in range(1, 6) or jevify_rating not in range(1, 6):
        raise ValueError("rating must be between 1 and 5")
    preferred = _string(data["preferred_next"], "preferred_next")
    if preferred not in {"graphify", "jevify", "neither"}:
        raise ValueError("preferred_next is invalid")
    paid = _integer(data["paid_request_count"], "paid_request_count")
    if paid < 0:
        raise ValueError("paid request count cannot be negative")
    graphify_start_graph = _hex(
        data["graphify_start_graph_sha256"], "graphify_start_graph_sha256", HEX64
    )
    jevify_start_graph = _hex(
        data["jevify_start_graph_sha256"], "jevify_start_graph_sha256", HEX64
    )
    graphify_start_manifest = _hex(
        data["graphify_start_manifest_sha256"], "graphify_start_manifest_sha256", HEX64
    )
    jevify_start_manifest = _hex(
        data["jevify_start_manifest_sha256"], "jevify_start_manifest_sha256", HEX64
    )
    graphify_diff = _hex(data["graphify_diff_sha256"], "graphify_diff_sha256", HEX64)
    jevify_diff = _hex(data["jevify_diff_sha256"], "jevify_diff_sha256", HEX64)
    if graphify_start_graph != jevify_start_graph:
        raise ValueError("starting graph hashes differ between conditions")
    if graphify_start_manifest != jevify_start_manifest:
        raise ValueError("starting manifest hashes differ between conditions")
    if graphify_diff != jevify_diff:
        raise ValueError("applied diff hashes differ between conditions")
    return SmokeReceipt(
        operator_id="operator-01",
        tool_order=("graphify", "jevify"),
        recorded_at=_timestamp(data["recorded_at"], "recorded_at"),
        candidate_commit=_hex(data["candidate_commit"], "candidate_commit", HEX40),
        comparison_start_mode="warm",
        target_resolution_correct=_bool(
            data["target_resolution_correct"], "target_resolution_correct"
        ),
        jevify_update_route=cast(UpdateRoute, route),
        structural_engine="graphify",
        memory_mode=cast(MemoryMode, memory_mode),
        memory_value=cast(MemoryValue, memory_value),
        attribution_correct=_bool(data["attribution_correct"], "attribution_correct"),
        comparative_claim_status=cast(ComparativeClaimStatus, claim_status),
        freshness_correct=_bool(data["freshness_correct"], "freshness_correct"),
        update_correct=_bool(data["update_correct"], "update_correct"),
        graphify_usefulness=graphify_rating,
        jevify_usefulness=jevify_rating,
        preferred_next=cast(Preference, preferred),
        jevify_only_novel_source_verified=_bool(
            data["jevify_only_novel_source_verified"],
            "jevify_only_novel_source_verified",
        ),
        paid_request_count=paid,
        graphify_run_sha256=_hex(data["graphify_run_sha256"], "graphify_run_sha256", HEX64),
        jevify_run_sha256=_hex(data["jevify_run_sha256"], "jevify_run_sha256", HEX64),
        graphify_start_graph_sha256=graphify_start_graph,
        jevify_start_graph_sha256=jevify_start_graph,
        graphify_start_manifest_sha256=graphify_start_manifest,
        jevify_start_manifest_sha256=jevify_start_manifest,
        graphify_diff_sha256=graphify_diff,
        jevify_diff_sha256=jevify_diff,
    )


def load_receipt_bundle(path: Path) -> SmokeReceipt:
    path = _private_directory(path)
    return _parse_receipt(_object(_private_file_bytes(path / "receipt.json")))


def score(
    receipt: SmokeReceipt | None, *, validation_failure_count: int = 0
) -> SmokeScore:
    if receipt is None or validation_failure_count:
        return SmokeScore(
            completed=False,
            comparison_start_mode=None,
            target_resolution_correct=False,
            jevify_update_route=None,
            structural_engine=None,
            graphify_usefulness=None,
            jevify_usefulness=None,
            preferred_next=None,
            novel_source_verified=False,
            memory_mode=None,
            memory_value=None,
            attribution_correct=False,
            comparative_claim_status=None,
            known_false_freshness=0,
            known_false_update=0,
            known_paid_requests=0,
            validation_failure_count=max(validation_failure_count, 1),
            decision="invalid_smoke",
        )
    false_freshness = int(not receipt.freshness_correct)
    false_update = int(not receipt.update_correct)
    invalid_memory_pair = (
        receipt.memory_mode == "graph_only" and receipt.memory_value != "not_tested"
    ) or (
        receipt.memory_mode == "reviewed_memory" and receipt.memory_value == "not_tested"
    )
    if (
        false_freshness
        or false_update
        or receipt.paid_request_count
        or invalid_memory_pair
        or not receipt.target_resolution_correct
        or not receipt.attribution_correct
        or receipt.comparative_claim_status == "unsupported"
    ):
        decision: Decision = "invalid_smoke"
    elif (
        receipt.preferred_next == "jevify"
        and receipt.jevify_usefulness >= 4
        and receipt.jevify_usefulness > receipt.graphify_usefulness
        and receipt.jevify_only_novel_source_verified
        and receipt.memory_mode == "reviewed_memory"
        and receipt.memory_value == "helpful"
    ):
        decision = "proceed_to_external_validation"
    elif (
        receipt.preferred_next == "jevify"
        and receipt.jevify_usefulness >= 4
        and receipt.jevify_usefulness > receipt.graphify_usefulness
        and receipt.jevify_only_novel_source_verified
        and receipt.memory_mode == "graph_only"
    ):
        decision = "proceed_to_memory_smoke"
    else:
        decision = "revise_or_extension"
    return SmokeScore(
        completed=True,
        comparison_start_mode=receipt.comparison_start_mode,
        target_resolution_correct=receipt.target_resolution_correct,
        jevify_update_route=receipt.jevify_update_route,
        structural_engine=receipt.structural_engine,
        graphify_usefulness=receipt.graphify_usefulness,
        jevify_usefulness=receipt.jevify_usefulness,
        preferred_next=receipt.preferred_next,
        novel_source_verified=receipt.jevify_only_novel_source_verified,
        memory_mode=receipt.memory_mode,
        memory_value=receipt.memory_value,
        attribution_correct=receipt.attribution_correct,
        comparative_claim_status=receipt.comparative_claim_status,
        known_false_freshness=false_freshness,
        known_false_update=false_update,
        known_paid_requests=receipt.paid_request_count,
        validation_failure_count=0,
        decision=decision,
    )


def serialize_score(result: SmokeScore) -> str:
    return json.dumps(asdict(result), sort_keys=True, separators=(",", ":"))


def _markdown(result: SmokeScore) -> str:
    return (
        "# Jevify operator smoke test\n\n"
        f"- Decision: `{result.decision}`\n"
        f"- Completed: {str(result.completed).lower()}\n"
        f"- Comparison start: {result.comparison_start_mode}\n"
        f"- Target resolution correct: {str(result.target_resolution_correct).lower()}\n"
        f"- Jevify update route: {result.jevify_update_route}\n"
        f"- Structural engine: {result.structural_engine}\n"
        f"- Graphify usefulness: {result.graphify_usefulness}\n"
        f"- Jevify usefulness: {result.jevify_usefulness}\n"
        f"- Preferred next: {result.preferred_next}\n"
        f"- Jevify-only source-verified value: {str(result.novel_source_verified).lower()}\n"
        f"- Memory mode/value: {result.memory_mode}/{result.memory_value}\n"
        f"- Attribution correct: {str(result.attribution_correct).lower()}\n"
        f"- Comparative claim status: {result.comparative_claim_status}\n"
        f"- Known false freshness/update claims: "
        f"{result.known_false_freshness}/{result.known_false_update}\n"
        f"- Known paid requests: {result.known_paid_requests}\n"
        f"- Validation failures: {result.validation_failure_count}\n"
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate")
    validate.add_argument("--bundle", type=Path, required=True)
    score_command = commands.add_parser("score")
    score_command.add_argument("--bundle", type=Path, required=True)
    score_command.add_argument("--json", type=Path, required=True)
    score_command.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        receipt = load_receipt_bundle(args.bundle)
        if args.command == "validate":
            result = score(receipt)
            if result.decision == "invalid_smoke":
                raise ValueError("unsafe or misattributed smoke evidence recorded")
            print("operator smoke receipt valid; 0 private-field violations; 0 paid requests")
            return 0
        result = score(receipt)
    except (OSError, ValueError) as exc:
        if args.command != "score":
            parser.error(str(exc))
        result = score(None, validation_failure_count=1)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(asdict(result), indent=2, sort_keys=True) + "\n")
    args.markdown.write_text(_markdown(result), encoding="utf-8")
    print(result.decision)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

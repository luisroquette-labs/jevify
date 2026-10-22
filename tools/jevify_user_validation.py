"""Validate private Jevify user-test receipts and publish aggregate decisions."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal, Sequence, cast


Tool = Literal["graphify", "jevify"]
Preference = Literal["graphify", "jevify", "neither"]
Decision = Literal["continue_product", "graphify_extension", "insufficient_evidence"]
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
FORBIDDEN_PRIVATE_FIELDS = frozenset(
    {"name", "email", "repo_path", "question", "prompt", "source", "memory", "credential"}
)

INITIAL_FIELDS = frozenset(
    {
        "schema_version",
        "stage",
        "participant_id",
        "eligible",
        "conflicted",
        "tool_order",
        "initial_at",
        "initial_commit",
        "freshness_correct",
        "update_correct",
        "graphify_usefulness",
        "jevify_usefulness",
        "freshness_trust",
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
TERMINAL_FIELDS = frozenset(
    {
        "schema_version",
        "stage",
        "participant_id",
        "observed_at",
        "repeat_at",
        "later_commit",
        "repeat_used",
        "repeat_without_reminder",
        "reminder_sent",
        "paid_request_count",
        "repeat_run_sha256",
        "initial_record_sha256",
    }
)


@dataclass(frozen=True)
class InitialRecord:
    participant_id: str
    eligible: bool
    conflicted: bool
    tool_order: tuple[Tool, Tool]
    initial_at: datetime
    initial_commit: str
    freshness_correct: bool
    update_correct: bool
    graphify_usefulness: int
    jevify_usefulness: int
    freshness_trust: int
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
class TerminalRecord:
    participant_id: str
    observed_at: datetime
    repeat_at: datetime | None
    later_commit: str | None
    repeat_used: bool
    repeat_without_reminder: bool
    reminder_sent: bool
    paid_request_count: int
    repeat_run_sha256: str | None
    initial_record_sha256: str


@dataclass(frozen=True)
class ParticipantReceipt:
    initial: InitialRecord
    terminal: TerminalRecord

    @property
    def participant_id(self) -> str:
        return self.initial.participant_id


@dataclass(frozen=True)
class ValidationScore:
    completed: int
    prefer_jevify: int
    repeated_jevify: int
    novel_source_verified: int
    known_false_freshness: int
    known_false_update: int
    known_paid_requests: int
    safety_failure_participant_ids: tuple[str, ...]
    invalid_participant_ids: tuple[str, ...]
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


def _object(raw: bytes, *, stage: str) -> dict[str, object]:
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid {stage} JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{stage} record must be an object")
    for key in value:
        if str(key).casefold() in FORBIDDEN_PRIVATE_FIELDS:
            raise ValueError(f"forbidden private field: {key}")
    expected = INITIAL_FIELDS if stage == "initial" else TERMINAL_FIELDS
    unknown = set(value) - expected
    missing = expected - set(value)
    if unknown:
        raise ValueError(f"unknown {stage} field: {sorted(unknown)[0]}")
    if missing:
        raise ValueError(f"missing {stage} field: {sorted(missing)[0]}")
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
    return parsed.astimezone(timezone.utc)


def _optional_timestamp(value: object, field: str) -> datetime | None:
    return None if value is None else _timestamp(value, field)


def _hex(value: object, field: str, pattern: re.Pattern[str]) -> str:
    text = _string(value, field)
    if pattern.fullmatch(text) is None:
        raise ValueError(f"{field} has invalid lowercase hexadecimal format")
    return text


def _optional_hex(value: object, field: str, pattern: re.Pattern[str]) -> str | None:
    return None if value is None else _hex(value, field, pattern)


def _parse_initial(data: dict[str, object]) -> InitialRecord:
    if data["schema_version"] != 1 or data["stage"] != "initial":
        raise ValueError("invalid initial schema version or stage")
    participant_id = _string(data["participant_id"], "participant_id")
    if re.fullmatch(r"p0[1-5]", participant_id) is None:
        raise ValueError("participant_id must be p01 through p05")
    eligible = _bool(data["eligible"], "eligible")
    conflicted = _bool(data["conflicted"], "conflicted")
    if not eligible:
        raise ValueError("participant is not eligible")
    if conflicted:
        raise ValueError("participant is conflicted")
    order = data["tool_order"]
    if (
        not isinstance(order, list)
        or len(order) != 2
        or not all(isinstance(tool, str) for tool in order)
        or tuple(order) not in {("graphify", "jevify"), ("jevify", "graphify")}
    ):
        raise ValueError("tool order must contain graphify and jevify exactly once")
    ratings = {
        field: _integer(data[field], field)
        for field in ("graphify_usefulness", "jevify_usefulness", "freshness_trust")
    }
    if any(value not in range(1, 6) for value in ratings.values()):
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
    return InitialRecord(
        participant_id=participant_id,
        eligible=eligible,
        conflicted=conflicted,
        tool_order=(cast(Tool, order[0]), cast(Tool, order[1])),
        initial_at=_timestamp(data["initial_at"], "initial_at"),
        initial_commit=_hex(data["initial_commit"], "initial_commit", HEX40),
        freshness_correct=_bool(data["freshness_correct"], "freshness_correct"),
        update_correct=_bool(data["update_correct"], "update_correct"),
        graphify_usefulness=ratings["graphify_usefulness"],
        jevify_usefulness=ratings["jevify_usefulness"],
        freshness_trust=ratings["freshness_trust"],
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


def _parse_terminal(data: dict[str, object], initial: InitialRecord) -> TerminalRecord:
    if data["schema_version"] != 1 or data["stage"] != "terminal":
        raise ValueError("invalid terminal schema version or stage")
    participant_id = _string(data["participant_id"], "participant_id")
    if participant_id != initial.participant_id:
        raise ValueError("participant IDs do not match")
    observed_at = _timestamp(data["observed_at"], "observed_at")
    if observed_at < initial.initial_at + timedelta(days=7):
        raise ValueError("observation occurred before the seven-day boundary")
    repeat_used = _bool(data["repeat_used"], "repeat_used")
    repeat_without_reminder = _bool(data["repeat_without_reminder"], "repeat_without_reminder")
    reminder_sent = _bool(data["reminder_sent"], "reminder_sent")
    repeat_at = _optional_timestamp(data["repeat_at"], "repeat_at")
    later_commit = _optional_hex(data["later_commit"], "later_commit", HEX40)
    repeat_hash = _optional_hex(data["repeat_run_sha256"], "repeat_run_sha256", HEX64)
    if reminder_sent or (repeat_used and not repeat_without_reminder):
        raise ValueError("reminder-contaminated repeat is invalid")
    if repeat_used:
        if repeat_at is None or repeat_hash is None:
            raise ValueError("repeat run timestamp and hash are required")
        if later_commit is None or later_commit == initial.initial_commit:
            raise ValueError("later commit must differ from the initial commit")
        if not initial.initial_at < repeat_at <= initial.initial_at + timedelta(days=7):
            raise ValueError("repeat timestamp is outside the seven-day window")
    elif any(value is not None for value in (repeat_at, later_commit, repeat_hash)):
        raise ValueError("unused repeat fields must be null")
    elif repeat_without_reminder:
        raise ValueError("repeat_without_reminder requires repeat use")
    paid = _integer(data["paid_request_count"], "paid_request_count")
    if paid < 0:
        raise ValueError("paid request count cannot be negative")
    return TerminalRecord(
        participant_id=participant_id,
        observed_at=observed_at,
        repeat_at=repeat_at,
        later_commit=later_commit,
        repeat_used=repeat_used,
        repeat_without_reminder=repeat_without_reminder,
        reminder_sent=reminder_sent,
        paid_request_count=paid,
        repeat_run_sha256=repeat_hash,
        initial_record_sha256=_hex(
            data["initial_record_sha256"], "initial_record_sha256", HEX64
        ),
    )


def _private_bundle_path(path: Path) -> Path:
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


def load_initial_record(path: Path) -> InitialRecord:
    path = _private_bundle_path(path)
    return _parse_initial(_object(_private_file_bytes(path / "initial.json"), stage="initial"))


def load_receipt_bundle(path: Path) -> ParticipantReceipt:
    path = _private_bundle_path(path)
    initial_bytes = _private_file_bytes(path / "initial.json")
    terminal_bytes = _private_file_bytes(path / "terminal.json")
    initial = _parse_initial(_object(initial_bytes, stage="initial"))
    terminal = _parse_terminal(_object(terminal_bytes, stage="terminal"), initial)
    if terminal.initial_record_sha256 != hashlib.sha256(initial_bytes).hexdigest():
        raise ValueError("initial record hash does not match terminal record")
    return ParticipantReceipt(initial=initial, terminal=terminal)


def score(
    receipts: Sequence[ParticipantReceipt],
    *,
    invalid_participant_ids: Sequence[str] = (),
    validation_failure_count: int = 0,
) -> ValidationScore:
    ordered = sorted(receipts, key=lambda receipt: receipt.participant_id)
    unique_ids = {receipt.participant_id for receipt in ordered}
    safety_failures = tuple(
        receipt.participant_id
        for receipt in ordered
        if not receipt.initial.freshness_correct or not receipt.initial.update_correct
    )
    paid_requests = sum(
        receipt.initial.paid_request_count + receipt.terminal.paid_request_count
        for receipt in ordered
    )
    prefer = sum(receipt.initial.preferred_next == "jevify" for receipt in ordered)
    repeated = sum(
        receipt.terminal.repeat_used
        and receipt.terminal.repeat_without_reminder
        and not receipt.terminal.reminder_sent
        for receipt in ordered
    )
    novel = sum(receipt.initial.jevify_only_novel_source_verified for receipt in ordered)
    complete = len(ordered) == 5 and len(unique_ids) == 5
    invalid_ids = tuple(sorted(set(invalid_participant_ids)))
    failure_count = max(validation_failure_count, len(invalid_ids))
    if not complete or safety_failures or paid_requests or failure_count:
        decision: Decision = "insufficient_evidence"
    elif prefer >= 3 and repeated >= 3 and novel >= 2:
        decision = "continue_product"
    else:
        decision = "graphify_extension"
    return ValidationScore(
        completed=len(unique_ids),
        prefer_jevify=prefer,
        repeated_jevify=repeated,
        novel_source_verified=novel,
        known_false_freshness=sum(
            not receipt.initial.freshness_correct for receipt in ordered
        ),
        known_false_update=sum(not receipt.initial.update_correct for receipt in ordered),
        known_paid_requests=paid_requests,
        safety_failure_participant_ids=safety_failures,
        invalid_participant_ids=invalid_ids,
        validation_failure_count=failure_count,
        decision=decision,
    )


def serialize_score(result: ValidationScore) -> str:
    return json.dumps(asdict(result), sort_keys=True, separators=(",", ":"))


def _load_manifest(
    path: Path, *, tolerate_receipt_errors: bool = False
) -> tuple[list[ParticipantReceipt], tuple[str, ...]]:
    try:
        parent_metadata = path.parent.lstat()
    except OSError as exc:
        raise ValueError(f"missing manifest directory: {path.parent}") from exc
    if stat.S_ISLNK(parent_metadata.st_mode) or not stat.S_ISDIR(parent_metadata.st_mode):
        raise ValueError("manifest parent must be a real directory")
    if stat.S_IMODE(parent_metadata.st_mode) != 0o700:
        raise ValueError("unsafe manifest directory permissions: expected mode 0700")
    raw = _private_file_bytes(path)
    try:
        manifest = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid manifest JSON") from exc
    if not isinstance(manifest, dict) or set(manifest) != {
        "schema_version",
        "candidate_commit",
        "session_date",
        "participants",
    }:
        raise ValueError("manifest fields do not match the frozen contract")
    if manifest["schema_version"] != 1:
        raise ValueError("unsupported manifest schema version")
    candidate_commit = _hex(manifest["candidate_commit"], "candidate_commit", HEX40)
    session_date = _string(manifest["session_date"], "session_date")
    try:
        datetime.strptime(session_date, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("session_date must use YYYY-MM-DD") from exc
    participants = manifest["participants"]
    if not isinstance(participants, list) or len(participants) != 5:
        raise ValueError("manifest must contain exactly five participants")
    expected_orders = [
        ["graphify", "jevify"],
        ["jevify", "graphify"],
        ["graphify", "jevify"],
        ["jevify", "graphify"],
        ["graphify", "jevify"],
    ]
    receipts = []
    invalid_participant_ids = []
    for index, entry in enumerate(participants, start=1):
        if not isinstance(entry, dict) or set(entry) != {
            "participant_id",
            "eligibility_evidence",
            "tool_order",
        }:
            raise ValueError("participant manifest entry is invalid")
        participant_id = f"p{index:02d}"
        if entry["participant_id"] != participant_id:
            raise ValueError("manifest participant IDs must be p01 through p05 in order")
        eligibility_evidence = _string(
            entry["eligibility_evidence"], "eligibility_evidence"
        )
        if eligibility_evidence not in (
            "prior_real_repository_use",
            "active_graphify_evaluation",
        ):
            raise ValueError(f"invalid eligibility evidence for {participant_id}")
        if entry["tool_order"] != expected_orders[index - 1]:
            raise ValueError(f"invalid frozen tool order for {participant_id}")
        try:
            receipt = load_receipt_bundle(path.parent / participant_id)
        except ValueError as exc:
            if tolerate_receipt_errors:
                invalid_participant_ids.append(participant_id)
                continue
            raise ValueError(f"{participant_id}: {exc}") from exc
        try:
            if list(receipt.initial.tool_order) != entry["tool_order"]:
                raise ValueError(f"receipt tool order differs from manifest for {participant_id}")
            if receipt.initial.initial_commit != candidate_commit:
                raise ValueError(f"receipt commit differs from manifest for {participant_id}")
        except ValueError:
            if tolerate_receipt_errors:
                invalid_participant_ids.append(participant_id)
                continue
            raise
        receipts.append(receipt)
    return receipts, tuple(invalid_participant_ids)


def _markdown(result: ValidationScore) -> str:
    return (
        "# Jevify five-user validation\n\n"
        f"- Decision: `{result.decision}`\n"
        f"- Completed: {result.completed}/5\n"
        f"- Prefer Jevify: {result.prefer_jevify}/5\n"
        f"- Reused Jevify: {result.repeated_jevify}/5\n"
        f"- Novel source-verified outcomes: {result.novel_source_verified}/5\n"
        "- Known false freshness/update claims among valid receipts: "
        f"{result.known_false_freshness}/{result.known_false_update}\n"
        f"- Known paid requests among valid receipts: {result.known_paid_requests}\n"
        f"- Validation failures: {result.validation_failure_count}\n"
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    validate_initial = commands.add_parser("validate-initial")
    validate_initial.add_argument("--bundle", type=Path, required=True)
    validate = commands.add_parser("validate")
    validate.add_argument("--manifest", type=Path, required=True)
    score_command = commands.add_parser("score")
    score_command.add_argument("--manifest", type=Path, required=True)
    score_command.add_argument("--json", type=Path, required=True)
    score_command.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "validate-initial":
            initial = load_initial_record(args.bundle)
            if not initial.freshness_correct or not initial.update_correct:
                raise ValueError(f"{initial.participant_id}: false freshness or update claim")
            if initial.paid_request_count:
                raise ValueError(f"{initial.participant_id}: paid request recorded")
            print(
                f"{initial.participant_id} initial receipt valid; "
                "0 private-field violations; 0 paid requests"
            )
            return 0
        if args.command == "score":
            try:
                receipts, invalid_ids = _load_manifest(
                    args.manifest, tolerate_receipt_errors=True
                )
                result = score(
                    receipts,
                    invalid_participant_ids=invalid_ids,
                    validation_failure_count=len(invalid_ids),
                )
            except (OSError, ValueError):
                result = score((), validation_failure_count=1)
            args.json.parent.mkdir(parents=True, exist_ok=True)
            args.json.write_text(json.dumps(asdict(result), indent=2, sort_keys=True) + "\n")
            args.markdown.write_text(_markdown(result), encoding="utf-8")
            print(result.decision)
            return 0
        receipts, _invalid_ids = _load_manifest(args.manifest)
        if args.command == "validate":
            result = score(receipts)
            if result.safety_failure_participant_ids:
                raise ValueError(
                    "round-ending participant failures: "
                    + ", ".join(result.safety_failure_participant_ids)
                )
            if result.known_paid_requests:
                affected = [
                    receipt.participant_id
                    for receipt in receipts
                    if receipt.initial.paid_request_count or receipt.terminal.paid_request_count
                ]
                raise ValueError("paid request recorded for: " + ", ".join(affected))
            print("5 valid receipts; 0 private-field violations; 0 paid requests")
            return 0
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

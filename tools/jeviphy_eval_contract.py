"""Immutable input contract for the Jeviphy v2 benchmark."""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Literal


STRATUM_COUNTS = {
    "valid_source": 40,
    "stale_source": 20,
    "no_source": 40,
    "ambiguous": 20,
}
Stratum = Literal["valid_source", "stale_source", "no_source", "ambiguous"]
_SHA = re.compile(r"[0-9a-f]{40}")


@dataclass(frozen=True)
class MemoryEvidence:
    summary: str
    source_paths: tuple[str, ...]
    source_commit: str | None
    reviewed_at: str | None


@dataclass(frozen=True)
class EvalCase:
    id: str
    repo_id: str
    stratum: Stratum
    question: str
    oracle_argv: tuple[str, ...]
    timeout_seconds: int
    gold_files: tuple[str, ...]
    gold_symbols: tuple[str, ...]
    memory: MemoryEvidence
    holdout: bool


@dataclass(frozen=True)
class RepoPin:
    id: str
    url: str
    commit: str
    language: str
    license: str


@dataclass(frozen=True)
class EvalManifest:
    schema_version: int
    graphify_commit: str
    repos: tuple[RepoPin, ...]
    cases: tuple[EvalCase, ...]


def _exact_keys(data: dict, expected: set[str], location: str) -> None:
    if set(data) != expected:
        raise ValueError(f"{location} fields differ from contract")


def _string(value: object, location: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise ValueError(f"{location} must be a non-empty string")
    return value


def _sha(value: object, location: str) -> str:
    text = _string(value, location)
    if not _SHA.fullmatch(text):
        raise ValueError(f"{location} must be 40 lowercase hex characters")
    return text


def _path(value: object, location: str) -> str:
    text = _string(value, location)
    parsed = PurePosixPath(text)
    if parsed.is_absolute() or ".." in parsed.parts or text in {".", ""} or "\\" in text:
        raise ValueError(f"{location} must be a safe relative POSIX path")
    return text


def _string_tuple(value: object, location: str, *, paths: bool = False) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{location} must be a list")
    convert = _path if paths else _string
    items = tuple(convert(item, f"{location} item") for item in value)
    if len(items) != len(set(items)):
        raise ValueError(f"{location} contains duplicates")
    return items


def _memory(data: object, case_id: str) -> MemoryEvidence:
    if not isinstance(data, dict):
        raise ValueError(f"case {case_id} memory must be an object")
    _exact_keys(data, {"summary", "source_paths", "source_commit", "reviewed_at"}, "memory")
    source_commit = data["source_commit"]
    reviewed_at = data["reviewed_at"]
    if source_commit is not None:
        source_commit = _sha(source_commit, "memory source commit")
    if reviewed_at is not None:
        reviewed_at = _string(reviewed_at, "memory reviewed_at")
    return MemoryEvidence(
        summary=_string(data["summary"], "memory summary", allow_empty=True),
        source_paths=_string_tuple(data["source_paths"], "memory source_paths", paths=True),
        source_commit=source_commit,
        reviewed_at=reviewed_at,
    )


def _repo(data: object) -> RepoPin:
    if not isinstance(data, dict):
        raise ValueError("repository must be an object")
    _exact_keys(data, {"id", "url", "commit", "language", "license"}, "repository")
    url = _string(data["url"], "repository URL")
    if not url.startswith("https://github.com/"):
        raise ValueError("repository URL must be an immutable GitHub source")
    return RepoPin(
        id=_string(data["id"], "repository ID"),
        url=url,
        commit=_sha(data["commit"], "repository commit"),
        language=_string(data["language"], "repository language"),
        license=_string(data["license"], "repository license"),
    )


def _case(data: object) -> EvalCase:
    if not isinstance(data, dict):
        raise ValueError("case must be an object")
    _exact_keys(
        data,
        {
            "id", "repo_id", "stratum", "question", "oracle_argv", "timeout_seconds",
            "gold_files", "gold_symbols", "memory", "holdout",
        },
        "case",
    )
    case_id = _string(data["id"], "case ID")
    stratum = data["stratum"]
    if stratum not in STRATUM_COUNTS:
        raise ValueError(f"case {case_id} has invalid stratum")
    timeout = data["timeout_seconds"]
    if isinstance(timeout, bool) or not isinstance(timeout, int) or not 0 < timeout <= 1800:
        raise ValueError(f"case {case_id} timeout must be between 1 and 1800 seconds")
    holdout = data["holdout"]
    if not isinstance(holdout, bool):
        raise ValueError(f"case {case_id} holdout must be boolean")
    oracle = _string_tuple(data["oracle_argv"], f"case {case_id} oracle_argv")
    if not oracle:
        raise ValueError("oracle command is required")
    memory = _memory(data["memory"], case_id)
    if stratum == "no_source" and (memory.source_paths or memory.source_commit):
        raise ValueError(f"case {case_id} no_source evidence must be empty")
    return EvalCase(
        id=case_id,
        repo_id=_string(data["repo_id"], f"case {case_id} repo_id"),
        stratum=stratum,
        question=_string(data["question"], f"case {case_id} question"),
        oracle_argv=oracle,
        timeout_seconds=timeout,
        gold_files=_string_tuple(data["gold_files"], f"case {case_id} gold_files", paths=True),
        gold_symbols=_string_tuple(data["gold_symbols"], f"case {case_id} gold_symbols"),
        memory=memory,
        holdout=holdout,
    )


def validate_manifest(manifest: EvalManifest) -> None:
    if manifest.schema_version != 2:
        raise ValueError("schema_version must be 2")
    if len(manifest.repos) < 6:
        raise ValueError("at least 6 repositories are required")
    if len({repo.language.casefold() for repo in manifest.repos}) < 3:
        raise ValueError("at least 3 languages are required")
    repo_ids = [repo.id for repo in manifest.repos]
    if len(repo_ids) != len(set(repo_ids)):
        raise ValueError("duplicate repository ID")
    case_ids = [case.id for case in manifest.cases]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("duplicate case ID")
    if Counter(case.stratum for case in manifest.cases) != STRATUM_COUNTS:
        raise ValueError("case strata differ from the frozen 120-case contract")
    unknown_repos = {case.repo_id for case in manifest.cases} - set(repo_ids)
    if unknown_repos:
        raise ValueError("case references unknown repository")
    holdout_repos = {case.repo_id for case in manifest.cases if case.holdout}
    for repo_id in holdout_repos:
        if any(case.repo_id == repo_id and not case.holdout for case in manifest.cases):
            raise ValueError("holdout repository cannot mix visible and hidden cases")
    if not holdout_repos or sum(case.holdout for case in manifest.cases) < 20:
        raise ValueError("holdout needs at least 20 cases")
    for case in manifest.cases:
        searchable = f"{case.question} {case.memory.summary}".casefold()
        for symbol in case.gold_symbols:
            normalized = symbol.removesuffix("()").lstrip(".").casefold()
            if normalized and normalized in searchable:
                raise ValueError(f"gold symbol leaked into case {case.id}")


def load_manifest(path: Path) -> EvalManifest:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("manifest must be an object")
    _exact_keys(data, {"schema_version", "graphify_commit", "repos", "cases"}, "manifest")
    if not isinstance(data["repos"], list) or not isinstance(data["cases"], list):
        raise ValueError("manifest repos and cases must be lists")
    manifest = EvalManifest(
        schema_version=data["schema_version"],
        graphify_commit=_sha(data["graphify_commit"], "Graphify commit"),
        repos=tuple(_repo(item) for item in data["repos"]),
        cases=tuple(_case(item) for item in data["cases"]),
    )
    validate_manifest(manifest)
    return manifest

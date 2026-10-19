"""Paired, resume-safe Jeviphy product evaluation primitives."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

from graphify.serve import _read_graph
from tools.jev_memory_pilot import candidate_pool
from tools.jeviphy_eval_contract import EvalCase
from tools.jeviphy_provenance import classify_source_evidence


@dataclass(frozen=True)
class RunPins:
    manifest_sha256: str
    graphify_commit: str
    jeviphy_commit: str
    python_version: str
    command_sha256: str


@dataclass(frozen=True)
class ArmRecord:
    arm: str
    status: str
    success: bool
    duration_ms: float
    output_sha256: str
    error_sha256: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    top5_hits: int | None = None
    first_hit: bool | None = None


@dataclass(frozen=True)
class PairRecord:
    case_id: str
    stratum: str
    pass_index: int
    order: tuple[str, str]
    graph_sha256: str
    baseline: ArmRecord
    jeviphy: ArmRecord

    @property
    def complete(self) -> bool:
        return bool(self.baseline.status and self.jeviphy.status)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def command_sha256(argv: Sequence[str]) -> str:
    return sha256_bytes(json.dumps(list(argv), separators=(",", ":")).encode())


def current_pins(manifest: Path, graphify_commit: str, repo: Path, argv: Sequence[str]) -> RunPins:
    if subprocess.check_output(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=repo, text=True
    ).strip():
        raise ValueError("Jeviphy checkout must be clean before a benchmark run")
    jeviphy_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    return RunPins(
        manifest_sha256=file_sha256(manifest),
        graphify_commit=graphify_commit,
        jeviphy_commit=jeviphy_commit,
        python_version=platform.python_version(),
        command_sha256=command_sha256(argv),
    )


def balanced_order(case_index: int, pass_index: int) -> tuple[str, str]:
    return ("graphify", "jeviphy") if (case_index + pass_index) % 2 == 0 else (
        "jeviphy",
        "graphify",
    )


def run_command_arm(
    arm: str,
    argv: Sequence[str],
    cwd: Path,
    timeout_seconds: int,
    *,
    env: dict[str, str] | None = None,
) -> ArmRecord:
    started = time.perf_counter_ns()
    try:
        result = subprocess.run(
            list(argv),
            cwd=cwd,
            capture_output=True,
            timeout=timeout_seconds,
            env=env,
        )
        status = "completed" if result.returncode == 0 else "failed"
        success = result.returncode == 0
        stdout, stderr = result.stdout, result.stderr
    except subprocess.TimeoutExpired as error:
        status, success = "timeout", False
        stdout = error.stdout or b""
        stderr = error.stderr or b""
    return ArmRecord(
        arm=arm,
        status=status,
        success=success,
        duration_ms=(time.perf_counter_ns() - started) / 1_000_000,
        output_sha256=sha256_bytes(stdout),
        error_sha256=sha256_bytes(stderr),
    )


def validate_live_limits(*, allow_network_agent: bool, max_agent_calls: int, max_cost_usd: float) -> None:
    if allow_network_agent and (max_agent_calls < 1 or max_cost_usd <= 0):
        raise ValueError("network agent requires positive call and cost ceilings")
    if not allow_network_agent and (max_agent_calls or max_cost_usd):
        raise ValueError("cost ceilings require --allow-network-agent")


def append_pair(path: Path, pins: RunPins, pair: PairRecord) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"pins": asdict(pins), "pair": asdict(pair)}
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def completed_pairs(path: Path, pins: RunPins) -> set[tuple[str, int]]:
    if not path.exists():
        return set()
    completed = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        payload = json.loads(line)
        if payload.get("pins") != asdict(pins):
            raise ValueError("run pins differ from journal")
        pair = payload["pair"]
        if not pair["baseline"]["status"] or not pair["jeviphy"]["status"]:
            raise ValueError("journal contains incomplete pair")
        key = (pair["case_id"], pair["pass_index"])
        if key in completed:
            raise ValueError("journal contains duplicate pair")
        completed.add(key)
    return completed


def seal_journal(path: Path, output: Path, pins: RunPins, expected: set[tuple[str, int]]) -> None:
    actual = completed_pairs(path, pins)
    if actual != expected:
        raise ValueError("journal does not contain every expected pair")
    if output.exists():
        raise FileExistsError(output)
    payload = {
        "pins": asdict(pins),
        "journal_sha256": file_sha256(path),
        "records": [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()],
    }
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(payload, stream, sort_keys=True)


def _candidate_record(
    arm: str, started: int, candidates: list[dict], gold_files: Sequence[str]
) -> ArmRecord:
    output = json.dumps(candidates, sort_keys=True, separators=(",", ":")).encode()
    ranked_files = [item.get("source_file") for item in candidates]
    gold = set(gold_files)
    return ArmRecord(
        arm=arm,
        status="completed",
        success=True,
        duration_ms=(time.perf_counter_ns() - started) / 1_000_000,
        output_sha256=sha256_bytes(output),
        error_sha256=sha256_bytes(b""),
        top5_hits=len(gold & set(ranked_files[:5])),
        first_hit=bool(ranked_files and ranked_files[0] in gold),
    )


def _cited_candidates(graph, paths: Sequence[str]) -> list[dict]:
    cited = set(paths)
    node_ids = sorted(
        node_id for node_id, data in graph.nodes(data=True) if data.get("source_file") in cited
    )[:10]
    return [
        {
            "node_id": node_id,
            "label": graph.nodes[node_id].get("label", node_id),
            "type": graph.nodes[node_id].get("type", ""),
            "source_file": graph.nodes[node_id].get("source_file", ""),
            "source_location": graph.nodes[node_id].get("source_location", ""),
            "baseline_rank": rank,
            "source_scoped": True,
        }
        for rank, node_id in enumerate(node_ids, 1)
    ]


def run_retrieval_pair(
    case: EvalCase,
    graph_path: Path,
    repo: Path,
    *,
    pass_index: int,
    order: tuple[str, str],
) -> tuple[PairRecord, dict[str, list[dict]]]:
    before = file_sha256(graph_path)
    graph = _read_graph(str(graph_path))
    results: dict[str, list[dict]] = {}
    records: dict[str, ArmRecord] = {}
    for arm in order:
        started = time.perf_counter_ns()
        if arm == "graphify" or not case.memory.source_paths:
            candidates = candidate_pool(graph_path, repo, case.question, graph=graph)
        else:
            evidence = classify_source_evidence(
                repo, graph, case.memory.source_commit, case.memory.source_paths
            )
            if evidence.usable_paths:
                candidates = candidate_pool(
                    graph_path,
                    repo,
                    case.question,
                    [case.memory.summary],
                    source_paths=list(evidence.usable_paths),
                    fast_source=True,
                    graph=graph,
                )
                if not candidates:
                    candidates = _cited_candidates(graph, evidence.usable_paths)
            else:
                candidates = candidate_pool(graph_path, repo, case.question, graph=graph)
        results[arm] = candidates
        records[arm] = _candidate_record(arm, started, candidates, case.gold_files)
    after = file_sha256(graph_path)
    if after != before:
        raise ValueError("graph changed during retrieval pair")
    return (
        PairRecord(
            case_id=case.id,
            stratum=case.stratum,
            pass_index=pass_index,
            order=order,
            graph_sha256=before,
            baseline=records["graphify"],
            jeviphy=records["jeviphy"],
        ),
        results,
    )

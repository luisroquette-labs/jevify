"""Frozen, offline runner comparison for Jeviphy zero-configuration behavior."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from graphify.serve import _read_graph
from tools.jeviphy_autorun import select_question


@dataclass(frozen=True)
class ZeroConfigScore:
    status: str
    cases: int
    repositories: int
    interaction_required: int
    exact_outputs: int
    exact_matches: int
    measured_pairs: int
    median_overhead_fraction: float | None
    p95_overhead_fraction: float | None
    failed_cases: tuple[str, ...]


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = (len(ordered) - 1) * fraction
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)


def validate_manifest(manifest: dict) -> None:
    repos, cases = manifest.get("repos"), manifest.get("cases")
    if not isinstance(repos, list) or len(repos) < 6:
        raise ValueError("manifest requires at least six repositories")
    if not isinstance(cases, list) or len(cases) != 30:
        raise ValueError("manifest requires exactly 30 cases")
    repo_ids = [item.get("id") for item in repos if isinstance(item, dict)]
    case_ids = [item.get("id") for item in cases if isinstance(item, dict)]
    if len(repo_ids) != len(set(repo_ids)) or len(case_ids) != len(set(case_ids)):
        raise ValueError("manifest IDs must be unique")
    if any(case.get("repo_id") not in repo_ids for case in cases):
        raise ValueError("case references unknown repository")
    required_variants = {"missing_graph", "stale_graph", "corrupt_graph", "repair_failure",
                         "outside_git", "invalid_corpus", "live_missing", "auto_question"}
    if required_variants - {case.get("variant") for case in cases}:
        raise ValueError("manifest is missing required outcome variants")


def score(records: list[dict], manifest: dict) -> ZeroConfigScore:
    validate_manifest(manifest)
    expected = {case["id"]: case for case in manifest["cases"]}
    by_id = {record.get("case_id"): record for record in records}
    if len(by_id) != len(records) or set(by_id) != set(expected):
        return ZeroConfigScore("insufficient_evidence", len(by_id), 6, 0, 0, 0, 0,
                               None, None, tuple(sorted(set(expected) - set(by_id))))
    failed = []
    interaction = 0
    exact_total = exact_matches = 0
    overheads = []
    for case_id, case in expected.items():
        record = by_id[case_id]
        interaction += int(bool(record.get("interaction_required")))
        if record.get("outcome") != case["expected"]:
            failed.append(case_id)
        if case["exact_output"]:
            exact_total += 1
            exact_matches += int(record.get("exact_match") is True)
        if case["timing"]:
            pairs = record.get("pairs", [])
            if len(pairs) != manifest["thresholds"]["measured_pairs"]:
                failed.append(case_id)
            for pair in pairs:
                direct = pair.get("direct_ms", 0)
                jeviphy = pair.get("jeviphy_ms", 0)
                if direct <= 0 or jeviphy <= 0:
                    failed.append(case_id)
                else:
                    overheads.append(jeviphy / direct - 1)
    median = statistics.median(overheads) if overheads else None
    p95 = percentile(overheads, 0.95) if overheads else None
    thresholds = manifest["thresholds"]
    passed = (
        not failed and interaction == 0 and exact_matches == exact_total and overheads
        and median <= thresholds["median_overhead_fraction"]
        and p95 <= thresholds["p95_overhead_fraction"]
    )
    return ZeroConfigScore(
        "pass" if passed else "fail", len(records), len(manifest["repos"]), interaction,
        exact_total, exact_matches, len(overheads), median, p95, tuple(sorted(set(failed))),
    )


def _run(argv: list[str], cwd: Path, env: dict[str, str], timeout: int = 120) -> dict:
    started = time.perf_counter_ns()
    try:
        result = subprocess.run(
            argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL, capture_output=True,
            timeout=timeout,
        )
        status = "completed"
        stdout, stderr, returncode = result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired as exc:
        status = "timeout"
        stdout, stderr, returncode = exc.stdout or b"", exc.stderr or b"", None
    text = (stdout + b"\n" + stderr).decode("utf-8", errors="replace").casefold()
    prompts = ("paste the key", "enter a key", "choose a question", "select a mode")
    return {
        "status": status,
        "returncode": returncode,
        "duration_ms": (time.perf_counter_ns() - started) / 1_000_000,
        "stdout": stdout,
        "stderr": stderr,
        "interaction_required": status == "timeout" or any(item in text for item in prompts),
    }


def _clean_env(blocker: Path) -> dict[str, str]:
    env = os.environ.copy()
    for key in list(env):
        if key.endswith("_API_KEY") or key.startswith("AWS_") or key in {
            "ANTHROPIC_AUTH_TOKEN", "GOOGLE_APPLICATION_CREDENTIALS",
        }:
            env.pop(key, None)
    env["PYTHONHASHSEED"] = "0"
    env["GRAPHIFY_QUERY_LOG_DISABLE"] = "1"
    env["PYTHONPATH"] = str(blocker)
    return env


def _parse_auto_answer(run: dict) -> bytes:
    if run["returncode"] != 0:
        return b""
    try:
        value = json.loads(run["stdout"])["answer"]
    except (KeyError, TypeError, json.JSONDecodeError):
        return b""
    return value.encode("utf-8") if isinstance(value, str) else b""


def _case_workspace(source: Path, variant: str, raw_dir: Path) -> tuple[Path, bool]:
    if variant == "outside_git":
        path = Path(tempfile.mkdtemp(prefix="outside-", dir=raw_dir))
        return path, False
    if variant not in {"missing_graph", "stale_graph", "corrupt_graph", "repair_failure"}:
        return source, False
    path = Path(tempfile.mkdtemp(prefix="repair-", dir=raw_dir))
    path.rmdir()
    subprocess.run(["git", "-C", str(source), "worktree", "add", "-q", "--detach",
                    str(path), "HEAD"], check=True)
    graph = path / "graphify-out/graph.json"
    if variant == "stale_graph":
        graph.parent.mkdir()
        data = json.loads((source / "graphify-out/graph.json").read_text())
        data["built_at_commit"] = "0" * 40
        graph.write_text(json.dumps(data))
    elif variant == "corrupt_graph":
        graph.parent.mkdir()
        graph.write_text("{")
    elif variant == "repair_failure":
        (path / "graphify-out").write_text("blocks output directory")
    return path, True


def run_evaluation(manifest_path: Path, repo_root: Path, output_dir: Path, runner: Path) -> tuple[list[dict], ZeroConfigScore]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_manifest(manifest)
    output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    output_dir.chmod(0o700)
    blocker = output_dir / "network-block"
    blocker.mkdir(exist_ok=True)
    (blocker / "sitecustomize.py").write_text(
        "import socket\n"
        "def blocked(*args, **kwargs): raise OSError('network disabled by evaluation')\n"
        "socket.create_connection = blocked\n"
        "_connect = socket.socket.connect\n"
        "socket.socket.connect = blocked\n"
    )
    env = _clean_env(blocker)
    repos = {item["id"]: item for item in manifest["repos"]}
    for item in manifest["repos"]:
        repo = repo_root / item["directory"]
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
        graph = repo / "graphify-out/graph.json"
        if head != item["commit"] or not graph.is_file() or sha256(graph.read_bytes()) != item["graph_sha256"]:
            raise ValueError(f"frozen repository or graph differs: {item['id']}")
    journal = output_dir / "records.jsonl"
    fd = os.open(journal, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    records = []
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        for index, case in enumerate(manifest["cases"]):
            repo_meta = repos[case["repo_id"]]
            source = repo_root / repo_meta["directory"]
            workspace, disposable = _case_workspace(source, case["variant"], output_dir)
            try:
                graph = workspace / "graphify-out/graph.json"
                question = case["question"]
                selection_ms = None
                if case["variant"] == "auto_question":
                    started = time.perf_counter_ns()
                    question = select_question(_read_graph(str(graph)), graph, None)
                    selection_ms = (time.perf_counter_ns() - started) / 1_000_000
                cwd = workspace
                if case["variant"] == "nested_explicit":
                    cwd = workspace / ".jeviphy-eval-nested"
                    cwd.mkdir(exist_ok=True)
                direct_cmd = [sys.executable, "-m", "graphify", "query", question,
                              "--graph", str(graph)]
                jev_cmd = [sys.executable, str(runner), "auto", "--question", question, "--json"]
                corpus = None
                if case["variant"] == "live_missing":
                    jev_cmd += ["--live", "--approved-paid-use", "--max-requests", "1"]
                elif case["variant"] == "invalid_corpus":
                    corpus = output_dir / f"{case['id']}-corpus.json"
                    corpus.write_text("{}")
                    corpus.chmod(0o600)
                    jev_cmd += ["--corpus", str(corpus)]
                pairs = []
                direct = None
                jeviphy = None
                if case["timing"]:
                    _run(direct_cmd, cwd, env)
                    _run(jev_cmd, cwd, env)
                    for pass_index in range(manifest["thresholds"]["measured_pairs"]):
                        order = ("direct", "jeviphy") if (index + pass_index) % 2 == 0 else (
                            "jeviphy", "direct",
                        )
                        arms = {}
                        for arm in order:
                            arms[arm] = _run(direct_cmd if arm == "direct" else jev_cmd, cwd, env)
                        direct, jeviphy = arms["direct"], arms["jeviphy"]
                        pairs.append({"direct_ms": direct["duration_ms"],
                                      "jeviphy_ms": jeviphy["duration_ms"]})
                else:
                    if case["exact_output"]:
                        direct = _run(direct_cmd, cwd, env)
                    jeviphy = _run(jev_cmd, cwd, env)
                assert jeviphy is not None
                expected_error = case["expected"] == "error"
                successful = jeviphy["returncode"] == 0
                outcome = "error" if not successful else "success"
                exact = None
                if case["exact_output"] and direct is not None:
                    exact = _parse_auto_answer(jeviphy) == direct["stdout"]
                record = {
                    "case_id": case["id"], "repo_id": case["repo_id"],
                    "variant": case["variant"], "outcome": outcome,
                    "expected_error": expected_error, "exact_match": exact,
                    "interaction_required": bool(jeviphy["interaction_required"]),
                    "pairs": pairs, "selection_ms": selection_ms,
                    "question_sha256": sha256(question.encode()),
                    "stdout_sha256": sha256(jeviphy["stdout"]),
                    "stderr_sha256": sha256(jeviphy["stderr"]),
                    "returncode": jeviphy["returncode"],
                }
                records.append(record)
                stream.write(json.dumps(record, sort_keys=True) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            finally:
                if disposable:
                    subprocess.run(["git", "-C", str(source), "worktree", "remove", "--force",
                                    str(workspace)], check=False, capture_output=True)
                    shutil.rmtree(workspace, ignore_errors=True)
    result = score(records, manifest)
    (output_dir / "score.json").write_text(json.dumps(asdict(result), indent=2) + "\n")
    return records, result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--runner", type=Path, required=True)
    args = parser.parse_args()
    _, result = run_evaluation(args.manifest, args.repo_root, args.output_dir, args.runner)
    print(json.dumps(asdict(result), sort_keys=True))
    return 0 if result.status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

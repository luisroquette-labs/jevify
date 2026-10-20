"""Measure Jeviphy clean install, offline query, reinstall, and uninstall."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts" / "install_jeviphy_skill.py"
MATRIX_KEYS = {"schema_version", "attempts"}


@dataclass(frozen=True)
class InstallRecord:
    attempt_id: str
    operating_system: str
    host: str
    jeviphy_commit: str
    success: bool
    seconds: float
    install_stdout_sha256: str
    install_stderr_sha256: str
    query_stdout_sha256: str
    query_stderr_sha256: str
    diagnostic: str | None


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _clean_env(home: Path) -> dict[str, str]:
    env = os.environ.copy()
    for key in list(env):
        if key.endswith("_API_KEY") or key.startswith("AWS_") or key in {
            "ANTHROPIC_AUTH_TOKEN", "GOOGLE_APPLICATION_CREDENTIALS",
        }:
            env.pop(key, None)
    env.update({"HOME": str(home), "GRAPHIFY_QUERY_LOG_DISABLE": "1", "PYTHONHASHSEED": "0"})
    return env


def _fixture(path: Path) -> Path:
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    (path / "app.py").write_text("def run():\n    return 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    subprocess.run(
        ["git", "-c", "user.name=Jeviphy", "-c", "user.email=eval@example.invalid",
         "commit", "-qm", "fixture"],
        cwd=path,
        check=True,
    )
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=path, text=True).strip()
    graph = {
        "directed": False, "multigraph": False, "graph": {},
        "nodes": [{"id": "app.py::run", "label": "run", "type": "function",
                   "community": 0, "source_file": "app.py", "source_location": "L1"}],
        "links": [], "built_at_commit": commit,
    }
    graph_path = path / "graphify-out/graph.json"
    graph_path.parent.mkdir()
    graph_path.write_text(json.dumps(graph), encoding="utf-8")
    return graph_path


def _run(argv: list[str], *, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv,
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=120,
    )


def run_attempt(
    attempt_root: Path,
    *,
    host: str,
    operating_system: str,
    index: int,
    candidate: str,
) -> InstallRecord:
    if host not in {"claude", "codex"}:
        raise ValueError("host must be claude or codex")
    home = attempt_root / "home"
    repo = attempt_root / "repo"
    home.mkdir(parents=True)
    graph = _fixture(repo)
    env = _clean_env(home)
    started = time.perf_counter()
    install_stdout = install_stderr = query_stdout = query_stderr = b""
    diagnostic = None
    success = False
    try:
        install = _run(
            [sys.executable, str(INSTALLER), "install", "--host", host, "--home", str(home)],
            cwd=ROOT,
            env=env,
        )
        install_stdout, install_stderr = install.stdout, install.stderr
        relative = Path(".codex/skills/jeviphy") if host == "codex" else Path(".claude/skills/jeviphy")
        runner = home / relative / "scripts/run.py"
        doctor = _run(
            [sys.executable, str(runner), "doctor", "--repo", str(repo), "--graph", str(graph)],
            cwd=repo,
            env=env,
        ) if install.returncode == 0 else install
        query = _run(
            [sys.executable, str(runner), "auto", "--question", "run", "--json"],
            cwd=repo,
            env=env,
        ) if doctor.returncode == 0 else doctor
        query_stdout, query_stderr = query.stdout, query.stderr
        reinstall = _run(
            [sys.executable, str(INSTALLER), "install", "--host", host, "--home", str(home)],
            cwd=ROOT,
            env=env,
        ) if query.returncode == 0 else query
        uninstall = _run(
            [sys.executable, str(INSTALLER), "uninstall", "--host", host, "--home", str(home)],
            cwd=ROOT,
            env=env,
        ) if reinstall.returncode == 0 else reinstall
        success = all(run.returncode == 0 for run in (install, doctor, query, reinstall, uninstall))
        if not success:
            diagnostic = "install sequence returned non-zero"
    except (OSError, subprocess.TimeoutExpired) as error:
        diagnostic = type(error).__name__
    return InstallRecord(
        attempt_id=f"{operating_system}-{host}-{index}",
        operating_system=operating_system,
        host=host,
        jeviphy_commit=candidate,
        success=success,
        seconds=round(time.perf_counter() - started, 3),
        install_stdout_sha256=_sha256(install_stdout),
        install_stderr_sha256=_sha256(install_stderr),
        query_stdout_sha256=_sha256(query_stdout),
        query_stderr_sha256=_sha256(query_stderr),
        diagnostic=diagnostic,
    )


def score_installs(records: list[InstallRecord]) -> dict:
    ids = [record.attempt_id for record in records]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate install attempt")
    candidates = {record.jeviphy_commit for record in records}
    if len(candidates) != 1:
        raise ValueError("install records mix candidate SHAs")
    systems = sorted({record.operating_system for record in records})
    successes = sum(record.success for record in records)
    return {
        "schema_version": 1,
        "jeviphy_commit": next(iter(candidates), None),
        "attempts": len(records),
        "successes": successes,
        "median_seconds": statistics.median(record.seconds for record in records) if records else None,
        "operating_systems": systems,
        "status": "pass" if len(records) == 20 and successes >= 18 and systems == ["Ubuntu", "macOS"] else "insufficient_evidence",
    }


def write_install_score(journals: list[Path], output: Path) -> dict:
    if not journals:
        raise ValueError("at least one install journal is required")
    records: list[InstallRecord] = []
    canonical = bytearray()
    for journal in journals:
        for line_number, line in enumerate(journal.read_bytes().splitlines(), start=1):
            try:
                payload = json.loads(line)
                record = InstallRecord(**payload)
            except (json.JSONDecodeError, TypeError) as error:
                raise ValueError(f"invalid install record: {journal}:{line_number}") from error
            if (
                record.operating_system not in {"Ubuntu", "macOS"}
                or record.host not in {"claude", "codex"}
                or not isinstance(record.success, bool)
                or not isinstance(record.seconds, (int, float))
                or isinstance(record.seconds, bool)
                or record.seconds < 0
            ):
                raise ValueError(f"invalid install record: {journal}:{line_number}")
            encoded = json.dumps(asdict(record), sort_keys=True).encode() + b"\n"
            if line + b"\n" != encoded:
                raise ValueError(f"non-canonical install record: {journal}:{line_number}")
            records.append(record)
            canonical.extend(encoded)
    score = score_installs(records)
    score["journal_sha256"] = _sha256(bytes(canonical))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(score, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return score


def _append(path: Path, record: InstallRecord) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as stream:
        stream.write(json.dumps(asdict(record), sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path)
    parser.add_argument("--os", dest="operating_system", choices=("Ubuntu", "macOS"))
    parser.add_argument("--candidate")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--score-from", type=Path, nargs="+")
    parser.add_argument("--score-output", type=Path)
    args = parser.parse_args()
    if args.score_from:
        if args.score_output is None:
            parser.error("--score-output is required with --score-from")
        write_install_score(args.score_from, args.score_output)
        return 0
    if not all((args.matrix, args.operating_system, args.candidate, args.output)):
        parser.error("--matrix, --os, --candidate, and --output are required")
    matrix = json.loads(args.matrix.read_text(encoding="utf-8"))
    if set(matrix) != MATRIX_KEYS or matrix.get("schema_version") != 1:
        parser.error("invalid install matrix")
    attempts = [item for item in matrix["attempts"] if item.get("os") == args.operating_system]
    for item in attempts:
        for index in range(item["repeat"]):
            root = args.output / "attempts" / f"{item['host']}-{index}"
            record = run_attempt(
                root,
                host=item["host"],
                operating_system=args.operating_system,
                index=index,
                candidate=args.candidate,
            )
            _append(args.output / "install-records.jsonl", record)
            if not record.success:
                raise RuntimeError(f"install attempt failed: {record.attempt_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

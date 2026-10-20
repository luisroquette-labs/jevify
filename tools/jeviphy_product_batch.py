"""Serial mini-swe-agent product runner that fails closed on provider errors."""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import time
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from tools.jeviphy_product_eval import validate_live_limits


INFRASTRUCTURE_MARKERS = (
    "billing cycle spend limit",
    "ImageBuildError",
    "Sandbox creation failed",
    "insufficient credits",
)
INFRASTRUCTURE_STATUSES = {
    "APIConnectionError",
    "AuthenticationError",
    "ImageBuildError",
    "RateLimitError",
    "SandboxError",
}


@dataclass(frozen=True)
class ArmResult:
    arm: str
    instance_id: str
    state: str
    exit_code: int
    trajectory: bool
    elapsed_seconds: float
    diagnostic: str | None = None


def _trajectory_path(output: Path, instance_id: str) -> Path:
    return output / instance_id / f"{instance_id}.traj.json"


def required_openrouter_budget(config: Path, agent_calls: int) -> Decimal:
    """Return the worst-case model spend declared by mini-swe-agent's config."""
    match = re.search(
        r"(?m)^\s{2}cost_limit:\s*([0-9]+(?:\.[0-9]+)?)\s*$",
        config.read_text(encoding="utf-8"),
    )
    if not match:
        raise ValueError(f"agent.cost_limit is missing from {config}")
    try:
        per_call = Decimal(match.group(1))
    except InvalidOperation as error:
        raise ValueError(f"agent.cost_limit is invalid in {config}") from error
    if per_call <= 0:
        raise ValueError(f"agent.cost_limit must be positive in {config}")
    return per_call * agent_calls


def _reported_statuses(output: Path) -> list[str]:
    statuses: list[str] = []
    paths = list(output.glob("exit_statuses_*.yaml"))
    if not paths:
        return statuses
    latest = max(paths, key=lambda path: path.stat().st_mtime_ns)
    for line in latest.read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.match(r"^ {4}([A-Za-z][A-Za-z0-9_]*):\s*$", line)
        if match:
            statuses.append(match.group(1))
    return statuses


def inspect_swebench_output(output: Path, instance_id: str, returncode: int) -> ArmResult:
    """Convert mini-swe-agent's process and artifacts into a fail-closed result."""
    trajectory = _trajectory_path(output, instance_id).exists()
    log_path = output / "runner.log"
    log = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
    statuses = _reported_statuses(output)
    details = ", ".join(statuses)
    marker = next((item for item in INFRASTRUCTURE_MARKERS if item in log or item in details), None)
    infrastructure_status = next(
        (status for status in statuses if status in INFRASTRUCTURE_STATUSES), None
    )

    if returncode == 124:
        state, diagnostic = "timeout", "agent exceeded the wall-clock limit"
    elif marker or infrastructure_status:
        state = "infrastructure_failed"
        diagnostic = details or marker or infrastructure_status
        if diagnostic is None:
            diagnostic = "infrastructure failure"
        if marker and marker not in diagnostic:
            diagnostic = f"{diagnostic}: {marker}"
    elif returncode != 0:
        state, diagnostic = "failed", f"agent command exited {returncode}"
    elif not trajectory:
        state, diagnostic = "failed", "missing trajectory"
    elif statuses and statuses != ["Submitted"]:
        state, diagnostic = "failed", details
    else:
        state, diagnostic = "completed", None

    return ArmResult("", instance_id, state, returncode, trajectory, 0, diagnostic)


def run_one(
    root: Path,
    output_root: Path,
    arm: str,
    instance_id: str,
    api_key: str,
    timeout_seconds: int,
) -> ArmResult:
    output = output_root / arm / instance_id
    output.mkdir(mode=0o700, parents=True, exist_ok=True)
    trajectory = _trajectory_path(output, instance_id)
    if trajectory.exists():
        return ArmResult(arm, instance_id, "reused", 0, True, 0, None)

    command = [
        "uvx",
        "--from",
        "mini-swe-agent[full]",
        "mini-extra",
        "swebench",
        "--subset",
        str(root / f"{arm}-train"),
        "--split",
        "train",
        "--filter",
        f"^{re.escape(instance_id)}$",
        "--output",
        str(output),
        "--workers",
        "1",
        "-c",
        "swebench.yaml",
        "-c",
        str(root / "mini-openrouter.yaml"),
        "--environment-class",
        "docker",
    ]
    env = os.environ.copy()
    env["OPENROUTER_API_KEY"] = api_key
    started = time.monotonic()
    log_path = output / "runner.log"
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            command,
            stdout=log,
            stderr=subprocess.STDOUT,
            env=env,
            start_new_session=True,
        )
        try:
            exit_code = process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            exit_code = 124

    inspected = inspect_swebench_output(output, instance_id, exit_code)
    return ArmResult(
        arm,
        instance_id,
        inspected.state,
        exit_code,
        inspected.trajectory,
        round(time.monotonic() - started, 3),
        inspected.diagnostic,
    )


def _append_result(path: Path, result: ArmResult) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    with os.fdopen(descriptor, "a", encoding="utf-8") as stream:
        stream.write(json.dumps(asdict(result), sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def run_batch(
    root: Path,
    instance_ids: list[str],
    api_key: str,
    *,
    timeout_seconds: int = 2100,
    output_root: Path | None = None,
) -> list[ArmResult]:
    output_root = output_root or root / "isolated"
    progress = output_root / "run-results.jsonl"
    results: list[ArmResult] = []
    for index, instance_id in enumerate(instance_ids):
        order = ("graphify", "jeviphy") if index % 2 == 0 else ("jeviphy", "graphify")
        for arm in order:
            result = run_one(root, output_root, arm, instance_id, api_key, timeout_seconds)
            results.append(result)
            _append_result(progress, result)
            if result.state == "infrastructure_failed":
                raise RuntimeError(
                    f"infrastructure failure in {arm}/{instance_id}: {result.diagnostic}"
                )

    output = output_root / "run-results.json"
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump([asdict(result) for result in results], stream, indent=2, sort_keys=True)
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=int, default=2100)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--allow-network-agent", action="store_true")
    parser.add_argument("--max-agent-calls", type=int, default=0)
    parser.add_argument("--max-cost-usd", type=float, default=0)
    args = parser.parse_args()

    validate_live_limits(
        allow_network_agent=args.allow_network_agent,
        max_agent_calls=args.max_agent_calls,
        max_cost_usd=args.max_cost_usd,
    )
    instance_ids = json.loads(args.cases.read_text(encoding="utf-8"))
    required_calls = len(instance_ids) * 2
    if required_calls > args.max_agent_calls:
        parser.error(f"{required_calls} arms exceed --max-agent-calls={args.max_agent_calls}")
    if args.timeout_seconds < 1:
        parser.error("--timeout-seconds must be positive")
    try:
        required_cost = required_openrouter_budget(
            args.root / "mini-openrouter.yaml", required_calls
        )
    except (OSError, ValueError) as error:
        parser.error(str(error))
    if Decimal(str(args.max_cost_usd)) < required_cost:
        parser.error(
            f"worst-case OpenRouter spend is ${required_cost}; "
            f"--max-cost-usd={args.max_cost_usd} is too low"
        )
    api_key = os.environ.get("JEVIPHY_OPENROUTER_API_KEY")
    if not api_key:
        parser.error("JEVIPHY_OPENROUTER_API_KEY is required")

    output_root = args.output_dir or args.root / "isolated"
    if any((output_root / name).exists() for name in ("run-results.jsonl", "run-results.json")):
        parser.error(f"output directory contains an earlier run: {output_root}")
    metadata = output_root / "approved-limits.json"
    metadata.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    metadata.write_text(
        json.dumps(
            {"max_agent_calls": args.max_agent_calls, "max_cost_usd": args.max_cost_usd},
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    metadata.chmod(0o600)
    run_batch(
        args.root,
        instance_ids,
        api_key,
        timeout_seconds=args.timeout_seconds,
        output_root=output_root,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

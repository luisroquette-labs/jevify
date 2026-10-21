"""Serial mini-swe-agent product runner that fails closed on provider errors."""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import signal
import subprocess
import time
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from tools.jeviphy_product_eval import (
    ProductArmRecord,
    evaluate_prediction,
    sha256_bytes,
    validate_live_limits,
)
from tools.jeviphy_product_dataset import validate_arm_datasets


INFRASTRUCTURE_MARKERS = (
    "billing cycle spend limit",
    "ImageBuildError",
    "No space left on device",
    "Sandbox creation failed",
    "insufficient credits",
)
INFRASTRUCTURE_STATUSES = {
    "APIConnectionError",
    "AuthenticationError",
    "ImageBuildError",
    "RateLimitError",
    "SandboxError",
    "TimeoutExpired",
}
MINI_SWE_AGENT_VERSION = "2.4.6"
SWEBENCH_VERSION = "5.0.2"


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
    """Return the aggregate stop threshold declared by mini-swe-agent's config."""
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


def configured_step_limit(config: Path) -> int:
    match = re.search(r"(?m)^\s{2}step_limit:\s*([0-9]+)\s*$", config.read_text(encoding="utf-8"))
    if not match or int(match.group(1)) < 1:
        raise ValueError(f"agent.step_limit must be positive in {config}")
    return int(match.group(1))


def configured_pull_timeout(config: Path) -> int:
    match = re.search(r"(?m)^\s{2}pull_timeout:\s*([0-9]+)\s*$", config.read_text(encoding="utf-8"))
    if not match or int(match.group(1)) < 1:
        raise ValueError(f"environment.pull_timeout must be positive in {config}")
    return int(match.group(1))


def configured_model_name(config: Path) -> str:
    match = re.search(
        r'(?m)^\s{2}model_name:\s*["\']?([^"\'\s]+)["\']?\s*$',
        config.read_text(encoding="utf-8"),
    )
    if not match:
        raise ValueError(f"model.model_name is missing from {config}")
    return match.group(1)


def select_benchmark_cases(
    instance_ids: list[str], cases: dict[str, dict], manifest_sha256: str, limit: int | None
) -> list[str]:
    """Select a deterministic, stratum-balanced prefix for the pre-GTM run."""
    if limit is None or limit == len(instance_ids):
        return list(instance_ids)
    if not 1 <= limit <= len(instance_ids):
        raise ValueError(f"case limit must be between 1 and {len(instance_ids)}")
    buckets: dict[str, list[str]] = {}
    for instance_id in instance_ids:
        buckets.setdefault(cases[instance_id]["stratum"], []).append(instance_id)
    for bucket in buckets.values():
        bucket.sort(
            key=lambda instance_id: sha256_bytes(
                f"{manifest_sha256}:{instance_id}".encode()
            )
        )
    selected: list[str] = []
    while len(selected) < limit:
        for stratum in sorted(buckets):
            if buckets[stratum]:
                selected.append(buckets[stratum].pop(0))
                if len(selected) == limit:
                    break
    return selected


def select_canary_case(instance_ids: list[str], manifest_sha256: str) -> str:
    if not instance_ids or len(instance_ids) != len(set(instance_ids)):
        raise ValueError("canary selection requires unique cases")
    ordered = sorted(instance_ids)
    return ordered[int(manifest_sha256[:16], 16) % len(ordered)]


def validate_run_root(output_root: Path, pins: dict) -> None:
    pins_path = output_root / "run-pins.json"
    if (output_root / "product-report.json").exists():
        raise ValueError("sealed product report already exists")
    if output_root.exists() and any(output_root.iterdir()) and not pins_path.exists():
        raise ValueError("fresh output directory contains unknown files")
    if pins_path.exists() and json.loads(pins_path.read_text(encoding="utf-8")) != pins:
        raise ValueError("run pins differ from the existing run")


def execution_command_sha256(
    *, root: Path, cases: Path, output_root: Path, timeout_seconds: int,
    max_agent_arms: int, max_cost_usd: Decimal, max_new_arms: int, canary: bool,
    agent_config_sha256: str, case_limit: int | None,
) -> str:
    payload = {
        "canary": canary,
        "case_limit": case_limit,
        "agent_config_sha256": agent_config_sha256,
        "cases": str(cases.resolve()),
        "max_agent_arms": max_agent_arms,
        "max_cost_usd": format(max_cost_usd, "f"),
        "max_new_arms": max_new_arms,
        "output_root": str(output_root.resolve()),
        "root": str(root.resolve()),
        "timeout_seconds": timeout_seconds,
    }
    return sha256_bytes(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())


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
        state, diagnostic = "infrastructure_failed", "agent exceeded the wall-clock limit"
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
        f"mini-swe-agent[full]=={MINI_SWE_AGENT_VERSION}",
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
    env["MSWEA_MODEL_RETRY_STOP_AFTER_ATTEMPT"] = "1"
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


def _append_product_record(path: Path, record: ProductArmRecord) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    with os.fdopen(descriptor, "a", encoding="utf-8") as stream:
        stream.write(json.dumps(asdict(record), sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def _prune_docker() -> None:
    subprocess.run(
        ["docker", "system", "prune", "--all", "--force"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def load_product_journal(path: Path) -> list[ProductArmRecord]:
    records: list[ProductArmRecord] = []
    seen: set[tuple[str, str]] = set()
    if not path.exists():
        return records
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            record = ProductArmRecord(**json.loads(line))
        except (TypeError, json.JSONDecodeError) as error:
            raise ValueError(f"invalid product journal line {line_number}") from error
        key = (record.arm, record.instance_id)
        if key in seen:
            raise ValueError(f"duplicate product journal arm: {record.arm}/{record.instance_id}")
        if record.cost_usd is None:
            raise ValueError(f"product journal cost is uncertain: {record.arm}/{record.instance_id}")
        try:
            cost = Decimal(record.cost_usd)
        except InvalidOperation as error:
            raise ValueError(f"invalid product journal cost: {record.cost_usd}") from error
        if not cost.is_finite() or cost < 0:
            raise ValueError(f"negative product journal cost: {record.cost_usd}")
        seen.add(key)
        records.append(record)
    return records


def remaining_limits(
    records: list[ProductArmRecord], max_agent_calls: int, max_cost_usd: Decimal
) -> tuple[int, Decimal]:
    costs: list[Decimal] = []
    for record in records:
        if record.cost_usd is None:
            raise ValueError(f"product journal cost is uncertain: {record.arm}/{record.instance_id}")
        try:
            cost = Decimal(record.cost_usd)
        except InvalidOperation as error:
            raise ValueError(f"invalid product journal cost: {record.cost_usd}") from error
        if not cost.is_finite() or cost < 0:
            raise ValueError(f"invalid product journal cost: {record.cost_usd}")
        costs.append(cost)
    spent = sum(costs, Decimal("0"))
    remaining_calls = max_agent_calls - len(records)
    remaining_cost = max_cost_usd - spent
    if remaining_calls < 1 or remaining_cost <= 0:
        raise ValueError("approved provider limit is exhausted")
    return remaining_calls, remaining_cost


def _failed_product_record(result: ArmResult, output: Path) -> ProductArmRecord:
    trajectory = _trajectory_path(output, result.instance_id)
    cost: str | None = None
    trajectory_hash = sha256_bytes(b"")
    if trajectory.is_file():
        trajectory_hash = sha256_bytes(trajectory.read_bytes())
        try:
            stats = json.loads(trajectory.read_text(encoding="utf-8"))["info"]["model_stats"]
            raw_cost = stats.get("instance_cost")
            cost = str(raw_cost) if raw_cost is not None else None
        except (KeyError, TypeError, json.JSONDecodeError):
            pass
    return ProductArmRecord(
        arm=result.arm,
        instance_id=result.instance_id,
        status=result.state,
        success=False,
        generation_seconds=result.elapsed_seconds,
        evaluation_seconds=0,
        prediction_sha256=sha256_bytes(b""),
        patch_sha256=sha256_bytes(b""),
        trajectory_sha256=trajectory_hash,
        input_tokens=None,
        output_tokens=None,
        cost_usd=cost,
        resolved=False,
        diagnostic=result.diagnostic,
    )


def evaluate_generated_arm(
    root: Path,
    output_root: Path,
    result: ArmResult,
    timeout_seconds: int,
    candidate_sha: str,
) -> ProductArmRecord:
    output = output_root / result.arm / result.instance_id
    if result.state != "completed":
        return _failed_product_record(result, output)
    prediction = output / "preds.json"
    trajectory = _trajectory_path(output, result.instance_id)
    if not re.fullmatch(r"[0-9a-f]{40}", candidate_sha):
        raise ValueError("candidate SHA must be a full lowercase Git SHA")
    run_id = re.sub(
        r"[^A-Za-z0-9_.-]", "_",
        f"jeviphy-{candidate_sha[:12]}-{result.arm}-{result.instance_id}",
    )
    evaluation_root = output / "official-evaluation"
    if evaluation_root.exists():
        raise ValueError(f"official evaluator directory already exists: {evaluation_root}")
    evaluation_root.mkdir(mode=0o700, parents=True)
    command = [
        "uvx",
        "--from",
        f"swebench=={SWEBENCH_VERSION}",
        "python",
        "-m",
        "swebench.harness.run_evaluation",
        "--dataset_name",
        str(root / f"{result.arm}-train"),
        "--split",
        "train",
        "--instance_ids",
        result.instance_id,
        "--predictions_path",
        str(prediction),
        "--max_workers",
        "1",
        "--run_id",
        run_id,
    ]
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=evaluation_root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        elapsed = round(time.monotonic() - started, 3)
        failed = _failed_product_record(
            ArmResult(result.arm, result.instance_id, "infrastructure_failed", 124, True,
                      result.elapsed_seconds, "official evaluator timed out"),
            output,
        )
        return ProductArmRecord(**{**asdict(failed), "evaluation_seconds": elapsed})
    elapsed = round(time.monotonic() - started, 3)
    report = evaluation_root / "logs" / "evaluation" / run_id / "results.json"
    if not report.is_file():
        current_reports = list(evaluation_root.glob(f"*.{run_id}.json"))
        if len(current_reports) == 1:
            report = current_reports[0]
    if not report.is_file():
        failed = _failed_product_record(
            ArmResult(result.arm, result.instance_id, "infrastructure_failed", completed.returncode,
                      True, result.elapsed_seconds, "official evaluator failed"),
            output,
        )
        return ProductArmRecord(**{**asdict(failed), "evaluation_seconds": elapsed})
    return evaluate_prediction(
        result.arm,
        result.instance_id,
        prediction,
        report,
        trajectory,
        generation_seconds=result.elapsed_seconds,
        evaluation_seconds=elapsed,
        run_root=output_root,
    )


def run_batch(
    root: Path,
    instance_ids: list[str],
    api_key: str,
    *,
    timeout_seconds: int = 2100,
    output_root: Path | None = None,
    max_new_arms: int = 12,
    max_agent_calls: int | None = None,
    max_cost_usd: Decimal | None = None,
    max_calls_per_arm: int = 80,
    candidate_sha: str,
) -> list[ProductArmRecord]:
    if max_calls_per_arm < 1:
        raise ValueError("max_calls_per_arm must be positive")
    output_root = output_root or root / "isolated"
    progress = output_root / "product-arms.jsonl"
    prior = load_product_journal(progress)
    completed_keys = {(record.arm, record.instance_id) for record in prior}
    results = list(prior)
    new_count = 0
    for index, instance_id in enumerate(instance_ids):
        order = ("graphify", "jeviphy") if index % 2 == 0 else ("jeviphy", "graphify")
        for arm in order:
            if (arm, instance_id) in completed_keys:
                continue
            if new_count >= max_new_arms:
                return results
            if max_agent_calls is not None and max_cost_usd is not None:
                _, cost = remaining_limits(results, max_agent_calls, max_cost_usd)
                os.environ["MSWEA_GLOBAL_CALL_LIMIT"] = str(max_calls_per_arm)
                os.environ["MSWEA_GLOBAL_COST_LIMIT"] = format(cost, "f")
            arm_output = output_root / arm / instance_id
            if arm_output.exists() and any(arm_output.iterdir()):
                raise ValueError(f"unjournaled arm output already exists: {arm_output}")
            result = run_one(root, output_root, arm, instance_id, api_key, timeout_seconds)
            record = evaluate_generated_arm(
                root, output_root, result, timeout_seconds, candidate_sha
            )
            _append_product_record(progress, record)
            results.append(record)
            completed_keys.add((arm, instance_id))
            new_count += 1
            pair_complete = all(
                (candidate, instance_id) in completed_keys
                for candidate in ("graphify", "jeviphy")
            )
            if pair_complete or record.status == "infrastructure_failed":
                _prune_docker()
            if record.status == "infrastructure_failed":
                raise RuntimeError(
                    f"infrastructure failure in {arm}/{instance_id}: {record.diagnostic}"
                )
    return results


def seal_product_journal(
    journal: Path,
    output: Path,
    *,
    expected_ids: list[str],
    strata: dict[str, str],
    pins: dict,
) -> dict:
    records = load_product_journal(journal)
    by_key = {(record.arm, record.instance_id): record for record in records}
    expected = {(arm, case_id) for case_id in expected_ids for arm in ("graphify", "jeviphy")}
    if set(by_key) != expected:
        raise ValueError(
            f"product journal does not contain the exact expected {len(expected)} arms"
        )
    pairs = []
    for case_id in expected_ids:
        baseline = by_key[("graphify", case_id)]
        candidate = by_key[("jeviphy", case_id)]
        baseline_arm = {
            "status": baseline.status,
            "success": baseline.success,
            "duration_ms": (baseline.generation_seconds + baseline.evaluation_seconds) * 1000,
        }
        candidate_arm = {
            "status": candidate.status,
            "success": candidate.success,
            "duration_ms": (candidate.generation_seconds + candidate.evaluation_seconds) * 1000,
        }
        if baseline.input_tokens is not None and candidate.input_tokens is not None:
            baseline_arm["input_tokens"] = baseline.input_tokens
            candidate_arm["input_tokens"] = candidate.input_tokens
        pairs.append({"pair": {
            "case_id": case_id,
            "stratum": strata[case_id],
            "pass_index": 0,
            "baseline": baseline_arm,
            "jeviphy": candidate_arm,
        }})
    payload = {
        "schema_version": 1,
        "pins": pins,
        "journal_sha256": sha256_bytes(journal.read_bytes()),
        "product_records": pairs,
    }
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=int, default=2100)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--allow-network-agent", action="store_true")
    parser.add_argument(
        "--max-agent-arms", "--max-agent-calls", dest="max_agent_calls", type=int, default=0
    )
    parser.add_argument("--max-cost-usd", type=float, default=0)
    parser.add_argument("--max-new-arms", type=int, default=12)
    parser.add_argument("--case-limit", type=int)
    parser.add_argument("--canary", action="store_true")
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()

    validate_live_limits(
        allow_network_agent=args.allow_network_agent or args.preview,
        max_agent_calls=args.max_agent_calls,
        max_cost_usd=args.max_cost_usd,
    )
    instance_ids = json.loads(args.cases.read_text(encoding="utf-8"))
    manifest_path = args.root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cases = {case["id"]: case for case in manifest["cases"]}
    if (
        not isinstance(instance_ids, list)
        or not all(isinstance(item, str) for item in instance_ids)
        or len(instance_ids) != len(set(instance_ids))
        or set(instance_ids) != set(cases)
    ):
        parser.error("cases must contain the complete frozen manifest set")
    manifest_sha256 = sha256_bytes(manifest_path.read_bytes())
    try:
        dataset_hashes = validate_arm_datasets(
            args.root / "graphify-train",
            args.root / "jeviphy-train",
            expected_ids=set(instance_ids),
            manifest_gold_symbols={key: value.get("gold_symbols", []) for key, value in cases.items()},
        )
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        parser.error(str(error))
    try:
        selected_ids = select_benchmark_cases(
            instance_ids, cases, manifest_sha256, args.case_limit
        )
    except ValueError as error:
        parser.error(str(error))
    run_ids = [select_canary_case(selected_ids, manifest_sha256)] if args.canary else selected_ids
    required_calls = len(run_ids) * 2
    if required_calls > args.max_agent_calls:
        parser.error(f"{required_calls} arms exceed --max-agent-arms={args.max_agent_calls}")
    if args.timeout_seconds < 1:
        parser.error("--timeout-seconds must be positive")
    if not 1 <= args.max_new_arms <= 12:
        parser.error("--max-new-arms must be between 1 and 12")
    try:
        config_path = args.root / "mini-openrouter.yaml"
        required_threshold = required_openrouter_budget(
            config_path, required_calls
        )
        max_calls_per_arm = configured_step_limit(config_path)
        docker_pull_timeout = configured_pull_timeout(config_path)
        model_name = configured_model_name(config_path)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    if Decimal(str(args.max_cost_usd)) < required_threshold:
        parser.error(
            f"aggregate OpenRouter stop threshold must be at least ${required_threshold}; "
            f"--max-cost-usd={args.max_cost_usd} is too low"
        )
    output_root = args.output_dir or args.root / "isolated"
    candidate_repo = Path(__file__).resolve().parents[1]
    if subprocess.check_output(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=candidate_repo,
        text=True,
    ).strip():
        parser.error("Jeviphy checkout must be clean before a benchmark run")
    candidate_sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=candidate_repo, text=True
    ).strip()
    docker_version = subprocess.check_output(["docker", "--version"], text=True).strip()
    execution_pins = {
        "agent_config_sha256": sha256_bytes(config_path.read_bytes()),
        "command_sha256": execution_command_sha256(
            root=args.root,
            cases=args.cases,
            output_root=output_root,
            timeout_seconds=args.timeout_seconds,
            max_agent_arms=args.max_agent_calls,
            max_cost_usd=Decimal(str(args.max_cost_usd)),
            max_new_arms=args.max_new_arms,
            canary=args.canary,
            agent_config_sha256=sha256_bytes(config_path.read_bytes()),
            case_limit=args.case_limit,
        ),
        "docker_version": docker_version,
        "docker_pull_timeout_seconds": docker_pull_timeout,
        "machine_class": f"{os.cpu_count()} vCPU/{platform.machine()}",
        "max_agent_arms": args.max_agent_calls,
        "case_limit": args.case_limit,
        "max_calls_per_arm": max_calls_per_arm,
        "max_new_arms_per_chunk": args.max_new_arms,
        "model_retry_attempts": 1,
        "provider_cost_stop_threshold_usd": format(Decimal(str(args.max_cost_usd)), "f"),
        "mini_swe_agent_version": MINI_SWE_AGENT_VERSION,
        "model": model_name,
        "python_version": platform.python_version(),
        "swebench_version": SWEBENCH_VERSION,
        "timeout_seconds": args.timeout_seconds,
        "selected_cases_sha256": sha256_bytes(
            json.dumps(run_ids, separators=(",", ":")).encode()
        ),
    }
    if args.preview:
        if output_root.exists():
            parser.error(f"preview output path already exists: {output_root}")
        preview = {
            "arm_count": required_calls,
            "candidate_sha": candidate_sha,
            "case_count": len(run_ids),
            "docker_version": docker_version,
            "graphify_dataset_sha256": dataset_hashes.graphify_sha256,
            "jeviphy_dataset_sha256": dataset_hashes.jeviphy_sha256,
            "manifest_sha256": manifest_sha256,
            "maximum_internal_model_calls": required_calls * max_calls_per_arm,
            "model": model_name,
            "output_path": str(output_root),
            "per_arm_cost_stop_threshold_usd": format(
                required_threshold / required_calls, "f"
            ),
            **execution_pins,
        }
        if args.canary:
            preview["selected_case"] = run_ids[0]
        print(json.dumps(preview, sort_keys=True))
        return 0

    api_key = os.environ.get("JEVIPHY_OPENROUTER_API_KEY")
    if not api_key:
        parser.error("JEVIPHY_OPENROUTER_API_KEY is required")
    pins = {
        "manifest_sha256": manifest_sha256,
        "graphify_commit": manifest["graphify_commit"],
        "jeviphy_commit": candidate_sha,
        "graphify_dataset_sha256": dataset_hashes.graphify_sha256,
        "jeviphy_dataset_sha256": dataset_hashes.jeviphy_sha256,
        **execution_pins,
    }
    pins_path = output_root / "run-pins.json"
    try:
        validate_run_root(output_root, pins)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        parser.error(str(error))
    pins_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    pins_path.write_text(json.dumps(pins, sort_keys=True), encoding="utf-8")
    pins_path.chmod(0o600)
    metadata = output_root / "approved-limits.json"
    metadata.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    limits = {"max_agent_calls": args.max_agent_calls, "max_cost_usd": str(args.max_cost_usd)}
    if metadata.exists() and json.loads(metadata.read_text(encoding="utf-8")) != limits:
        parser.error("approved limits differ from the existing run")
    metadata.write_text(json.dumps(limits, sort_keys=True), encoding="utf-8")
    metadata.chmod(0o600)
    records = run_batch(
        args.root,
        run_ids,
        api_key,
        timeout_seconds=args.timeout_seconds,
        output_root=output_root,
        max_new_arms=args.max_new_arms,
        max_agent_calls=args.max_agent_calls,
        max_cost_usd=Decimal(str(args.max_cost_usd)),
        max_calls_per_arm=max_calls_per_arm,
        candidate_sha=candidate_sha,
    )
    if len(records) == required_calls:
        seal_product_journal(
            output_root / "product-arms.jsonl",
            output_root / "product-report.json",
            expected_ids=run_ids,
            strata={key: value["stratum"] for key, value in cases.items()},
            pins=pins,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

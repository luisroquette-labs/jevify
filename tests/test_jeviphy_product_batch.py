import json
import os
from pathlib import Path

import pytest

from tools.jeviphy_product_batch import inspect_swebench_output, run_batch


def _write_status(output: Path, status: str, instance_id: str = "case-1") -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "exit_statuses_1.yaml").write_text(
        f"instances_by_exit_status:\n    {status}:\n    - {instance_id}\n",
        encoding="utf-8",
    )


def test_zero_exit_with_image_build_error_is_infrastructure_failure(tmp_path):
    output = tmp_path / "case-1"
    _write_status(output, "ImageBuildError")
    (output / "runner.log").write_text(
        "Container terminated due to reaching billing cycle spend limit",
        encoding="utf-8",
    )

    result = inspect_swebench_output(output, "case-1", returncode=0)

    assert result.state == "infrastructure_failed"
    assert result.trajectory is False
    assert "ImageBuildError" in result.diagnostic
    assert "billing cycle spend limit" in result.diagnostic


def test_zero_exit_without_trajectory_is_failure(tmp_path):
    output = tmp_path / "case-1"
    output.mkdir()

    result = inspect_swebench_output(output, "case-1", returncode=0)

    assert result.state == "failed"
    assert result.trajectory is False
    assert result.diagnostic == "missing trajectory"


def test_trajectory_marks_completed_run(tmp_path):
    output = tmp_path / "case-1"
    trajectory = output / "case-1" / "case-1.traj.json"
    trajectory.parent.mkdir(parents=True)
    trajectory.write_text("{}", encoding="utf-8")

    result = inspect_swebench_output(output, "case-1", returncode=0)

    assert result.state == "completed"
    assert result.trajectory is True
    assert result.diagnostic is None


def test_latest_status_wins_over_stale_failed_attempt(tmp_path):
    output = tmp_path / "case-1"
    _write_status(output, "ImageBuildError")
    old_status = output / "exit_statuses_1.yaml"
    trajectory = output / "case-1" / "case-1.traj.json"
    trajectory.parent.mkdir()
    trajectory.write_text("{}", encoding="utf-8")
    new_status = output / "exit_statuses_2.yaml"
    new_status.write_text(
        "instances_by_exit_status:\n    Submitted:\n    - case-1\n",
        encoding="utf-8",
    )
    os.utime(old_status, ns=(1, 1))
    os.utime(new_status, ns=(2, 2))

    result = inspect_swebench_output(output, "case-1", returncode=0)

    assert result.state == "completed"


def test_agent_limit_with_trajectory_is_a_failed_attempt(tmp_path):
    output = tmp_path / "case-1"
    _write_status(output, "LimitsExceeded")
    trajectory = output / "case-1" / "case-1.traj.json"
    trajectory.parent.mkdir()
    trajectory.write_text("{}", encoding="utf-8")

    result = inspect_swebench_output(output, "case-1", returncode=0)

    assert result.state == "failed"
    assert result.diagnostic == "LimitsExceeded"


def test_batch_stops_after_first_infrastructure_failure(tmp_path, monkeypatch):
    calls = []

    def failed_arm(root, arm, instance_id, api_key, timeout_seconds):
        calls.append((arm, instance_id))
        from tools.jeviphy_product_batch import ArmResult

        return ArmResult(arm, instance_id, "infrastructure_failed", 0, False, 0.1, "quota")

    monkeypatch.setattr("tools.jeviphy_product_batch.run_one", failed_arm)
    with pytest.raises(RuntimeError, match="infrastructure failure"):
        run_batch(tmp_path, ["case-1", "case-2"], "secret", timeout_seconds=1)

    assert calls == [("graphify", "case-1")]
    progress = [json.loads(line) for line in (tmp_path / "isolated/run-results.jsonl").read_text().splitlines()]
    assert progress[0]["state"] == "infrastructure_failed"

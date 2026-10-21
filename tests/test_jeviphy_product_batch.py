import json
import os
import sys
from decimal import Decimal
from pathlib import Path

import pytest

from tools.jeviphy_product_eval import sha256_bytes
from tools.jeviphy_product_batch import (
    ArmResult,
    configured_model_name,
    configured_step_limit,
    evaluate_generated_arm,
    execution_command_sha256,
    inspect_swebench_output,
    load_product_journal,
    main as product_main,
    remaining_limits,
    required_openrouter_budget,
    run_batch,
    run_one,
    select_canary_case,
    seal_product_journal,
    validate_run_root,
)


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
    assert result.diagnostic is not None
    assert "ImageBuildError" in result.diagnostic
    assert "billing cycle spend limit" in result.diagnostic


def test_disk_exhaustion_is_infrastructure_failure(tmp_path):
    output = tmp_path / "case-1"
    output.mkdir()
    (output / "runner.log").write_text("OSError: No space left on device", encoding="utf-8")

    result = inspect_swebench_output(output, "case-1", returncode=0)

    assert result.state == "infrastructure_failed"
    assert result.diagnostic == "No space left on device"


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
    pruned = []

    def failed_arm(root, output_root, arm, instance_id, api_key, timeout_seconds):
        calls.append((arm, instance_id))
        from tools.jeviphy_product_batch import ArmResult

        return ArmResult(arm, instance_id, "infrastructure_failed", 0, False, 0.1, "quota")

    monkeypatch.setattr("tools.jeviphy_product_batch.run_one", failed_arm)
    monkeypatch.setattr("tools.jeviphy_product_batch._prune_docker", lambda: pruned.append(True))
    monkeypatch.setattr(
        "tools.jeviphy_product_batch.evaluate_generated_arm",
        lambda root, output_root, result, timeout, candidate_sha: _product_record(
            result.arm, result.instance_id, status="infrastructure_failed", cost="0.01"
        ),
    )
    with pytest.raises(RuntimeError, match="infrastructure failure"):
        run_batch(
            tmp_path, ["case-1", "case-2"], "secret", timeout_seconds=1,
            candidate_sha="a" * 40,
        )

    assert calls == [("graphify", "case-1")]
    progress = [
        json.loads(line)
        for line in (tmp_path / "isolated/product-arms.jsonl").read_text().splitlines()
    ]
    assert progress[0]["status"] == "infrastructure_failed"
    assert pruned == [True]


def test_batch_writes_to_separate_output_root(tmp_path, monkeypatch):
    output_root = tmp_path / "fresh-run"

    def completed_arm(root, output_root, arm, instance_id, api_key, timeout_seconds):
        from tools.jeviphy_product_batch import ArmResult

        return ArmResult(arm, instance_id, "completed", 0, True, 0.1)

    monkeypatch.setattr("tools.jeviphy_product_batch.run_one", completed_arm)
    monkeypatch.setattr(
        "tools.jeviphy_product_batch.evaluate_generated_arm",
        lambda root, output_root, result, timeout, candidate_sha: _product_record(
            result.arm, result.instance_id, cost="0.01"
        ),
    )
    run_batch(
        tmp_path, ["case-1"], "secret", timeout_seconds=1, output_root=output_root,
        candidate_sha="a" * 40,
    )

    assert (output_root / "product-arms.jsonl").exists()
    assert not (tmp_path / "isolated").exists()


def test_required_openrouter_budget_uses_per_agent_limit(tmp_path):
    config = tmp_path / "mini-openrouter.yaml"
    config.write_text(
        "agent:\n  cost_limit: 0.08\n  step_limit: 80\nmodel:\n  model_name: example\n",
        encoding="utf-8",
    )

    assert required_openrouter_budget(config, 186) == Decimal("14.88")
    assert configured_step_limit(config) == 80
    assert configured_model_name(config) == "example"


def test_canary_selection_is_deterministic_and_order_independent():
    cases = ["case-3", "case-1", "case-2"]
    selected = select_canary_case(cases, "f" * 64)
    assert selected == select_canary_case(list(reversed(cases)), "f" * 64)
    assert selected in cases


def test_canary_selection_rejects_duplicate_cases():
    with pytest.raises(ValueError, match="unique cases"):
        select_canary_case(["case-1", "case-1"], "f" * 64)


def test_preview_needs_no_provider_key_and_creates_no_output(tmp_path, monkeypatch, capsys):
    from tools.jeviphy_product_dataset import DatasetHashes

    root = tmp_path / "private"
    root.mkdir()
    (root / "manifest.json").write_text(json.dumps({
        "graphify_commit": "b" * 40,
        "cases": [{"id": "case-1", "gold_symbols": [], "stratum": "valid_source"}],
    }))
    cases = root / "all-cases.json"
    cases.write_text('["case-1"]')
    (root / "mini-openrouter.yaml").write_text(
        'agent:\n  cost_limit: 0.08\n  step_limit: 80\nmodel:\n  model_name: "example/model"\n'
    )
    monkeypatch.delenv("JEVIPHY_OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr(
        "tools.jeviphy_product_batch.validate_arm_datasets",
        lambda *args, **kwargs: DatasetHashes("1" * 64, "2" * 64),
    )

    def check_output(command, **kwargs):
        if command[:2] == ["git", "status"]:
            return ""
        if command[:2] == ["git", "rev-parse"]:
            return "a" * 40 + "\n"
        if command == ["docker", "--version"]:
            return "Docker version test\n"
        raise AssertionError(command)

    monkeypatch.setattr("tools.jeviphy_product_batch.subprocess.check_output", check_output)
    output = tmp_path / "new-output"
    monkeypatch.setattr(sys, "argv", [
        "jeviphy-product-batch", "--root", str(root), "--cases", str(cases),
        "--output-dir", str(output), "--max-agent-arms", "2",
        "--max-cost-usd", "0.16", "--max-new-arms", "2", "--canary", "--preview",
    ])

    assert product_main() == 0
    preview = json.loads(capsys.readouterr().out)
    assert preview["arm_count"] == 2
    assert preview["agent_config_sha256"] == sha256_bytes(
        (root / "mini-openrouter.yaml").read_bytes()
    )
    assert preview["maximum_internal_model_calls"] == 160
    assert preview["mini_swe_agent_version"] == "2.4.6"
    assert preview["selected_case"] == "case-1"
    assert preview["swebench_version"] == "5.0.2"
    assert not output.exists()


def test_run_root_rejects_unknown_or_sealed_state(tmp_path):
    pins = {"jeviphy_commit": "a" * 40}
    unknown = tmp_path / "unknown"
    unknown.mkdir()
    (unknown / "partial.txt").write_text("partial")
    with pytest.raises(ValueError, match="unknown files"):
        validate_run_root(unknown, pins)

    sealed = tmp_path / "sealed"
    sealed.mkdir()
    (sealed / "run-pins.json").write_text(json.dumps(pins))
    (sealed / "product-report.json").write_text("{}")
    with pytest.raises(ValueError, match="sealed product report"):
        validate_run_root(sealed, pins)


def test_execution_command_hash_is_canonical(tmp_path):
    values = {
        "root": tmp_path / "root", "cases": tmp_path / "cases.json",
        "output_root": tmp_path / "out", "timeout_seconds": 30,
        "max_agent_arms": 2, "max_cost_usd": Decimal("0.16"),
        "max_new_arms": 2, "canary": True, "agent_config_sha256": "f" * 64,
    }
    assert execution_command_sha256(**values) == execution_command_sha256(**dict(reversed(list(values.items()))))


def test_product_arm_uses_local_docker_instead_of_modal(tmp_path, monkeypatch):
    captured = {}

    class Process:
        pid = 1

        def wait(self, timeout=None):
            return 1

    def popen(command, **kwargs):
        captured["command"] = command
        return Process()

    monkeypatch.setattr("tools.jeviphy_product_batch.subprocess.Popen", popen)
    run_one(tmp_path, tmp_path / "output", "graphify", "case-1", "secret", 1)

    assert captured["command"][-2:] == ["--environment-class", "docker"]
    assert captured["command"][2] == "mini-swe-agent[full]==2.4.6"
    assert "swebench_modal.yaml" not in captured["command"]


def _product_record(arm, instance_id, *, status="completed", cost="0.02"):
    from tools.jeviphy_product_eval import ProductArmRecord

    return ProductArmRecord(
        arm, instance_id, status, False, 1, 2, "a" * 64, "b" * 64, "c" * 64,
        10, 5, cost, False, None,
    )


def test_two_chunks_keep_per_arm_call_limit_and_reduce_total_cost(tmp_path, monkeypatch):
    seen = []
    pruned = []

    def completed_arm(root, output_root, arm, instance_id, api_key, timeout_seconds):
        from tools.jeviphy_product_batch import ArmResult

        seen.append((os.environ["MSWEA_GLOBAL_CALL_LIMIT"], os.environ["MSWEA_GLOBAL_COST_LIMIT"]))
        return ArmResult(arm, instance_id, "completed", 0, True, 0.1)

    monkeypatch.setattr("tools.jeviphy_product_batch.run_one", completed_arm)
    monkeypatch.setattr("tools.jeviphy_product_batch._prune_docker", lambda: pruned.append(True))
    monkeypatch.setattr(
        "tools.jeviphy_product_batch.evaluate_generated_arm",
        lambda root, output_root, result, timeout, candidate_sha: _product_record(
            result.arm, result.instance_id, cost="0.02"
        ),
    )
    output = tmp_path / "out"
    run_batch(
        tmp_path, ["case-1"], "secret", output_root=output, max_new_arms=1,
        max_agent_calls=4, max_cost_usd=Decimal("0.10"),
        candidate_sha="a" * 40,
    )
    assert pruned == []
    run_batch(
        tmp_path, ["case-1"], "secret", output_root=output, max_new_arms=1,
        max_agent_calls=4, max_cost_usd=Decimal("0.10"),
        candidate_sha="a" * 40,
    )

    assert seen == [("80", "0.10"), ("80", "0.08")]
    assert pruned == [True]


def test_uncertain_journal_cost_blocks_resume(tmp_path):
    journal = tmp_path / "product-arms.jsonl"
    journal.write_text(json.dumps(_product_record("graphify", "case-1", cost=None).__dict__) + "\n")

    with pytest.raises(ValueError, match="cost is uncertain"):
        load_product_journal(journal)


def test_remaining_limits_reject_exhausted_budget():
    with pytest.raises(ValueError, match="exhausted"):
        remaining_limits([_product_record("graphify", "case-1", cost="0.10")], 2, Decimal("0.10"))


def test_seal_product_journal_requires_complete_pairs(tmp_path):
    journal = tmp_path / "product-arms.jsonl"
    rows = [
        _product_record("graphify", "case-1", cost="0.01"),
        _product_record("jeviphy", "case-1", cost="0.02"),
    ]
    journal.write_text("".join(json.dumps(row.__dict__) + "\n" for row in rows), encoding="utf-8")
    output = tmp_path / "product-report.json"

    payload = seal_product_journal(
        journal, output, expected_ids=["case-1"],
        strata={"case-1": "valid_source"}, pins={"jeviphy_commit": "a" * 40},
    )

    pair = payload["product_records"][0]["pair"]
    assert pair["baseline"]["duration_ms"] == 3000
    assert pair["jeviphy"]["input_tokens"] == 10
    assert output.stat().st_mode & 0o777 == 0o600


def test_completed_generation_uses_official_swebench_report_even_on_nonzero_exit(
    tmp_path, monkeypatch
):
    output = tmp_path / "out" / "graphify" / "case-1"
    trajectory = output / "case-1" / "case-1.traj.json"
    trajectory.parent.mkdir(parents=True)
    trajectory.write_text(json.dumps({"info": {"model_stats": {
        "instance_cost": "0.01", "input_tokens": 10, "output_tokens": 2
    }}}), encoding="utf-8")
    (output / "preds.json").write_text(json.dumps({"case-1": {
        "instance_id": "case-1", "model_name_or_path": "model", "model_patch": "diff"
    }}), encoding="utf-8")
    captured = {}

    def run(command, **kwargs):
        if command[:3] == ["docker", "system", "prune"]:
            captured["pruned"] = True
            return type("Completed", (), {"returncode": 0})()
        captured["command"] = command
        run_id = command[-1]
        report = Path(kwargs["cwd"]) / f"model.{run_id}.json"
        report.write_text(json.dumps({
            "completed_ids": ["case-1"], "resolved_ids": ["case-1"],
            "unresolved_ids": [], "error_ids": [], "infra_failure_ids": [],
        }), encoding="utf-8")
        return type("Completed", (), {"returncode": 1})()

    monkeypatch.setattr("tools.jeviphy_product_batch.subprocess.run", run)
    record = evaluate_generated_arm(
        tmp_path, tmp_path / "out",
        ArmResult("graphify", "case-1", "completed", 0, True, 1.0), 30, "a" * 40,
    )

    assert captured["command"][:4] == ["uvx", "--from", "swebench==5.0.2", "python"]
    assert captured["command"][-1].startswith("jeviphy-aaaaaaaaaaaa-graphify-")
    assert record.success is True
    assert record.resolved is True


def test_official_eval_rejects_unpinned_candidate_sha(tmp_path):
    with pytest.raises(ValueError, match="full lowercase Git SHA"):
        evaluate_generated_arm(
            tmp_path,
            tmp_path / "out",
            ArmResult("graphify", "case-1", "completed", 0, True, 1.0),
            30,
            "short",
        )


def test_failed_generation_defers_prune_to_batch_pair_boundary(tmp_path, monkeypatch):
    pruned = []
    monkeypatch.setattr("tools.jeviphy_product_batch._prune_docker", lambda: pruned.append(True))

    record = evaluate_generated_arm(
        tmp_path,
        tmp_path / "out",
        ArmResult("graphify", "case-1", "failed", 1, False, 1.0, "failed"),
        30,
        "a" * 40,
    )

    assert record.status == "failed"
    assert pruned == []

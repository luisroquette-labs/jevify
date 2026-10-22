"""Mechanical release gates for the Jeviphy v2 benchmark."""

from __future__ import annotations

import argparse
import json
import random
import statistics
from dataclasses import asdict, dataclass
from pathlib import Path


NO_DIFFERENCE = "The frozen v2 benchmark did not demonstrate a Jeviphy advantage."
RETRIEVAL_ONLY = "Jeviphy improved source-backed retrieval on the frozen v2 benchmark."
INTERNAL_PRODUCT_WIN = (
    "Jeviphy passed the internal frozen v2 product gates; external reproduction is pending."
)
REPRODUCED_PRODUCT_WIN = "Jeviphy surpassed Graphify on the frozen v2 benchmark."
BETA_READY = "Jeviphy is ready for a limited source-aware beta."


@dataclass(frozen=True)
class GateResult:
    status: str
    metrics: dict[str, object]


@dataclass(frozen=True)
class Scorecard:
    retrieval: GateResult
    product: GateResult
    usability: GateResult
    compatibility: GateResult
    reproduction: GateResult


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = (len(ordered) - 1) * fraction
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)


def _paired_bootstrap(differences: list[float], *, resamples: int = 10_000) -> tuple[float, float]:
    if not differences:
        raise ValueError("paired differences are required")
    rng = random.Random(20261019)
    means = [
        statistics.fmean(rng.choices(differences, k=len(differences))) for _ in range(resamples)
    ]
    return (_percentile(means, 0.025), _percentile(means, 0.975))


def _arm(pair: dict, name: str) -> dict:
    return pair[name]


def _first_pairs(records: list[dict]) -> list[dict]:
    by_case: dict[str, dict] = {}
    for wrapper in records:
        pair = wrapper.get("pair", wrapper)
        current = by_case.get(pair["case_id"])
        if current is None or pair["pass_index"] < current["pass_index"]:
            by_case[pair["case_id"]] = pair
    return list(by_case.values())


def _score_retrieval(records: list[dict]) -> GateResult:
    if not records:
        return GateResult("insufficient_evidence", {})
    first = _first_pairs(records)
    valid = [pair for pair in first if pair["stratum"] == "valid_source"]
    stale = [pair for pair in first if pair["stratum"] == "stale_source"]
    controls = [pair for pair in first if pair["stratum"] == "no_source"]
    timed_valid = [
        wrapper.get("pair", wrapper)
        for wrapper in records
        if wrapper.get("pair", wrapper)["stratum"] == "valid_source"
    ]
    if not valid or not stale or not controls:
        return GateResult("insufficient_evidence", {})
    differences = [
        (_arm(pair, "jeviphy")["top5_hits"] - _arm(pair, "baseline")["top5_hits"]) / 5
        for pair in valid
    ]
    ci95 = _paired_bootstrap(differences)
    baseline_precision = statistics.fmean(_arm(pair, "baseline")["top5_hits"] / 5 for pair in valid)
    jeviphy_precision = statistics.fmean(_arm(pair, "jeviphy")["top5_hits"] / 5 for pair in valid)
    baseline_first = sum(bool(_arm(pair, "baseline")["first_hit"]) for pair in valid)
    jeviphy_first = sum(bool(_arm(pair, "jeviphy")["first_hit"]) for pair in valid)
    stale_losses = sum(
        _arm(pair, "jeviphy")["top5_hits"] < _arm(pair, "baseline")["top5_hits"]
        for pair in stale
    )
    controls_identical = all(
        _arm(pair, "jeviphy")["output_sha256"] == _arm(pair, "baseline")["output_sha256"]
        for pair in controls
    )
    baseline_times = [_arm(pair, "baseline")["duration_ms"] for pair in timed_valid]
    jeviphy_times = [_arm(pair, "jeviphy")["duration_ms"] for pair in timed_valid]
    p50_ratio = statistics.median(jeviphy_times) / statistics.median(baseline_times)
    p95_ratio = _percentile(jeviphy_times, 0.95) / _percentile(baseline_times, 0.95)
    passed = (
        jeviphy_precision > baseline_precision
        and jeviphy_first > baseline_first
        and ci95[0] > 0
        and stale_losses == 0
        and controls_identical
        and p50_ratio < 1
        and p95_ratio <= 1.05
    )
    return GateResult(
        "pass" if passed else "fail",
        {
            "baseline_precision_at_5": baseline_precision,
            "jeviphy_precision_at_5": jeviphy_precision,
            "precision_difference_ci95": ci95,
            "baseline_first_hits": baseline_first,
            "jeviphy_first_hits": jeviphy_first,
            "stale_losses": stale_losses,
            "controls_byte_identical": controls_identical,
            "p50_time_ratio": p50_ratio,
            "p95_time_ratio": p95_ratio,
        },
    )


def _score_product(records: list[dict]) -> GateResult:
    seen: set[tuple[str, int]] = set()
    for wrapper in records:
        pair = wrapper.get("pair", wrapper) if isinstance(wrapper, dict) else None
        if not isinstance(pair, dict):
            raise ValueError("product record must contain a pair")
        case_id, pass_index = pair.get("case_id"), pair.get("pass_index")
        if not isinstance(case_id, str) or not isinstance(pass_index, int):
            raise ValueError("product pair has invalid identity")
        key = (case_id, pass_index)
        if key in seen:
            raise ValueError("product evidence contains a duplicate pair")
        seen.add(key)
        if pair.get("stratum") not in {"valid_source", "stale_source", "no_source"}:
            raise ValueError("product pair has an unknown stratum")
        for arm_name in ("baseline", "jeviphy"):
            arm = pair.get(arm_name)
            if not isinstance(arm, dict) or not isinstance(arm.get("success"), bool):
                raise ValueError("product pair must contain boolean success for both arms")
            duration = arm.get("duration_ms")
            if not isinstance(duration, (int, float)) or isinstance(duration, bool) or duration <= 0:
                raise ValueError("product arm duration must be positive")
    pairs = _first_pairs(records)
    if len(pairs) != 30:
        return GateResult("insufficient_evidence", {})
    differences = [
        float(bool(_arm(pair, "jeviphy")["success"]))
        - float(bool(_arm(pair, "baseline")["success"]))
        for pair in pairs
    ]
    success_difference_pp = statistics.fmean(differences) * 100
    ci95 = tuple(value * 100 for value in _paired_bootstrap(differences))
    controls = [pair for pair in pairs if pair["stratum"] == "no_source"]
    if not controls:
        return GateResult("insufficient_evidence", {})
    control_difference_pp = statistics.fmean(
        float(bool(_arm(pair, "jeviphy")["success"]))
        - float(bool(_arm(pair, "baseline")["success"]))
        for pair in controls
    ) * 100
    baseline_times = [_arm(pair, "baseline")["duration_ms"] for pair in pairs]
    jeviphy_times = [_arm(pair, "jeviphy")["duration_ms"] for pair in pairs]
    time_ratio = statistics.median(jeviphy_times) / statistics.median(baseline_times)
    p95_ratio = _percentile(jeviphy_times, 0.95) / _percentile(baseline_times, 0.95)
    token_pairs = [
        pair
        for pair in pairs
        if _arm(pair, "baseline").get("input_tokens") is not None
        and _arm(pair, "jeviphy").get("input_tokens") is not None
    ]
    token_ratio = (
        statistics.median(_arm(pair, "jeviphy")["input_tokens"] for pair in token_pairs)
        / statistics.median(_arm(pair, "baseline")["input_tokens"] for pair in token_pairs)
        if token_pairs
        else None
    )
    efficient = time_ratio <= 0.80 or (token_ratio is not None and token_ratio <= 0.85)
    passed = (
        success_difference_pp >= 10
        and ci95[0] > 0
        and control_difference_pp >= -2
        and efficient
        and p95_ratio <= 1.05
    )
    return GateResult(
        "pass" if passed else "fail",
        {
            "success_difference_pp": success_difference_pp,
            "success_difference_ci95_pp": ci95,
            "control_difference_pp": control_difference_pp,
            "median_time_ratio": time_ratio,
            "p95_time_ratio": p95_ratio,
            "median_input_token_ratio": token_ratio,
        },
    )


def score_run(report: dict) -> Scorecard:
    retrieval = _score_retrieval(report.get("retrieval_records", []))
    product = _score_product(report.get("product_records", []))
    usability_data = report.get("usability")
    if not usability_data:
        usability = GateResult("insufficient_evidence", {})
    else:
        attempts = usability_data.get("attempts", 0)
        successes = usability_data.get("successes", 0)
        median_seconds = usability_data.get("median_seconds")
        systems = {
            str(system).casefold() for system in usability_data.get("operating_systems", [])
        }
        passed = (
            attempts >= 20
            and successes / attempts >= 0.9
            and isinstance(median_seconds, (int, float))
            and median_seconds < 300
            and any("macos" in system for system in systems)
            and any("ubuntu" in system for system in systems)
        )
        usability = GateResult("pass" if passed else "fail", dict(usability_data))
    compatibility_value = report.get("compatibility")
    compatibility = GateResult(
        "pass" if compatibility_value is True else (
            "fail" if compatibility_value is False else "insufficient_evidence"
        ),
        {"graphify_compatible": compatibility_value},
    )
    receipts = report.get("reproductions", [])
    independent = [receipt for receipt in receipts if receipt.get("independent") is True]
    systems = {str(receipt.get("os", "")).casefold() for receipt in independent}
    reproduced = len(independent) >= 2 and any("ubuntu" in system or "linux" in system for system in systems)
    reproduction = GateResult(
        "pass" if reproduced else ("fail" if receipts else "insufficient_evidence"),
        {"independent_receipts": len(independent), "operating_systems": sorted(systems)},
    )
    return Scorecard(retrieval, product, usability, compatibility, reproduction)


def allowed_claim(scorecard: Scorecard) -> str:
    if all(
        gate.status == "pass"
        for gate in (
            scorecard.retrieval,
            scorecard.product,
            scorecard.usability,
            scorecard.compatibility,
            scorecard.reproduction,
        )
    ):
        return REPRODUCED_PRODUCT_WIN
    if all(
        gate.status == "pass"
        for gate in (
            scorecard.retrieval,
            scorecard.product,
            scorecard.usability,
            scorecard.compatibility,
        )
    ):
        return INTERNAL_PRODUCT_WIN
    if all(
        gate.status == "pass"
        for gate in (scorecard.retrieval, scorecard.usability, scorecard.compatibility)
    ):
        return BETA_READY
    if scorecard.retrieval.status == "pass":
        return RETRIEVAL_ONLY
    return NO_DIFFERENCE


def write_scorecard(report_path: Path, output_path: Path, markdown_path: Path) -> Scorecard:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    scorecard = score_run(report)
    claim = allowed_claim(scorecard)
    gates = asdict(scorecard)
    payload = {"allowed_claim": claim, "gates": gates}
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    rows = [
        f"| {name.title()} | {gate['status']} |"
        for name, gate in gates.items()
    ]
    markdown_path.write_text(
        "# Jeviphy v2 scorecard\n\n"
        f"> {claim}\n\n"
        "| Gate | Status |\n| --- | --- |\n"
        + "\n".join(rows)
        + "\n",
        encoding="utf-8",
    )
    return scorecard


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args()
    scorecard = write_scorecard(args.report, args.output, args.markdown)
    gates = (
        scorecard.retrieval,
        scorecard.product,
        scorecard.usability,
        scorecard.compatibility,
        scorecard.reproduction,
    )
    raise SystemExit(0 if all(gate.status == "pass" for gate in gates) else 1)


if __name__ == "__main__":
    main()

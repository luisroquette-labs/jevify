"""Small checks for the paired complete-query stress report."""

import pytest

from tools.jeviphy_full_stress import source_p95_advantage_interval


def test_source_p95_interval_keeps_controls_out_of_activation_claim():
    rows = [
        {"id": case_id, "source_backed": True, "baseline_ms": 100.0,
         "jeviphy_ms": 10.0}
        for case_id in ("a", "b") for _ in range(3)
    ] + [
        {"id": "control", "source_backed": False, "baseline_ms": 10.0,
         "jeviphy_ms": 1000.0}
        for _ in range(3)
    ]
    assert source_p95_advantage_interval(rows, resamples=100) == [90.0, 90.0]
    with pytest.raises(ValueError, match="source-backed"):
        source_p95_advantage_interval(rows[-3:], resamples=100)

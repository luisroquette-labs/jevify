"""Small checks for the paired complete-query stress report."""

import pytest
import networkx as nx

from tools.jeviphy_full_stress import (
    p95_advantage_interval,
    source_p95_advantage_interval,
    validate_frozen_cases,
)


def test_frozen_cases_reject_gold_name_and_source_leaks():
    graph = nx.Graph()
    graph.add_node("gold", label="target_name()", source_file="src/right.py")
    case = {
        "id": "case", "question": "Where is the behavior?", "summary": "Reviewed source.",
        "source_paths": ["src/right.py"], "gold_node_ids": ["gold"],
    }
    validate_frozen_cases([case], graph)
    with pytest.raises(ValueError, match="label leaked"):
        validate_frozen_cases([{**case, "question": "Call target_name please"}], graph)
    with pytest.raises(ValueError, match="source differs"):
        validate_frozen_cases([{**case, "source_paths": ["src/wrong.py"]}], graph)


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
    assert p95_advantage_interval(rows, resamples=100) == [-990.0, 90.0]
    with pytest.raises(ValueError, match="source-backed"):
        source_p95_advantage_interval(rows[-3:], resamples=100)

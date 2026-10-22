import json
from collections import Counter
from copy import deepcopy

import pytest

from tools.jevify_eval_contract import STRATUM_COUNTS, load_manifest


SHA = "a" * 40


def manifest_dict():
    repos = [
        {
            "id": f"repo-{index}",
            "url": f"https://github.com/example/repo-{index}",
            "language": ("Python", "TypeScript", "Go")[index % 3],
        }
        for index in range(1, 7)
    ]
    strata = [name for name, count in STRATUM_COUNTS.items() for _ in range(count)]
    cases = []
    for index, stratum in enumerate(strata):
        repo_index = index // 20 + 1
        no_source = stratum == "no_source"
        cases.append(
            {
                "id": f"case-{index:03}",
                "repo_id": f"repo-{repo_index}",
                "base_commit": SHA,
                "stratum": stratum,
                "question": f"What behavior should case {index} preserve?",
                "timeout_seconds": 300,
                "image": f"swebench/example:{index}",
                "fail_to_pass": [f"test_case_{index}"],
                "pass_to_pass": [],
                "gold_files": [f"src/file_{index}.py"],
                "gold_symbols": [f"target_{index}"],
                "memory": {
                    "summary": "The earlier change preserved the public contract.",
                    "source_paths": [] if no_source else [f"src/file_{index}.py"],
                    "source_commit": None if no_source else SHA,
                    "reviewed_at": None if no_source else "2026-10-19T00:00:00Z",
                },
                "holdout": repo_index == 1,
            }
        )
    return {
        "schema_version": 2,
        "graphify_commit": SHA,
        "dataset_id": "SWE-bench/SWE-bench_Multilingual",
        "dataset_revision": SHA,
        "repos": repos,
        "cases": cases,
    }


def write_manifest(tmp_path, data):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_contract_accepts_exact_frozen_shape(tmp_path):
    manifest = load_manifest(write_manifest(tmp_path, manifest_dict()))
    assert Counter(case.stratum for case in manifest.cases) == STRATUM_COUNTS
    assert sum(case.holdout for case in manifest.cases) == 20


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("duplicate_id", "duplicate case ID"),
        ("branch_ref", "base_commit must be 40 lowercase hex characters"),
        ("leaked_symbol", "gold symbol leaked"),
        ("missing_oracle", "at least one fail-to-pass test is required"),
        ("short_holdout", "holdout needs at least 20 cases"),
        ("two_languages", "at least 3 languages"),
    ],
)
def test_contract_rejects_invalid_cohort(tmp_path, mutation, message):
    data = deepcopy(manifest_dict())
    if mutation == "duplicate_id":
        data["cases"][1]["id"] = data["cases"][0]["id"]
    elif mutation == "branch_ref":
        data["cases"][0]["base_commit"] = "main"
    elif mutation == "leaked_symbol":
        data["cases"][0]["question"] += " target_0"
    elif mutation == "missing_oracle":
        data["cases"][0]["fail_to_pass"] = []
    elif mutation == "short_holdout":
        for case in data["cases"]:
            case["holdout"] = False
    elif mutation == "two_languages":
        for index, repo in enumerate(data["repos"]):
            repo["language"] = ("Python", "Go")[index % 2]
    with pytest.raises(ValueError, match=message):
        load_manifest(write_manifest(tmp_path, data))


def test_contract_rejects_unsafe_path(tmp_path):
    data = manifest_dict()
    data["cases"][0]["memory"]["source_paths"] = ["../secret.txt"]
    with pytest.raises(ValueError, match="safe relative POSIX path"):
        load_manifest(write_manifest(tmp_path, data))


def test_contract_requires_exact_holdout_size(tmp_path):
    data = manifest_dict()
    data["cases"][0]["holdout"] = False
    with pytest.raises(ValueError, match="at least 20"):
        load_manifest(write_manifest(tmp_path, data))

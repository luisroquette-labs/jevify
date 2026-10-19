"""Paired offline answer and retrieval stress test on a private frozen cohort."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
import platform
import random
import statistics
import subprocess
import time
from collections import defaultdict
from pathlib import Path

from graphify.serve import _read_graph
from tools.jev_memory_pilot import candidate_pool, query_unscoped_graphify, query_with_decisions
from tools.jeviphy_stress import percentile


def answer_hits(output: str, gold: list[str], graph) -> int:
    return sum(
        f'NODE {graph.nodes[nid].get("label", nid)} '
        f'[src={graph.nodes[nid].get("source_file", "")} ' in output
        for nid in gold
    )


def validate_frozen_cases(cases: list[dict], graph) -> None:
    """Reject labels leaked into prompts and gold nodes outside cited sources."""
    for case in cases:
        text = f'{case["question"]} {case["summary"]}'.casefold()
        cited = set(case["source_paths"])
        for node_id in case["gold_node_ids"]:
            node = graph.nodes[node_id]
            name = node.get("label", "").removesuffix("()").lstrip(".").casefold()
            if name and name in text:
                raise ValueError(f'gold label leaked into case {case["id"]}')
            if node.get("source_file") not in cited:
                raise ValueError(f'gold source differs from case {case["id"]}')


def p95_advantage_interval(
    rows: list[dict], *, source_only: bool = False, resamples: int = 10_000,
) -> list[float]:
    """Resample cases, keeping their repeated paired timings together."""
    by_case = defaultdict(list)
    for row in rows:
        if not source_only or row["source_backed"]:
            by_case[row["id"]].append(row)
    ids = sorted(by_case)
    if not ids:
        raise ValueError("matching cases are required")
    rng = random.Random(20261018)
    advantages = []
    for _ in range(resamples):
        sample = [row for case_id in rng.choices(ids, k=len(ids)) for row in by_case[case_id]]
        advantages.append(
            percentile([row["baseline_ms"] for row in sample], .95)
            - percentile([row["jeviphy_ms"] for row in sample], .95)
        )
    return [round(percentile(advantages, quantile), 2) for quantile in (.025, .975)]


def source_p95_advantage_interval(rows: list[dict], *, resamples: int = 10_000) -> list[float]:
    """Backward-compatible source-only interval used by existing reports."""
    try:
        return p95_advantage_interval(rows, source_only=True, resamples=resamples)
    except ValueError as error:
        raise ValueError("source-backed cases are required") from error


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--graph", type=Path, required=True)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--passes", type=int, default=3)
    parser.add_argument("--source-cases", type=int, default=20)
    parser.add_argument("--control-cases", type=int, default=10)
    args = parser.parse_args()
    if args.passes < 3:
        parser.error("at least three passes are required")
    if args.output.exists() or args.output.parent.stat().st_mode & 0o077:
        parser.error("output must not exist and its directory must be private")
    if args.manifest.stat().st_mode & 0o077:
        parser.error("input manifest must be mode 0600")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    cases = manifest["cases"]
    expected_cases = args.source_cases + args.control_cases
    if (args.source_cases < 1 or args.control_cases < 1
            or len(cases) != expected_cases
            or len({case["id"] for case in cases}) != expected_cases):
        parser.error("manifest case counts differ from the requested frozen cohort")
    if (sum(case["source_backed"] for case in cases) != args.source_cases
            or any(not case["source_paths"] or not case["gold_node_ids"]
                   for case in cases if case["source_backed"])
            or any(case["source_paths"] or case["gold_node_ids"]
                   for case in cases if not case["source_backed"])):
        parser.error("manifest source/control shape differs from the requested cohort")
    graph_hash = hashlib.sha256(args.graph.read_bytes()).hexdigest()
    source_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=args.repo, text=True,
    ).strip()
    if graph_hash != manifest["graph_sha256"] or source_commit != manifest["source_commit"]:
        parser.error("graph or source checkout differs from frozen manifest")
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=args.repo):
        parser.error("source checkout has uncommitted changes")
    graph = _read_graph(str(args.graph))
    if any(nid not in graph for case in cases for nid in case["gold_node_ids"]):
        parser.error("gold label is absent from the pinned graph")
    try:
        validate_frozen_cases(cases, graph)
    except ValueError as error:
        parser.error(str(error))

    semantic = []
    for case in cases:
        gold = set(case["gold_node_ids"])
        baseline = candidate_pool(args.graph, args.repo, case["question"], graph=graph)
        assisted = candidate_pool(
            args.graph, args.repo, case["question"], [case["summary"]],
            source_paths=case["source_paths"], fast_source=True, graph=graph,
        )
        semantic.append({
            "id": case["id"], "source_backed": case["source_backed"],
            "gold_ids": case["gold_node_ids"],
            "baseline_ids": [item["node_id"] for item in baseline],
            "jeviphy_ids": [item["node_id"] for item in assisted],
            "baseline_hits": len(gold & {item["node_id"] for item in baseline[:5]}),
            "jeviphy_hits": len(gold & {item["node_id"] for item in assisted[:5]}),
            "source_scoped": bool(assisted and assisted[0].get("source_scoped")),
        })

    def run(case: dict, assisted: bool) -> tuple[float, str]:
        start = time.perf_counter_ns()
        if assisted and not case["source_paths"]:
            output = query_unscoped_graphify(args.graph, case["question"])
        elif assisted:
            loaded = _read_graph(str(args.graph))
            candidates = candidate_pool(
                args.graph, args.repo, case["question"], [case["summary"]],
                source_paths=case["source_paths"], fast_source=True, graph=loaded,
            )
            with contextlib.redirect_stderr(io.StringIO()):
                output = query_with_decisions(
                    args.graph, args.repo,
                    {"id": case["id"], "question": case["question"], "observations": []},
                    candidates, {}, eligible_node_ids=set(), threshold=.8,
                    candidate_mode="fast-source", graph=loaded,
                )
        else:
            output = query_unscoped_graphify(args.graph, case["question"])
        return (time.perf_counter_ns() - start) / 1_000_000, output

    run(cases[0], False)
    run(cases[0], True)
    rows = []
    first_answers = []
    for repeat in range(args.passes):
        for index, case in enumerate(cases):
            order = (False, True) if (repeat + index) % 2 == 0 else (True, False)
            outputs = {arm: run(case, arm) for arm in order}
            baseline_ms, baseline_text = outputs[False]
            jeviphy_ms, jeviphy_text = outputs[True]
            rows.append({
                "id": case["id"], "pass": repeat + 1,
                "source_backed": case["source_backed"],
                "baseline_ms": baseline_ms, "jeviphy_ms": jeviphy_ms,
                "baseline_answer_hits": answer_hits(baseline_text, case["gold_node_ids"], graph),
                "jeviphy_answer_hits": answer_hits(jeviphy_text, case["gold_node_ids"], graph),
                "same_answer": baseline_text == jeviphy_text,
            })
            if repeat == 0:
                first_answers.append({
                    "id": case["id"], "baseline": baseline_text, "jeviphy": jeviphy_text,
                })
        print(f"pass {repeat + 1}/{args.passes} complete", flush=True)

    baseline_ms = [row["baseline_ms"] for row in rows]
    jeviphy_ms = [row["jeviphy_ms"] for row in rows]
    source_rows = [row for row in rows if row["source_backed"]]
    controls = [row for row in rows if not row["source_backed"]]
    summary = {
        "cases": len(cases), "paired_runs": len(rows),
        "source_backed_cases": sum(case["source_backed"] for case in cases),
        "baseline_precision_at_5": sum(row["baseline_hits"] for row in semantic) / (5 * len(cases)),
        "jeviphy_precision_at_5": sum(row["jeviphy_hits"] for row in semantic) / (5 * len(cases)),
        "source_baseline_hits": sum(row["baseline_hits"] for row in semantic if row["source_backed"]),
        "source_jeviphy_hits": sum(row["jeviphy_hits"] for row in semantic if row["source_backed"]),
        "source_gains": sum(row["jeviphy_hits"] > row["baseline_hits"] for row in semantic if row["source_backed"]),
        "source_losses": sum(row["jeviphy_hits"] < row["baseline_hits"] for row in semantic if row["source_backed"]),
        "source_scoped_count": sum(row["source_scoped"] for row in semantic if row["source_backed"]),
        "first_pass_baseline_answer_hits": sum(
            row["baseline_answer_hits"] for row in rows[:len(cases)]
        ),
        "first_pass_jeviphy_answer_hits": sum(
            row["jeviphy_answer_hits"] for row in rows[:len(cases)]
        ),
        "baseline_p50_ms": round(statistics.median(baseline_ms), 2),
        "jeviphy_p50_ms": round(statistics.median(jeviphy_ms), 2),
        "baseline_p95_ms": round(percentile(baseline_ms, .95), 2),
        "jeviphy_p95_ms": round(percentile(jeviphy_ms, .95), 2),
        "pooled_p95_advantage_ci95_ms": p95_advantage_interval(rows),
        "jeviphy_faster_pairs": sum(a < b for a, b in zip(jeviphy_ms, baseline_ms)),
        "source_baseline_p50_ms": round(percentile([row["baseline_ms"] for row in source_rows], .5), 2),
        "source_jeviphy_p50_ms": round(percentile([row["jeviphy_ms"] for row in source_rows], .5), 2),
        "source_baseline_p95_ms": round(percentile([row["baseline_ms"] for row in source_rows], .95), 2),
        "source_jeviphy_p95_ms": round(percentile([row["jeviphy_ms"] for row in source_rows], .95), 2),
        "source_p95_advantage_ci95_ms": source_p95_advantage_interval(rows),
        "source_faster_pairs": sum(row["jeviphy_ms"] < row["baseline_ms"] for row in source_rows),
        "first_pass_source_answer_losses": sum(
            row["jeviphy_answer_hits"] < row["baseline_answer_hits"]
            for row in rows[:len(cases)] if row["source_backed"]
        ),
        "controls_byte_identical": all(row["same_answer"] for row in controls),
    }
    report = {
        "manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
        "graph_sha256": graph_hash, "source_commit": source_commit,
        "runner_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parents[1], text=True,
        ).strip(),
        "python": platform.python_version(), "machine": platform.machine(),
        "summary": summary, "semantic": semantic, "rows": rows,
        "first_pass_answers": first_answers,
    }
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(report, stream)
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()

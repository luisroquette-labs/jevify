"""Paired, offline Graphify/Jevify candidate stress test over a private cohort."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import resource
import statistics
import subprocess
import time
from pathlib import Path

from tools.jev_memory_pilot import candidate_pool


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    return ordered[lower] + (ordered[min(lower + 1, len(ordered) - 1)] - ordered[lower]) * (position - lower)


def peak_rss_bytes() -> int:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return value * 1024 if platform.system() == "Linux" else value


def summarize(rows: list[dict]) -> dict:
    baseline = [row["baseline_ms"] for row in rows]
    assisted = [row["assisted_ms"] for row in rows]
    first_pass = rows[:30]
    scored = [row for row in first_pass if row["source_backed"]]
    return {
        "cases": len(first_pass),
        "source_backed_cases": len(scored),
        "paired_runs": len(rows),
        "identical_top_five": sum(row["same_top_five"] for row in rows),
        "baseline_top_five_prefix_preserved": sum(row["baseline_top_five_prefix_preserved"]
                                                   for row in rows),
        "baseline_file_hit_top_ten": sum(row["baseline_file_hit"] for row in scored),
        "assisted_file_hit_top_ten": sum(row["assisted_file_hit"] for row in scored),
        "file_hit_gains": sum(row["assisted_file_hit"] and not row["baseline_file_hit"] for row in scored),
        "file_hit_losses": sum(row["baseline_file_hit"] and not row["assisted_file_hit"] for row in scored),
        "baseline_p50_ms": round(statistics.median(baseline), 2),
        "baseline_p95_ms": round(percentile(baseline, .95), 2),
        "assisted_p50_ms": round(statistics.median(assisted), 2),
        "assisted_p95_ms": round(percentile(assisted, .95), 2),
        "median_paired_ratio": round(statistics.median(a / b for a, b in zip(assisted, baseline)), 3),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--graph", type=Path, required=True)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--passes", type=int, default=3)
    parser.add_argument("--assisted-mode", choices=("memory", "fast-source"), default="memory")
    args = parser.parse_args()
    if args.passes < 3:
        parser.error("at least three passes are required")
    if args.output.exists() or args.output.parent.stat().st_mode & 0o077:
        parser.error("output must not exist and its directory must be private")
    if args.manifest.stat().st_mode & 0o077:
        parser.error("input manifest must be mode 0600")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    cases = manifest["cases"]
    if len(cases) != 30 or len({case["id"] for case in cases}) != 30:
        parser.error("expected 30 distinct frozen cases")
    graph_hash = hashlib.sha256(args.graph.read_bytes()).hexdigest()
    source_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=args.repo, text=True,
    ).strip()
    if graph_hash != manifest["graph_sha256"] or source_commit != manifest["source_commit"]:
        parser.error("graph or source checkout differs from frozen manifest")
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=args.repo):
        parser.error("source checkout has uncommitted changes")

    def run(case: dict, assisted: bool) -> tuple[float, list[dict]]:
        start = time.perf_counter_ns()
        pool = candidate_pool(
            args.graph, args.repo, case["question"],
            [case["summary"]] if assisted else None,
            source_paths=case["source_paths"] if assisted else None,
            fast_source=assisted and args.assisted_mode == "fast-source",
        )
        return (time.perf_counter_ns() - start) / 1_000_000, pool

    # Warm each path once; opposite order on alternating pairs limits order bias.
    run(cases[0], False)
    run(cases[0], True)
    rows = []
    for pass_number in range(args.passes):
        for index, case in enumerate(cases):
            order = (False, True) if (pass_number + index) % 2 == 0 else (True, False)
            outputs = {assisted: run(case, assisted) for assisted in order}
            baseline_ms, baseline = outputs[False]
            assisted_ms, assisted_pool = outputs[True]
            sources = set(case["source_paths"])
            rows.append({
                "case_id": case["id"],
                "pass": pass_number + 1,
                "first_arm": "assisted" if order[0] else "baseline",
                "source_backed": case["source_backed"],
                "baseline_ms": baseline_ms,
                "assisted_ms": assisted_ms,
                "same_top_five": [item["node_id"] for item in baseline[:5]] == [item["node_id"] for item in assisted_pool[:5]],
                "baseline_top_five_prefix_preserved": (
                    [item["node_id"] for item in assisted_pool[:min(5, len(baseline))]]
                    == [item["node_id"] for item in baseline[:5]]
                ),
                "baseline_file_hit": any(item["source_file"] in sources for item in baseline) if sources else False,
                "assisted_file_hit": any(item["source_file"] in sources for item in assisted_pool) if sources else False,
                "baseline_ids": [item["node_id"] for item in baseline],
                "assisted_ids": [item["node_id"] for item in assisted_pool],
            })
        print(f"pass {pass_number + 1}/{args.passes} complete", flush=True)
    report = {
        "assisted_mode": args.assisted_mode,
        "graph_sha256": graph_hash,
        "manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
        "source_commit": source_commit,
        "python": platform.python_version(),
        "machine": platform.machine(),
        "peak_rss_bytes": peak_rss_bytes(),
        "summary": summarize(rows),
        "rows": rows,
    }
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps(report["summary"], sort_keys=True))


if __name__ == "__main__":
    main()

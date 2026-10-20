# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "graphifyy @ git+https://github.com/luisroquette-labs/jeviphy.git@119111cb5022b6ccf252c55b0644e46e4f05d9be",
# ]
# ///
"""Portable Jeviphy entry point for Claude Code and Codex skill installs."""

import argparse
import json
import os
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from tools.jev_memory_pilot import main as query_main
from tools.jeviphy_autorun import ContextError, auto, inspect_context
from tools.jeviphy_eval_contract import load_manifest
from tools.jeviphy_product_eval import balanced_order, run_retrieval_pair


def head(repo: Path) -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()


def doctor(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="jeviphy doctor")
    parser.add_argument("--repo", type=Path)
    parser.add_argument("--graph", type=Path)
    parser.add_argument("--corpus", type=Path)
    args = parser.parse_args(argv)
    state = inspect_context(Path.cwd(), repo=args.repo, graph=args.graph)
    checks = {
        "repo": state.context.repo.is_dir(),
        "graph": state.context.graph.is_file(),
        "graph_current": state.status == "ready",
    }
    if args.corpus is not None:
        checks["corpus"] = args.corpus.is_file()
        checks["corpus_private"] = (
            args.corpus.is_file() and args.corpus.stat().st_mode & 0o077 == 0
        )
    print(json.dumps({"ok": all(checks.values()), "checks": checks}, sort_keys=True))
    return 0 if all(checks.values()) else 1


def benchmark(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="jeviphy benchmark")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--graph", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--passes", type=int, default=5)
    args = parser.parse_args(argv)
    if args.passes < 5:
        parser.error("at least five measured passes are required")
    manifest = load_manifest(args.manifest)
    case = next((item for item in manifest.cases if item.id == args.case_id), None)
    if case is None:
        parser.error("case ID not found")
    if head(args.repo) != case.base_commit:
        parser.error("repository HEAD differs from case base_commit")
    run_retrieval_pair(
        case, args.graph, args.repo, pass_index=-1, order=("graphify", "jeviphy")
    )
    records = []
    for pass_index in range(args.passes):
        pair, _ = run_retrieval_pair(
            case,
            args.graph,
            args.repo,
            pass_index=pass_index,
            order=balanced_order(0, pass_index),
        )
        records.append(asdict(pair))
    if args.output.exists():
        parser.error("output already exists")
    descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump({"case_id": case.id, "records": records}, stream, sort_keys=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments or arguments[0] == "auto":
        return auto(arguments[1:] if arguments else [], Path.cwd())
    if arguments[0] == "--help":
        return auto(arguments, Path.cwd())
    if arguments[0] == "doctor":
        return doctor(arguments[1:])
    if arguments[0] == "query":
        return query_main(arguments[1:])
    if arguments[0] == "benchmark":
        return benchmark(arguments[1:])
    raise SystemExit("unknown command; use auto --question QUESTION")

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ContextError, ValueError) as exc:
        print(f"jeviphy: {exc}", file=sys.stderr)
        raise SystemExit(1) from None

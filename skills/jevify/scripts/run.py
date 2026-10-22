# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "graphifyy @ git+https://github.com/luisroquette-labs/jevify.git@253e1fd05972f0e107c75325a56d510260df80c3",
# ]
# ///
"""Portable Jevify entry point for Claude Code and Codex skill installs."""

import argparse
import json
import os
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from tools.jevify_autorun import (
    ContextError,
    auto,
    finalize_update,
    inspect_context,
    run_update,
)


def head(repo: Path) -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()


def doctor(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="jevify doctor")
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
    freshness = asdict(state.freshness)
    freshness["changed_by_type"] = dict(state.freshness.changed_by_type)
    freshness["deleted_by_type"] = dict(state.freshness.deleted_by_type)
    print(json.dumps({
        "ok": all(checks.values()), "checks": checks, "freshness": freshness,
    }, sort_keys=True))
    return 0 if all(checks.values()) else 1


def _receipt_payload(receipt, repo: Path | None, graph: Path | None) -> dict:
    insights = receipt.insights
    freshness = receipt.pending_after or receipt.pending_before
    stats = insights.graph_stats if insights else receipt.after or receipt.before
    payload = asdict(receipt)
    payload.pop("insights", None)
    payload.update({
        "schema_version": 2,
        "repo": str(repo.resolve()) if repo else None,
        "graph": str(graph.resolve()) if graph else None,
        "question": None,
        "mode": "graph_only",
        "live_enrichment": "not_requested",
        "answer": None,
        "freshness": asdict(freshness),
        "update": {
            "status": receipt.status,
            "route": asdict(receipt.route),
            "diagnostic": receipt.diagnostic,
            "report_path": receipt.report_path,
            "visualization": receipt.visualization,
        },
        "graph_stats": asdict(stats) if stats else {},
        "health": insights.health if insights else receipt.health or {},
        "god_nodes": list(insights.god_nodes) if insights else [],
        "connections": list(insights.connections) if insights else [],
        "questions": [asdict(item) for item in insights.questions] if insights else [],
        "answer_truncated": False,
        "suggested_narrowing": None,
    })
    return payload


def _render_receipt(payload: dict) -> str:
    update_data = payload["update"]
    stats = payload["graph_stats"]
    health = payload["health"]
    lines = [
        "Update",
        f"- Status: {update_data['status']}",
        f"- Route: {update_data['route']['kind']}",
    ]
    if update_data["diagnostic"]:
        lines.append(f"- Diagnostic: {update_data['diagnostic']}")
    lines.extend([
        "",
        "Graph",
        f"- Nodes: {stats.get('nodes', 'unavailable')}",
        f"- Edges: {stats.get('edges', 'unavailable')}",
        f"- Communities: {stats.get('communities', 'unavailable')}",
        "",
        "Health",
    ])
    caveats = [(key, value) for key, value in health.items() if value]
    lines.extend(
        [f"- {key}: {value}" for key, value in caveats]
        or ["- No nonzero diagnostic counts."]
    )
    lines.extend(["", "God Nodes"])
    lines.extend(
        [f"- {item['label']}: {item['degree']} relations" for item in payload["god_nodes"]]
        or ["- None available."]
    )
    lines.extend(["", "Connections"])
    lines.extend(
        [f"- {item['source']} -> {item['target']}" for item in payload["connections"]]
        or ["- None available."]
    )
    lines.extend(["", "Suggested Questions"])
    lines.extend(
        [f"- {item['text']}" for item in payload["questions"]]
        or ["- No source-backed question signal."]
    )
    lines.extend(["", "Memory / JEV", "- Not requested; no paid API used."])
    return "\n".join(lines) + "\n"


def update(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="jevify update")
    parser.add_argument("--repo", type=Path)
    parser.add_argument("--graph", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    receipt = run_update(Path.cwd(), repo=args.repo, graph=args.graph)
    state = inspect_context(Path.cwd(), repo=args.repo, graph=args.graph)
    payload = _receipt_payload(receipt, state.context.repo, state.context.graph)
    if args.json:
        print(json.dumps(payload, sort_keys=True))
    else:
        print(_render_receipt(payload), end="")
    if receipt.status == "requires_host":
        return 20
    return 0 if receipt.status in {"already_current", "updated"} else 1


def finalize(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="jevify finalize")
    parser.add_argument("--repo", type=Path)
    parser.add_argument("--graph", type=Path)
    parser.add_argument("--backup", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    receipt = finalize_update(
        Path.cwd(), repo=args.repo, graph=args.graph, backup=args.backup,
    )
    state = inspect_context(Path.cwd(), repo=args.repo, graph=args.graph)
    payload = _receipt_payload(receipt, state.context.repo, state.context.graph)
    if args.json:
        print(json.dumps(payload, sort_keys=True))
    else:
        print(_render_receipt(payload), end="")
    return 0 if receipt.status == "updated" else 1


def benchmark(argv: list[str]) -> int:
    from tools.jevify_eval_contract import load_manifest
    from tools.jevify_product_eval import balanced_order, run_retrieval_pair

    parser = argparse.ArgumentParser(prog="jevify benchmark")
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
        case, args.graph, args.repo, pass_index=-1, order=("graphify", "jevify")
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
    if arguments[0] == "update":
        return update(arguments[1:])
    if arguments[0] == "finalize":
        return finalize(arguments[1:])
    if arguments[0] == "query":
        from tools.jev_memory_pilot import main as query_main

        return query_main(arguments[1:])
    if arguments[0] == "benchmark":
        return benchmark(arguments[1:])
    raise SystemExit("unknown command; use auto --question QUESTION")

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ContextError, ValueError) as exc:
        print(f"jevify: {exc}", file=sys.stderr)
        raise SystemExit(1) from None

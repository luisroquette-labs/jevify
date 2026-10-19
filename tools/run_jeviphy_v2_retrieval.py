"""Build pinned graphs and run the complete Jeviphy v2 offline retrieval cohort."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from dataclasses import asdict
from pathlib import Path

from tools.jeviphy_eval_contract import load_manifest
from tools.jeviphy_product_eval import (
    append_pair,
    balanced_order,
    completed_pairs,
    current_pins,
    run_retrieval_pair,
)


MARKER = ".jeviphy-v2-workspace"


def safe_name(repo_id: str) -> str:
    return repo_id.replace("/", "__")


def prepare_workspace(path: Path) -> None:
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.chmod(0o700)
    marker = path / MARKER
    if marker.exists() and marker.read_text(encoding="utf-8") != "jeviphy-v2\n":
        raise ValueError("workspace marker differs")
    marker.write_text("jeviphy-v2\n", encoding="utf-8")


def ensure_graph_commit(path: Path, expected: str) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    actual = data.get("built_at_commit")
    if actual not in {None, expected}:
        raise ValueError("Graphify stamped a different source commit")
    if actual is None:
        data["built_at_commit"] = expected
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
        os.replace(temporary, path)


def reset_graph_outputs(graph_dir: Path) -> None:
    """Remove case-specific output while retaining content-addressed extraction cache."""
    if not graph_dir.exists():
        return
    for path in graph_dir.iterdir():
        if path.name == "cache":
            continue
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()


def run(args: argparse.Namespace) -> None:
    manifest_path = args.manifest.resolve()
    project = args.project.resolve()
    workspace = args.workspace.resolve()
    graphify = args.graphify.resolve()
    manifest = load_manifest(manifest_path)
    prepare_workspace(workspace)
    repos_root = workspace / "repos"
    repos_root.mkdir(exist_ok=True)
    journal = workspace / "retrieval.jsonl"
    graphify_argv = [str(graphify), "update", ".", "--no-cluster"]
    pins = current_pins(manifest_path, manifest.graphify_commit, project, graphify_argv)
    done = completed_pairs(journal, pins)
    selected = [case for case in manifest.cases if not args.case_id or case.id == args.case_id]
    if args.case_id and not selected:
        raise ValueError("case ID not found")
    if args.max_cases:
        selected = selected[: args.max_cases]
    expected = {(case.id, pass_index) for case in selected for pass_index in range(args.passes)}
    env = dict(os.environ)
    for key in (
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "JEV_MEMORY_PILOT_API_KEY",
    ):
        env.pop(key, None)

    for case_index, case in enumerate(selected):
        if all((case.id, pass_index) in done for pass_index in range(args.passes)):
            continue
        repo = repos_root / safe_name(case.repo_id)
        if not repo.exists():
            subprocess.run(
                ["git", "clone", "--filter=blob:none", "--no-checkout", f"https://github.com/{case.repo_id}.git", str(repo)],
                check=True,
            )
        subprocess.run(
            ["git", "fetch", "--depth=1", "origin", case.base_commit], cwd=repo, check=True
        )
        subprocess.run(
            ["git", "checkout", "--detach", "--force", case.base_commit], cwd=repo, check=True
        )
        graph_dir = repo / "graphify-out"
        reset_graph_outputs(graph_dir)
        subprocess.run(graphify_argv, cwd=repo, env=env, check=True)
        graph_path = graph_dir / "graph.json"
        ensure_graph_commit(graph_path, case.base_commit)
        run_retrieval_pair(
            case,
            graph_path,
            repo,
            pass_index=-1,
            order=("graphify", "jeviphy"),
        )
        for pass_index in range(args.passes):
            if (case.id, pass_index) in done:
                continue
            pair, _ = run_retrieval_pair(
                case,
                graph_path,
                repo,
                pass_index=pass_index,
                order=balanced_order(case_index, pass_index),
            )
            append_pair(journal, pins, pair)
            done.add((case.id, pass_index))
        reset_graph_outputs(graph_dir)
        print(f"{case_index + 1}/{len(selected)} {case.id}", flush=True)

    if done & expected != expected:
        raise ValueError("retrieval cohort is incomplete")
    records = [json.loads(line) for line in journal.read_text(encoding="utf-8").splitlines()]
    output = workspace / "retrieval-report.json"
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(
            {
                "pins": asdict(pins),
                "manifest": str(manifest_path),
                "retrieval_records": [
                    record for record in records
                    if (record["pair"]["case_id"], record["pair"]["pass_index"]) in expected
                ],
            },
            stream,
            sort_keys=True,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--graphify", type=Path, required=True)
    parser.add_argument("--passes", type=int, default=5)
    parser.add_argument("--max-cases", type=int)
    parser.add_argument("--case-id")
    args = parser.parse_args()
    if args.passes < 5:
        parser.error("at least five passes are required")
    if args.max_cases is not None and args.max_cases < 1:
        parser.error("max-cases must be positive")
    run(args)


if __name__ == "__main__":
    main()

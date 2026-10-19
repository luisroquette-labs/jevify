#!/usr/bin/env python3
"""Run the two approved maintainer outreach steps without an open agent session."""

from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR if (SCRIPT_DIR / "docs/outreach").is_dir() else SCRIPT_DIR.parent
DEFAULT_STATE = Path.home() / ".local/share/jeviphy-outreach/state.json"
TASKS = (
    {
        "id": "graphify-evidence-v1",
        "due": "2026-10-21T10:30:00-03:00",
        "action": "graphify_comment",
    },
    {
        "id": "claude-mem-source-paths-v1",
        "due": "2026-10-24T11:00:00-03:00",
        "action": "claude_mem_discussion",
    },
)


def run_gh(args: list[str]) -> str:
    result = subprocess.run(
        ["gh", *args],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return result.stdout


def graphify_comment() -> str:
    marker = "jeviphy-outreach:graphify-evidence-v1"
    comments = run_gh([
        "api", "--paginate", "repos/Graphify-Labs/graphify/issues/4530/comments",
        "--jq", ".[].body",
    ])
    if marker in comments:
        return "already_present"
    run_gh([
        "pr", "comment", "4530", "--repo", "Graphify-Labs/graphify",
        "--body-file", str(ROOT / "docs/outreach/graphify-pr-4530.md"),
    ])
    return "published"


def claude_mem_discussion() -> str:
    marker = "jeviphy-outreach:claude-mem-source-paths-v1"
    query = """
      query($owner:String!, $name:String!) {
        repository(owner:$owner, name:$name) {
          id
          discussionCategories(first:20) { nodes { id name } }
          discussions(first:50, orderBy:{field:CREATED_AT, direction:DESC}) {
            nodes { body url }
          }
        }
      }
    """
    payload = json.loads(run_gh([
        "api", "graphql", "-f", f"query={query}",
        "-F", "owner=thedotmack", "-F", "name=claude-mem",
    ]))
    repo = payload["data"]["repository"]
    if any(marker in (node.get("body") or "") for node in repo["discussions"]["nodes"]):
        return "already_present"

    categories = {node["name"].casefold(): node["id"] for node in repo["discussionCategories"]["nodes"]}
    category_id = categories.get("show and tell") or categories.get("ideas")
    if not category_id:
        raise RuntimeError("Claude Mem has neither a Show and tell nor Ideas discussion category")

    mutation = """
      mutation($repositoryId:ID!, $categoryId:ID!, $title:String!, $body:String!) {
        createDiscussion(input:{repositoryId:$repositoryId, categoryId:$categoryId, title:$title, body:$body}) {
          discussion { url }
        }
      }
    """
    body = (ROOT / "docs/outreach/claude-mem-discussion.md").read_text()
    run_gh([
        "api", "graphql", "-f", f"query={mutation}",
        "-F", f"repositoryId={repo['id']}", "-F", f"categoryId={category_id}",
        "-f", "title=Experiment: optional source_paths bridge from reviewed memory to Graphify",
        "-f", f"body={body}",
    ])
    return "published"


ACTIONS = {
    "graphify_comment": graphify_comment,
    "claude_mem_discussion": claude_mem_discussion,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--now", help="ISO timestamp override for deterministic checks")
    parser.add_argument("--state-file", type=Path, default=DEFAULT_STATE)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    now = dt.datetime.fromisoformat(args.now) if args.now else dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        raise ValueError("--now must include a timezone")

    args.state_file.parent.mkdir(parents=True, exist_ok=True)
    lock_path = args.state_file.with_suffix(".lock")
    with lock_path.open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state: dict[str, Any] = {}
        if args.state_file.exists():
            state = json.loads(args.state_file.read_text())

        changed = False
        for task in TASKS:
            if task["id"] in state:
                continue
            due = dt.datetime.fromisoformat(task["due"])
            if now < due:
                continue
            if args.dry_run:
                print(f"due: {task['id']} ({task['action']})")
                continue
            outcome = ACTIONS[task["action"]]()
            state[task["id"]] = {
                "completed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "outcome": outcome,
            }
            changed = True
            print(f"completed: {task['id']} ({outcome})")

        if changed:
            temporary = args.state_file.with_suffix(".tmp")
            temporary.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
            os.replace(temporary, args.state_file)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BlockingIOError:
        print("another outreach scheduler instance is running", file=sys.stderr)
        raise SystemExit(0)

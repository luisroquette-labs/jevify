"""Zero-configuration orchestration for the portable Jeviphy runner."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import networkx as nx

from graphify.analyze import suggest_questions
from graphify.serve import _communities_from_graph, _read_graph

PROVIDER_ENV_KEYS = (
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "OPENAI_API_KEY",
    "AZURE_OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "OPENROUTER_API_KEY",
    "JEV_MEMORY_PILOT_API_KEY",
    "DEEPSEEK_API_KEY",
    "MOONSHOT_API_KEY",
    "OLLAMA_API_KEY",
    "GRAPHIFY_API_KEY",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "AWS_SECURITY_TOKEN",
)


class ContextError(ValueError):
    """The current repository cannot produce a valid invocation context."""


@dataclass(frozen=True)
class InvocationContext:
    repo: Path
    graph: Path
    head: str


@dataclass(frozen=True)
class ContextState:
    status: Literal["ready", "missing", "corrupt", "stale"]
    context: InvocationContext
    loaded_graph: nx.Graph | None = None
    diagnostic: str = ""


def _git_output(repo: Path, *args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", *args], cwd=repo, text=True, stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        raise ContextError(f"{repo.resolve()} is not inside a Git worktree") from None


def git_root(cwd: Path) -> Path:
    return Path(_git_output(cwd.resolve(), "rev-parse", "--show-toplevel")).resolve()


def inspect_context(
    cwd: Path, *, repo: Path | None = None, graph: Path | None = None,
) -> ContextState:
    resolved_repo = git_root(repo if repo is not None else cwd)
    resolved_graph = (
        graph if graph is not None and graph.is_absolute()
        else resolved_repo / (graph or Path("graphify-out/graph.json"))
    ).resolve()
    context = InvocationContext(
        repo=resolved_repo,
        graph=resolved_graph,
        head=_git_output(resolved_repo, "rev-parse", "HEAD"),
    )
    if not resolved_graph.is_file():
        return ContextState("missing", context, diagnostic="graph is missing")
    try:
        raw = json.loads(resolved_graph.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("graph root is not an object")
        loaded = _read_graph(str(resolved_graph))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return ContextState("corrupt", context, diagnostic=str(exc))
    persisted = raw.get("built_at_commit")
    normalized = loaded.graph.get("_built_at_commit")
    if (
        not isinstance(persisted, str)
        or not persisted.strip()
        or normalized != persisted.strip()
        or normalized != context.head
    ):
        return ContextState("stale", context, loaded, "graph commit differs from HEAD")
    return ContextState("ready", context, loaded)


def _repair_command(state: ContextState) -> list[str]:
    if state.status == "missing":
        operation = ["extract", ".", "--code-only"]
    elif state.status == "corrupt":
        operation = ["extract", ".", "--force", "--code-only"]
    else:
        operation = ["update", "."]
    return [sys.executable, "-m", "graphify", *operation]


def _run_repair(command: list[str], repo: Path, env: dict[str, str]):
    return subprocess.run(
        command,
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        shell=False,
    )


def ensure_context(
    cwd: Path, *, repo: Path | None = None, graph: Path | None = None,
) -> InvocationContext:
    state = inspect_context(cwd, repo=repo, graph=graph)
    if state.status == "ready":
        return state.context
    command = _repair_command(state)
    env = os.environ.copy()
    for key in PROVIDER_ENV_KEYS:
        env.pop(key, None)
    env.update(GRAPHIFY_NO_AUTO_REFRESH="1", PYTHONHASHSEED="0")
    result = _run_repair(command, state.context.repo, env)
    if result.returncode:
        diagnostic = (result.stderr or result.stdout or "no diagnostic").strip()[:1000]
        raise ContextError(
            f"graph repair failed ({' '.join(command)}): {diagnostic}"
        )
    repaired = inspect_context(cwd, repo=state.context.repo, graph=state.context.graph)
    if repaired.status != "ready":
        raise ContextError(f"repair produced invalid graph: {repaired.diagnostic}")
    return repaired.context


def _community_labels(graph_path: Path, communities: dict[int, list[str]]) -> dict[int, str]:
    labels_path = graph_path.parent / ".graphify_labels.json"
    try:
        raw = json.loads(labels_path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            labels = {int(key): value for key, value in raw.items()
                      if isinstance(value, str) and value.strip()}
            if labels:
                return labels
    except (OSError, ValueError, json.JSONDecodeError):
        pass
    return {community: f"Community {community}" for community in communities}


def select_question(graph: nx.Graph, graph_path: Path, question: str | None) -> str:
    if question is not None and question.strip():
        return question.strip()
    communities = _communities_from_graph(graph)
    suggestions = suggest_questions(
        graph, communities, _community_labels(graph_path, communities), top_n=5,
    )
    usable = [item for item in suggestions
              if isinstance(item.get("question"), str) and item["question"].strip()]
    preferred = [item for item in usable if not item.get("low_confidence")]
    selected = preferred or usable
    if not selected:
        raise ContextError("graph has no question signal; run graphify update .")
    return selected[0]["question"].strip()

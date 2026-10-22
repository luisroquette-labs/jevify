"""Zero-configuration orchestration for the portable Jevify runner."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

import networkx as nx

from graphify.analyze import suggest_questions
from graphify.diagnostics import diagnose_file
from graphify.paths import write_json_atomic
from graphify.serve import _communities_from_graph, _query_graph_text, _read_graph
from tools.jevify_graph_state import GraphFreshness, inspect_graph_freshness
from tools.jevify_insights import (
    InsightBundle,
    QueryResult,
    SuggestedQuestion,
    build_insights,
    query_result,
)

PROVIDER_ENV_KEYS = (
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "OPENAI_API_KEY",
    "AZURE_OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "OPENROUTER_API_KEY",
    "JEV_MEMORY_PILOT_API_KEY",
    "DEEPSEEK_API_KEY",
    "MOONSHOT_API_KEY",
    "OLLAMA_API_KEY",
    "GRAPHIFY_API_KEY",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "AWS_SECURITY_TOKEN",
)

BLOCKING_HEALTH_KEYS = (
    "missing_endpoint_edges",
    "dangling_endpoint_edges",
    "directed_same_endpoint_collapsed_edges",
    "undirected_same_endpoint_collapsed_edges",
)

BACKUP_ARTIFACTS = (
    "graph.json",
    "manifest.json",
    "GRAPH_REPORT.md",
    "graph.html",
    ".graph.html.stale",
    ".graphify_labels.json",
    ".graphify_analysis.json",
    ".graphify_semantic_marker",
    ".graphify_root",
    "cost.json",
)
MISSING_GRAPH_MARKER = ".jevify-missing-graph"


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
    freshness: GraphFreshness
    loaded_graph: nx.Graph | None = None
    diagnostic: str = ""


@dataclass(frozen=True)
class GraphStats:
    nodes: int
    edges: int
    communities: int
    built_at_commit: str | None


@dataclass(frozen=True)
class UpdateRoute:
    kind: Literal["none", "local_graphify", "host_graphify", "blocked"]
    operation: Literal["none", "extract", "update", "refresh"]
    reason: str


@dataclass(frozen=True)
class UpdateReceipt:
    status: Literal["already_current", "updated", "requires_host", "blocked"]
    route: UpdateRoute
    before: GraphStats | None
    after: GraphStats | None
    pending_before: GraphFreshness
    pending_after: GraphFreshness | None
    diagnostic: str = ""
    backup_path: str | None = None
    report_path: str | None = None
    visualization: Literal["updated", "skipped", "unchanged"] = "unchanged"
    health: dict[str, int] | None = None
    insights: InsightBundle | None = None


@dataclass(frozen=True)
class AutoResult:
    schema_version: int
    mode: Literal["graph_only", "memory_offline", "memory_live"]
    repo: str
    graph: str
    question: str | None
    live_enrichment: Literal["not_requested", "applied", "skipped"]
    answer: str | None
    freshness: dict
    update: dict | None
    graph_stats: dict
    health: dict[str, int]
    god_nodes: tuple[dict, ...]
    connections: tuple[dict, ...]
    questions: tuple[SuggestedQuestion, ...]
    answer_truncated: bool = False
    suggested_narrowing: str | None = None


def _git_output(repo: Path, *args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", *args], cwd=repo, text=True, stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        raise ContextError(f"{repo.resolve()} is not inside a Git worktree") from None


def git_root(cwd: Path) -> Path:
    return Path(_git_output(cwd.resolve(), "rev-parse", "--show-toplevel")).resolve()


def _git_identity(cwd: Path) -> tuple[Path, str]:
    output = _git_output(cwd.resolve(), "rev-parse", "--show-toplevel", "HEAD").splitlines()
    if len(output) != 2:
        raise ContextError(f"{cwd.resolve()} is not inside a Git worktree")
    return Path(output[0]).resolve(), output[1]


def inspect_context(
    cwd: Path, *, repo: Path | None = None, graph: Path | None = None,
) -> ContextState:
    resolved_repo, head = _git_identity(repo if repo is not None else cwd)
    resolved_graph = (
        graph if graph is not None and graph.is_absolute()
        else resolved_repo / (graph or Path("graphify-out/graph.json"))
    ).resolve()
    context = InvocationContext(
        repo=resolved_repo,
        graph=resolved_graph,
        head=head,
    )
    freshness = inspect_graph_freshness(resolved_repo, resolved_graph)
    if not resolved_graph.is_file():
        return ContextState("missing", context, freshness, diagnostic="graph is missing")
    try:
        raw = json.loads(resolved_graph.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("graph root is not an object")
        loaded = _read_graph(str(resolved_graph), query_mode=True)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return ContextState("corrupt", context, freshness, diagnostic=str(exc))
    persisted = raw.get("built_at_commit")
    normalized = loaded.graph.get("_built_at_commit")
    if (
        not isinstance(persisted, str)
        or not persisted.strip()
        or normalized != persisted.strip()
        or normalized != context.head
    ):
        return ContextState(
            "stale", context, freshness, loaded, "graph commit differs from HEAD",
        )
    if freshness.status != "current":
        return ContextState("stale", context, freshness, loaded, freshness.diagnostic)
    return ContextState("ready", context, freshness, loaded)


def graph_stats(graph_path: Path) -> GraphStats:
    graph = _read_graph(str(graph_path), query_mode=True)
    communities = {
        data.get("community")
        for _, data in graph.nodes(data=True)
        if data.get("community") is not None
    }
    built_at_commit = graph.graph.get("_built_at_commit")
    return GraphStats(
        graph.number_of_nodes(),
        graph.number_of_edges(),
        len(communities),
        built_at_commit if isinstance(built_at_commit, str) else None,
    )


def plan_update(state: ContextState) -> UpdateRoute:
    if state.freshness.status == "unavailable":
        return UpdateRoute("blocked", "none", state.freshness.diagnostic)
    if state.status == "ready" and state.freshness.status == "current":
        return UpdateRoute("none", "none", "graph and manifest are current")
    if (
        state.status == "stale"
        and state.loaded_graph is not None
        and state.freshness.status == "current"
    ):
        return UpdateRoute(
            "local_graphify", "refresh",
            "manifest is current; refresh commit metadata and artifacts",
        )
    operation: Literal["extract", "update"] = (
        "extract" if state.status in {"missing", "corrupt"} else "update"
    )
    if state.freshness.requires_semantic_host:
        return UpdateRoute(
            "host_graphify", operation, "semantic files require the Graphify host workflow",
        )
    return UpdateRoute("local_graphify", operation, "code-only Graphify update")


def _repair_command(state: ContextState, route: UpdateRoute) -> list[str]:
    if route.operation == "refresh":
        return [sys.executable, "-m", "graphify", "cluster-only", "."]
    if route.operation == "update":
        return [sys.executable, "-m", "graphify", "update", "."]
    command = [sys.executable, "-m", "graphify", "extract", ".", "--code-only"]
    if state.status == "corrupt" or state.context.graph.is_file():
        command.append("--force")
    return command


def _run_repair(command: list[str], repo: Path, env: dict[str, str]):
    return subprocess.run(
        command,
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        shell=False,
    )


def _child_environment() -> dict[str, str]:
    env = os.environ.copy()
    for key in PROVIDER_ENV_KEYS:
        env.pop(key, None)
    env.update(
        GRAPHIFY_BACKEND="none",
        GRAPHIFY_NO_AUTO_REFRESH="1",
        PYTHONHASHSEED="0",
    )
    return env


def _private_backup(graph_path: Path) -> Path | None:
    directory = Path(tempfile.mkdtemp(prefix="jevify-graph-backup-"))
    directory.chmod(0o700)
    backup = directory / "graph.json"
    for name in BACKUP_ARTIFACTS:
        source = graph_path.parent / name
        if source.is_file():
            destination = directory / name
            shutil.copyfile(source, destination)
            destination.chmod(0o600)
    if not backup.is_file():
        backup.touch(mode=0o600)
        marker = directory / MISSING_GRAPH_MARKER
        marker.touch(mode=0o600)
    return backup


def _discard_backup(backup: Path | None) -> None:
    if backup is None:
        return
    for name in (*BACKUP_ARTIFACTS, MISSING_GRAPH_MARKER):
        (backup.parent / name).unlink(missing_ok=True)
    backup.parent.rmdir()


def _restore_backup(backup: Path | None, graph_path: Path) -> None:
    if backup is None:
        graph_path.unlink(missing_ok=True)
        return
    graph_path.parent.mkdir(parents=True, exist_ok=True)
    missing_graph = (backup.parent / MISSING_GRAPH_MARKER).is_file()
    for name in BACKUP_ARTIFACTS:
        saved = backup.parent / name
        target = graph_path.parent / name
        if name == "graph.json" and missing_graph:
            target.unlink(missing_ok=True)
            saved.unlink(missing_ok=True)
        elif saved.is_file():
            os.replace(saved, target)
        else:
            target.unlink(missing_ok=True)
    (backup.parent / MISSING_GRAPH_MARKER).unlink(missing_ok=True)
    backup.parent.rmdir()


def _blocking_health(health: Mapping[str, int]) -> dict[str, int]:
    return {key: int(health.get(key, 0) or 0)
            for key in BLOCKING_HEALTH_KEYS if health.get(key, 0)}


def _artifact_validation(
    graph_path: Path,
    stats: GraphStats,
    *,
    env: Mapping[str, str],
    html_before: bytes | None,
) -> tuple[bool, str, str | None, Literal["updated", "skipped", "unchanged"]]:
    report = graph_path.parent / "GRAPH_REPORT.md"
    try:
        report_text = report.read_text(encoding="utf-8")
    except OSError as exc:
        return False, str(exc), None, "unchanged"
    expected = rf"- {stats.nodes} nodes .* {stats.edges} edges .* {stats.communities} communities"
    if re.search(expected, report_text) is None:
        return False, "GRAPH_REPORT.md counts do not match graph.json", str(report), "unchanged"
    if env.get("GRAPHIFY_VIZ_NODE_LIMIT") == "0":
        return True, "", str(report), "skipped"
    html = graph_path.parent / "graph.html"
    stale = graph_path.parent / ".graph.html.stale"
    if not html.is_file() or stale.exists():
        return False, "graph visualization is missing or stale", str(report), "unchanged"
    html_after = html.read_bytes()
    visualization = "updated" if html_before != html_after else "unchanged"
    return True, "", str(report), visualization


def run_code_update(
    state: ContextState,
    route: UpdateRoute,
    env: dict[str, str],
    *,
    backup: Path | None,
) -> UpdateReceipt:
    graph_path = state.context.graph
    before = _safe_graph_stats(backup)
    html = graph_path.parent / "graph.html"
    html_before = html.read_bytes() if html.is_file() else None
    command = _repair_command(state, route)
    if route.operation == "refresh":
        try:
            data = json.loads(graph_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("graph root is not an object")
            data["built_at_commit"] = state.context.head
            write_json_atomic(graph_path, data, compact=True)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            _restore_backup(backup, graph_path)
            return UpdateReceipt(
                "blocked", route, before, None,
                state.freshness, None, str(exc)[:4096],
            )
    result = _run_repair(command, state.context.repo, env)
    diagnostic = (result.stderr or result.stdout or "").strip()[:4096]
    if result.returncode:
        _restore_backup(backup, graph_path)
        return UpdateReceipt(
            "blocked", route, before, None,
            state.freshness, None, diagnostic or "Graphify update failed",
        )
    if route.operation == "extract" and graph_path.is_file():
        cluster_command = [sys.executable, "-m", "graphify", "cluster-only", "."]
        clustered = _run_repair(cluster_command, state.context.repo, env)
        cluster_diagnostic = (clustered.stderr or clustered.stdout or "").strip()
        diagnostic = "\n".join(filter(None, (diagnostic, cluster_diagnostic)))[:4096]
        if clustered.returncode:
            _restore_backup(backup, graph_path)
            return UpdateReceipt(
                "blocked", route, before, None, state.freshness, None,
                diagnostic or "Graphify artifact generation failed",
            )
    inspected = inspect_context(
        state.context.repo, repo=state.context.repo, graph=graph_path,
    )
    try:
        after = graph_stats(graph_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        _restore_backup(backup, graph_path)
        return UpdateReceipt(
            "blocked", route, before, None,
            state.freshness, inspected.freshness, str(exc)[:4096],
        )
    accepted = (
        inspected.status == "ready"
        and inspected.freshness.pending_total == 0
        and inspected.context.head == after.built_at_commit
    )
    if not accepted:
        _restore_backup(backup, graph_path)
        return UpdateReceipt(
            "blocked", route, before, after,
            state.freshness, inspected.freshness,
            inspected.diagnostic or "Graphify left pending work",
        )
    artifacts_ok, artifact_diagnostic, report_path, visualization = _artifact_validation(
        graph_path, after, env=env, html_before=html_before,
    )
    if not artifacts_ok:
        _restore_backup(backup, graph_path)
        return UpdateReceipt(
            "blocked", route, before, after,
            state.freshness, inspected.freshness, artifact_diagnostic,
            report_path=report_path,
        )
    if inspected.loaded_graph is None:
        _restore_backup(backup, graph_path)
        return UpdateReceipt(
            "blocked", route, before, after, state.freshness, inspected.freshness,
            "accepted graph could not be loaded", report_path=report_path,
        )
    try:
        insights = build_insights(inspected.loaded_graph, graph_path)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        _restore_backup(backup, graph_path)
        return UpdateReceipt(
            "blocked", route, before, after, state.freshness, inspected.freshness,
            str(exc)[:4096], report_path=report_path,
        )
    blockers = _blocking_health(insights.health)
    if blockers:
        _restore_backup(backup, graph_path)
        return UpdateReceipt(
            "blocked", route, before, after, state.freshness, inspected.freshness,
            f"blocking Graphify health counts: {blockers}",
            report_path=report_path, health=insights.health,
        )
    _discard_backup(backup)
    return UpdateReceipt(
        "updated", route, before, after, state.freshness, inspected.freshness,
        diagnostic=diagnostic, report_path=report_path, visualization=visualization,
        insights=insights,
    )


def _safe_graph_stats(graph_path: Path | None) -> GraphStats | None:
    if graph_path is None:
        return None
    try:
        return graph_stats(graph_path)
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def run_update(
    cwd: Path, *, repo: Path | None = None, graph: Path | None = None,
) -> UpdateReceipt:
    state = inspect_context(cwd, repo=repo, graph=graph)
    route = plan_update(state)
    before = _safe_graph_stats(state.context.graph)
    if route.kind == "none":
        if state.loaded_graph is None or before is None:
            return UpdateReceipt(
                "blocked", route, before, None, state.freshness, None,
                "current graph could not be loaded or measured",
            )
        try:
            insights = build_insights(state.loaded_graph, state.context.graph)
        except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
            return UpdateReceipt(
                "blocked", route, before, None, state.freshness, None,
                str(exc)[:4096],
            )
        blockers = _blocking_health(insights.health)
        if blockers:
            return UpdateReceipt(
                "blocked", route, before, before, state.freshness, state.freshness,
                f"blocking Graphify health counts: {blockers}",
                health=insights.health,
            )
        artifacts_ok, diagnostic, report_path, visualization = _artifact_validation(
            state.context.graph,
            before,
            env=_child_environment(),
            html_before=(state.context.graph.parent / "graph.html").read_bytes()
            if (state.context.graph.parent / "graph.html").is_file() else None,
        )
        if not artifacts_ok:
            return UpdateReceipt(
                "blocked", route, before, before, state.freshness, state.freshness,
                diagnostic, report_path=report_path, visualization=visualization,
                health=insights.health,
            )
        return UpdateReceipt(
            "already_current", route, before, before,
            state.freshness, state.freshness,
            report_path=report_path, visualization=visualization, insights=insights,
        )
    if route.kind == "blocked":
        return UpdateReceipt(
            "blocked", route, before, None, state.freshness, None,
            route.reason,
        )
    backup = _private_backup(state.context.graph)
    if route.kind == "host_graphify":
        return UpdateReceipt(
            "requires_host", route, before, None, state.freshness, None,
            route.reason, str(backup) if backup is not None else None,
        )
    if state.status == "corrupt":
        state.context.graph.unlink()
    return run_code_update(state, route, _child_environment(), backup=backup)


def _validated_backup(path: Path | None) -> Path | None:
    if path is None:
        return None
    resolved = path.resolve()
    if (
        resolved.name != "graph.json"
        or not resolved.parent.name.startswith("jevify-graph-backup-")
        or not resolved.is_file()
        or resolved.stat().st_mode & 0o077
        or resolved.parent.stat().st_mode & 0o077
    ):
        raise ValueError("invalid Jevify graph backup")
    return resolved


def finalize_update(
    cwd: Path,
    *,
    repo: Path | None = None,
    graph: Path | None = None,
    backup: Path | None = None,
) -> UpdateReceipt:
    state = inspect_context(cwd, repo=repo, graph=graph)
    route = UpdateRoute("host_graphify", "update", "verify Graphify host workflow")
    try:
        accepted_backup = _validated_backup(backup)
    except ValueError as exc:
        return UpdateReceipt(
            "blocked", route, None, None, state.freshness, None, str(exc),
        )
    before = _safe_graph_stats(accepted_backup)

    def blocked(diagnostic: str, health: dict[str, int] | None = None) -> UpdateReceipt:
        if accepted_backup is not None:
            _restore_backup(accepted_backup, state.context.graph)
        return UpdateReceipt(
            "blocked", route, before, None, state.freshness, None,
            diagnostic[:4096], health=health,
        )

    if state.status != "ready" or state.freshness.pending_total:
        return blocked(state.diagnostic or "Graphify host workflow is incomplete")
    try:
        after = graph_stats(state.context.graph)
        artifacts_ok, diagnostic, report_path, visualization = _artifact_validation(
            state.context.graph,
            after,
            env=os.environ,
            html_before=(state.context.graph.parent / "graph.html").read_bytes()
            if (state.context.graph.parent / "graph.html").is_file() else None,
        )
        summary = diagnose_file(
            state.context.graph, root=state.context.repo, max_examples=3,
        )
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        return blocked(str(exc))
    health_keys = (*BLOCKING_HEALTH_KEYS, "self_loop_edges", "exact_duplicate_edges",
                   "relation_variant_groups", "unverified_node_count")
    health = {key: int(summary.get(key, 0) or 0) for key in health_keys}
    if not artifacts_ok:
        return blocked(diagnostic, health)
    blockers = _blocking_health(health)
    if blockers:
        return blocked(f"blocking Graphify health counts: {blockers}", health)
    if state.loaded_graph is None:
        return blocked("accepted graph could not be loaded", health)
    try:
        insights = build_insights(state.loaded_graph, state.context.graph)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        return blocked(str(exc), health)
    _discard_backup(accepted_backup)
    return UpdateReceipt(
        "updated", route, before, after, state.freshness, state.freshness,
        report_path=report_path, visualization=visualization, health=health,
        insights=insights,
    )


def ensure_context(
    cwd: Path, *, repo: Path | None = None, graph: Path | None = None,
) -> InvocationContext:
    receipt = run_update(cwd, repo=repo, graph=graph)
    if receipt.status in {"already_current", "updated"}:
        return inspect_context(cwd, repo=repo, graph=graph).context
    if receipt.status == "requires_host":
        raise ContextError("semantic update requires the Graphify host workflow")
    raise ContextError(f"graph repair failed: {receipt.diagnostic}")


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


def query_graphify_exact(
    graph: nx.Graph, graph_path: Path, question: str,
) -> QueryResult:
    answer = _query_graph_text(
        graph, question, depth=2, graph_path=str(graph_path.resolve()), seeds=None,
    ) + "\n"
    return query_result(answer)


def _corpus_identity(path: Path) -> tuple[str, str, str]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("cases"), list):
        raise ValueError("corpus needs one case")
    cases = raw["cases"]
    observations = raw.get("observations")
    if len(cases) != 1 or not isinstance(cases[0], dict) or not isinstance(observations, list):
        raise ValueError("corpus needs exactly one case")
    case = cases[0]
    selected = case.get("observation_ids")
    if not isinstance(selected, list):
        raise ValueError("corpus case has invalid observations")
    by_id = {item.get("id"): item for item in observations if isinstance(item, dict)}
    projects = {by_id[item].get("project") for item in selected if item in by_id}
    if (len(projects) != 1 or not all(isinstance(item, str) and item for item in projects)
            or any(item not in by_id for item in selected)):
        raise ValueError("corpus observations need one project")
    case_id, question = case.get("id"), case.get("question")
    if not isinstance(case_id, str) or not case_id or not isinstance(question, str) or not question.strip():
        raise ValueError("corpus case identity is invalid")
    project = next(iter(projects))
    if not isinstance(project, str):
        raise ValueError("corpus observations need one project")
    return case_id, project, question.strip()


def auto(argv: list[str], cwd: Path) -> int:
    """Run a source-verified query with repository and question discovery."""
    import argparse

    parser = argparse.ArgumentParser(prog="jevify auto")
    parser.add_argument("--question")
    parser.add_argument("--repo", type=Path)
    parser.add_argument("--graph", type=Path)
    parser.add_argument("--corpus", type=Path)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--approved-paid-use", action="store_true")
    parser.add_argument("--max-requests", type=int, default=0)
    parser.add_argument("--threshold", type=float, default=0.8)
    args = parser.parse_args(argv)
    receipt = run_update(cwd, repo=args.repo, graph=args.graph)
    if receipt.status not in {"already_current", "updated"}:
        if receipt.status == "requires_host":
            raise ContextError("semantic update requires the Graphify host workflow")
        raise ContextError(f"graph update blocked: {receipt.diagnostic}")
    context = inspect_context(cwd, repo=args.repo, graph=args.graph).context
    graph = _read_graph(str(context.graph), query_mode=True)
    if graph is None:
        raise ContextError("graph could not be loaded")
    corpus_identity = None
    corpus_status = None
    if args.corpus is not None:
        try:
            corpus_identity = _corpus_identity(args.corpus)
        except (OSError, ValueError, json.JSONDecodeError):
            corpus_status = "memory_enrichment=skipped"
    corpus_question = corpus_identity[2] if corpus_identity else None
    question = select_question(graph, context.graph, args.question or corpus_question)
    if corpus_identity and args.question and question != corpus_question:
        corpus_status = "memory_enrichment=skipped"
        corpus_identity = None
    answer = None
    graph_query = QueryResult("", False, None)
    mode: Literal["graph_only", "memory_offline", "memory_live"] = "graph_only"
    live_status: Literal["not_requested", "applied", "skipped"] = (
        "skipped" if args.live else "not_requested"
    )
    cost = None
    if corpus_identity and args.corpus is not None:
        from tools.jev_memory_pilot import PilotConfig, run_pilot

        case_id, project, _ = corpus_identity
        try:
            outcome = run_pilot(PilotConfig(
                repo=context.repo, graph=context.graph, corpus=args.corpus,
                case_id=case_id, project=project, candidate_mode="fast-source",
                threshold=args.threshold, live=args.live,
                approved_paid_use=args.approved_paid_use, max_requests=args.max_requests,
            ))
        except (OSError, ValueError, json.JSONDecodeError):
            corpus_status = "memory_enrichment=skipped"
        else:
            answer = outcome.answer
            live_status = outcome.live_enrichment
            cost = outcome.actual_cost
            if outcome.live_enrichment == "applied":
                mode = "memory_live"
            elif outcome.memory_applied:
                mode = "memory_offline"
    if answer is None:
        queried = query_graphify_exact(graph, context.graph, question)
        graph_query = queried if isinstance(queried, QueryResult) else query_result(queried)
        answer = graph_query.answer
    insight_bundle = receipt.insights or build_insights(graph, context.graph)
    freshness = asdict(receipt.pending_after or receipt.pending_before)
    result = AutoResult(
        2,
        mode,
        str(context.repo),
        str(context.graph),
        question,
        live_status,
        answer,
        freshness,
        {"status": receipt.status, "route": asdict(receipt.route)},
        asdict(insight_bundle.graph_stats),
        insight_bundle.health,
        insight_bundle.god_nodes,
        insight_bundle.connections,
        insight_bundle.questions,
        graph_query.truncated,
        graph_query.suggested_narrowing,
    )
    if args.json:
        print(json.dumps(asdict(result), sort_keys=True))
    else:
        print(f"Question: {question}")
        print(answer, end="" if answer.endswith("\n") else "\n")
    statuses = []
    if corpus_status:
        statuses.append(corpus_status)
    if args.live:
        statuses.append(f"live_enrichment={live_status}")
    for status in dict.fromkeys(statuses):
        print(status, file=sys.stderr)
    if cost is not None:
        print(f"Jev actual cost: USD {cost:.8f}", file=sys.stderr)
    return 0

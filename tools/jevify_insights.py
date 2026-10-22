"""Compact, source-backed Graphify insights for Jevify."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import networkx as nx

from graphify.analyze import god_nodes, suggest_questions, surprising_connections
from graphify.diagnostics import diagnose_file
from graphify.serve import _communities_from_graph


@dataclass(frozen=True)
class GraphStats:
    nodes: int
    edges: int
    communities: int
    built_at_commit: str | None


@dataclass(frozen=True)
class SuggestedQuestion:
    text: str
    kind: str
    why: str
    low_confidence: bool


@dataclass(frozen=True)
class InsightBundle:
    graph_stats: GraphStats
    health: dict[str, int]
    god_nodes: tuple[dict, ...]
    connections: tuple[dict, ...]
    questions: tuple[SuggestedQuestion, ...]


@dataclass(frozen=True)
class QueryResult:
    answer: str
    truncated: bool
    suggested_narrowing: str | None


def _community_labels(graph_path: Path, communities: dict[int, list[str]]) -> dict[int, str]:
    labels_path = graph_path.parent / ".graphify_labels.json"
    try:
        raw = json.loads(labels_path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            labels = {
                int(key): value for key, value in raw.items()
                if isinstance(value, str) and value.strip()
            }
            if labels:
                return labels
    except (OSError, ValueError, json.JSONDecodeError):
        pass
    return {community: f"Community {community}" for community in communities}


def normalize_question(text: str) -> str:
    """Remove repeated backticked labels without rewording Graphify's question."""
    seen: set[str] = set()
    output = ""
    cursor = 0
    for match in re.finditer(r"`[^`]+`", text):
        label = match.group(0)
        output += text[cursor:match.start()]
        if label in seen:
            output = re.sub(r"(?:,\s*|\s+and\s+)$", "", output)
        else:
            seen.add(label)
            output += label
        cursor = match.end()
    output += text[cursor:]
    output = re.sub(r"\s{2,}", " ", output)
    output = re.sub(r"\s+([?,.])", r"\1", output).strip()
    labels = list(re.finditer(r"`[^`]+`", output))
    if len(labels) > 5:
        output = output[:labels[4].end()].rstrip(", ") + " and other communities?"
    return output


def _rank_questions(raw: list[dict], gods: list[dict], connections: list[dict]) -> tuple[SuggestedQuestion, ...]:
    candidates = list(raw)
    existing = {
        item.get("question") for item in candidates if isinstance(item.get("question"), str)
    }
    for god in gods:
        question = f"What responsibilities make `{god['label']}` a central abstraction?"
        if question not in existing:
            candidates.append({
                "type": "god_node",
                "question": question,
                "why": f"Highest structural degree ({god['degree']}).",
            })
            existing.add(question)
    for connection in connections:
        question = (
            f"What explains the connection between `{connection['source']}` "
            f"and `{connection['target']}`?"
        )
        if question not in existing:
            candidates.append({
                "type": "surprising_connection",
                "question": question,
                "why": connection.get("why") or connection.get("note") or "Cross-graph connection.",
                "low_confidence": connection.get("confidence") == "AMBIGUOUS",
            })
            existing.add(question)

    priority = {
        "bridge_node": 0,
        "verify_inferred": 1,
        "god_node": 2,
        "surprising_connection": 3,
        "isolated_nodes": 4,
        "low_cohesion": 5,
        "ambiguous_edge": 6,
    }
    prepared: list[SuggestedQuestion] = []
    seen_text: set[str] = set()
    for item in candidates:
        question = item.get("question")
        if not isinstance(question, str) or not question.strip():
            continue
        text = normalize_question(question)
        if not text or text in seen_text:
            continue
        if item.get("type") == "surprising_connection":
            labels = re.findall(r"`[^`]+`", text)
            if len(set(labels)) < 2:
                continue
        seen_text.add(text)
        prepared.append(SuggestedQuestion(
            text=text,
            kind=str(item.get("type") or "graph_signal"),
            why=str(item.get("why") or "Graphify structural signal."),
            low_confidence=bool(item.get("low_confidence")),
        ))
    prepared.sort(key=lambda item: (
        item.low_confidence,
        priority.get(item.kind, 5),
    ))
    by_kind: dict[str, list[SuggestedQuestion]] = {}
    for item in prepared:
        by_kind.setdefault(item.kind, []).append(item)
    diversified: list[SuggestedQuestion] = []
    while by_kind and len(diversified) < 5:
        for kind in tuple(by_kind):
            diversified.append(by_kind[kind].pop(0))
            if not by_kind[kind]:
                del by_kind[kind]
            if len(diversified) == 5:
                break
    return tuple(diversified)


def build_insights(graph: nx.Graph, graph_path: Path) -> InsightBundle:
    communities = _communities_from_graph(graph)
    labels = _community_labels(graph_path, communities)
    gods = god_nodes(graph, top_n=5)
    connections = surprising_connections(graph, communities, top_n=5)
    raw_questions = suggest_questions(graph, communities, labels, top_n=7)
    summary = diagnose_file(graph_path, root=graph_path.parent.parent, max_examples=0)
    health_keys = (
        "missing_endpoint_edges",
        "dangling_endpoint_edges",
        "directed_same_endpoint_collapsed_edges",
        "undirected_same_endpoint_collapsed_edges",
        "self_loop_edges",
        "exact_duplicate_edges",
        "relation_variant_groups",
        "unverified_node_count",
    )
    health = {key: int(summary.get(key, 0) or 0) for key in health_keys}
    built_at_commit = graph.graph.get("_built_at_commit")
    stats = GraphStats(
        graph.number_of_nodes(), graph.number_of_edges(), len(communities),
        built_at_commit if isinstance(built_at_commit, str) else None,
    )
    return InsightBundle(
        stats,
        health,
        tuple(gods),
        tuple(connections),
        _rank_questions(raw_questions, gods, connections),
    )


def query_result(answer: str) -> QueryResult:
    truncated = answer.lstrip().startswith("[!] TRUNCATED:")
    narrowing = (
        "Narrow with graphify path, graphify explain, or context_filter."
        if truncated else None
    )
    return QueryResult(answer, truncated, narrowing)

"""Git-aware validation for memory-cited source paths."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Sequence

import networkx as nx


@dataclass(frozen=True)
class SourceEvidence:
    usable_paths: tuple[str, ...]
    rejected_paths: tuple[str, ...]
    reason: str


def _is_test_path(path: str) -> bool:
    lowered = path.casefold()
    return any(marker in lowered for marker in (
        "test/", "tests/", "spec/", "/test/", "/tests/", "/spec/",
        "_test.", ".test.", "-test.",
    ))


def classify_source_evidence(
    repo: Path,
    graph: nx.Graph,
    source_commit: str | None,
    paths: Sequence[str],
) -> SourceEvidence:
    """Keep only tracked graph paths unchanged since an ancestor commit."""
    unique_paths = tuple(dict.fromkeys(paths))
    if not source_commit:
        return SourceEvidence((), unique_paths, "source_commit_missing")
    if unique_paths and all(_is_test_path(path) for path in unique_paths):
        return SourceEvidence((), unique_paths, "test_only_paths_need_unscoped_query")
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", source_commit, "HEAD"],
        cwd=repo,
        capture_output=True,
    ).returncode:
        return SourceEvidence((), unique_paths, "source_commit_not_ancestor")

    graph_paths = {
        source
        for _, data in graph.nodes(data=True)
        if isinstance(source := data.get("source_file"), str) and source
    }
    usable: list[str] = []
    rejected: list[str] = []
    for relative in unique_paths:
        parsed = PurePosixPath(relative)
        safe = (
            isinstance(relative, str)
            and bool(relative)
            and not parsed.is_absolute()
            and ".." not in parsed.parts
            and "\\" not in relative
            and parsed.as_posix() == relative
            and relative != "."
        )
        tracked = safe and subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", relative],
            cwd=repo,
            capture_output=True,
        ).returncode == 0
        unchanged = tracked and subprocess.run(
            ["git", "diff", "--quiet", source_commit, "HEAD", "--", relative],
            cwd=repo,
        ).returncode == 0
        (usable if unchanged and relative in graph_paths else rejected).append(relative)
    reason = "fresh_graph_paths" if usable else "no_fresh_graph_paths"
    return SourceEvidence(tuple(usable), tuple(rejected), reason)

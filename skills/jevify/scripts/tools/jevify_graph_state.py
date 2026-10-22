"""Read-only Graphify manifest freshness inspection for Jevify."""

from __future__ import annotations

import json
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from graphify.detect import classify_file, detect_incremental
from graphify.watch import _read_build_excludes, _read_build_gitignore

SEMANTIC_TYPES = frozenset({"document", "paper", "image", "video"})


@dataclass(frozen=True)
class GraphFreshness:
    status: Literal["current", "pending", "unavailable"]
    changed_by_type: tuple[tuple[str, int], ...] = ()
    deleted_by_type: tuple[tuple[str, int], ...] = ()
    deleted: int = 0
    skipped_sensitive: tuple[str, ...] = ()
    requires_semantic_host: bool = False
    diagnostic: str = ""

    @property
    def pending_total(self) -> int:
        return sum(count for _, count in self.changed_by_type) + self.deleted


def inspect_graph_freshness(repo: Path, graph_path: Path) -> GraphFreshness:
    """Compare the live corpus with Graphify's manifest without mutating the repo."""
    manifest = graph_path.parent / "manifest.json"
    diagnostic = ""
    if manifest.is_file():
        try:
            raw = json.loads(manifest.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("manifest root is not an object")
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            return GraphFreshness("unavailable", diagnostic=str(exc)[:1000])
    else:
        diagnostic = "graph manifest is missing"

    try:
        with tempfile.TemporaryDirectory(prefix="jevify-freshness-") as cache:
            result = detect_incremental(
                repo,
                manifest_path=str(manifest),
                kind="ast",
                extra_excludes=_read_build_excludes(graph_path.parent),
                gitignore=_read_build_gitignore(graph_path.parent),
                cache_root=Path(cache),
            )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return GraphFreshness("unavailable", diagnostic=str(exc)[:1000])

    changed = tuple(sorted(
        (kind, len(paths))
        for kind, paths in result.get("new_files", {}).items()
        if paths
    ))
    deleted_files = tuple(result.get("deleted_files", []))
    deleted_kinds = [classify_file(Path(path)) for path in deleted_files]
    deleted_by_type = tuple(sorted(Counter(
        kind.value for kind in deleted_kinds if kind is not None
    ).items()))
    pending_kinds = {kind for kind, _count in changed + deleted_by_type}
    return GraphFreshness(
        "pending" if changed or deleted_files else "current",
        changed_by_type=changed,
        deleted_by_type=deleted_by_type,
        deleted=len(deleted_files),
        skipped_sensitive=tuple(result.get("skipped_sensitive", [])),
        requires_semantic_host=(
            any(kind is None for kind in deleted_kinds)
            or bool(pending_kinds & SEMANTIC_TYPES)
        ),
        diagnostic=diagnostic,
    )

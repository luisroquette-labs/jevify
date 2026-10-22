# Jevify Graphify Amplification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `$jevify --update` execute or orchestrate the complete applicable Graphify workflow, prove the resulting graph is current, and return a concise actionable insight bundle without relying on paid JEV.

**Architecture:** Keep Graphify as the only structural extraction and graph-writing engine. Add a read-only freshness adapter and an insight adapter at the Jevify boundary; the runner handles deterministic code-only updates, while the installed skill routes semantic files through Graphify's existing host-agent workflow before Jevify finalizes and reports. Memory and JEV remain optional layers after structural truth is established.

**Tech Stack:** Python 3.10+, standard library, NetworkX, existing Graphify detect/build/analyze/diagnostics/query APIs, pytest, Ruff, Pyright, `uv`, GitHub Actions.

**Spec:** `.specs/tasks/draft/jevify-graphify-amplification.feature.md`

## Global Constraints

- Graphify remains the sole producer of structural nodes, edges, communities, reports, and visualizations.
- Jevify must never report `ready` or `updated` from `built_at_commit == HEAD` alone.
- Default execution makes no paid API call, reads no ambient personal provider credential, and sets `GRAPHIFY_BACKEND=none` for subprocess work.
- Semantic documents are processed through the Graphify skill's host-agent workflow; an unavailable or incomplete semantic path returns `blocked`.
- Preserve Graphify shrink guards, semantic-completeness guards, manifest semantics, and the last accepted graph on failure.
- Update-only output contains three to five questions but does not automatically execute a broad Graphify traversal.
- JEV remains optional; do not claim speed, quality, relevance, or product superiority from this implementation.
- Do not add a dependency, daemon, hosted service, vector store, OAuth flow, benchmark run, or provider integration.
- Keep private observations and payloads outside Git with directory mode `0700` and file mode `0600`.
- Use a single task branch and PR to `jevify`; run typecheck, lint, and tests only through `mac-gate`; never run a local build.

## Review Focus

1. **Same HEAD, stale manifest:** a modified or untracked supported file must make `graph_current` false even when the graph commit equals `HEAD`; Task 1 adds this exact regression.
2. **Mixed corpus without a paid backend:** code must not advance while semantic files remain pending; Tasks 2 and 3 test the host handoff and fail-closed finalization.
3. **Graph preservation on failure:** corrupt replacement, shrink refusal, incomplete semantic extraction, and diagnostic failure must leave the last accepted graph intact; Task 3 tests each state.
4. **Question usefulness:** repeated labels, low-confidence dominance, no-signal graphs, and huge/truncated traversals must not produce a misleading insight bundle; Task 4 pins the ranking and rendering behavior.
5. **Installed-copy parity:** project modules, portable skill modules, command routing, and generated install artifacts must stay byte-equivalent and use the merged Jevify commit; Task 5 covers drift and clean-home execution.

---

## File and Interface Map

| Responsibility | File |
| --- | --- |
| Product behavior contract | `.specs/tasks/draft/jevify-graphify-amplification.feature.md` |
| Freshness data and manifest-aware inspection | `tools/jevify_graph_state.py` |
| Portable freshness module | `skills/jevify/scripts/tools/jevify_graph_state.py` |
| Insight ranking and presentation data | `tools/jevify_insights.py` |
| Portable insight module | `skills/jevify/scripts/tools/jevify_insights.py` |
| Auto/update orchestration | `tools/jevify_autorun.py` |
| Portable orchestration | `skills/jevify/scripts/tools/jevify_autorun.py` |
| CLI subcommands and JSON envelope | `skills/jevify/scripts/run.py` |
| Agent host workflow | `skills/jevify/SKILL.md` |
| Graph build/query rules | `skills/jevify/references/graph.md` |
| Freshness, update, and insight tests | `tests/test_jevify_autorun.py` |
| CLI and portable-copy tests | `tests/test_jevify_skill.py` |
| Clean-home installation behavior | `tests/test_jevify_install.py` |
| Public evidence and claim boundary | `docs/jevify-graphify-amplification-evaluation.md` |
| Product positioning | `README.md`, `docs/jevify-roadmap.md`, `docs/jevify/index.html` |

### Task 1: Replace Commit-Only Freshness With Manifest Truth

**Files:**
- Create: `tools/jevify_graph_state.py`
- Create: `skills/jevify/scripts/tools/jevify_graph_state.py`
- Modify: `tools/jevify_autorun.py:80-120`
- Modify: `skills/jevify/scripts/tools/jevify_autorun.py:80-120`
- Modify: `skills/jevify/scripts/run.py:24-43`
- Modify: `tests/test_jevify_autorun.py`
- Modify: `tests/test_jevify_skill.py`

**Interfaces:**
- Consumes: `repo: Path`, `graph_path: Path`, `head: str`.
- Produces: `GraphFreshness`, `inspect_graph_freshness(...) -> GraphFreshness`, and an enriched `ContextState` whose `status == "ready"` only when commit and manifest checks pass.

- [ ] **Step 1: Write failing same-HEAD manifest tests**

Add these fixtures and tests to `tests/test_jevify_autorun.py`:

```python
def test_same_head_with_modified_code_is_stale(repo_with_graph):
    repo, _ = repo_with_graph
    write_graphify_manifest(repo)
    (repo / "app.py").write_text("def run(): return 2\n", encoding="utf-8")

    state = inspect_context(repo)

    assert state.status == "stale"
    assert state.freshness.changed_by_type == (("code", 1),)
    assert state.freshness.deleted == 0


def test_same_head_with_new_document_is_stale(repo_with_graph):
    repo, _ = repo_with_graph
    write_graphify_manifest(repo)
    (repo / "DECISION.md").write_text("# Decision\n", encoding="utf-8")

    state = inspect_context(repo)

    assert state.status == "stale"
    assert state.freshness.requires_semantic_host is True


def test_same_head_with_deleted_file_is_stale(repo_with_graph):
    repo, _ = repo_with_graph
    write_graphify_manifest(repo)
    (repo / "app.py").unlink()

    freshness = inspect_context(repo).freshness
    assert freshness.deleted == 1
    assert freshness.deleted_by_type == (("code", 1),)
```

- [ ] **Step 2: Run the tests and verify the false-ready regression**

Run:

```bash
mac-gate uv run --frozen pytest \
  tests/test_jevify_autorun.py::test_same_head_with_modified_code_is_stale \
  tests/test_jevify_autorun.py::test_same_head_with_new_document_is_stale \
  tests/test_jevify_autorun.py::test_same_head_with_deleted_file_is_stale -q
```

Expected: FAIL because current `inspect_context()` returns `ready` whenever `built_at_commit` equals `HEAD`.

- [ ] **Step 3: Add immutable freshness types**

Create both copies of `jevify_graph_state.py` with this public shape:

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

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
```

Keep the result immutable and JSON-safe through a separate `asdict()` call in the CLI; do not put full file contents or memory observations in it.

- [ ] **Step 4: Implement manifest-aware inspection using Graphify's detector**

Implement:

```python
def inspect_graph_freshness(repo: Path, graph_path: Path) -> GraphFreshness:
    manifest = graph_path.parent / "manifest.json"
    with tempfile.TemporaryDirectory(prefix="jevify-freshness-") as cache:
        result = detect_incremental(
            repo,
            manifest_path=str(manifest),
            extra_excludes=_read_build_excludes(graph_path.parent),
            gitignore=_read_build_gitignore(graph_path.parent),
            cache_root=Path(cache),
        )
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
    unknown_deleted = any(kind is None for kind in deleted_kinds)
    semantic_kinds = {kind for kind, _count in changed + deleted_by_type}
    return GraphFreshness(
        "pending" if changed or deleted_files else "current",
        changed_by_type=changed,
        deleted_by_type=deleted_by_type,
        deleted=len(deleted_files),
        skipped_sensitive=tuple(result.get("skipped_sensitive", [])),
        requires_semantic_host=(
            unknown_deleted or bool(semantic_kinds & SEMANTIC_TYPES)
        ),
        diagnostic="graph manifest is missing" if not manifest.is_file() else "",
    )
```

Import `Counter`, `classify_file`, `detect_incremental`, `_read_build_excludes`, and `_read_build_gitignore` at module scope so tests can replace the detector without touching Graphify internals. Use a temporary cache so `doctor` remains read-only with respect to the target repository. Catch only `OSError`, `ValueError`, and `json.JSONDecodeError`; return `unavailable` with the exact bounded diagnostic instead of treating detector failure as current.

- [ ] **Step 5: Gate `ready` on both commit and manifest state**

Add `freshness: GraphFreshness` immediately after `context` in `ContextState`, before the optional loaded graph and diagnostic fields. In `inspect_context()`, call `inspect_graph_freshness()` immediately after resolving the repository, graph path, and `HEAD`, so missing and corrupt graphs still carry the detected corpus types. Preserve the existing missing/corrupt/commit checks. Return `stale` whenever an otherwise valid graph has freshness other than `current`.

Change `doctor` JSON to include:

```json
{
  "checks": {"repo": true, "graph": true, "graph_current": false},
  "freshness": {
    "status": "pending",
    "changed_by_type": {"code": 15, "document": 5},
    "deleted_by_type": {},
    "deleted": 0,
    "requires_semantic_host": true
  },
  "ok": false
}
```

- [ ] **Step 6: Add no-mutation and sensitive-file tests**

```python
def test_doctor_freshness_scan_does_not_mutate_repo(repo_with_graph):
    repo, graph = repo_with_graph
    manifest = write_graphify_manifest(repo)
    before = {path: path.read_bytes() for path in (graph, manifest)}
    status_before = _git_status(repo)

    assert doctor(["--repo", str(repo)]) == 0

    assert {path: path.read_bytes() for path in (graph, manifest)} == before
    assert _git_status(repo) == status_before


def test_freshness_surfaces_sensitive_skip(repo_with_graph, monkeypatch):
    repo, graph = repo_with_graph
    monkeypatch.setattr(graph_state, "detect_incremental", lambda *_a, **_k: {
        "new_files": {}, "deleted_files": [], "skipped_sensitive": [".env.production"],
    })
    result = inspect_graph_freshness(repo, graph)
    assert result.skipped_sensitive == (".env.production",)


def test_malformed_manifest_is_unavailable_not_current(repo_with_graph):
    repo, graph = repo_with_graph
    (graph.parent / "manifest.json").write_text("{", encoding="utf-8")
    assert inspect_graph_freshness(repo, graph).status == "unavailable"
```

- [ ] **Step 7: Run focused checks and commit**

```bash
mac-gate uv run --frozen pytest tests/test_jevify_autorun.py tests/test_jevify_skill.py -q
mac-gate uv run --frozen ruff check tools/jevify_graph_state.py tools/jevify_autorun.py tests/test_jevify_autorun.py
```

Expected: all focused tests and Ruff pass.

```bash
git add .specs/tasks/draft/jevify-graphify-amplification.feature.md \
  tools/jevify_graph_state.py tools/jevify_autorun.py \
  skills/jevify/scripts/tools/jevify_graph_state.py \
  skills/jevify/scripts/tools/jevify_autorun.py \
  skills/jevify/scripts/run.py tests/test_jevify_autorun.py tests/test_jevify_skill.py
git commit -m "fix: verify Jevify graph freshness from the manifest"
```

### Task 2: Add an Explicit Fail-Closed Update Contract

**Files:**
- Modify: `tools/jevify_graph_state.py`
- Modify: `skills/jevify/scripts/tools/jevify_graph_state.py`
- Modify: `tools/jevify_autorun.py`
- Modify: `skills/jevify/scripts/tools/jevify_autorun.py`
- Modify: `skills/jevify/scripts/run.py`
- Modify: `tests/test_jevify_autorun.py`
- Modify: `tests/test_jevify_skill.py`

**Interfaces:**
- Consumes: `ContextState`, the resolved graph path, and a sanitized child environment.
- Produces: `UpdateRoute`, `UpdateReceipt`, `plan_update(state) -> UpdateRoute`, and `run_code_update(route, graph_path, env) -> UpdateReceipt`.

- [ ] **Step 1: Write failing route-selection tests**

```python
@pytest.mark.parametrize(
    ("status", "changed", "semantic", "expected"),
    [
        ("ready", (), False, "none"),
        ("stale", (("code", 2),), False, "local_graphify"),
        ("stale", (("code", 2), ("document", 1)), True, "host_graphify"),
        ("missing", (("code", 2),), False, "local_graphify"),
        ("missing", (("document", 1),), True, "host_graphify"),
    ],
)
def test_plan_update_routes_by_pending_work(
    repo_with_graph, status, changed, semantic, expected,
):
    repo, graph_path = repo_with_graph
    freshness = GraphFreshness(
        "current" if status == "ready" else "pending",
        changed_by_type=changed,
        requires_semantic_host=semantic,
    )
    state = ContextState(
        status,
        InvocationContext(repo, graph_path, _commit(repo)),
        freshness=freshness,
    )

    assert plan_update(state).kind == expected
```

Add these explicit assertions:

```python
def test_corrupt_graph_routes_from_detected_corpus(corrupt_state):
    assert plan_update(corrupt_state(code=1)).kind == "local_graphify"
    assert plan_update(corrupt_state(document=1)).kind == "host_graphify"


def test_code_deletion_only_routes_to_local_graphify(stale_state):
    state = stale_state(deleted=1, deleted_by_type=(("code", 1),))
    assert plan_update(state).kind == "local_graphify"


def test_document_deletion_routes_through_full_graphify_flow(stale_state):
    state = stale_state(deleted=1, deleted_by_type=(("document", 1),))
    assert plan_update(state).kind == "host_graphify"


def test_unavailable_freshness_is_blocked(stale_state):
    state = stale_state(freshness_status="unavailable")
    assert plan_update(state).kind == "blocked"


```

Jevify does not expose or forward a user-supplied Graphify `--force`; a shrink refusal remains a typed `blocked` result requiring a separate, explicit Graphify decision. The sole internal `--force` below replaces an unreadable corrupt file only after preserving its bytes.

- [ ] **Step 2: Run tests and verify missing update types**

Run `mac-gate uv run --frozen pytest tests/test_jevify_autorun.py -q`.

Expected: FAIL because `UpdateRoute` and `plan_update` do not exist.

- [ ] **Step 3: Add the update types**

```python
@dataclass(frozen=True)
class GraphStats:
    nodes: int
    edges: int
    communities: int
    built_at_commit: str | None


@dataclass(frozen=True)
class UpdateRoute:
    kind: Literal["none", "local_graphify", "host_graphify", "blocked"]
    operation: Literal["none", "extract", "update"]
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
```

For a corrupt graph, `run_update()` creates a mode-`0600` copy under a mode-`0700` directory returned by `tempfile.mkdtemp(prefix="jevify-graph-backup-")`. Store its absolute path in `backup_path`. Local routes restore and delete it inside the same process on failure; host routes keep it only until `finalize` accepts or restores the replacement.

- [ ] **Step 4: Implement the deterministic local Graphify route**

For code-only pending work, call one argument-array subprocess from the repository:

```python
if route.operation == "update":
    command = [sys.executable, "-m", "graphify", "update", "."]
else:
    command = [sys.executable, "-m", "graphify", "extract", ".", "--code-only"]
    if graph_path.is_file():
        command.append("--force")
```

Pin these exact arrays in `test_existing_code_graph_uses_graphify_update`, `test_missing_code_graph_uses_code_only_extract`, and `test_corrupt_code_graph_uses_forced_code_only_extract`. The child environment must remove every key in `PROVIDER_ENV_KEYS` and set:

```python
env.update(
    GRAPHIFY_BACKEND="none",
    GRAPHIFY_NO_AUTO_REFRESH="1",
    PYTHONHASHSEED="0",
)
```

Capture stdout/stderr, cap the stored diagnostic at 4 KiB, never use `shell=True`, and never retry.

- [ ] **Step 5: Reinspect after the child exits**

Return `updated` only when all conditions hold:

```python
accepted = (
    result.returncode == 0
    and inspected.status == "ready"
    and inspected.freshness.pending_total == 0
    and inspected.context.head == graph_stats(inspected.context.graph).built_at_commit
)
assert accepted is True
```

Also require `GRAPH_REPORT.md` to exist and contain the accepted node and edge counts using Graphify's existing report format. Set `visualization=skipped` only when the frozen child environment has `GRAPHIFY_VIZ_NODE_LIMIT=0`; otherwise require `graph.html` to exist and `.graph.html.stale` to be absent, reporting `updated` when its hash changed and `unchanged` when Graphify kept a still-valid visualization. Otherwise return `blocked` and preserve the Graphify diagnostic. Add tests for exit nonzero, exit zero with pending work, wrong commit, malformed replacement, missing/mismatched report, stale/missing visualization, and unexpected shrink refusal.

- [ ] **Step 6: Add `update` routing to the portable CLI**

`run.py update [--repo PATH] [--graph PATH] [--json]` must:

- return `0` for `already_current` or `updated`;
- return `20` with `status=requires_host` for semantic work;
- return `1` with `status=blocked` for every incomplete or unsafe outcome.

Keep `auto`, `doctor`, `query`, and `benchmark` compatible. Do not treat exit `20` as an error in the installed skill; it is a typed host handoff.

- [ ] **Step 7: Run focused checks and commit**

```bash
mac-gate uv run --frozen pytest tests/test_jevify_autorun.py tests/test_jevify_skill.py -q
mac-gate uv run --frozen ruff check tools/jevify_graph_state.py tools/jevify_autorun.py skills/jevify/scripts/run.py
```

```bash
git add tools/jevify_graph_state.py tools/jevify_autorun.py \
  skills/jevify/scripts/tools/jevify_graph_state.py \
  skills/jevify/scripts/tools/jevify_autorun.py \
  skills/jevify/scripts/run.py tests/test_jevify_autorun.py tests/test_jevify_skill.py
git commit -m "feat: add fail-closed Jevify graph updates"
```

### Task 3: Orchestrate Semantic Updates Through the Graphify Skill

**Files:**
- Modify: `skills/jevify/SKILL.md`
- Modify: `skills/jevify/references/graph.md`
- Modify: `skills/jevify/scripts/run.py`
- Modify: `tests/test_jevify_skill.py`
- Modify: `tests/test_jevify_install.py`

**Interfaces:**
- Consumes: update JSON with `status=requires_host` and `pending_before.requires_semantic_host=true`.
- Produces: one host-level Graphify update followed by `run.py finalize --repo PATH --json`, with no user interaction; finalization returns verified freshness and health, while Task 4 adds insights.

- [ ] **Step 1: Add failing installed-contract tests**

Assert the generated Claude and Codex skills contain all of these literal requirements:

```python
required = [
    "$jevify --update",
    "status=requires_host",
    "use the installed Graphify skill",
    "do not report success before finalize",
    "do not use a paid provider",
    "resume Jevify automatically",
]
```

Add a clean-home process test where a mixed fixture returns `requires_host` with exit `20` and does not modify `graph.json` before host orchestration.

- [ ] **Step 2: Run tests and verify the contract is absent**

```bash
mac-gate uv run --frozen pytest tests/test_jevify_skill.py tests/test_jevify_install.py -q
```

Expected: FAIL on the missing update/handoff wording and exit contract.

- [ ] **Step 3: Replace the ambiguous repair paragraph in `SKILL.md`**

Document this exact host flow:

```text
1. Run `uv run "$JEVIFY_SKILL_DIR/scripts/run.py" update --json`.
2. If status is already_current or updated, render the receipt.
3. If status is requires_host, invoke the installed Graphify skill's `--update`
   workflow in the same repository with provider keys unset. If graph.json was
   corrupt, preserve the backup already created at the receipt's `backup_path`.
   Preserve the same `GRAPHIFY_VIZ_NODE_LIMIT` value through finalization.
4. Run `uv run "$JEVIFY_SKILL_DIR/scripts/run.py" finalize --json` with the
   receipt's backup path when present.
5. Continue only when finalize returns current graph, zero pending files, and
   an acceptable integrity diagnostic. Delete the backup only after success;
   restore it after any failed or interrupted replacement. Otherwise report blocked.
```

The host must not ask the user for a repository, provider key, question, mode, or permission to continue. Existing cost guardrails still prohibit paid providers.

- [ ] **Step 4: Implement `finalize` as verification, not repair**

`finalize` must never run Graphify. It calls `inspect_context` and `diagnose_file`, verifies the report counts, and rejects a missing or stale-marked `graph.html` unless `GRAPHIFY_VIZ_NODE_LIMIT=0`; then it returns a verification receipt. It returns exit `1` unless freshness is current, artifacts are acceptable, and no blocking health count is nonzero. Task 4 extends the successful receipt with insights after `jevify_insights.py` exists.

Blocking counts are:

```python
BLOCKING_HEALTH_KEYS = (
    "missing_endpoint_edges",
    "dangling_endpoint_edges",
    "directed_same_endpoint_collapsed_edges",
    "undirected_same_endpoint_collapsed_edges",
)
```

Self-loops, relation variants, syntax warnings, sensitive skips, and unverified semantic nodes remain visible caveats but do not silently become blockers.

- [ ] **Step 5: Add failure-preservation tests**

```python
@pytest.mark.parametrize("diagnostic", [
    "semantic extraction is incomplete",
    "refusing to overwrite",
    "dangling endpoint",
])
def test_failed_host_update_preserves_accepted_graph(
    repo_with_graph, monkeypatch, diagnostic,
):
    repo, graph = repo_with_graph
    accepted = graph.read_bytes()
    monkeypatch.setattr(
        autorun, "inspect_context", lambda *_args, **_kwargs: blocked_context(diagnostic)
    )

    receipt = finalize_update(repo, backup=write_private_backup(graph))

    assert receipt.status == "blocked"
    assert graph.read_bytes() == accepted


def test_corrupt_semantic_handoff_restores_exact_graph_bytes(
    repo_with_graph, monkeypatch,
):
    repo, graph = repo_with_graph
    accepted = graph.read_bytes()
    backup = write_private_backup(graph)
    graph.write_text("{interrupted", encoding="utf-8")
    monkeypatch.setattr(
        autorun, "inspect_context", lambda *_args, **_kwargs: corrupt_context()
    )

    receipt = finalize_update(repo, backup=backup)

    assert receipt.status == "blocked"
    assert graph.read_bytes() == accepted
```

Implement `write_private_backup()` in the test fixture with mode `0600`; production backup paths live under a mode-`0700` temporary directory outside Git and are deleted after either restoration or accepted finalization.

- [ ] **Step 6: Audit canonical and installed host artifacts**

```bash
mac-gate uv run --frozen pytest \
  tests/test_jevify_skill.py::test_portable_skill_code_matches_project_code \
  tests/test_jevify_install.py -q
```

Expected: canonical project modules match the portable Jevify modules, and clean-home Claude/Codex installs contain the same semantic handoff contract.

- [ ] **Step 7: Run focused checks and commit**

```bash
mac-gate uv run --frozen pytest tests/test_jevify_skill.py tests/test_jevify_install.py -q
```

```bash
git add skills/jevify/SKILL.md skills/jevify/references/graph.md \
  skills/jevify/scripts/run.py tests/test_jevify_skill.py tests/test_jevify_install.py
git commit -m "feat: route Jevify semantic updates through Graphify"
```

### Task 4: Produce a Compact Actionable Insight Bundle

**Files:**
- Create: `tools/jevify_insights.py`
- Create: `skills/jevify/scripts/tools/jevify_insights.py`
- Modify: `tools/jevify_autorun.py`
- Modify: `skills/jevify/scripts/tools/jevify_autorun.py`
- Modify: `skills/jevify/scripts/run.py`
- Modify: `tests/test_jevify_autorun.py`
- Modify: `tests/test_jevify_skill.py`

**Interfaces:**
- Consumes: accepted `graph.json`, optional explicit user question.
- Produces: `InsightBundle`, `build_insights(graph, graph_path) -> InsightBundle`, schema-v2 JSON fields, and the successful `finalize` extension consumed by Task 3's host flow.

- [ ] **Step 1: Write failing question-quality tests**

```python
def test_insights_return_three_to_five_diversified_questions(cleanmymac_graph):
    bundle = build_insights(cleanmymac_graph, cleanmymac_graph_path)
    assert 3 <= len(bundle.questions) <= 5
    assert len({question.kind for question in bundle.questions}) >= 2


def test_question_text_deduplicates_repeated_labels(sample_graph):
    bundle = build_insights(sample_graph, sample_graph_path)
    text = bundle.questions[0].text
    assert text.count("`SafeCleaner`") == 1
    assert text.count("`CleanupDestination`") == 1


def test_low_confidence_question_does_not_outrank_bridge(monkeypatch, sample_graph):
    monkeypatch.setattr(insights, "suggest_questions", lambda *_args, **_kwargs: [
        {"type": "ambiguous_edge", "question": "ambiguous", "why": "hint",
         "low_confidence": True},
        {"type": "bridge_node", "question": "bridge", "why": "crosses communities",
         "low_confidence": False},
    ])

    bundle = build_insights(sample_graph, sample_graph_path)

    assert [item.text for item in bundle.questions] == ["bridge", "ambiguous"]


def test_update_only_does_not_call_graph_query(
    monkeypatch, sample_graph, sample_graph_path, repo_with_graph,
):
    monkeypatch.setattr(autorun, "query_graphify_exact", lambda *_: pytest.fail())
    repo, _graph_path = repo_with_graph
    receipt = finalize_update(repo)
    assert receipt.insights.questions
```

- [ ] **Step 2: Run tests and confirm the current raw-question behavior**

Run `mac-gate uv run --frozen pytest tests/test_jevify_autorun.py -q`.

Expected: FAIL because the insight types and label normalization do not exist.

- [ ] **Step 3: Add focused insight types**

```python
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
```

Use Graphify's existing `god_nodes`, `surprising_connections`, `suggest_questions`, `_communities_from_graph`, and `diagnose_file`; never recreate graph analysis.

- [ ] **Step 4: Normalize and rank Graphify questions at the Jevify boundary**

Implement `normalize_question()` to preserve backticked labels in first-seen order and remove repeated label arguments. Rank non-low-confidence bridge questions first, then inferred God Node questions, isolated-node questions, and ambiguous-edge hints. Diversify round-robin by type and cap at five.

Do not modify `graphify/analyze.py` in this task. If the normalized output is broadly useful upstream, capture it as a separate future Graphify proposal after Jevify proves the behavior.

- [ ] **Step 5: Add truncation-aware explicit queries**

Keep explicit questions on `query_graphify_exact`. Add a response status:

```python
@dataclass(frozen=True)
class QueryResult:
    answer: str
    truncated: bool
    suggested_narrowing: str | None
```

Detect Graphify's structured truncation marker from the query result. When truncated, label the answer incomplete and recommend the existing `path`, `explain`, or `context_filter` seam; do not increase the budget automatically.

- [ ] **Step 6: Extend JSON without hiding existing fields**

Set `schema_version=2`. Keep `repo`, `graph`, `question`, `mode`, `live_enrichment`, and `answer`. Add `freshness`, `update`, `graph_stats`, `health`, `god_nodes`, `connections`, and `questions`. For update-only results, use JSON `null` for `question` and `answer`.

- [ ] **Step 7: Add human rendering tests**

Pin this section order:

```text
Update
Graph
Health
God Nodes
Connections
Suggested Questions
Memory / JEV
```

Assert a five-question output fits within 140 lines, contains no raw 200-node traversal, and discloses every nonzero caveat.

- [ ] **Step 8: Run focused checks and commit**

```bash
mac-gate uv run --frozen pytest tests/test_jevify_autorun.py tests/test_jevify_skill.py -q
mac-gate uv run --frozen ruff check tools/jevify_insights.py tools/jevify_autorun.py tests/test_jevify_autorun.py
```

```bash
git add tools/jevify_insights.py tools/jevify_autorun.py \
  skills/jevify/scripts/tools/jevify_insights.py \
  skills/jevify/scripts/tools/jevify_autorun.py \
  skills/jevify/scripts/run.py tests/test_jevify_autorun.py tests/test_jevify_skill.py
git commit -m "feat: surface actionable Jevify graph insights"
```

### Task 5: Preserve Portable Installation and Graphify Compatibility

**Files:**
- Modify: `scripts/install_jevify_skill.py`
- Modify: `tests/test_jevify_install.py`
- Modify: `tests/test_graph_invariance.py`
- Modify: `tests/test_jevify_skill.py`
- Modify: `skills/jevify/scripts/run.py` dependency pin

**Interfaces:**
- Consumes: canonical project modules and current merged candidate SHA.
- Produces: receipt-owned Claude/Codex installations with identical update behavior and unchanged Graphify structural output.

- [ ] **Step 1: Add portable-copy parity tests**

Compare these exact file pairs byte-for-byte:

```python
PORTABLE_MODULES = (
    "jevify_autorun.py",
    "jevify_graph_state.py",
    "jevify_insights.py",
)
```

Add a test that the PEP 723 dependency in `skills/jevify/scripts/run.py` points to the implementation candidate commit used by the installer evidence, not the pre-amplification commit.

- [ ] **Step 2: Add clean-home update tests**

For both Claude and Codex temporary homes:

1. install Jevify;
2. run `doctor` against a ready fixture;
3. modify a source file without committing;
4. assert `doctor` returns `graph_current=false`;
5. run the code-only update;
6. assert a second `doctor` returns `graph_current=true`;
7. reinstall idempotently and uninstall through the receipt.

Provider variables must contain sentinel values in the parent test and be absent from the Graphify child.

- [ ] **Step 3: Preserve graph invariance**

Run the same fixture through direct Graphify code-only update and Jevify code-only update. Canonicalize only volatile metadata and assert identical node and edge multisets:

```python
assert canonical_graph(jevify_graph) == canonical_graph(graphify_graph)
```

Do not exempt missing nodes, edges, confidence, direction, `source_file`, or community membership.

- [ ] **Step 4: Run compatibility checks and commit**

```bash
mac-gate uv run --frozen pytest \
  tests/test_jevify_install.py tests/test_jevify_skill.py tests/test_graph_invariance.py -q
```

```bash
git add scripts/install_jevify_skill.py skills/jevify/scripts/run.py \
  tests/test_jevify_install.py tests/test_jevify_skill.py tests/test_graph_invariance.py
git commit -m "test: prove portable Jevify update compatibility"
```

### Task 6: Run Bounded Product Evidence and Publish Only Supported Claims

**Files:**
- Create: `docs/jevify-graphify-amplification-evaluation.md`
- Modify: `README.md`
- Modify: `docs/jevify-roadmap.md`
- Modify: `docs/jevify-beta-evidence.md`
- Modify: `benchmarks/jevify-beta/scorecard.md`
- Modify: `benchmarks/jevify-beta/scorecard.json`
- Modify: `docs/jevify/index.html`

**Interfaces:**
- Consumes: tested candidate SHA, one CleanMyMac reproduction, one code-only fixture, one mixed public fixture.
- Produces: immutable local evidence receipt and public claims limited to verified update parity and actionable output.

- [ ] **Step 1: Freeze a three-case acceptance manifest before running outputs**

Create a private mode-`0600` manifest outside Git with this script so the candidate SHA is captured rather than typed:

```python
import json
import os
import subprocess
from pathlib import Path

root = Path.home() / ".local/share/jevify/graphify-amplification"
root.mkdir(parents=True, exist_ok=True, mode=0o700)
root.chmod(0o700)
payload = {
    "schema_version": 1,
    "candidate_sha": subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True,
    ).strip(),
    "cases": [
        {"id": "cleanmymac-mixed", "expected_route": "host_graphify"},
        {"id": "axios-code-only", "expected_route": "local_graphify",
         "origin": "https://github.com/axios/axios.git",
         "commit": "c6cce43cd94489f655f4488c5a50ecaf781c94f2"},
        {"id": "gson-mixed", "expected_route": "host_graphify",
         "origin": "https://github.com/google/gson.git",
         "commit": "796193d0326a2f44bc314bf24262732ea3e64014"},
    ],
}
path = root / "acceptance-manifest.json"
descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
    json.dump(payload, stream, sort_keys=True)
```

For `axios-code-only`, append a newline to the first tracked `lib/**/*.js` file in lexical order. For `gson-mixed`, append a newline to `gson/src/main/java/com/google/gson/Gson.java` and `README.md`. For `cleanmymac-mixed`, use an isolated worktree at `3179c59d47eca5b71dfd5ac8d69ccf043f41ec0a`, copy in the accepted current Graphify artifacts, then append a newline to `Sources/CleanMyMac/SafeCleaner.swift` and `README.md`. Record the manifest SHA-256 in the evaluation report, not the private checkout paths or questions.

- [ ] **Step 2: Run the bounded acceptance cases**

For each case, record before/after counts, pending file counts, route, integrity summary, report counts, visualization status, question count, duplicated-label count, paid request count, and terminal status. This is a three-case product acceptance check, not a latency or superiority benchmark.

Pass gates:

- pending after update is zero;
- direct Graphify and Jevify structural graphs are equivalent;
- blocking integrity counts are zero;
- `GRAPH_REPORT.md` exists and its node/edge counts match the accepted graph;
- `graph.html` exists without `.graph.html.stale`, or the frozen environment explicitly sets `GRAPHIFY_VIZ_NODE_LIMIT=0`;
- three to five questions are returned;
- duplicated-label count is zero;
- paid request count is zero;
- a second update returns `already_current` without rewriting graph artifacts.

- [ ] **Step 3: Write the evaluation report**

Document the candidate SHA, Graphify version, manifest hash, environments, exact gates, results, caveats, and the CleanMyMac regression. State explicitly that the evidence proves update parity and output usefulness under three bounded cases, not product superiority, general answer quality, or a JEV gain.

- [ ] **Step 4: Update product copy and scorecard**

Use this positioning consistently:

> Jevify orchestrates the complete Graphify workflow, verifies that the graph is current, and adds prioritized questions and optional reviewed memory. Graphify remains the structural engine; JEV remains optional.

Remove or reject wording such as `upgrade`, `better`, `faster`, `more efficient`, `anabolic`, or `replaces Graphify` from public claims.

- [ ] **Step 5: Run all local gates through `mac-gate`**

The repository has no npm preflight. Run the current CI-equivalent commands exactly; do not run them outside `mac-gate`:

```bash
mac-gate uv sync --all-extras --frozen
mac-gate uv run --frozen pytest tests/ -q --tb=short
mac-gate uv run --frozen ruff check graphify tools skills/jevify/scripts tests
mac-gate uv run --frozen pyright \
  tools/jevify_autorun.py tools/jevify_graph_state.py tools/jevify_insights.py \
  skills/jevify/scripts/run.py skills/jevify/scripts/tools/jevify_autorun.py \
  skills/jevify/scripts/tools/jevify_graph_state.py \
  skills/jevify/scripts/tools/jevify_insights.py
mac-gate uv run --frozen python -m tools.skillgen --check
mac-gate uv run --frozen python -m tools.skillgen --audit-coverage
mac-gate uv run --frozen python -m tools.skillgen --schema-singleton
mac-gate uv run --frozen python -m tools.skillgen --monolith-roundtrip
mac-gate uv run --frozen python -m tools.skillgen --always-on-roundtrip
mac-gate env GRAPHIFY_TEST_CLI="$PWD/.venv/bin/graphify" bun test tests/pi.test.ts
mac-gate uv run --frozen bandit -r graphify skills/jevify/scripts/tools \
  tools/jev_memory_pilot.py tools/jev_memory_pilot_api.py \
  tools/jevify_demo.py tools/jevify_stress.py tools/jevify_full_stress.py \
  tools/jevify_paid_stress.py tools/jevify_product_batch.py \
  tools/jevify_product_dataset.py tools/jevify_product_eval.py \
  tools/jevify_evidence_bundle.py tools/jevify_install_eval.py \
  tools/jevify_reproduction.py tools/jevify_zero_config_eval.py \
  tools/jevify_claim_check.py -ll
mac-gate uv run --frozen pip-audit --strict
```

Expected: every command exits `0`. Do not run `next build`, a Codespace, a paid API, or a long benchmark.

- [ ] **Step 6: Refresh Graphify after code changes**

Run the repository's existing Graphify update workflow locally with provider keys unset. Validate `built_at_commit`, graph size, shrink behavior, and `graphify diagnose multigraph`. Keep graph artifacts local unless they are already versioned by this repository's policy.

- [ ] **Step 7: Review the complete diff and commit documentation**

```bash
git diff --check
git diff --stat origin/jevify...HEAD
git diff origin/jevify...HEAD -- \
  .specs skills/jevify tools tests scripts README.md docs benchmarks
```

Confirm every public claim is supported by the bounded receipt.

```bash
git add README.md docs/jevify-roadmap.md docs/jevify-beta-evidence.md \
  docs/jevify-graphify-amplification-evaluation.md docs/jevify/index.html \
  benchmarks/jevify-beta/scorecard.md benchmarks/jevify-beta/scorecard.json
git commit -m "docs: document Jevify Graphify amplification evidence"
```

- [ ] **Step 8: Push one branch, update one PR, and integrate autonomously**

Push `feat/jevify-graphify-amplification-20261022`, open one PR to `jevify`, review the diff, and wait for all required checks on the latest SHA. Merge only after the local gate and every required GitHub/Pages check are green; then verify the post-merge CI and public page at their persisted terminal states.

## Completion Gate

The implementation is complete only when all of these are true:

- same-HEAD manifest drift is detected and covered by regression tests;
- code-only and semantic update routes terminate honestly;
- Graphify artifacts and integrity protections are preserved;
- Jevify returns three to five useful questions without duplicated labels or an automatic broad traversal;
- installed Claude/Codex copies behave identically;
- the three bounded acceptance cases pass without paid calls;
- documentation makes Graphify dependency and JEV's optional status explicit;
- the single PR is merged and post-merge checks are terminal green.

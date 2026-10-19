# Jeviphy Phase 2 Product Superiority Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible product benchmark and the smallest provenance, fallback, and usability improvements required for Jeviphy to demonstrate a real advantage over its pinned Graphify base.

**Architecture:** Keep Graphify as the unchanged graph and query engine. Extend the existing Jeviphy pilot with manifest validation, Git-aware source freshness, a paired runner, and a mechanical scorecard; expose those capabilities through the existing portable skill runner instead of creating a second application stack. Optimize only from training repositories, freeze a holdout before changes, and allow the scorecard to reject the superiority claim.

**Tech Stack:** Python 3.10+, standard library, NetworkX, existing Graphify APIs, pytest, JSON Schema-shaped validation without a new dependency, Git, `uv`, and the existing portable Claude Code/Codex skill.

**Spec:** `.specs/tasks/draft/jeviphy-phase-2-product-superiority.feature.md`

## Global Constraints

- Pin both arms to the same upstream Graphify SHA, graph bytes, repository commit, machine class, Python version, agent/model, context limit, and wall-clock limit.
- Use Graphify v8 commit `86c57be8204673c2a1b9849a3292a7dd3ab373d8`, the current upstream head verified on 2026-10-19; changing this pin creates benchmark v3.
- Freeze 120 tasks from at least 6 public repositories and 3 languages: 40 valid source-backed, 20 stale/misleading, 40 no-source controls, and 20 cross-file/ambiguous.
- Keep at least 20 tasks from one repository as an unseen holdout until the candidate release is frozen.
- Require at least +10 percentage points in task success with a positive 95% paired bootstrap lower bound; preserve no-source success within 2 percentage points.
- Require at least 15% lower median input tokens or 20% lower median completion time; keep overall p95 completion time within 5%.
- Reject changed, missing, untracked, non-ancestor, or graph-absent source evidence and use exact unscoped Graphify fallback when no usable path remains.
- Make no paid model call or content upload by default; live execution still requires explicit user approval, positive call limit, and positive cost ceiling.
- Keep graph inputs read-only and private corpora/transcripts outside Git with mode `0600`.
- Add no runtime dependency; reuse the current Jeviphy pilot, stress runner, and skill parity test.
- Use branch → one PR → `jeviphy`; run local gates only through `mac-gate`.

## Review Focus

1. **Partially stale evidence:** retain unchanged valid paths, reject changed paths, and fall back only when none remain; Task 2 covers the mixed case.
2. **Resume after input drift:** reject a journal when any repository, graph, arm, manifest, or command hash changes; Task 4 covers each pin.
3. **Timeout and crash accounting:** preserve every failed arm in the denominator and never compare an incomplete pair; Task 4 covers timeout, non-zero exit, and missing result.
4. **Claim inflation:** emit only the exact release-table claim and fail closed when confidence, parity, usability, or reproduction is missing; Task 5 covers each result class.
5. **Installer damage:** uninstall only files listed in its receipt and preserve pre-existing skill directories; Task 6 covers clean and conflicting homes.

---

## File and Interface Map

| Responsibility | File |
| --- | --- |
| SDD acceptance contract | `.specs/tasks/draft/jeviphy-phase-2-product-superiority.feature.md` |
| Manifest model and validation | `tools/jeviphy_eval_contract.py` |
| Source freshness classification | `tools/jeviphy_provenance.py` |
| Paired retrieval and task runner | `tools/jeviphy_product_eval.py` |
| Bootstrap metrics and release decision | `tools/jeviphy_product_score.py` |
| Existing retrieval/fallback integration | `tools/jev_memory_pilot.py` |
| Portable user commands | `skills/jeviphy/scripts/run.py` |
| Clean-home installer | `scripts/install_jeviphy_skill.py` |
| Public cohort contract | `benchmarks/jeviphy-v2/manifest.schema.json` and `benchmarks/jeviphy-v2/README.md` |
| Public evidence | `docs/jeviphy-v2-evaluation.md` |

### Task 1: Freeze and Validate the Benchmark Contract

**Files:**
- Create: `tools/jeviphy_eval_contract.py`
- Create: `tests/test_jeviphy_eval_contract.py`
- Create: `benchmarks/jeviphy-v2/manifest.schema.json`
- Create: `benchmarks/jeviphy-v2/README.md`

**Interfaces:**
- Consumes: JSON manifest path and repository-local public metadata.
- Produces: `load_manifest(path: Path) -> EvalManifest`, `validate_manifest(manifest: EvalManifest) -> None`, and frozen dataclasses `EvalManifest`, `RepoPin`, `EvalCase`, `MemoryEvidence`.

- [ ] **Step 1: Write failing validation tests**

Create tests that construct a minimal valid 120-case manifest with 6 repository pins and 3 languages, then mutate one property per test:

```python
def test_contract_accepts_exact_frozen_shape(valid_manifest_path):
    manifest = load_manifest(valid_manifest_path)
    assert Counter(case.stratum for case in manifest.cases) == {
        "valid_source": 40,
        "stale_source": 20,
        "no_source": 40,
        "ambiguous": 20,
    }


@pytest.mark.parametrize("mutation, message", [
    ("duplicate_id", "duplicate case ID"),
    ("branch_ref", "repository commit must be 40 lowercase hex characters"),
    ("leaked_symbol", "gold symbol leaked"),
    ("missing_oracle", "oracle command is required"),
    ("short_holdout", "holdout needs at least 20 cases"),
    ("two_languages", "at least 3 languages"),
])
def test_contract_rejects_invalid_cohort(valid_manifest_dict, mutation, message, tmp_path):
    mutate_manifest(valid_manifest_dict, mutation)
    path = write_manifest(tmp_path, valid_manifest_dict)
    with pytest.raises(ValueError, match=message):
        load_manifest(path)
```

- [ ] **Step 2: Run the focused tests and confirm failure**

Run `mac-gate uv run --frozen pytest tests/test_jeviphy_eval_contract.py -q`.

Expected: collection fails with `ModuleNotFoundError: No module named 'tools.jeviphy_eval_contract'`.

- [ ] **Step 3: Implement immutable contract types and validation**

Use frozen dataclasses and explicit standard-library validation:

```python
@dataclass(frozen=True)
class MemoryEvidence:
    summary: str
    source_paths: tuple[str, ...]
    source_commit: str | None
    reviewed_at: str | None


@dataclass(frozen=True)
class EvalCase:
    id: str
    repo_id: str
    stratum: Literal["valid_source", "stale_source", "no_source", "ambiguous"]
    question: str
    oracle_argv: tuple[str, ...]
    timeout_seconds: int
    gold_files: tuple[str, ...]
    gold_symbols: tuple[str, ...]
    memory: MemoryEvidence
    holdout: bool


@dataclass(frozen=True)
class RepoPin:
    id: str
    url: str
    commit: str
    language: str


@dataclass(frozen=True)
class EvalManifest:
    schema_version: int
    graphify_commit: str
    repos: tuple[RepoPin, ...]
    cases: tuple[EvalCase, ...]
```

Validate exact keys, safe relative POSIX paths, 40-character lowercase Git SHAs, positive timeouts no greater than 1800 seconds, non-empty argv arrays, unique IDs, exact stratum counts, repository/language minimums, and the holdout count. Normalize neither questions nor paths; reject invalid input.

- [ ] **Step 4: Add the public schema and cohort instructions**

Define the same required fields in `manifest.schema.json` with `additionalProperties: false`. In `README.md`, prescribe this order: select public repository commits, write questions and oracles, freeze gold files/symbols, split the holdout, add reviewed memory evidence, hash the manifest, then run either arm. State that changing the manifest creates a new benchmark version.

- [ ] **Step 5: Run tests and commit**

Run:

```bash
mac-gate uv run --frozen pytest tests/test_jeviphy_eval_contract.py -q
mac-gate uv run --frozen ruff check tools/jeviphy_eval_contract.py tests/test_jeviphy_eval_contract.py
```

Expected: both commands exit `0`.

Commit:

```bash
git add tools/jeviphy_eval_contract.py tests/test_jeviphy_eval_contract.py benchmarks/jeviphy-v2
git commit -m "test: freeze Jeviphy v2 evaluation contract"
```

### Task 2: Reject Stale Source Evidence Before Retrieval

**Files:**
- Create: `tools/jeviphy_provenance.py`
- Create: `tests/test_jeviphy_provenance.py`
- Modify: `tools/jev_memory_pilot.py`
- Modify: `tests/test_jev_memory_pilot.py`
- Modify: `skills/jeviphy/scripts/tools/jev_memory_pilot.py`

**Interfaces:**
- Consumes: `classify_source_evidence(repo: Path, graph: nx.Graph, source_commit: str | None, paths: Sequence[str])` inputs and existing `candidate_pool(...)`.
- Produces: `SourceEvidence` with `usable_paths`, `rejected_paths`, and `reason`; `candidate_pool(...)` receives only `usable_paths`.

- [ ] **Step 1: Write provenance tests in temporary Git repositories**

Cover unchanged, changed, deleted, untracked, traversal, non-ancestor, graph-absent, and mixed paths:

```python
def test_changed_path_is_rejected(repo_with_two_commits, graph):
    evidence = classify_source_evidence(
        repo_with_two_commits.path,
        graph,
        repo_with_two_commits.first_commit,
        ["src/changed.py"],
    )
    assert evidence.usable_paths == ()
    assert evidence.rejected_paths == ("src/changed.py",)
    assert evidence.reason == "no_fresh_graph_paths"


def test_mixed_paths_keep_only_fresh_graph_paths(repo_with_two_commits, graph):
    evidence = classify_source_evidence(
        repo_with_two_commits.path,
        graph,
        repo_with_two_commits.first_commit,
        ["src/stable.py", "src/changed.py"],
    )
    assert evidence.usable_paths == ("src/stable.py",)
    assert evidence.rejected_paths == ("src/changed.py",)
```

Add a pilot regression test that patches `query_unscoped_graphify` and proves an empty `usable_paths` set returns its output unchanged.

- [ ] **Step 2: Run the focused tests and confirm failure**

Run `mac-gate uv run --frozen pytest tests/test_jeviphy_provenance.py tests/test_jev_memory_pilot.py -q`.

Expected: import failure for `tools.jeviphy_provenance` and fallback regression failure.

- [ ] **Step 3: Implement Git-aware classification**

Create:

```python
@dataclass(frozen=True)
class SourceEvidence:
    usable_paths: tuple[str, ...]
    rejected_paths: tuple[str, ...]
    reason: str


def classify_source_evidence(
    repo: Path,
    graph: nx.Graph,
    source_commit: str | None,
    paths: Sequence[str],
) -> SourceEvidence:
    graph_paths = {str(data.get("source_file")) for _, data in graph.nodes(data=True)}
    unique_paths = tuple(dict.fromkeys(paths))
    if not source_commit or subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor", source_commit, "HEAD"]
    ).returncode:
        return SourceEvidence((), unique_paths, "source_commit_not_ancestor")
    usable, rejected = [], []
    for relative in unique_paths:
        candidate = (repo / relative).resolve()
        safe = candidate.is_relative_to(repo.resolve())
        tracked = safe and subprocess.run(
            ["git", "-C", str(repo), "ls-files", "--error-unmatch", "--", relative],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode == 0
        unchanged = tracked and subprocess.run(
            ["git", "-C", str(repo), "diff", "--quiet", source_commit, "HEAD", "--", relative]
        ).returncode == 0
        (usable if unchanged and relative in graph_paths else rejected).append(relative)
    return SourceEvidence(
        tuple(usable), tuple(rejected), "fresh_graph_paths" if usable else "no_fresh_graph_paths"
    )
```

Resolve paths without leaving `repo`; use `git merge-base --is-ancestor`, `git ls-files --error-unmatch`, and `git diff --quiet <source_commit>..HEAD -- <path>`. Build the graph-backed path set from node `source_file` attributes. Missing `source_commit` makes all paths ineligible for freshness-sensitive mode. Return paths in input order without duplicates.

- [ ] **Step 4: Wire classification into the existing fast-source path**

Add optional `source_commit: str | None = None` to `candidate_pool(...)`. When `fast_source` is true, call `classify_source_evidence`; pass only `usable_paths` to the current source-scoping logic. If none remain, return the same candidate list produced with `memory_summaries=None`, preserving order and fields.

Copy the repository implementation to the portable skill path and retain the existing byte-parity assertion in `tests/test_jeviphy_skill.py`.

- [ ] **Step 5: Run tests and commit**

Run:

```bash
mac-gate uv run --frozen pytest tests/test_jeviphy_provenance.py tests/test_jev_memory_pilot.py tests/test_jeviphy_skill.py -q
mac-gate uv run --frozen ruff check tools/jeviphy_provenance.py tools/jev_memory_pilot.py tests/test_jeviphy_provenance.py
```

Expected: all commands exit `0`, including byte parity.

Commit:

```bash
git add tools/jeviphy_provenance.py tools/jev_memory_pilot.py tests/test_jeviphy_provenance.py tests/test_jev_memory_pilot.py skills/jeviphy/scripts/tools/jev_memory_pilot.py
git commit -m "feat: reject stale Jeviphy source evidence"
```

### Task 3: Create the Frozen Public Cohort Without Viewing Holdout Results

**Files:**
- Create: `benchmarks/jeviphy-v2/manifest.json`
- Create: `benchmarks/jeviphy-v2/MANIFEST.sha256`
- Create: `benchmarks/jeviphy-v2/selection-log.md`
- Test: `tests/test_jeviphy_v2_manifest.py`

**Interfaces:**
- Consumes: public immutable repositories and `load_manifest(...)` from Task 1.
- Produces: the exact 120-case public benchmark used by every later task.

- [ ] **Step 1: Select repository pins before writing cases**

Use these exact public pins and allocations, verified on 2026-10-19:

| Repository | Commit | Language | Cases | Strata: valid/stale/control/ambiguous |
| --- | --- | --- | ---: | --- |
| `pallets/click` | `2247b35ea1c47c727d7a06e51fa280e12a863ff6` | Python | 20 holdout | 7/3/7/3 |
| `pallets/itsdangerous` | `672971d66a2ef9f85151e53283113f33d642dabd` | Python | 20 | 7/3/7/3 |
| `sindresorhus/p-limit` | `a8a6fbec4e0e866d6d779b10889bb4f5567e70eb` | TypeScript | 20 | 7/3/7/3 |
| `sindresorhus/p-map` | `d61b6a33cc1d5533ad5711b435959f3f78c3d2fe` | TypeScript | 20 | 7/3/7/3 |
| `tidwall/gjson` | `690362d6edf4bcbde1e9f54d552d3814f1cd5bcb` | Go | 20 | 6/4/6/4 |
| `charmbracelet/lipgloss` | `19f011f1cc573e5d2bf9d7a9c4f14d429647759e` | Go | 20 | 6/4/6/4 |

Verify each license from the pinned tree before accepting cases; reject and replace the whole repository before the manifest freeze if it is not permissive or cannot run offline after dependency installation. Do not substitute a branch head for a listed commit.

- [ ] **Step 2: Write deterministic tasks and oracles**

For each repository, derive tasks from closed bug-fix commits or existing focused tests. Store an argv oracle that can run offline after dependencies are installed. Questions describe behavior without copying gold symbol names. Memory summaries describe prior decisions without gold symbols; only `source_paths` may reveal files.

- [ ] **Step 3: Write the manifest hash before either arm runs**

Run:

```bash
shasum -a 256 benchmarks/jeviphy-v2/manifest.json > benchmarks/jeviphy-v2/MANIFEST.sha256
```

Expected: the file contains one lowercase 64-character digest followed by the manifest path.

- [ ] **Step 4: Validate labels before either arm runs**

Create `tests/test_jeviphy_v2_manifest.py`:

```python
def test_public_manifest_satisfies_frozen_contract():
    manifest = load_manifest(Path("benchmarks/jeviphy-v2/manifest.json"))
    assert len(manifest.cases) == 120
    assert sum(case.holdout for case in manifest.cases) >= 20


def test_public_manifest_hash_is_pinned():
    manifest = Path("benchmarks/jeviphy-v2/manifest.json")
    expected = Path("benchmarks/jeviphy-v2/MANIFEST.sha256").read_text().split()[0]
    assert hashlib.sha256(manifest.read_bytes()).hexdigest() == expected
```

- [ ] **Step 5: Freeze and commit the cohort**

Run:

```bash
mac-gate uv run --frozen pytest tests/test_jeviphy_eval_contract.py tests/test_jeviphy_v2_manifest.py -q
git add benchmarks/jeviphy-v2 tests/test_jeviphy_v2_manifest.py
git commit -m "test: freeze public Jeviphy v2 cohort"
```

Expected: validation passes and the committed hash matches. Do not execute retrieval or agent arms before this commit exists.

### Task 4: Run Paired Arms With Resume-Safe Evidence

**Files:**
- Create: `tools/jeviphy_product_eval.py`
- Create: `tests/test_jeviphy_product_eval.py`
- Modify: `tools/jeviphy_full_stress.py`

**Interfaces:**
- Consumes: `EvalManifest`, `candidate_pool(...)`, `query_unscoped_graphify(...)`, and an agent argv template containing `{repo}`, `{question_file}`, and `{context_file}`.
- Produces: `run_retrieval_pair(...) -> PairRecord`, `run_task_pair(...) -> PairRecord`, append-only JSONL journal, and a sealed result JSON.

- [ ] **Step 1: Write runner boundary tests**

Use local stub executables and temporary Git repositories to prove alternating order, timeout accounting, non-zero oracle failure, graph immutability, exact control output, and pin-aware resume:

```python
def test_resume_rejects_changed_graph(run_fixture):
    run_fixture.write_completed_pair()
    run_fixture.graph.write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="graph hash differs from journal"):
        resume_run(run_fixture.config)


def test_timeout_remains_failed_in_pair(run_fixture):
    pair = run_task_pair(run_fixture.case, run_fixture.timeout_agent, order=("graphify", "jeviphy"))
    assert pair.graphify.status == "timeout"
    assert pair.graphify.success is False
    assert pair.complete is True
```

- [ ] **Step 2: Run the tests and confirm failure**

Run `mac-gate uv run --frozen pytest tests/test_jeviphy_product_eval.py -q`.

Expected: import failure for `tools.jeviphy_product_eval`.

- [ ] **Step 3: Implement immutable run records**

Define frozen `ArmRecord` and `PairRecord` dataclasses. Invoke subprocesses with argv lists, `shell=False`, bounded timeouts, isolated task worktrees, and explicit environment allowlists. Hash stdout and stderr; store full transcripts only in the private run directory. Append and `fsync` each completed pair before starting the next one.

- [ ] **Step 4: Add strict pinning and balanced execution**

Before every arm, verify repository HEAD, clean status, graph SHA-256, manifest SHA-256, Graphify SHA, Jeviphy SHA, Python version, command hash, and unchanged graph mtime/content. Alternate arm order by case index and pass. Run one unmeasured warm-up and at least five retrieval passes.

- [ ] **Step 5: Add explicit live-execution guardrails**

Default to retrieval-only offline execution. Require all three flags before launching the supplied agent command:

```text
--allow-network-agent
--max-agent-calls <positive integer>
--max-cost-usd <positive decimal>
```

Reject a manifest whose paired arms exceed the call limit. Record the approved ceilings, while never reading or persisting API keys.

- [ ] **Step 6: Run tests and commit**

Run:

```bash
mac-gate uv run --frozen pytest tests/test_jeviphy_product_eval.py tests/test_jeviphy_full_stress.py -q
mac-gate uv run --frozen ruff check tools/jeviphy_product_eval.py tools/jeviphy_full_stress.py tests/test_jeviphy_product_eval.py
```

Expected: all commands exit `0`.

Commit:

```bash
git add tools/jeviphy_product_eval.py tools/jeviphy_full_stress.py tests/test_jeviphy_product_eval.py
git commit -m "feat: add paired Jeviphy product evaluator"
```

### Task 5: Calculate Gates and Block Inflated Claims

**Files:**
- Create: `tools/jeviphy_product_score.py`
- Create: `tests/test_jeviphy_product_score.py`

**Interfaces:**
- Consumes: sealed result JSON from Task 4 and reproduction receipts from Task 7.
- Produces: `score_run(report: dict) -> Scorecard`, `allowed_claim(scorecard: Scorecard) -> str`, machine-readable JSON, and Markdown scorecard.

- [ ] **Step 1: Write threshold and confidence tests**

Build synthetic paired records around every boundary:

```python
def test_retrieval_win_cannot_be_called_product_superiority(retrieval_only_win):
    scorecard = score_run(retrieval_only_win)
    assert scorecard.retrieval.status == "pass"
    assert scorecard.product.status == "fail"
    assert allowed_claim(scorecard) == "Jeviphy improved source-backed retrieval on the frozen v2 benchmark."


def test_confidence_interval_crossing_zero_blocks_claim(product_point_estimate_win):
    scorecard = score_run(product_point_estimate_win)
    assert scorecard.product.success_difference_pp >= 10
    assert scorecard.product.success_ci95[0] <= 0
    assert scorecard.product.status == "fail"
```

Also cover exactly 10 percentage points, exactly -2 control points, exactly +5% p95, missing failures, missing usability, and zero/one/two reproduction receipts.

- [ ] **Step 2: Run the tests and confirm failure**

Run `mac-gate uv run --frozen pytest tests/test_jeviphy_product_score.py -q`.

Expected: import failure for `tools.jeviphy_product_score`.

- [ ] **Step 3: Implement deterministic scoring**

Use a fixed bootstrap seed of `20261019` and 10,000 paired resamples by case ID. Calculate success difference, precision@5 difference, control difference, token ratio, p50/p95 time ratios, stale-evidence losses, and control byte equality. Missing or malformed records yield `insufficient_evidence`, never exclusion.

Map outcomes to only these claim strings:

```python
NO_DIFFERENCE = "The frozen v2 benchmark did not demonstrate a Jeviphy advantage."
RETRIEVAL_ONLY = "Jeviphy improved source-backed retrieval on the frozen v2 benchmark."
INTERNAL_PRODUCT_WIN = "Jeviphy passed the internal frozen v2 product gates; external reproduction is pending."
REPRODUCED_PRODUCT_WIN = "Jeviphy surpassed Graphify on the frozen v2 benchmark."
```

- [ ] **Step 4: Run tests and commit**

Run:

```bash
mac-gate uv run --frozen pytest tests/test_jeviphy_product_score.py -q
mac-gate uv run --frozen ruff check tools/jeviphy_product_score.py tests/test_jeviphy_product_score.py
```

Expected: both commands exit `0`.

Commit:

```bash
git add tools/jeviphy_product_score.py tests/test_jeviphy_product_score.py
git commit -m "feat: score Jeviphy product superiority gates"
```

### Task 6: Make the Existing Skill Installable and Diagnosable

**Files:**
- Modify: `skills/jeviphy/scripts/run.py`
- Modify: `skills/jeviphy/SKILL.md`
- Create: `scripts/install_jeviphy_skill.py`
- Create: `tests/test_jeviphy_install.py`
- Modify: `tests/test_jeviphy_skill.py`

**Interfaces:**
- Consumes: Task 1 contract, Task 2 provenance classifier, Task 4 runner, and existing `skills/jeviphy` directory.
- Produces: `doctor`, `query`, and `benchmark` subcommands plus receipt-based `install` and `uninstall` actions.

- [ ] **Step 1: Write clean-home and conflict tests**

Run the installer against temporary `HOME` directories. Cover Codex, Claude Code, both hosts, missing Graphify, pre-existing destination, uninstall receipt, and repeated install:

```python
def test_uninstall_preserves_preexisting_skill(tmp_path):
    destination = tmp_path / ".codex/skills/jeviphy"
    destination.mkdir(parents=True)
    marker = destination / "owned-by-user.txt"
    marker.write_text("keep", encoding="utf-8")
    result = run_installer(tmp_path, "install", "--host", "codex")
    assert result.returncode != 0
    assert marker.read_text() == "keep"
```

- [ ] **Step 2: Run the tests and confirm failure**

Run `mac-gate uv run --frozen pytest tests/test_jeviphy_install.py tests/test_jeviphy_skill.py -q`.

Expected: installer test fails because `scripts/install_jeviphy_skill.py` does not exist.

- [ ] **Step 3: Add receipt-based installation**

Copy the checked-in `skills/jeviphy` tree without following symlinks. Refuse a pre-existing destination unless its receipt matches the same source files. Store a JSON receipt containing relative paths and SHA-256 hashes. Uninstall only files whose current hashes still match the receipt, then remove empty directories.

- [ ] **Step 4: Add the three skill commands**

Keep the current query behavior as the default for backward compatibility. Add subparsers:

```text
python skills/jeviphy/scripts/run.py doctor --repo PATH --graph PATH --corpus PATH
python skills/jeviphy/scripts/run.py query --repo PATH --graph PATH --corpus PATH --case-id ID --fast-source
python skills/jeviphy/scripts/run.py benchmark --manifest PATH --graph PATH --repo-root PATH --output PATH
```

`doctor` prints one JSON object and exits non-zero for each missing or stale prerequisite. `query` preserves exact Graphify fallback. `benchmark` defaults to offline retrieval.

- [ ] **Step 5: Measure 20 clean scripted installs**

Run exactly 20 temporary-home installs: 5 macOS Codex, 5 macOS Claude Code, 5 Ubuntu Codex, and 5 Ubuntu Claude Code. Store only aggregate success and time metrics in the result report. Pass when at least 18 of 20 succeed and median clone-to-doctor time is below 300 seconds.

- [ ] **Step 6: Run tests and commit**

Run:

```bash
mac-gate uv run --frozen pytest tests/test_jeviphy_install.py tests/test_jeviphy_skill.py tests/test_jev_memory_pilot.py -q
mac-gate uv run --frozen ruff check scripts/install_jeviphy_skill.py skills/jeviphy/scripts/run.py tests/test_jeviphy_install.py
```

Expected: all commands exit `0`.

Commit:

```bash
git add scripts/install_jeviphy_skill.py skills/jeviphy tests/test_jeviphy_install.py tests/test_jeviphy_skill.py
git commit -m "feat: add Jeviphy install and doctor workflow"
```

### Task 7: Run the Candidate, Reproduce It, and Publish the Honest Result

**Files:**
- Create: `docs/jeviphy-v2-evaluation.md`
- Create: `benchmarks/jeviphy-v2/reproductions/README.md`
- Create after receipt: `benchmarks/jeviphy-v2/reproductions/<github-handle>-<os>.json`
- Modify only after scoring: `README.md`
- Modify only after scoring: `docs/jeviphy/index.html`

**Interfaces:**
- Consumes: frozen manifest, candidate SHA, approved agent command/budget if product arms use a network model, sealed results, and independent receipts.
- Produces: public raw hashes, exact scorecard claim, and release/no-release decision.

- [ ] **Step 1: Verify the candidate still contains the pinned Graphify SHA**

Fetch `Graphify-Labs/graphify` and require `git merge-base --is-ancestor 86c57be8204673c2a1b9849a3292a7dd3ab373d8 HEAD` to exit `0`. Do not rebase after the manifest freeze. If a newer Graphify release is selected, stop v2 and create benchmark v3 with new repository graphs, manifest hashes, and baseline results.

- [ ] **Step 2: Run the offline retrieval benchmark first**

Run the five-pass paired retrieval suite and score it. If no-source byte equality or stale-evidence safety fails, stop the candidate, fix the responsible task, rerun focused tests, regenerate a new candidate SHA, and restart evaluation from the frozen manifest.

- [ ] **Step 3: Obtain separate approval before any network agent benchmark**

Present the exact model/provider, 240 maximum paired calls, input estimate, published unit prices, and a hard dollar ceiling. Run no network task until the user explicitly approves those current-turn costs. Use the same model settings for both arms.

- [ ] **Step 4: Run product arms once on the frozen candidate**

Execute all training cases, freeze the candidate SHA, then unlock and execute the holdout without code changes. Seal raw JSONL into result JSON and record SHA-256 hashes. Failed and timed-out tasks stay in the report.

- [ ] **Step 5: Collect two independent reproduction receipts**

Publish the reproduction command and JSON receipt schema. Require receipt fields `reviewer`, `os`, `machine`, `manifest_sha256`, `graph_sha256`, `graphify_commit`, `jeviphy_commit`, `result_sha256`, and `scorecard`. At least one receipt must come from Ubuntu and neither reviewer may have authored retrieval changes.

- [ ] **Step 6: Generate the evidence report and public copy mechanically**

Run the scorer to produce JSON and Markdown. `docs/jeviphy-v2-evaluation.md`, `README.md`, and the page must use exactly `allowed_claim(scorecard)` plus the cohort size, hashes, confidence interval, negative findings, and limitations. If any required gate fails, retain the current restrained positioning.

- [ ] **Step 7: Run the full repository gate**

Run:

```bash
mac-gate uv run --frozen pre-commit run --all-files
mac-gate uv run --frozen pytest tests/ -q --tb=short
```

Expected: both commands exit `0`. Do not run a local build.

- [ ] **Step 8: Commit, push, and require current remote checks**

Commit:

```bash
git add benchmarks/jeviphy-v2 docs/jeviphy-v2-evaluation.md README.md docs/jeviphy/index.html
git commit -m "docs: publish Jeviphy v2 benchmark decision"
```

Push the single task branch, update its one PR to `jeviphy`, and require every lightweight GitHub check plus any configured deployment preview on the latest SHA. Merge only when the report claim matches the mechanical scorecard and all required checks are green.

## Plan Self-Review Record

- **Spec coverage:** Tasks 1–7 cover cohort freezing, provenance, exact fallback, paired execution, scoring, local-first safety, product commands, usability, compatibility, reproduction, and claim control.
- **Placeholder scan:** The plan contains no deferred implementation markers or unspecified error-handling steps.
- **Type consistency:** `EvalManifest`, `SourceEvidence`, `ArmRecord`, `PairRecord`, and `Scorecard` are introduced before downstream use with stable names.
- **Review focus coverage:** Mixed staleness is in Task 2; pin drift and failed arms are in Task 4; claim classes are in Task 5; installer ownership is in Task 6.
- **Scope control:** The plan reuses Graphify and the existing Jeviphy skill. It adds no database, model, vector store, web service, or runtime dependency.

# Jeviphy Zero-Configuration Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make bare `/jeviphy` complete a useful, source-verified query with no repository, question, corpus, mode, or credential prompt.

**Architecture:** Add one small orchestration module at the portable runner boundary. It resolves the current Git repository and graph, selects a Graphify-generated question when needed, then routes to the existing exact Graphify fallback or existing memory-aware runner; memory and live Jev stay optional. Keep discovery and fallback in Python so Claude Code and Codex consume the same behavior instead of relying on prompt interpretation.

**Tech Stack:** Python 3.10+, standard library, NetworkX, existing Graphify `suggest_questions` and query APIs, existing Jeviphy provenance/runner modules, pytest, Git, `uv`.

**Spec:** `.specs/tasks/draft/jeviphy-zero-configuration-parity.feature.md`

## Global Constraints

- Preserve Graphify as the unchanged extraction and query engine.
- Bare invocation defaults to the current Git worktree and `<repo>/graphify-out/graph.json`.
- Default execution is offline and reads no provider key.
- Corpus and live Jev are optional; their absence or failure cannot block the Graphify answer.
- Do not add a hosted provider, OAuth flow, vector database, runtime dependency, or second application stack.
- Do not change or combine the currently running frozen benchmark; evaluate this candidate separately.
- Keep graphs read-only and private corpora outside Git with existing `0700`/`0600` permissions.
- Preserve explicit `doctor`, `query`, and `benchmark` compatibility.
- Use one task branch and one PR to `jeviphy`; run applicable local gates only through `mac-gate`.

## Review Focus

1. **Nested working directory:** resolve the containing Git root and never use a nested `graphify-out`; Task 1 pins this behavior.
2. **Legacy graph metadata:** accept `_built_at_commit` and `built_at_commit`, reject conflicts and stale values; Task 1 covers all forms.
3. **No useful question:** fail with one bounded diagnostic without asking the user; Task 2 covers empty and low-confidence-only graphs.
4. **Provider failure after approval:** make one attempt, disclose only `live_enrichment=skipped`, and return exit zero with offline output; Task 4 covers HTTP, timeout, redirect, malformed response, and missing key.
5. **Output compatibility:** keep the Graphify answer byte-identical outside the optional audit envelope; Tasks 3 and 5 compare exact bytes.

---

## File and Interface Map

| Responsibility | File |
| --- | --- |
| SDD behavior contract | `.specs/tasks/draft/jeviphy-zero-configuration-parity.feature.md` |
| Auto context, question, and result envelope | `tools/jeviphy_autorun.py` |
| Portable copy of orchestration | `skills/jeviphy/scripts/tools/jeviphy_autorun.py` |
| CLI routing and compatible flags | `skills/jeviphy/scripts/run.py` |
| Existing exact Graphify fallback | `tools/jev_memory_pilot.py` |
| Installed host instructions | `skills/jeviphy/SKILL.md` |
| Auto-path unit tests | `tests/test_jeviphy_autorun.py` |
| Portable CLI and doctor tests | `tests/test_jeviphy_skill.py` |
| Clean-home host tests | `tests/test_jeviphy_install.py` |
| Frozen usability harness | `tools/jeviphy_zero_config_eval.py` |
| Usability harness tests | `tests/test_jeviphy_zero_config_eval.py` |
| Public result report | `docs/jeviphy-zero-configuration-evaluation.md` |

### Task 1: Resolve Repository and Graph Without Parameters

**Files:**
- Create: `tools/jeviphy_autorun.py`
- Create: `tests/test_jeviphy_autorun.py`
- Create: `skills/jeviphy/scripts/tools/jeviphy_autorun.py`
- Modify: `tests/test_jeviphy_skill.py`

**Interfaces:**
- Consumes: `cwd: Path`, optional explicit repository and graph paths.
- Produces: `InvocationContext(repo: Path, graph: Path, head: str)` and `resolve_context(cwd: Path, repo: Path | None = None, graph: Path | None = None) -> InvocationContext`.

- [ ] **Step 1: Write failing repository-discovery tests**

```python
def test_resolve_context_uses_containing_git_root(repo_with_graph, monkeypatch):
    repo, graph = repo_with_graph
    nested = repo / "src" / "nested"
    nested.mkdir(parents=True)
    context = resolve_context(nested)
    assert context.repo == repo.resolve()
    assert context.graph == graph.resolve()


def test_resolve_context_rejects_outside_git(tmp_path):
    with pytest.raises(ContextError, match="not inside a Git worktree"):
        resolve_context(tmp_path)
```

Add cases for an explicit repository, an explicit graph, and paths containing spaces.

- [ ] **Step 2: Run the tests and confirm the missing module**

Run:

```bash
mac-gate uv run --frozen pytest tests/test_jeviphy_autorun.py -q
```

Expected: FAIL during collection with `ModuleNotFoundError: tools.jeviphy_autorun`.

- [ ] **Step 3: Implement the immutable invocation context**

```python
@dataclass(frozen=True)
class InvocationContext:
    repo: Path
    graph: Path
    head: str


class ContextError(ValueError):
    pass


def git_root(cwd: Path) -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise ContextError(f"{cwd.resolve()} is not inside a Git worktree")
    return Path(result.stdout.strip()).resolve()
```

`resolve_context` uses the explicit repository when supplied, otherwise `git_root(cwd)`. Its default graph is `repo / "graphify-out/graph.json"`. It reads `HEAD`, loads the graph only through `_read_graph`, and returns a specific missing or stale diagnostic. If both metadata fields exist and disagree, treat the graph as stale.

- [ ] **Step 4: Add graph-state tests**

Test these exact states:

```python
@pytest.mark.parametrize("metadata_key", ["_built_at_commit", "built_at_commit"])
def test_current_graph_metadata_is_accepted(repo_with_graph, metadata_key): ...


def test_conflicting_graph_commit_fields_are_rejected(repo_with_graph): ...

def test_missing_graph_names_extract_command(repo_without_graph): ...

def test_stale_graph_names_update_command(repo_with_stale_graph): ...
```

The repair command must quote the absolute repository path with `shlex.join` and must never execute during context resolution.

- [ ] **Step 5: Keep the portable module byte-equivalent**

Copy `tools/jeviphy_autorun.py` to `skills/jeviphy/scripts/tools/jeviphy_autorun.py` and extend `test_portable_skill_code_matches_project_code` to compare both files byte for byte.

- [ ] **Step 6: Run focused tests and commit**

```bash
mac-gate uv run --frozen pytest tests/test_jeviphy_autorun.py tests/test_jeviphy_skill.py -q
mac-gate uv run --frozen ruff check tools/jeviphy_autorun.py tests/test_jeviphy_autorun.py
```

Expected: all tests and lint pass.

```bash
git add tools/jeviphy_autorun.py skills/jeviphy/scripts/tools/jeviphy_autorun.py tests/test_jeviphy_autorun.py tests/test_jeviphy_skill.py
git commit -m "feat: resolve Jeviphy context automatically"
```

### Task 2: Select a Graph Question Without Asking the User

**Files:**
- Modify: `tools/jeviphy_autorun.py`
- Modify: `skills/jeviphy/scripts/tools/jeviphy_autorun.py`
- Modify: `tests/test_jeviphy_autorun.py`

**Interfaces:**
- Consumes: `graph: nx.Graph`, optional `question: str | None`.
- Produces: `select_question(graph: nx.Graph, question: str | None) -> str`.

- [ ] **Step 1: Write failing precedence and selection tests**

```python
def test_explicit_question_wins(sample_graph):
    assert select_question(sample_graph, " What calls createClient? ") == (
        "What calls createClient?"
    )


def test_first_high_confidence_suggestion_wins(monkeypatch, sample_graph):
    monkeypatch.setattr(autorun, "suggest_questions", lambda *args, **kwargs: [
        {"question": "low", "low_confidence": True},
        {"question": "selected", "low_confidence": False},
        {"question": "later", "low_confidence": False},
    ])
    assert select_question(sample_graph, None) == "selected"
```

Also test whitespace-only explicit input, low-confidence-only suggestions, a `no_signal` record, and an empty graph.

- [ ] **Step 2: Run the focused tests and confirm failure**

Run `mac-gate uv run --frozen pytest tests/test_jeviphy_autorun.py -q`.

Expected: FAIL because `select_question` is missing.

- [ ] **Step 3: Implement deterministic selection with existing Graphify APIs**

```python
def select_question(graph: nx.Graph, question: str | None) -> str:
    if question is not None and question.strip():
        return question.strip()
    communities = _communities_from_graph(graph)
    labels = load_community_labels(graph_path.parent, communities)
    suggestions = suggest_questions(graph, communities, labels, top_n=5)
    usable = [item for item in suggestions if item.get("question")]
    preferred = [item for item in usable if not item.get("low_confidence")]
    selected = (preferred or usable)
    if not selected:
        raise ContextError("graph has no question signal; run graphify update .")
    return selected[0]["question"]
```

Use Graphify's existing `_communities_from_graph` helper. Load `.graphify_labels.json` with integer keys when valid and fall back to `Community {id}` labels, matching Graphify server behavior. Do not add a second ranking algorithm.

- [ ] **Step 4: Verify determinism**

Run the same graph 20 times with `PYTHONHASHSEED` values `0` through `19` in subprocesses. Assert the selected question is identical in every run.

- [ ] **Step 5: Synchronize the portable copy, test, and commit**

```bash
cp tools/jeviphy_autorun.py skills/jeviphy/scripts/tools/jeviphy_autorun.py
mac-gate uv run --frozen pytest tests/test_jeviphy_autorun.py tests/test_jeviphy_skill.py -q
mac-gate uv run --frozen ruff check tools/jeviphy_autorun.py tests/test_jeviphy_autorun.py
git add tools/jeviphy_autorun.py skills/jeviphy/scripts/tools/jeviphy_autorun.py tests/test_jeviphy_autorun.py
git commit -m "feat: select Jeviphy questions automatically"
```

### Task 3: Add the Bare Auto Command and Optional Corpus

**Files:**
- Modify: `skills/jeviphy/scripts/run.py`
- Modify: `tools/jeviphy_autorun.py`
- Modify: `skills/jeviphy/scripts/tools/jeviphy_autorun.py`
- Modify: `tests/test_jeviphy_skill.py`
- Modify: `tests/test_jeviphy_autorun.py`

**Interfaces:**
- Consumes: `auto(argv: Sequence[str], cwd: Path) -> int`, optional `--question`, `--repo`, `--graph`, `--corpus`, `--case-id`, `--project`, and `--json`.
- Produces: `AutoResult(schema_version, mode, repo, graph, question, live_enrichment, answer)` and process exit status.

- [ ] **Step 1: Write a failing end-to-end bare invocation test**

```python
def test_bare_runner_queries_current_repo_without_network(repo_with_graph, monkeypatch):
    repo, _ = repo_with_graph
    monkeypatch.chdir(repo / "src")
    monkeypatch.setenv("JEV_MEMORY_PILOT_API_KEY", "must-not-be-read")
    with patch("tools.jeviphy_autorun.query_unscoped_graphify", return_value="answer\n") as query:
        assert run.main([]) == 0
    query.assert_called_once()
```

Patch `os.environ.get` narrowly or pass an environment mapping so the test proves the default path never requests `JEV_MEMORY_PILOT_API_KEY`.

- [ ] **Step 2: Add failing JSON-envelope and corpus-routing tests**

```python
def test_auto_json_has_stable_envelope(repo_with_graph, capsys): ...
def test_missing_corpus_uses_graph_only(repo_with_graph): ...
def test_valid_corpus_delegates_to_existing_query_main(repo_with_graph, private_corpus): ...
def test_invalid_corpus_falls_back_without_prompt(repo_with_graph, invalid_corpus): ...
```

For invalid optional corpus input, emit one bounded stderr status and use graph-only fallback. Keep explicit evaluation commands strict.

- [ ] **Step 3: Route no arguments and `auto` through one implementation**

```python
def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments or arguments[0] == "auto":
        return auto(arguments[1:] if arguments else [], Path.cwd())
    if arguments[0] == "doctor":
        return doctor(arguments[1:])
    if arguments[0] == "query":
        return query_command(arguments[1:])
    if arguments[0] == "benchmark":
        return benchmark(arguments[1:])
    return auto(arguments, Path.cwd())
```

`query QUESTION` is the human-facing query form. Preserve the legacy pilot argument set behind `query --corpus ... --case-id ...` by detecting those flags and delegating to `query_main`.

- [ ] **Step 4: Implement the result envelope**

```python
@dataclass(frozen=True)
class AutoResult:
    schema_version: int
    mode: Literal["graph_only", "memory_offline", "memory_live"]
    repo: str
    graph: str
    question: str
    live_enrichment: Literal["not_requested", "applied", "skipped"]
    answer: str
```

Human output prints `Question: ...`, then the unchanged answer. JSON uses `json.dumps(asdict(result), sort_keys=True)`. Never include observation summaries or provider bodies.

- [ ] **Step 5: Make doctor defaults match auto discovery**

Change `doctor` so `--repo` and `--graph` are optional and default through `resolve_context`. Add corpus checks only when `--corpus` is supplied. Keep non-zero exit status for missing/stale graph or an explicitly supplied invalid corpus.

- [ ] **Step 6: Run focused tests and commit**

```bash
mac-gate uv run --frozen pytest tests/test_jeviphy_autorun.py tests/test_jeviphy_skill.py tests/test_jev_memory_pilot.py -q
mac-gate uv run --frozen ruff check tools/jeviphy_autorun.py skills/jeviphy/scripts/run.py tests/test_jeviphy_autorun.py tests/test_jeviphy_skill.py
git add tools/jeviphy_autorun.py skills/jeviphy/scripts tests/test_jeviphy_autorun.py tests/test_jeviphy_skill.py
git commit -m "feat: add zero-configuration Jeviphy command"
```

### Task 4: Finish Gracefully When Live Jev Is Unavailable

**Files:**
- Modify: `tools/jev_memory_pilot_api.py`
- Modify: `skills/jeviphy/scripts/tools/jev_memory_pilot_api.py`
- Modify: `tools/jev_memory_pilot.py`
- Modify: `skills/jeviphy/scripts/tools/jev_memory_pilot.py`
- Modify: `tests/test_jev_memory_pilot.py`
- Modify: `tests/test_jeviphy_autorun.py`

**Interfaces:**
- Consumes: existing `decide_once(...)` and live flags.
- Produces: `DecisionOutcome(answers, model_id, cost, status)` where status is `not_requested`, `applied`, or `skipped`.

- [ ] **Step 1: Pin every unavailable-provider outcome**

```python
@pytest.mark.parametrize("failure", [
    "missing_key", "http_401", "http_429", "redirect", "timeout", "malformed", "missing_cost",
])
def test_live_failure_returns_offline_answer_without_prompt(failure, live_case, capsys): ...
```

Mock `call_jev` for each outcome. Assert one call at most, exit zero, exact offline answer, no provider body, no key value, and exactly one `live_enrichment=skipped` status.

- [ ] **Step 2: Introduce the typed decision outcome**

```python
@dataclass(frozen=True)
class DecisionOutcome:
    answers: dict[tuple[str, str], dict]
    model_id: str | None
    cost: float | None
    status: Literal["not_requested", "applied", "skipped"]
```

Return `skipped` for every caught uncertain outcome. Do not widen the caught exception set beyond provider/network/validation failures. Programming errors must still fail tests.

- [ ] **Step 3: Thread status into `AutoResult`**

The auto command maps `DecisionOutcome.status` directly into `live_enrichment`. Human output emits no question or remediation request. Stderr contains only the bounded status.

- [ ] **Step 4: Preserve the no-retry contract**

Assert the provider mock call count is exactly one for failures after a request and zero for a missing key. Keep the existing paid-use flag and request-cap validation before any network call.

- [ ] **Step 5: Synchronize portable modules, test, and commit**

```bash
cp tools/jev_memory_pilot.py skills/jeviphy/scripts/tools/jev_memory_pilot.py
cp tools/jev_memory_pilot_api.py skills/jeviphy/scripts/tools/jev_memory_pilot_api.py
cp tools/jeviphy_autorun.py skills/jeviphy/scripts/tools/jeviphy_autorun.py
mac-gate uv run --frozen pytest tests/test_jev_memory_pilot.py tests/test_jeviphy_autorun.py tests/test_jeviphy_skill.py -q
mac-gate uv run --frozen ruff check tools/jev_memory_pilot.py tools/jev_memory_pilot_api.py tools/jeviphy_autorun.py
git add tools skills/jeviphy/scripts tests/test_jev_memory_pilot.py tests/test_jeviphy_autorun.py tests/test_jeviphy_skill.py
git commit -m "fix: preserve Jeviphy answers when live enrichment fails"
```

### Task 5: Make Claude Code and Codex Use the Executable Contract

**Files:**
- Modify: `skills/jeviphy/SKILL.md`
- Modify: `scripts/install_jeviphy_skill.py`
- Modify: `tests/test_jeviphy_install.py`
- Modify: `tests/test_jeviphy_skill.py`

**Interfaces:**
- Consumes: installed skill directory and portable `scripts/run.py`.
- Produces: identical bare invocation for Claude Code and Codex.

- [ ] **Step 1: Write skill-contract tests before editing prose**

```python
def test_skill_bare_path_delegates_to_runner():
    text = skill_text()
    assert "python scripts/run.py auto" in text
    assert "Do not reproduce auto discovery in the host prompt" in text


def test_installed_hosts_contain_auto_module(tmp_path):
    assert run_installer(tmp_path, "install", "both").returncode == 0
    for host in (".claude", ".codex"):
        assert (tmp_path / host / "skills/jeviphy/scripts/tools/jeviphy_autorun.py").is_file()
```

- [ ] **Step 2: Reduce the skill's default flow to one executable call**

The default section must instruct the host to run the portable auto command from the current directory, then verify cited source files before reporting. Keep memory-gateway retrieval as an optional host action that creates a private corpus and reruns auto with `--corpus`; never make it a prerequisite.

- [ ] **Step 3: Test installation and upgrade behavior**

Cover clean installs, repeated receipt-owned installs, refusal to overwrite an unowned directory, and uninstall preservation. Verify both hosts receive byte-identical Jeviphy files.

- [ ] **Step 4: Run host tests and commit**

```bash
mac-gate uv run --frozen pytest tests/test_jeviphy_install.py tests/test_jeviphy_skill.py tests/test_jeviphy_autorun.py -q
mac-gate uv run --frozen ruff check scripts/install_jeviphy_skill.py tests/test_jeviphy_install.py tests/test_jeviphy_skill.py
git add skills/jeviphy scripts/install_jeviphy_skill.py tests/test_jeviphy_install.py tests/test_jeviphy_skill.py
git commit -m "feat: unify bare Jeviphy across Claude and Codex"
```

### Task 6: Prove Zero-Configuration Usability Against Graphify

**Files:**
- Create: `tools/jeviphy_zero_config_eval.py`
- Create: `tests/test_jeviphy_zero_config_eval.py`
- Create: `benchmarks/jeviphy-zero-config/manifest.json`
- Create: `benchmarks/jeviphy-zero-config/manifest.schema.json`
- Create: `docs/jeviphy-zero-configuration-evaluation.md`

**Interfaces:**
- Consumes: 30 frozen cases from at least 6 public repositories, exact commits, prebuilt graph hashes, and direct Graphify/Jeviphy commands.
- Produces: append-only JSONL records and `score(records: Sequence[RunRecord]) -> ZeroConfigScore`.

- [ ] **Step 1: Write manifest and scorer tests**

```python
def test_manifest_requires_30_cases_and_6_repositories(valid_manifest): ...
def test_score_requires_every_paired_case(records): ...
def test_score_fails_when_any_user_followup_occurs(records): ...
def test_score_checks_exact_fallback_after_header(records): ...
def test_score_enforces_median_and_p95_overhead(records): ...
```

The scorer returns `pass`, `fail`, or `insufficient_evidence`; missing pairs never disappear from the denominator.

- [ ] **Step 2: Freeze the usability manifest before running**

Each case records repository URL, immutable commit, graph SHA-256, explicit or auto-question mode, expected repair state, Graphify command, Jeviphy command, timeout, and whether memory/live enrichment is available. Include ready graph, nested cwd, explicit question, no corpus, stale graph, missing graph, outside Git, malformed corpus, missing key, and expired key cases.

- [ ] **Step 3: Implement paired execution without shell interpolation**

Use argument arrays with `subprocess.run`, a clean temporary home, network disabled for default cases, alternating arm order, one warm-up, and five measured passes for timing cases. Record stdout/stderr hashes, exit status, elapsed time, prompt/follow-up count, selected question, and input pins.

- [ ] **Step 4: Generate the mechanical scorecard**

Pass only when all spec quality gates pass. Write raw records outside Git first, redact and hash them, then commit only the aggregate report and artifact hashes. The report must say `not demonstrated` for any missing gate.

- [ ] **Step 5: Run local validation**

```bash
mac-gate uv run --frozen pytest tests/test_jeviphy_zero_config_eval.py tests/test_jeviphy_autorun.py tests/test_jeviphy_skill.py -q
mac-gate uv run --frozen ruff check tools/jeviphy_zero_config_eval.py tests/test_jeviphy_zero_config_eval.py
```

Expected: tests and lint pass. Do not run the 30-case benchmark inside the test suite.

- [ ] **Step 6: Run the frozen 30-case comparison and publish the bounded result**

Run the evaluator serially with its declared cost and time ceiling. Keep the existing large benchmark alive and separate. Publish completion, follow-up count, exact-fallback rate, median/p95 overhead, and each failure class. Do not claim parity unless every gate passes.

- [ ] **Step 7: Commit the harness and public report**

```bash
git add tools/jeviphy_zero_config_eval.py tests/test_jeviphy_zero_config_eval.py benchmarks/jeviphy-zero-config docs/jeviphy-zero-configuration-evaluation.md
git commit -m "test: prove Jeviphy zero-configuration parity"
```

### Task 7: Final Review, Installation, and Integration

**Files:**
- Review: every file changed in Tasks 1 through 6.
- Update only if evidence requires it: `README.md`, `docs/jeviphy/index.html`.

**Interfaces:**
- Consumes: completed implementation and frozen scorecard.
- Produces: one integrated release candidate with installed Claude Code/Codex skills.

- [ ] **Step 1: Review the complete diff against the SDD spec**

Verify every `ZC1` through `ZC8` requirement has a test and implementation. Search for duplicate repository discovery, question selection, provider retry, and credential-remediation prose; remove duplicates rather than adding wrappers.

- [ ] **Step 2: Run the canonical local gate**

This Python repository has no `npm run preflight:ci`. Run its applicable CI gates through the shared Mac queue:

```bash
mac-gate uv sync --all-extras --frozen
mac-gate uv run --frozen pytest tests/ -q --tb=short
mac-gate uv run --frozen ruff check tools scripts tests
```

Do not run a local web build. This repository has no applicable Vercel Preview deployment.

- [ ] **Step 3: Push one branch and open one PR to `jeviphy`**

Include the zero-configuration scorecard, exact commit, local gate output, and the statement permitted by the scorecard. Do not ask Luis to review or merge.

- [ ] **Step 4: Require remote checks on the latest SHA**

Wait for CI, CodeQL, security scan, skill generation, Pi guard, PR standards, and every supported Python version. Fix deterministic failures and rerun the same gates; do not bypass checks.

- [ ] **Step 5: Integrate and verify post-merge state**

Merge only when required checks are green. Wait for `jeviphy` branch CI and CodeQL to finish successfully on the merge commit.

- [ ] **Step 6: Install the integrated skill for both hosts**

Run the receipt-based installer from the integrated commit for Claude Code and Codex. Verify both installed copies contain `jeviphy_autorun.py` and produce the same bare-command output in isolated temporary homes.

- [ ] **Step 7: Preserve benchmark separation**

Record the existing large benchmark's original candidate SHA and this release candidate SHA. Never combine their records. Schedule a fresh paired product run only after the zero-configuration usability gate passes.

## Self-Review Result

- **Spec coverage:** ZC1–ZC8 map to Tasks 1–6; integration and installed-state proof are in Task 7.
- **Placeholder scan:** no deferred implementation placeholders remain.
- **Type consistency:** `InvocationContext`, `AutoResult`, `DecisionOutcome`, and `ZeroConfigScore` have one definition and named consumers.
- **Review focus:** nested worktrees, metadata migration, absent question signal, provider failures, and exact output compatibility each have an owning test.
- **Scope:** the plan adds one orchestration module and one evaluation harness; it reuses existing Graphify and Jeviphy logic and adds no runtime dependency.

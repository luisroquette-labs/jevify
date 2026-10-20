# Jeviphy Zero-Configuration Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Use subagents only when the active instructions explicitly authorize delegation. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make bare `/jeviphy` complete a useful, source-verified query with no repository, question, corpus, mode, or credential prompt.

**Architecture:** Add one small orchestration module at the portable runner boundary. It resolves the current Git repository, performs one bounded offline graph repair when required, selects a Graphify-generated question when needed, then routes to the existing exact Graphify fallback or existing memory-aware runner; memory and live Jev stay optional. Keep discovery and fallback in Python so Claude Code and Codex consume the same behavior instead of relying on prompt interpretation.

**Tech Stack:** Python 3.10+, standard library, NetworkX, existing Graphify `suggest_questions` and query APIs, existing Jeviphy provenance/runner modules, pytest, Git, `uv`.

**Spec:** `.specs/tasks/draft/jeviphy-zero-configuration-parity.feature.md`

## Global Constraints

- Preserve Graphify as the unchanged extraction and query engine.
- Bare invocation defaults to the current Git worktree and `<repo>/graphify-out/graph.json`.
- Default execution is offline and reads no provider key.
- Corpus and live Jev are optional; their absence or failure cannot block the Graphify answer.
- Do not add a hosted provider, OAuth flow, vector database, runtime dependency, or second application stack.
- Do not change or combine the currently running frozen benchmark; evaluate this candidate separately.
- Keep queries read-only. Automatic repair may update only `graphify-out/` through Graphify; keep private corpora outside Git with existing `0700`/`0600` permissions.
- Preserve explicit `doctor`, `query`, and `benchmark` compatibility.
- Use one task branch and one PR to `jeviphy`; run applicable local gates only through `mac-gate`.

## Review Focus

1. **Nested working directory and repair:** resolve the containing Git root, never use a nested `graphify-out`, and perform at most one offline repair; Task 1 pins this behavior.
2. **Graph metadata boundary:** require persisted `built_at_commit` and verify Graphify normalizes it to in-memory `_built_at_commit`; Task 1 covers missing, malformed, and stale values.
3. **No useful question:** fail with one bounded diagnostic without asking the user; Task 2 covers empty and low-confidence-only graphs.
4. **Provider failure after approval:** make one attempt, disclose only `live_enrichment=skipped`, and return exit zero with offline output; Task 4 covers HTTP, timeout, redirect, malformed response, and missing key.
5. **Output compatibility:** keep the Graphify answer byte-identical outside the optional audit envelope; Tasks 3 and 6 compare exact bytes.

---

## File and Interface Map

| Responsibility | File |
| --- | --- |
| SDD behavior contract | `.specs/tasks/draft/jeviphy-zero-configuration-parity.feature.md` |
| Auto context, bounded repair, question, and result envelope | `tools/jeviphy_autorun.py` |
| Portable copy of orchestration | `skills/jeviphy/scripts/tools/jeviphy_autorun.py` |
| CLI routing and compatible flags | `skills/jeviphy/scripts/run.py` |
| Structured pilot core and exact Graphify fallback | `tools/jev_memory_pilot.py` |
| Bounded Jev request adapter | `tools/jev_memory_pilot_api.py` |
| Installed host instructions | `skills/jeviphy/SKILL.md` |
| Auto-path unit tests | `tests/test_jeviphy_autorun.py` |
| Portable CLI and doctor tests | `tests/test_jeviphy_skill.py` |
| Clean-home host tests | `tests/test_jeviphy_install.py` |
| Frozen usability harness | `tools/jeviphy_zero_config_eval.py` |
| Usability harness tests | `tests/test_jeviphy_zero_config_eval.py` |
| Public result report | `docs/jeviphy-zero-configuration-evaluation.md` |

### Task 1: Resolve and Repair the Graph Without Parameters

**Files:**
- Create: `tools/jeviphy_autorun.py`
- Create: `tests/test_jeviphy_autorun.py`
- Create: `skills/jeviphy/scripts/tools/jeviphy_autorun.py`
- Modify: `tests/test_jeviphy_skill.py`

**Interfaces:**
- Consumes: `cwd: Path`, optional explicit repository and graph paths.
- Produces: `InvocationContext(repo: Path, graph: Path, head: str)`, pure `inspect_context(...) -> ContextState`, and bounded `ensure_context(...) -> InvocationContext`.

- [ ] **Step 1: Write failing repository-discovery tests**

```python
def test_ensure_context_uses_containing_git_root(repo_with_graph, monkeypatch):
    repo, graph = repo_with_graph
    nested = repo / "src" / "nested"
    nested.mkdir(parents=True)
    context = ensure_context(nested)
    assert context.repo == repo.resolve()
    assert context.graph == graph.resolve()


def test_ensure_context_rejects_outside_git(tmp_path):
    with pytest.raises(ContextError, match="not inside a Git worktree"):
        ensure_context(tmp_path)
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

`inspect_context` uses the explicit repository when supplied, otherwise `git_root(cwd)`. Its default graph is `repo / "graphify-out/graph.json"`. It reads `HEAD`, loads the graph only through `_read_graph`, and returns a specific missing or stale diagnostic. Read the raw JSON only to validate the persisted top-level `built_at_commit`, then load through `_read_graph` and compare its normalized `_built_at_commit` with `HEAD`. Missing, blank, non-string, or mismatched values are stale.

- [ ] **Step 4: Add graph-state tests**

Test these exact states:

```python
def test_persisted_commit_is_normalized_and_accepted(repo_with_graph): ...

@pytest.mark.parametrize("value", [None, "", 42])
def test_missing_or_malformed_persisted_commit_is_stale(repo_with_graph, value): ...

def test_stale_graph_runs_one_offline_update_then_revalidates(repo_with_stale_graph): ...

def test_corrupt_graph_runs_one_code_only_extract_then_revalidates(repo_with_corrupt_graph): ...

def test_missing_graph_runs_one_code_only_extract_then_revalidates(repo_without_graph): ...

def test_failed_repair_does_not_retry(repo_without_graph): ...
```

Keep inspection pure. `ensure_context` may execute one argument-array child process with cwd set to the repository:

- missing: `[sys.executable, "-m", "graphify", "extract", ".", "--code-only"]`;
- corrupt: `[sys.executable, "-m", "graphify", "extract", ".", "--force", "--code-only"]`;
- stale: `[sys.executable, "-m", "graphify", "update", "."]`.

Copy the current environment, set `GRAPHIFY_NO_AUTO_REFRESH=1` and `PYTHONHASHSEED=0`, then remove `GEMINI_API_KEY`, `GOOGLE_API_KEY`, `OPENAI_API_KEY`, `AZURE_OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY`, `JEV_MEMORY_PILOT_API_KEY`, `DEEPSEEK_API_KEY`, `MOONSHOT_API_KEY`, `OLLAMA_API_KEY`, `GRAPHIFY_API_KEY`, and AWS credential variables. Test the removal with sentinel values. Reinspect after the child exits. Never retry, use a shell, or accept an invalid repaired graph.

- [ ] **Step 5: Keep the portable module byte-equivalent**

Copy `tools/jeviphy_autorun.py` to `skills/jeviphy/scripts/tools/jeviphy_autorun.py`. Split the existing combined assertion into two tests:

- `test_portable_skill_code_matches_project_code` compares current project and portable bytes, including `jeviphy_autorun.py` immediately;
- `test_pinned_commit_matches_portable_core` compares only files that exist in the currently pinned commit.

Do not require the old pin to contain the newly created module.

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
- Produces: `select_question(graph: nx.Graph, graph_path: Path, question: str | None) -> str`.

- [ ] **Step 1: Write failing precedence and selection tests**

```python
def test_explicit_question_wins(sample_graph):
    assert select_question(sample_graph, graph_path, " What calls createClient? ") == (
        "What calls createClient?"
    )


def test_first_high_confidence_suggestion_wins(monkeypatch, sample_graph):
    monkeypatch.setattr(autorun, "suggest_questions", lambda *args, **kwargs: [
        {"question": "low", "low_confidence": True},
        {"question": "selected", "low_confidence": False},
        {"question": "later", "low_confidence": False},
    ])
    assert select_question(sample_graph, graph_path, None) == "selected"
```

Also test whitespace-only explicit input, low-confidence-only suggestions, a `no_signal` record, and an empty graph.

- [ ] **Step 2: Run the focused tests and confirm failure**

Run `mac-gate uv run --frozen pytest tests/test_jeviphy_autorun.py -q`.

Expected: FAIL because `select_question` is missing.

- [ ] **Step 3: Implement deterministic selection with existing Graphify APIs**

```python
def select_question(graph: nx.Graph, graph_path: Path, question: str | None) -> str:
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

### Task 3: Add One Structured Query Core and the Bare Auto Command

**Files:**
- Modify: `tools/jev_memory_pilot.py`
- Modify: `tools/jev_memory_pilot_api.py`
- Modify: `skills/jeviphy/scripts/tools/jev_memory_pilot.py`
- Modify: `skills/jeviphy/scripts/tools/jev_memory_pilot_api.py`
- Modify: `tools/jeviphy_autorun.py`
- Modify: `skills/jeviphy/scripts/tools/jeviphy_autorun.py`
- Modify: `skills/jeviphy/scripts/run.py`
- Modify: `tests/test_jev_memory_pilot.py`
- Modify: `tests/test_jeviphy_autorun.py`
- Modify: `tests/test_jeviphy_skill.py`

**Interfaces:**
- `run_pilot(config: PilotConfig) -> PilotOutcome` returns answer, model, cost, whether trusted memory changed the traversal seeds, and normalized live-enrichment status; the legacy `main()` only parses, calls it, and prints.
- `auto(argv: Sequence[str], cwd: Path) -> int` accepts optional `--question`, `--repo`, `--graph`, `--corpus`, `--json`, and the existing bounded live flags.
- `AutoResult(schema_version, mode, repo, graph, question, live_enrichment, answer)` is the only auto JSON envelope.

- [ ] **Step 1: Pin the current legacy behavior before refactoring**

Add characterization tests for graph-only output, valid offline decisions, dry-run, missing key, rejected key, and paid success. Assert stdout, stderr category, sidecar creation, request count, and exit status. These tests must pass before changing the runner.

- [ ] **Step 2: Extract a structured core without changing legacy output**

Move the body after argument parsing into `run_pilot(PilotConfig)`. Return:

```python
@dataclass(frozen=True)
class PilotOutcome:
    answer: str
    model_id: str | None
    actual_cost: float | None
    memory_applied: bool
    live_enrichment: Literal["not_requested", "applied", "skipped"]
```

Make `decide_once` return data without printing. `run_pilot` maps `live=False` to `not_requested`, a validated live response to `applied`, and every bounded live fallback to `skipped`. `main()` preserves the existing strict required arguments and byte-compatible stdout/stderr by formatting the outcome at the CLI boundary. Do not catch programming errors or weaken corpus validation.

- [ ] **Step 3: Write failing auto-routing tests**

Cover:

```python
def test_bare_runner_uses_current_repo_without_reading_provider_key(...): ...
def test_explicit_auto_question_wins(...): ...
def test_single_case_corpus_uses_trusted_fast_source_seed(...): ...
def test_corpus_without_eligible_source_stays_graph_only(...): ...
def test_multiple_case_corpus_falls_back_once_without_prompt(...): ...
def test_explicit_question_mismatching_corpus_falls_back_to_graph(...): ...
def test_auto_json_has_stable_envelope(...): ...
def test_query_subcommand_keeps_legacy_parser(...): ...
```

Question precedence is: explicit `--question`, one valid corpus case, then Graphify suggestion. A corpus participates only when it has exactly one case, one consistent project, and a question equal to the selected question; any ambiguity or mismatch emits one status and uses graph-only mode. Offline corpus execution reuses `candidate_mode="fast-source"`; it reports memory use only when trusted cited nodes actually seed Graphify.

- [ ] **Step 4: Implement the auto result and default path**

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

Bare execution never reads `JEV_MEMORY_PILOT_API_KEY`. Live mode reads it only after `--live --approved-paid-use --max-requests 1`, successful corpus validation, and construction of at least one eligible pair. A live request with no eligible pair returns `skipped` with zero credential access and zero provider calls. Set `mode=memory_live` only for `live_enrichment=applied`; otherwise set `memory_offline` only when `PilotOutcome.memory_applied` is true, and `graph_only` for exact fallback. Copy `PilotOutcome.live_enrichment` into the auto envelope; every bounded unavailable outcome preserves the offline answer. Only the outer CLI prints status, so each failure produces exactly one line.

Human output is `Question: ...\n` followed by the unchanged answer. JSON uses `json.dumps(asdict(result), sort_keys=True)` and contains no corpus text, provider body, or secret.

- [ ] **Step 5: Keep CLI grammar unambiguous**

```python
def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments or arguments[0] == "auto":
        return auto(arguments[1:] if arguments else [], Path.cwd())
    if arguments[0] == "doctor":
        return doctor(arguments[1:])
    if arguments[0] == "query":
        return query_main(arguments[1:])
    if arguments[0] == "benchmark":
        return benchmark(arguments[1:])
    raise SystemExit("unknown command; use auto --question QUESTION")
```

`query` remains the strict legacy pilot command. Explicit zero-configuration questions use `auto --question QUESTION`; unknown commands and misspelled options fail with one usage diagnostic. Never detect legacy mode by searching for flags or reinterpret an option as question text.

- [ ] **Step 6: Make doctor use the same resolver**

Make `--repo` and `--graph` optional and inspect them through `inspect_context`. Run corpus checks only when `--corpus` is present. Doctor remains read-only: missing/stale/corrupt graph and an explicitly supplied invalid corpus are non-zero. Only `auto` invokes `ensure_context` repair.

- [ ] **Step 7: Synchronize portable files and create the core commit**

Copy the four project modules into `skills/jeviphy/scripts/tools/` and update current project-to-portable byte-parity tests. Keep the pinned-commit test on the old file set until the new immutable core commit exists. Run the focused suite while excluding only `test_pinned_commit_matches_portable_core`, whose old immutable pin is expected to fail until the next commit:

```bash
mac-gate uv run --frozen pytest \
  tests/test_jev_memory_pilot.py tests/test_jeviphy_autorun.py tests/test_jeviphy_skill.py \
  -q -k 'not test_pinned_commit_matches_portable_core'
git add tools skills/jeviphy/scripts tests/test_jev_memory_pilot.py \
  tests/test_jeviphy_autorun.py tests/test_jeviphy_skill.py
git commit -m "feat: add zero-configuration Jeviphy core"
CORE_SHA=$(git rev-parse HEAD)
```

Update the PEP 723 `graphifyy @ git+...@<sha>` pin in `skills/jeviphy/scripts/run.py` to the printed `CORE_SHA`. The pin must reference the preceding core commit because a commit cannot contain its own SHA.

- [ ] **Step 8: Validate the pin and commit the pin update**

```bash
mac-gate uv run --frozen pytest tests/test_jev_memory_pilot.py tests/test_jeviphy_autorun.py tests/test_jeviphy_skill.py -q
mac-gate uv run --frozen ruff check tools/jev_memory_pilot.py tools/jev_memory_pilot_api.py tools/jeviphy_autorun.py skills/jeviphy/scripts/run.py tests/test_jeviphy_autorun.py
```

Expand `test_pinned_commit_matches_portable_core` to all four modules and assert their project and portable bytes equal the files at `CORE_SHA`, then commit the pin-only update. Do not modify those modules after this point without repeating the core-commit/pin sequence.

### Task 4: Preserve Graceful Live Fallback Without New Provider Machinery

**Files:**
- Modify only if a regression test fails: `tools/jev_memory_pilot_api.py`
- Modify only if the project file changes: `skills/jeviphy/scripts/tools/jev_memory_pilot_api.py`
- Modify: `tests/test_jev_memory_pilot_api.py`
- Modify: `tests/test_jeviphy_autorun.py`

- [ ] **Step 1: Reuse the existing bounded provider behavior**

The API blocks redirects, performs one request, rejects malformed/missing-cost responses, and returns baseline inputs for missing or rejected keys. Its status-free return is normalized by `run_pilot`; add regression coverage without introducing another provider abstraction.

- [ ] **Step 2: Pin auto-level status mapping**

For missing key, HTTP 401/429, redirect, timeout, malformed JSON, oversized response, and missing cost, assert:

- zero or one provider call as appropriate;
- exit zero from `auto`;
- the exact offline answer;
- exactly one `live_enrichment=skipped` status;
- no provider response body, key, or credential-remediation request.

For a valid response, assert `memory_live`, `live_enrichment=applied`, and the actual cost line. Default, dry-run, invalid-corpus, and empty-pair paths must make zero provider calls; invalid-corpus and empty-pair paths must also make zero key reads.

- [ ] **Step 3: Run the focused gate**

```bash
mac-gate uv run --frozen pytest tests/test_jev_memory_pilot_api.py tests/test_jev_memory_pilot.py tests/test_jeviphy_autorun.py -q
```

If production modules change, repeat Task 3 Steps 7–8 so the portable dependency pin remains truthful.

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
    assert "uv run" in text
    assert "scripts/run.py auto" in text
    assert "Do not reproduce auto discovery in the host prompt" in text


def test_installed_hosts_contain_auto_module(tmp_path):
    assert run_installer(tmp_path, "install", "both").returncode == 0
    for host in (".claude", ".codex"):
        assert (tmp_path / host / "skills/jeviphy/scripts/tools/jeviphy_autorun.py").is_file()
```

- [ ] **Step 2: Reduce the skill's default flow to one executable call**

The default section must resolve the installed skill directory, then run `uv run <installed-skill-dir>/scripts/run.py auto` while preserving the target repository as the process cwd. A relative `python scripts/run.py` command is invalid because cwd belongs to the target repository and a clean host may not have Graphify dependencies installed. After the command, verify cited source files before reporting. Keep memory-gateway retrieval as an optional host action that creates a private corpus and reruns auto with `--corpus`; never make it a prerequisite.

- [ ] **Step 3: Test installation and upgrade behavior**

Cover clean installs, repeated receipt-owned installs, refusal to overwrite an unowned directory, and uninstall preservation. Verify both hosts receive byte-identical Jeviphy files. From a nested directory in a temporary Git repository, execute each installed runner with `uv run <absolute-script-path> auto --question ...`; assert it keeps the target cwd and completes without importing from the Jeviphy checkout.

- [ ] **Step 4: Run host tests and commit**

```bash
mac-gate uv run --frozen pytest tests/test_jeviphy_install.py tests/test_jeviphy_skill.py tests/test_jeviphy_autorun.py -q
mac-gate uv run --frozen ruff check scripts/install_jeviphy_skill.py tests/test_jeviphy_install.py tests/test_jeviphy_skill.py
git add skills/jeviphy scripts/install_jeviphy_skill.py tests/test_jeviphy_install.py tests/test_jeviphy_skill.py
git commit -m "feat: unify bare Jeviphy across Claude and Codex"
```

### Task 6: Prove Runner Usability Against Direct Graphify

**Files:**
- Create: `tools/jeviphy_zero_config_eval.py`
- Create: `tests/test_jeviphy_zero_config_eval.py`
- Create: `benchmarks/jeviphy-zero-config/manifest.json`
- Create: `benchmarks/jeviphy-zero-config/manifest.schema.json`
- Create: `docs/jeviphy-zero-configuration-evaluation.md`

**Interfaces:**
- Consumes: 30 frozen runner cases from at least 6 public repositories, immutable commits, graph hashes, and explicit expected outcomes.
- Produces: private append-only JSONL plus `score(records) -> ZeroConfigScore` with `pass`, `fail`, or `insufficient_evidence`.

- [ ] **Step 1: Write manifest and scorer tests**

Test the 30-case/6-repository minimum, complete paired denominators, exact fallback, diagnostics, median/p95 overhead, and `interaction_required == 0`. Missing, timed-out, or malformed records produce `insufficient_evidence`, never disappear.

- [ ] **Step 2: Freeze cases and denominators before execution**

Include ready graph, nested cwd, explicit question, auto question, no corpus, source-seeded single-case corpus, no-eligible-source corpus, ambiguous corpus, successful stale/missing/corrupt repairs, forced repair failure, outside Git, missing key, and expired key. Mark which cases enter exact-output and timing denominators; error-path cases do not enter latency ratios.

- [ ] **Step 3: Compare the same question in both arms**

For auto-question cases, select the question once before the timed region, persist its hash, then run direct Graphify and Jeviphy with that same question. Measure selection latency separately. Alternate arm order, perform one warm-up, and run five measured pairs for timing cases.

- [ ] **Step 4: Prove the runner does not request interaction or network by default**

Run every case with stdin connected to `DEVNULL`. Classify a prompt, stdin read, timeout waiting for input, or credential instruction as `interaction_required`. For default and repair cases, inject a temporary `sitecustomize.py` that rejects IPv4/IPv6 socket connections; both arms use the same environment. Assert repair child environments contain no provider key.

Use argument arrays with `subprocess.run`; never interpolate shell strings. Record exit code, elapsed time, stdout/stderr hashes, selected-question hash, interaction status, arm order, and immutable input pins.

- [ ] **Step 5: Generate the mechanical scorecard**

Pass only when every SDD quality gate passes. Write raw records under a mode-0700 directory outside Git, commit only aggregate counts, timings, hashes, and failure classes, and state `not demonstrated` for any missing gate. Label the result as **runner-level** evidence; host model behavior is covered only by deterministic delegation tests unless separately authorized and measured.

- [ ] **Step 6: Validate, run serially, and commit evidence**

```bash
mac-gate uv run --frozen pytest tests/test_jeviphy_zero_config_eval.py tests/test_jeviphy_autorun.py tests/test_jeviphy_skill.py -q
mac-gate uv run --frozen ruff check tools/jeviphy_zero_config_eval.py tests/test_jeviphy_zero_config_eval.py
```

Run the frozen evaluator serially with a declared time ceiling and no paid API. Keep the existing large benchmark separate. Commit the harness, frozen manifest/schema, and bounded public report only after the run completes.

- [ ] **Step 7: Loop on every failed gate before integration**

When the score is `fail` or `insufficient_evidence`, retain that immutable result, map the failure to its owning task, add one regression test, apply the smallest correction, and rerun that task's focused gate. Create a new candidate SHA and rerun the same frozen manifest; never edit case membership or thresholds after viewing results. Repeat until the scorecard passes or a concrete external blocker is documented. Task 7 cannot start with a non-passing scorecard.

### Task 7: Final Review, Installation, and Integration

**Files:**
- Review: every file changed in Tasks 1 through 6.
- Update only if evidence requires it: `README.md`, `docs/jeviphy/index.html`.

**Precondition:** the frozen zero-configuration scorecard is `pass` for the exact candidate SHA.

**Interfaces:**
- Consumes: completed implementation and passing frozen scorecard.
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

## Optimization Loop

A change is **substantial** when it changes architecture, task order, an interface, a testable acceptance rule, a safety boundary, or the evidence needed for a claim. Wording and formatting alone do not reset the convergence streak.

- **Pass 1 — substantial improvements found and applied:** fixed the undefined `graph_path` interface; removed the `query QUESTION` collision with the strict legacy parser; defined single-case corpus inference; reused existing no-retry provider behavior; added the immutable core-commit/self-pin sequence; made runner-level interaction and network evidence measurable; and required both arms to use the same frozen question.
- **Pass 2 — substantial improvements found and applied:** corrected persisted versus in-memory graph metadata; added corrupt/malformed graph cases; updated every question-selection example to the real signature; made provider helpers silent and centralized exactly-once status output; and prevented a mismatched corpus question from influencing an explicit query.
- **Pass 3 — substantial improvements found and applied:** changed the installed command to absolute skill-path execution through `uv run` while preserving the target cwd; added clean-home execution proof; made unknown commands fail closed; and made the core-commit/self-pin transition directly executable.
- **Pass 4 — substantial improvement found and applied:** added a fail-to-owning-task correction loop with immutable failed evidence and blocked integration unless the frozen scorecard passes for the exact candidate SHA.
- **Pass 5 — substantial improvement found and applied:** moved credential access behind corpus validation and non-empty eligible-pair construction, with explicit zero-read and zero-call regression coverage.
- **Pass 6 — substantial improvement found and applied:** defined real offline memory behavior through the existing trusted `fast-source` path and made result modes reflect whether memory actually changed traversal seeds.
- **Pass 7 — substantial improvement found and applied:** separated current project-to-portable byte parity from immutable dependency-pin parity so the new autorun module can be developed before it exists in the next pinned commit.
- **Pass 8 — substantial improvement found and applied:** replaced repair instructions with one automatic offline Graphify extract/update attempt, credential-stripped child execution, mandatory revalidation, and fail-closed no-retry behavior.
- **Pass 9 — no substantial improvement:** architecture, interfaces, acceptance rules, safety boundaries, task order, and evidence gates remained unchanged; only the file map and credential-removal list were clarified.
- **Pass 10 — substantial improvement found and applied:** split corrupt-graph recovery from missing-graph creation and required Graphify `extract --force --code-only` for the corrupt artifact path.
- **Pass 11 — no substantial improvement:** architecture, CLI grammar, repair flow, cost boundary, privacy boundary, evidence denominators, and integration gate remained complete; only one task cross-reference was corrected.
- **Pass 12 — no substantial improvement:** a final adversarial scan found no unresolved interface, contradictory scenario, unsafe provider path, mutable benchmark threshold, or integration bypass.
- **Consecutive passes without substantial improvement:** 2 of 2 — convergence goal met.

## Self-Review Result

- **Spec coverage:** ZC1–ZC8 map to Tasks 1–6; integration and installed-state proof are in Task 7.
- **Placeholder scan:** no deferred implementation placeholders remain.
- **Type consistency:** `InvocationContext`, `PilotOutcome`, `AutoResult`, and `ZeroConfigScore` each have one definition and named consumers.
- **Scope:** one orchestration module, one small query-core extraction, and one evaluation harness; no runtime dependency or provider machinery is added.

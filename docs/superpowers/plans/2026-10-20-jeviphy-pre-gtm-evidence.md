# Jeviphy Pre-GTM Evidence and Release Candidate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert Jeviphy's proven retrieval improvement into a mechanically scored product, usability, compatibility, and reproduction decision before any GTM campaign.

**Architecture:** Preserve the frozen v2 retrieval result and Graphify engine. Add the missing bridge from mini-swe-agent predictions to official SWE-bench evaluation, assemble every evidence source into one immutable report, and let the existing scorecard choose the strongest permitted claim. Run expensive work in a GitHub Codespace; keep default Jeviphy offline and local-first.

**Tech Stack:** Python 3.10+, pytest, standard library, mini-swe-agent, SWE-bench Docker harness, GitHub Codespaces through `codespace-manager`, GitHub Actions for lightweight checks, existing Graphify and Jeviphy modules.

**Spec:** `.specs/tasks/draft/jeviphy-pre-gtm-evidence.feature.md`

## Global Constraints

- Preserve benchmark v2 manifest SHA `ce54fe1c5c531d10947ea363a05cbb0ed6dcd0336324752b03276306713584ac` and Graphify pin `4342e67107f77db54098d7873b563ff20830dcb8`; changed inputs create benchmark v3.
- Preserve the published retrieval result and its raw artifact hashes; never rewrite historical results with a new candidate.
- A trajectory, submitted patch, zero exit code, or retrieval hit is not product-task success; only the official SWE-bench evaluator decides success.
- Default Jeviphy performs no paid call. Live execution requires current-conversation approval, project-scoped credentials, positive call ceilings and cost stop thresholds, and a fresh private output directory.
- Product generation, Docker evaluation, full suite, and install matrices run on GitHub compute; do not run them directly on the Mac.
- Typecheck, lint, and focused tests use the project's Python equivalents; when local execution is needed, use `mac-gate`. Do not add a dependency unless the official evaluator requires it in the remote run environment.
- Tasks 1–6 form one implementation task with one branch and one PR to `jeviphy`. Task 7 starts only after that merge and uses its own beta-evidence branch and one PR. Own both reviews, checks, merges, and post-merge verification without asking Luis to review.
- Do not start GTM until the scorecard emits the corresponding allowed claim.
- Do not attribute offline provenance results to JEV; describe JEV as optional until a separate JEV-on versus JEV-off gate passes.

## Review Focus

1. **False success:** trajectory exists but official tests fail; Task 1 pins unresolved as `success=false`.
2. **Mixed evidence:** records from different candidates, models, manifests, or machines; Task 2 rejects every mismatched pin.
3. **Paid partial run:** provider or Docker fails after some arms; Task 1 preserves completed evidence and stops without uncertain retry.
4. **Claim inflation:** retrieval passes while product or reproduction fails; Task 3 emits only the exact allowed claim.
5. **Fake independence:** a receipt is duplicated or authored by an implementation contributor; Task 4 rejects it.

---

## Current State and Remaining Work

Already complete and retained:

- 120-case frozen v2 manifest and 600-pair retrieval report;
- retrieval gate pass, including salted holdout;
- 30-case zero-configuration pass;
- receipt-based Claude/Codex installer;
- Docker product runner with cost preflight;
- CI, CodeQL, Ruff, Bandit, and `pip-audit` gates.

Remaining critical path:

1. turn generated predictions into officially evaluated product pairs;
2. run the frozen product arms remotely under an approved provider budget;
3. unify existing and new evidence without mixing SHAs;
4. collect two-OS install evidence and independent receipts;
5. freeze a release candidate and publish the scorecard-selected claim.

## File and Interface Map

| Responsibility | File |
| --- | --- |
| Pre-GTM acceptance contract | `.specs/tasks/draft/jeviphy-pre-gtm-evidence.feature.md` |
| Live arm generation and official evaluation | `tools/jeviphy_product_batch.py` |
| Product record dataclasses and sealing | `tools/jeviphy_product_eval.py` |
| Unified evidence assembly | `tools/jeviphy_evidence_bundle.py` |
| Mechanical release decision | `tools/jeviphy_product_score.py` |
| Product-run tests | `tests/test_jeviphy_product_batch.py` |
| Arm-dataset integrity | `tools/jeviphy_product_dataset.py` and `tests/test_jeviphy_product_dataset.py` |
| Evidence-bundle tests | `tests/test_jeviphy_evidence_bundle.py` |
| Scorecard tests | `tests/test_jeviphy_product_score.py` |
| Clean-install measurement | `tools/jeviphy_install_eval.py` |
| Install-evaluation tests | `tests/test_jeviphy_install_eval.py` |
| Frozen public evidence | `benchmarks/jeviphy-v2/results/` and `docs/jeviphy-v2-evaluation.md` |
| Reproduction contract | `benchmarks/jeviphy-v2/reproductions/README.md` |

### Task 1: Make Product Arms Officially Scoreable

**Files:**
- Create: `tools/jeviphy_product_dataset.py`
- Create: `tests/test_jeviphy_product_dataset.py`
- Modify: `tools/jeviphy_product_batch.py`
- Modify: `tools/jeviphy_product_eval.py`
- Modify: `tests/test_jeviphy_product_batch.py`
- Modify: `tests/test_jeviphy_product_eval.py`
- Modify: `benchmarks/jeviphy-v2/README.md`

**Interfaces:**
- Consumes: paired Graphify/Jeviphy datasets, mini-swe-agent `preds.json`, trajectory, frozen dataset path, `instance_id`, immutable `RunPins`, and private output root.
- Produces: `validate_arm_case(...)`, `validate_arm_datasets(...)`, `ProductArmRecord`, `evaluate_prediction(...) -> ProductArmRecord`, `--max-new-arms`, append-only `product-arms.jsonl`, and sealed `product-report.json` compatible with `score_run(...)`.

- [ ] **Step 1: Write failing tests for the success boundary**

Add a frozen product arm type and fixtures for resolved, unresolved, missing prediction, duplicate prediction, provider failure, evaluator failure, forbidden dataset drift, and leaked gold material:

```python
def test_trajectory_without_resolved_report_is_not_success(tmp_path):
    prediction = write_prediction(tmp_path, patch="diff --git a/a.py b/a.py\n")
    report = write_eval_report(tmp_path, resolved=False)
    arm = evaluate_prediction("graphify", "case-1", prediction, report, elapsed_seconds=1.0)
    assert arm.status == "completed"
    assert arm.success is False


def test_missing_or_duplicate_prediction_fails_closed(tmp_path):
    with pytest.raises(ValueError, match="exactly one prediction"):
        load_prediction(tmp_path / "preds.json", "case-1")


def test_arm_datasets_allow_only_bounded_context_difference(tmp_path):
    graphify, jeviphy = paired_dataset_fixture(tmp_path)
    jeviphy["problem_statement"] += "\nReviewed source: src/router.py"
    validate_arm_case(graphify, jeviphy)
    jeviphy["test_patch"] += "\nleak"
    with pytest.raises(ValueError, match="test_patch differs"):
        validate_arm_case(graphify, jeviphy)
```

- [ ] **Step 2: Run focused tests remotely and confirm failure**

Run in the task Codespace after proving its SHA and clean status:

```bash
uv sync --all-extras --frozen
uv run --frozen pytest tests/test_jeviphy_product_dataset.py tests/test_jeviphy_product_batch.py tests/test_jeviphy_product_eval.py -q
```

Expected: failure because the dataset validator, `ProductArmRecord`, `load_prediction`, and `evaluate_prediction` do not exist.

- [ ] **Step 3: Validate paired datasets before any model call**

Load both dataset splits and index them by `instance_id`. Require the complete frozen 120-case set. Compare every field byte-for-byte except `problem_statement`, then validate the added Jeviphy suffix against these limits: at most 20 source paths, at most 8 KiB UTF-8, no `patch` or `test_patch` substring, and no gold symbol from the manifest. Write the canonical hashes of both datasets into `RunPins`.

- [ ] **Step 4: Add immutable product records**

Add this shape to `tools/jeviphy_product_eval.py`:

```python
@dataclass(frozen=True)
class ProductArmRecord:
    arm: str
    instance_id: str
    status: str
    success: bool
    generation_seconds: float
    evaluation_seconds: float
    prediction_sha256: str
    patch_sha256: str
    trajectory_sha256: str
    input_tokens: int | None
    output_tokens: int | None
    cost_usd: str | None
    resolved: bool
    diagnostic: str | None = None
```

Hash bytes before parsing. Reject empty patches, unexpected instance IDs, duplicate predictions, missing evaluator reports, and non-boolean `resolved` values. Diagnostics contain status names and paths relative to the private run root, never provider bodies or credentials.

- [ ] **Step 5: Invoke the official evaluator for each completed prediction**

After mini-swe-agent produces `preds.json`, execute:

```python
[
    sys.executable,
    "-m", "swebench.harness.run_evaluation",
    "--dataset_name", str(root / f"{arm}-train"),
    "--predictions_path", str(predictions),
    "--max_workers", "1",
    "--run_id", run_id,
]
```

Use a run ID derived from candidate SHA, arm, and instance ID. Keep evaluator output under the arm directory. Parse only that run ID's report. Record evaluator timeout or Docker/image failure as `infrastructure_failed` and stop the serial batch.

- [ ] **Step 6: Seal pairs in the existing scorecard shape**

For each case, pair its two `ProductArmRecord` values and write:

```json
{
  "pair": {
    "case_id": "repo__issue",
    "stratum": "valid_source",
    "pass_index": 0,
    "baseline": {"success": false, "duration_ms": 1000.0},
    "jeviphy": {"success": true, "duration_ms": 800.0}
  }
}
```

Map `generation_seconds + evaluation_seconds` to `duration_ms`. Copy token counts only when both arms report them. Seal only when the expected case set matches exactly; retain failed and timed-out arms as `success=false`.

- [ ] **Step 7: Enforce provider and global limits**

Treat the validated CLI ceilings as totals for the complete candidate run. Before every paid arm, count completed paid arms and sum their decimal `cost_usd` values from the validated journal. Compute `remaining_arms = max_agent_arms - completed_arms` and `remaining_cost = max_cost_usd - spent_cost`; reject missing, malformed, negative, duplicated, or uncertain cost records before starting another arm. Set `MSWEA_GLOBAL_CALL_LIMIT` to the frozen per-arm `agent.step_limit` and `MSWEA_GLOBAL_COST_LIMIT` to the remaining total cost. Refuse an existing `preds.json`, evaluator directory, or sealed report in a fresh run root. Preserve resume only through the append-only arm journal with identical pins.

Add `--max-new-arms` with a positive upper bound of 12. The pre-GTM runner uses two arms so every paired case becomes a remote checkpoint. Count only arms absent from the validated journal, flush and fsync the journal, and leave final sealing unavailable until the expected 60-arm set is complete.

Add a regression test that runs two simulated chunks and proves both receive the frozen per-arm call ceiling while the second receives the original total cost ceiling minus the first arm's decimal cost. A journal arm without provider cost must block the next paid chunk rather than assuming zero.

- [ ] **Step 8: Validate and commit**

Run remotely:

```bash
uv run --frozen pytest tests/test_jeviphy_product_dataset.py tests/test_jeviphy_product_batch.py tests/test_jeviphy_product_eval.py -q
uv run --frozen ruff check tools/jeviphy_product_dataset.py tools/jeviphy_product_batch.py tools/jeviphy_product_eval.py tests/test_jeviphy_product_dataset.py tests/test_jeviphy_product_batch.py tests/test_jeviphy_product_eval.py
uv run --frozen pyright tools/jeviphy_product_dataset.py tools/jeviphy_product_batch.py tools/jeviphy_product_eval.py
```

Expected: all exit `0`.

Commit:

```bash
git add tools/jeviphy_product_dataset.py tools/jeviphy_product_batch.py tools/jeviphy_product_eval.py tests/test_jeviphy_product_dataset.py tests/test_jeviphy_product_batch.py tests/test_jeviphy_product_eval.py benchmarks/jeviphy-v2/README.md
git commit -m "feat: score product arms with SWE-bench"
```

### Task 2: Assemble One Immutable Evidence Bundle

**Files:**
- Create: `tools/jeviphy_evidence_bundle.py`
- Create: `tests/test_jeviphy_evidence_bundle.py`
- Modify: `tools/jeviphy_product_score.py`
- Modify: `tests/test_jeviphy_product_score.py`

**Interfaces:**
- Consumes: retrieval report, sealed product report, zero-config score, install score, compatibility receipt, reproduction receipts, and exact candidate pins.
- Produces: `assemble_bundle(inputs: EvidenceInputs) -> dict`, `validate_reproduction_receipt(...)`, and canonical `evidence-bundle.json` for `score_run(...)`.

- [ ] **Step 1: Write failing evidence-integrity tests**

```python
def test_bundle_rejects_mixed_candidate_shas(valid_inputs):
    valid_inputs.product["pins"]["jeviphy_commit"] = "f" * 40
    with pytest.raises(ValueError, match="candidate SHA differs"):
        assemble_bundle(valid_inputs)


def test_bundle_rejects_duplicate_or_self_authored_receipts(valid_inputs):
    receipt = valid_inputs.reproductions[0]
    valid_inputs.reproductions = [receipt, receipt]
    with pytest.raises(ValueError, match="duplicate reviewer"):
        assemble_bundle(valid_inputs)
```

Also test manifest mismatch, retrieval hash mismatch, incomplete product pairs, wrong zero-config candidate, unknown fields, and a receipt author present in `retrieval_authors`.

- [ ] **Step 2: Run tests and confirm failure**

Run:

```bash
mac-gate uv run --frozen pytest tests/test_jeviphy_evidence_bundle.py -q
```

Expected: collection fails because `tools.jeviphy_evidence_bundle` does not exist.

- [ ] **Step 3: Implement strict canonical assembly**

Use frozen dataclasses for file inputs. Read every file once, verify SHA-256 before parsing, require exact top-level keys, and emit sorted JSON with a trailing newline. The bundle shape is:

```json
{
  "schema_version": 1,
  "pins": {},
  "retrieval_records": [],
  "product_records": [],
  "usability": {},
  "compatibility": true,
  "reproductions": [],
  "source_hashes": {}
}
```

Do not copy private trajectories, prompts, memory text, provider logs, or patches into the public bundle.

- [ ] **Step 4: Make product-score validation fail closed**

Before scoring, require each product pair to contain both arms, boolean success, positive duration, matching case ID, unique `(case_id, pass_index)`, and a known stratum. Return `insufficient_evidence` for missing evidence and raise `ValueError` for contradictory evidence. Add the beta-only claim:

```python
BETA_READY = "Jeviphy is ready for a limited source-aware beta."
```

Emit it only when retrieval, usability, and compatibility pass while product or reproduction does not.

- [ ] **Step 5: Validate and commit**

Run:

```bash
mac-gate uv run --frozen pytest tests/test_jeviphy_evidence_bundle.py tests/test_jeviphy_product_score.py -q
mac-gate uv run --frozen ruff check tools/jeviphy_evidence_bundle.py tools/jeviphy_product_score.py tests/test_jeviphy_evidence_bundle.py tests/test_jeviphy_product_score.py
```

Commit:

```bash
git add tools/jeviphy_evidence_bundle.py tools/jeviphy_product_score.py tests/test_jeviphy_evidence_bundle.py tests/test_jeviphy_product_score.py
git commit -m "feat: assemble immutable Jeviphy evidence"
```

### Task 3: Produce Two-OS Usability and Compatibility Evidence

**Files:**
- Create: `tools/jeviphy_install_eval.py`
- Create: `tests/test_jeviphy_install_eval.py`
- Create: `benchmarks/jeviphy-v2/install-matrix.json`
- Create: `.github/workflows/jeviphy-rc-evidence.yml`
- Modify: `docs/jeviphy-zero-configuration-evaluation.md`

**Interfaces:**
- Consumes: candidate checkout, temporary home, host `claude|codex`, OS label, and installed runner.
- Produces: append-only install records and a sealed usability JSON with `attempts`, `successes`, `median_seconds`, `operating_systems`, and candidate SHA.

- [ ] **Step 1: Write failing measurement tests**

Test clean install, `doctor`, bare offline query, reinstall, receipt-safe uninstall, conflicting destination, changed installed file, and aggregation across both OS labels:

```python
def test_install_score_requires_twenty_attempts_and_both_systems():
    records = passing_records(ubuntu=10, macos=10)
    score = score_installs(records)
    assert score["attempts"] == 20
    assert score["successes"] == 20
    assert score["operating_systems"] == ["macOS", "Ubuntu"]
```

- [ ] **Step 2: Implement the isolated clean-home evaluator**

For each matrix entry, create a temporary `HOME`, install one host, run `doctor`, execute one offline query in a tiny pinned Git fixture, reinstall, and uninstall. Close stdin, remove all provider keys, set `GRAPHIFY_QUERY_LOG_DISABLE=1`, and hash stdout/stderr instead of persisting contents.

Use this checked-in matrix:

```json
{
  "schema_version": 1,
  "attempts": [
    {"os": "Ubuntu", "host": "claude", "repeat": 5},
    {"os": "Ubuntu", "host": "codex", "repeat": 5},
    {"os": "macOS", "host": "claude", "repeat": 5},
    {"os": "macOS", "host": "codex", "repeat": 5}
  ]
}
```

- [ ] **Step 3: Run Ubuntu evidence remotely**

Use the 4-core task Codespace and prove candidate SHA before running ten attempts. Store the raw private journal outside Git and copy only the sealed aggregate plus hashes into the evidence workspace. Stop the Codespace after completion.

- [ ] **Step 4: Run macOS evidence on a release-candidate tag**

Create `jeviphy-rc-evidence.yml` with `on.push.tags: ["jeviphy-rc-*"]`, `macos-latest`, a 15-minute timeout, and concurrency keyed by tag with `cancel-in-progress: true`. Run only the ten macOS clean-home attempts; do not run the repository suite or a build. Upload the sealed aggregate and journal hashes as artifacts. The tag must point to the exact candidate SHA.

- [ ] **Step 5: Attach the frozen zero-config result**

Verify the existing 30-case score, manifest hash, runner SHA, 24/24 exact outputs, 0 prompts, and latency thresholds. Do not rerun unless the candidate changes `jeviphy_autorun.py`, the portable runner, installer, or Graphify query behavior. If any of those files changed, create a fresh output directory and rerun all 30 cases.

- [ ] **Step 6: Validate and commit**

Run:

```bash
mac-gate uv run --frozen pytest tests/test_jeviphy_install_eval.py tests/test_jeviphy_install.py tests/test_jeviphy_skill.py tests/test_jeviphy_zero_config_eval.py -q
mac-gate uv run --frozen ruff check tools/jeviphy_install_eval.py tests/test_jeviphy_install_eval.py
```

Commit code, matrix, public aggregate, and updated documentation. Exclude temporary homes and raw logs.

### Task 4: Validate Independent Reproduction Receipts

**Files:**
- Create: `tools/jeviphy_reproduction.py`
- Create: `tests/test_jeviphy_reproduction.py`
- Modify: `benchmarks/jeviphy-v2/reproductions/README.md`
- Create after external submission: `benchmarks/jeviphy-v2/reproductions/<github-handle>-<os>.json`

**Interfaces:**
- Consumes: canonical receipt JSON, benchmark pins, retrieval-change author list, and public result hash.
- Produces: `validate_receipts(paths, pins, authors) -> tuple[Receipt, ...]`.

- [ ] **Step 1: Write receipt-validation tests**

Cover two valid reviewers, missing Linux, duplicate reviewer, mismatched manifest/result/candidate hash, implementation author, missing payload hash, unknown field, and malformed canonical JSON.

- [ ] **Step 2: Implement canonical receipt validation**

Require:

```json
{
  "schema_version": 1,
  "reviewer": "github-handle",
  "independent": true,
  "os": "Ubuntu 24.04",
  "machine": "4 vCPU, 16 GB RAM",
  "manifest_sha256": "...",
  "graphify_commit": "...",
  "jeviphy_commit": "...",
  "result_sha256": "...",
  "scorecard": {"retrieval": "pass"},
  "payload_sha256": "sha256 of canonical payload without this field"
}
```

The payload hash detects accidental edits; it is not an identity credential. Independence depends on a real external reviewer submitting the receipt through their GitHub identity.

- [ ] **Step 3: Publish a one-command reproduction path**

Document the exact clone, checkout, `uv sync --frozen`, retrieval command, score command, receipt generator, and expected hashes. The command must run offline after dependencies and frozen repositories are present.

- [ ] **Step 4: Validate and commit the contract**

Run:

```bash
mac-gate uv run --frozen pytest tests/test_jeviphy_reproduction.py -q
mac-gate uv run --frozen ruff check tools/jeviphy_reproduction.py tests/test_jeviphy_reproduction.py
```

Commit the validator and documentation. External receipts arrive later through the same branch/PR if they are available before release; automation must not fabricate them.

### Task 5: Execute the Frozen Remote Product Benchmark

**Files:**
- Private input: `$PRIVATE_ROOT/{graphify-train,jeviphy-train,mini-openrouter.yaml,all-cases.json}`
- Private output: `$PRIVATE_OUTPUT/`
- Public aggregate after sealing: `benchmarks/jeviphy-v2/results/product-report.json`
- Modify: `docs/jeviphy-v2-evaluation.md`

**Interfaces:**
- Consumes: approved provider/model/content/call/cost scope and Task 1's frozen runner.
- Produces: official evaluated product pairs, hashes, aggregate metrics, and an explicit product-gate decision.

- [ ] **Step 1: Freeze and print the execution preview without a provider key**

In the Codespace, validate both complete arm datasets, then print only: candidate SHA, manifest hash, selected-case hash, both dataset hashes, model name, case count `30`, arm count `60`, chunk size, per-arm cost stop threshold, aggregate cost stop threshold, Docker version, and output path. Verify the checkout is clean and the output path does not contain an earlier run. Do not pool the earlier Modal or partial Docker outputs.

- [ ] **Step 2: Run a two-arm live canary under its own approval**

Before the full run, request approval for exactly two paid agent arms, up to 320 internal model calls under the frozen 160-step limit, and the configured two-arm maximum of `$0.32`. Run one case chosen by a manifest hash before outputs are viewed. Require both predictions, both official evaluations, a sealed pair, and a scorecard-readable record. Discard the canary from the 30-case denominator and use a new output directory for the candidate run. The earlier four-arm 80-step pilot is diagnostic evidence only because both Jeviphy arms exhausted that artificial ceiling before evaluation.

- [ ] **Step 3: Stop at the full paid-use boundary**

Obtain current-conversation approval for exactly 60 paid agent arms, up to 9,600 internal model calls under the frozen 160-step limit, and the calculated maximum. At `agent.cost_limit: 0.16`, the ceiling is `$9.60`; recalculate from the frozen configuration rather than hard-coding it. The owner authorized the spend required to complete this benchmark in the current conversation. Do not infer future approval from the canary, an earlier conversation, or a GitHub/AWS compute authorization.

- [ ] **Step 4: Run the serial generation and official evaluation**

Execute through `codespace-manager`:

```bash
uv run --frozen python -m tools.jeviphy_product_batch \
  --root "$PRIVATE_ROOT" \
  --cases "$PRIVATE_ROOT/all-cases.json" \
  --output-dir "$PRIVATE_OUTPUT" \
  --allow-network-agent \
  --max-agent-arms 60 \
  --max-cost-usd 9.60 \
  --max-new-arms 2 \
  --case-limit 30
```

Run in paired chunks with `--max-new-arms 2`. The runner alternates arms, evaluates each prediction officially, journals each arm, and stops on provider or evaluation infrastructure failure. Set `MSWEA_MODEL_RETRY_STOP_AFTER_ATTEMPT=1`; uncertain provider timeouts are never retried. Resume is allowed only with identical pins. `codespace-manager` must stop the Codespace after each chunk; never leave a benchmark command detached.

- [ ] **Step 5: Seal and score without tuning**

Generate `product-report.json`, assemble the evidence bundle, and run `tools.jeviphy_product_score`. Do not change thresholds, cases, prompts, model, or context after seeing results. If a harness defect is fixed, invalidate the affected run and record the old result separately.

- [ ] **Step 6: Publish the result even when negative**

Commit only sanitized records, aggregate metrics, hashes, denominators, failure counts, costs, and the scorecard-selected claim. Keep trajectories, patches, provider logs, keys, and full task outputs private.

### Task 6: Freeze the Release Candidate and Decide Beta Eligibility

**Files:**
- Modify: `benchmarks/jeviphy-v2/results/scorecard.json`
- Modify: `benchmarks/jeviphy-v2/results/scorecard.md`
- Modify: `docs/jeviphy-v2-evaluation.md`
- Modify: `docs/jeviphy-roadmap.md`
- Modify: `docs/jeviphy/index.html`
- Create: `docs/jeviphy-pre-gtm-release-checklist.md`

**Interfaces:**
- Consumes: immutable evidence bundle and mechanical scorecard.
- Produces: release decision, exact public claim, reproduction instructions, a three-minute demo path, and beta eligibility.

- [ ] **Step 1: Generate every public claim mechanically**

The page and report read the allowed claim from the scorecard artifact during their content check. Add a test that fails if the sales page contains `faster`, `better`, `more effective`, or `surpassed` without the matching passing gate and benchmark scope in the same section. Also fail if copy attributes an offline source-aware result to JEV without a separate JEV comparison artifact.

- [ ] **Step 2: Create the three-minute product demonstration**

Document one path only:

```bash
python scripts/install_jeviphy_skill.py install --host both
cd /path/to/repository
/jeviphy
```

Show automatic repository discovery, question selection, offline Graphify fallback, optional source-backed context, and the audit envelope. Do not include provider setup in the default demo.

- [ ] **Step 3: Apply the release decision table**

- Safety or compatibility failure: stop release and return to the owning task.
- Retrieval + usability + compatibility: limited beta with the beta-only claim.
- Product also passes, reproduction pending: internal candidate; no public superiority claim.
- Every benchmark gate passes: the release candidate may enter private beta with the exact reproduced benchmark claim.

- [ ] **Step 4: Run final repository gates**

In the task Codespace:

```bash
uv sync --all-extras --frozen
uv run --frozen pytest -q
uv run --frozen ruff check .
uv run --frozen pip-audit --strict
```

Run `graphify update .` remotely with provider keys unset. The full suite must match the candidate SHA. Do not use a local `next build`; this repository has no Vercel application gate.

- [ ] **Step 5: Push one PR and integrate autonomously**

Push the task branch, open one PR to `jeviphy`, wait for CI and CodeQL on the latest SHA, review the diff, merge, and verify post-merge CI on the merge commit. Stop the clean Codespace afterward and retain it only if evidence needed for reproduction remains there.

### Task 7: Run the Private Beta and Gate Mass GTM

**Execution boundary:** Start a new beta-evidence branch from the integrated Tasks 1–6 candidate. Keep all later beta updates in that branch and its single PR.

**Files:**
- Create: `benchmarks/jeviphy-beta/protocol.json`
- Create: `benchmarks/jeviphy-beta/protocol.schema.json`
- Create: `tools/jeviphy_beta_score.py`
- Create: `tests/test_jeviphy_beta_score.py`
- Create after consent: `benchmarks/jeviphy-beta/results/aggregate.json`
- Modify after completion: `docs/jeviphy-roadmap.md`

**Interfaces:**
- Consumes: consented, data-minimized beta receipts from 5–10 external Graphify or Claude-Mem users.
- Produces: `score_beta(records) -> BetaScore` and the mass-GTM decision.

- [ ] **Step 1: Freeze the onboarding protocol before recruitment**

The protocol contains one install path, one bare `/jeviphy` or `$jeviphy` task, a ten-minute timer, and these booleans: `installed_without_help`, `useful_answer_under_10m`, `first_task_without_correction`, `credential_exposure`, `unapproved_upload`, `destructive_change`, and `graph_corruption`. Freeze the protocol hash before the first participant starts.

- [ ] **Step 2: Write and implement the mechanical beta scorer**

```python
def test_beta_requires_four_successes_and_zero_safety_incidents():
    result = score_beta(five_records(successes=4, incidents=0))
    assert result.status == "pass"
    assert score_beta(five_records(successes=3, incidents=0)).status == "fail"
    assert score_beta(five_records(successes=5, incidents=1)).status == "fail"
```

Reject duplicate participants, missing consent timestamps, mixed versions, unknown fields, and fewer than five records. Store elapsed time as a bucket (`<5m`, `5-10m`, `>10m`) rather than raw activity logs.

- [ ] **Step 3: Prepare the beta package without sending it**

Create a one-page invitation, install command, three-minute walkthrough, feedback form, privacy statement, and troubleshooting link. The package must quote only the scorecard-selected claim and identify the benchmark scope. External messages remain drafts until sending is explicitly authorized.

- [ ] **Step 4: Collect receipts and publish only the aggregate**

Validate each receipt on arrival. Keep participant-level records private with mode `0600`. Commit only totals, OS/host counts, elapsed buckets, success counts, incident counts, candidate SHA, and protocol hash.

- [ ] **Step 5: Decide mass GTM mechanically**

Proceed only with at least five participants, at least four complete successes, and zero safety incidents. A failed beta returns to the owning product or onboarding task; it does not trigger copy changes that hide the failure.

## Plan Self-Review Record

- **Pass 1:** substantial improvements applied — replaced the stale “run trajectories and score” assumption with official SWE-bench patch evaluation; separated beta readiness from a public superiority claim; added a unified evidence bundle and explicit paid-use boundary.
- **Pass 2:** substantial improvements applied — prohibited mixing the old Modal/partial evidence with the Docker candidate; expanded the full run to 120 cases/240 arms; added paired-dataset leakage validation, a paid two-arm canary, remote macOS release-tag evidence, and honest receipt hashing.
- **Pass 3:** substantial improvements applied — bounded the 240-arm run into 12-arm remote chunks; separated source-provenance evidence from JEV claims; added a measurable five-user private-beta gate before mass GTM.
- **Pass 4:** no substantial improvement found — corrected the receipt field name and added the already-required chunk limit to the example command; architecture, gates, and task order remained unchanged.
- **Pass 5:** substantial improvement applied — split engineering/release-candidate work from the later external beta into two sequential task branches and PRs; aligned the declared dataset-validator interfaces with their test examples.
- **Pass 6:** no substantial improvement found — all 11 spec requirements map to owning tasks, the 39 steps have concrete commands or code, interfaces are consistent, and placeholder/code-fence scans passed.
- **Pass 7:** substantial improvement applied — made paid call limits and cost stop thresholds cumulative across all resume-safe chunks, preventing each new process from resetting and multiplying the approved budget.
- **Pass 8:** substantial improvement applied after the v8 Graphify arm stalled for the full 35-minute wall timeout — reduced the pre-GTM candidate to a deterministic balanced 30-case subset, checkpointed every pair, disabled uncertain model retries, and retained all 120 cases for leakage validation.
- **Pass 9:** no substantial improvement found — failure, resume, privacy, paired-order, official-evaluation, and claim-boundary reviews found no new design gap; clarified that uncertain cost blocks the very next paid arm.
- **Pass 10:** no substantial improvement found — verified the frozen manifest hash, current scorecard states, zero-configuration result, file map, interface names, requirement coverage, and executable commands without finding another material change.

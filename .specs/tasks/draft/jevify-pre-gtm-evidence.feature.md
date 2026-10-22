# Feature: Jevify Pre-GTM Evidence and Release Candidate

**Status:** Draft
**Owner:** Jevify maintainers
**Date:** 2026-10-20
**Decision target:** Decide mechanically whether Jevify is ready for a narrow beta, a benchmark-backed public launch, or more product work.

## Product decision - 2026-10-21

Jevify ships as a transparent technical beta. The release makes no product
advantage claim over Graphify. The supported public evidence is limited to:

- clean installation: 20/20 attempts passed on Ubuntu and macOS;
- zero configuration: 30/30 cases completed without interaction;
- Graphify compatibility: passed for the pinned candidate;
- local suite: 8,608 tests passed.

The paid product benchmark is closed at 0/60 for v13. The eight v11 pairs are
diagnostic only and cannot support a public claim. No long benchmark or paid API
run is required for this beta decision.

## Current Evidence

- Clean installation passed 20/20 attempts on Ubuntu and macOS.
- Zero-configuration execution passed 30/30 cases without interaction.
- The pinned candidate passed its Graphify compatibility receipt.
- The local suite passed 8,608 tests.
- Product benchmark v13 stopped at 0/60; the eight v11 pairs remain diagnostic only.
- Historical retrieval reports remain technical records, not beta claims.

## Archived product question

The stopped benchmark asked whether Jevify changed completed coding-task outcomes
while preserving Graphify behavior. The beta decision does not answer or publish
a claim from that question.

## Non-Goals

- Replacing Graphify extraction, graph format, clustering, or visualization.
- Making JEV or any paid provider mandatory for the default command.
- Tuning against holdout outcomes after the candidate is frozen.
- Treating trajectory creation, patch submission, retrieval accuracy, or human preference as task success.
- Publishing a product-advantage claim over Graphify.
- Attributing an offline source-provenance gain to JEV. JEV remains optional and requires its own positive evidence.

## Stopped product evaluation protocol

### Arms

1. **Graphify:** the pinned Graphify baseline and the same coding agent/model.
2. **Jevify:** the same Graphify revision, agent, model, task, container image, context limit, and timeout, with only Jevify context enabled.

Each case runs both arms. Arm order alternates by case. The official SWE-bench harness evaluates both generated patches against the same immutable task definition.

### Product success

A product arm succeeds only when all conditions hold:

1. mini-swe-agent writes a prediction containing the expected instance ID and a non-empty `model_patch`;
2. the official SWE-bench Docker evaluator completes without infrastructure failure;
3. the evaluator reports the instance as resolved;
4. fail-to-pass tests pass and pass-to-pass tests do not regress.

A trajectory, `Submitted` status, zero process exit, or plausible diff alone is never success.

### Required gates

The historical v2 scorecard thresholds remain frozen for auditability:

- product success advantage at least 10 percentage points;
- paired 95% bootstrap lower bound greater than zero;
- no-source success regression no worse than 2 percentage points;
- median input tokens at least 15% lower or median completion time at least 20% lower;
- overall p95 completion time no more than 5% slower;
- retrieval, usability, compatibility, and reproduction gates also pass.

These thresholds do not authorize a beta claim. The benchmark is stopped and its
partial records remain diagnostic.

## Functional Requirements

### PG1 — Immutable candidate and inputs

The run records the Jevify SHA, Graphify SHA, manifest SHA-256, agent-config SHA-256, model identifier, mini-swe-agent version, SWE-bench version, Python version, Docker version, machine class, command hash, chunk size, and cost stop thresholds. Any mismatch aborts resume or aggregation.

The Graphify and Jevify datasets must have identical instance IDs, repository pins, test patches, fail-to-pass tests, pass-to-pass tests, environment images, and metadata. A checked-in whitelist defines the only permitted arm difference: the Jevify problem statement may add bounded source-backed context. The validator rejects gold patch text, gold symbols, test patch text, or fields outside that whitelist.

The Graphify and Jevify datasets must have identical instance IDs, repository pins, test patches, fail-to-pass tests, pass-to-pass tests, environment images, and metadata. A checked-in whitelist defines the only permitted arm difference: the Jevify problem statement may add bounded source-backed context. The validator rejects gold patch text, gold symbols, test patch text, or fields outside that whitelist.

### PG2 — Scoreable product records

The product runner emits one append-only JSONL record per completed arm and one sealed paired report. Each arm records status, prediction hash, patch hash, trajectory hash, elapsed time, token counts when supplied, provider cost when supplied, evaluator status, resolved outcome, and bounded diagnostic.

Only a pair with both evaluated arms enters the comparison. Interrupted, timed-out, provider-failed, or evaluator-failed arms remain failures in the denominator.

### PG3 — Official patch evaluation

The evaluator consumes the `preds.json` produced by mini-swe-agent and invokes `python -m swebench.harness.run_evaluation` with Docker and one worker. Evaluation artifacts remain in the private run directory. A parser accepts only the pinned run ID and instance ID and rejects missing, duplicated, or contradictory reports.

### PG4 — Cost and execution safety

The default path remains offline. A live run requires all of:

- `--allow-network-agent`;
- positive `--max-agent-arms` and `--max-cost-usd`;
- a fresh output directory;
- a project-scoped provider credential;
- explicit approval in the current conversation before execution.

The runner sets mini-swe-agent global call and cost stop thresholds from the same approved values. Mini-swe-agent checks cost after a provider response, so the final request can cross a threshold; the runner records that actual cost and makes no later call once the aggregate approved threshold is exhausted. The frozen agent configuration sets `environment.pull_timeout: 900` so cold SWE-bench images can finish downloading before Docker startup is judged unavailable. Provider and Docker failures stop the serial run without retrying an uncertain write.

Arm ceilings and cost stop thresholds are cumulative across resume-safe chunks. Before each arm, the runner verifies the append-only journal, subtracts completed arms and actual reported spend from the single approved totals, passes the remaining cost allowance to mini-swe-agent, and applies the frozen per-arm step limit as the internal model-call ceiling. Missing, malformed, negative, or uncertain cost data blocks resume. Restarting a process never resets the user's approved budget.

The first four-arm Docker pilot is historical diagnostic evidence only: the 80-step ceiling ended both Jevify arms before official evaluation while Graphify completed both. The replacement protocol gives both arms the same 160-step ceiling and `$0.16` per-arm cost stop threshold, pins the complete agent configuration by SHA-256, and uses a fresh run root. No pilot outcome is pooled into the candidate denominator.

The subsequent six-arm v5 run is also historical diagnostic evidence only. It exposed a harness defect that classified a model-generated malformed patch in SWE-bench `error_ids` as infrastructure failure. The fixed runner records `error_ids` as product failures, reserves `infra_failure_ids` or a missing report for infrastructure failures, and starts from a fresh run root and candidate SHA. No v5 record is pooled into the replacement run.

The ten-arm v6 run is historical diagnostic evidence only. It exposed that mini-swe-agent's `TimeoutExpired` status during Docker container startup was classified as a product failure with uncertain cost. The fixed runner classifies that status as `infrastructure_failed`, stops without charging the product denominator, and starts from a fresh run root and candidate SHA. No v6 record is pooled into the replacement run.

The three-arm v7 run is historical diagnostic evidence only. It exposed misleading cost-ceiling language and an arm-at-a-time wrapper that discarded a reusable Docker image between paired arms. The replacement run labels mini-swe-agent cost values as post-response stop thresholds, reserves chunks of 12 arms already permitted by this specification, and uses a fresh run root. No v7 record is pooled into the replacement run.

The one-arm v8 run is historical diagnostic evidence only. Its Graphify arm started Docker immediately but produced no trajectory or cost before the 35-minute outer timeout. The replacement protocol disables mini-swe-agent's ten-attempt model retry loop, treats the outer timeout as infrastructure failure, checkpoints one pair at a time, and uses a fresh run root. No v8 record is pooled into the replacement run.

The one-arm v9 canary is historical diagnostic evidence only. It reproduced the v8 stall in mini-swe-agent batch mode while a direct provider request returned HTTP 200 in under one second and the supported single-instance runner reached the model and wrote a trajectory. The replacement uses `swebench-single` for each already-serial arm and derives the official prediction file from its trajectory. No v9 record is pooled into the replacement run.

### PG5 — Remote compute

Product generation and SWE-bench evaluation run in a managed GitHub Codespace through `codespace-manager`. The run proves the remote checkout SHA and clean state before execution. The Codespace is stopped after each command. No product benchmark or full suite runs directly on the Mac.

The pre-GTM candidate run contains a deterministic, stratum-balanced 30-case subset and 60 arms in the same environment class. The complete frozen 120-case datasets remain the leakage-validation source. Earlier Modal or partial runs remain historical evidence and are never pooled with the Docker candidate.

The run is split into resume-safe chunks of exactly one paired case, at most two new arms. Each chunk revalidates every pin, appends complete arm records, stops the Codespace afterward, and never seals the final report until all 60 expected arms exist. At a 35-minute arm timeout, one chunk has a 70-minute worst-case bound.

The model backend disables automatic retries with `MSWEA_MODEL_RETRY_STOP_AFTER_ATTEMPT=1`. Each arm uses mini-swe-agent's single-instance runner, avoiding the batch executor that stalled even with one worker. A provider or outer wall timeout is infrastructure failure and stops before another paid arm. This prevents a stalled request from consuming the whole batch window or being retried with uncertain billing.

### PG6 — Unified evidence bundle

A deterministic assembler combines:

- frozen retrieval records;
- official product records;
- the frozen zero-configuration score;
- clean-install measurements for Claude Code and Codex on Ubuntu and macOS;
- Graphify compatibility evidence;
- independent reproduction receipts.

The assembler rejects changed hashes, mixed candidate SHAs, incomplete denominators, unknown fields, duplicate receipts, and receipts authored by a retrieval-change author.

### PG7 — Usability and compatibility

Twenty clean-home installation attempts are required: five Claude and five Codex installs on Ubuntu, plus the same matrix on macOS. At least 18/20 must pass and median clone-to-doctor time must be below five minutes. Ubuntu runs in the managed Codespace. macOS runs in a lightweight GitHub Actions release-candidate-tag workflow; neither matrix runs on Luis's Mac.

Compatibility passes only when the current candidate retains:

- exact no-source Graphify output;
- zero interactive prompts across the frozen 30-case zero-config set;
- automatic missing, stale, and corrupt graph repair;
- bounded offline fallback for missing or rejected live credentials;
- receipt-safe uninstall behavior.

### PG8 — Independent reproduction

Two people who did not author the retrieval change must reproduce the frozen retrieval result. At least one receipt must come from Linux. Receipts include reviewer identity, OS, machine, all input hashes, result hash, scorecard status, and `payload_sha256` over the canonical JSON payload. GitHub PR authorship supplies the identity trail; the payload hash only detects accidental content drift.

Internal automation may validate receipts but may not manufacture independence.

### PG9 — Technical beta readiness

A technical beta may start when installation, zero-configuration behavior, compatibility, and the local suite pass. Retrieval comparisons, product superiority, and independent reproduction are not release gates for this decision. The beta records only:

- successful install;
- time to first useful answer;
- whether the first task completed without assistance;
- fallback mode;
- explicit qualitative feedback.

No source code, prompts, memories, or graph contents are collected by default.

### PG10 — Claim policy

The beta scorecard permits only factual, non-comparative claims:

| Evidence | Allowed wording |
| --- | --- |
| 20 clean installs | “20 of 20 clean installation attempts passed on Ubuntu and macOS.” |
| 30 zero-configuration cases | “30 of 30 zero-configuration cases completed without interaction.” |
| Compatibility receipt | “The pinned candidate passed the Graphify compatibility check.” |
| Local suite | “8,608 local tests passed.” |

Any failed safety or compatibility gate blocks release. Product benchmark data remains diagnostic and must not be converted into a public comparison.

No page or outreach may claim that JEV caused a measured improvement unless a separately frozen JEV-on versus JEV-off comparison passes its own gate. Until then, describe Jevify as source-aware Graphify orchestration with optional JEV enrichment.

### PG11 — Private beta before mass GTM

Mass GTM requires a completed private beta with at least five external participants. At least four must install without maintainer intervention, obtain a useful first answer within ten minutes, and complete the scripted first task without maintainer correction. Any credential exposure, source upload without consent, destructive repository change, or graph corruption blocks GTM regardless of aggregate success.

Beta records contain participant handle, consent timestamp, version, OS, host, elapsed buckets, outcome booleans, fallback mode, and optional feedback. They never contain source code, prompts, memory text, graph contents, provider keys, or private repository names.

## Acceptance Scenarios

### Scenario: Trajectory exists but tests fail

**Given** mini-swe-agent emits a trajectory and prediction
**And** the official evaluator reports the task unresolved
**When** the arm is sealed
**Then** `success` is false
**And** the task remains in the denominator.

### Scenario: Provider succeeds but evaluation infrastructure fails

**Given** a non-empty patch was produced
**And** Docker image creation fails or the evaluator cannot produce a report
**When** the batch inspects the result
**Then** the arm is `infrastructure_failed`
**And** the serial batch stops before another paid arm.

### Scenario: Docker container startup times out before a model call

**Given** mini-swe-agent reports `TimeoutExpired` while starting the task container
**And** no trajectory exists
**When** the product runner inspects the arm
**Then** the arm is `infrastructure_failed`
**And** the arm is excluded from the product denominator
**And** the serial batch stops before another paid arm.

### Scenario: Generated patch cannot be applied

**Given** the provider returns a non-empty malformed patch
**And** the official report lists the instance in `error_ids` but not `infra_failure_ids`
**When** the batch inspects the result
**Then** the arm is a product `failed` result
**And** the batch keeps it in the denominator without retrying the paid generation.

### Scenario: Resume inputs changed

**Given** a partial journal
**When** any candidate, manifest, tool, model, command, or machine pin differs
**Then** resume fails before a new arm starts.

### Scenario: Product gate fails after retrieval passes

**Given** the retrieval gate passes
**And** the official product success confidence interval crosses zero
**When** the scorecard is generated
**Then** the allowed claim remains retrieval-only or beta-only
**And** no superiority wording is emitted.

### Scenario: External receipt is self-authored

**Given** a receipt reviewer appears in the retrieval-change author set
**When** the evidence bundle is assembled
**Then** the receipt is rejected as non-independent.

## Definition of Done

- The beta scorecard publishes installation, zero-configuration, compatibility, and suite evidence with exact scope.
- The v13 stop receipt records 0/60 and the v11 eight-pair result remains diagnostic only.
- README, presentation, participant brief, AI context, and public page contain no comparative product claim.
- The package includes focused questions for Graphify, Claude Mem, and JEV reviewers.
- One task branch, one PR, required checks, and post-merge CI are green.

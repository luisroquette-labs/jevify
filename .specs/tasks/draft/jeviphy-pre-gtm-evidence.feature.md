# Feature: Jeviphy Pre-GTM Evidence and Release Candidate

**Status:** Draft
**Owner:** Jeviphy maintainers
**Date:** 2026-10-20
**Decision target:** Decide mechanically whether Jeviphy is ready for a narrow beta, a benchmark-backed public launch, or more product work.

## Current Evidence

- The frozen v2 retrieval gate passed on 120 public tasks and 600 paired measurements.
- Valid-source precision@5 improved from 4.0% to 24.5%; first hits improved from 4/40 to 40/40.
- Stale-source losses were 0/20 and no-source outputs were byte-identical in 40/40 controls.
- The 30-case zero-configuration evaluation passed, but its evidence is not yet incorporated into the unified v2 scorecard.
- Product-task success, complete two-OS install evidence, and two independent reproductions remain insufficient.
- The live product runner now uses Docker, but a completed trajectory is not proof that the generated patch passes the official SWE-bench tests.

## Product Question

Can Jeviphy improve completed coding-task success, or achieve equal success with materially lower time or token use, while preserving Graphify behavior when source-backed memory is absent or stale?

## Non-Goals

- Replacing Graphify extraction, graph format, clustering, or visualization.
- Making JEV or any paid provider mandatory for the default command.
- Tuning against holdout outcomes after the candidate is frozen.
- Treating trajectory creation, patch submission, retrieval accuracy, or human preference as task success.
- Publishing “faster”, “better”, or “more effective” beyond metrics whose gates pass.
- Attributing an offline source-provenance gain to JEV. JEV remains optional and requires its own positive evidence.

## Evidence Model

### Arms

1. **Graphify:** the pinned Graphify baseline and the same coding agent/model.
2. **Jeviphy:** the same Graphify revision, agent, model, task, container image, context limit, and timeout, with only Jeviphy context enabled.

Each case runs both arms. Arm order alternates by case. The official SWE-bench harness evaluates both generated patches against the same immutable task definition.

### Product success

A product arm succeeds only when all conditions hold:

1. mini-swe-agent writes a prediction containing the expected instance ID and a non-empty `model_patch`;
2. the official SWE-bench Docker evaluator completes without infrastructure failure;
3. the evaluator reports the instance as resolved;
4. fail-to-pass tests pass and pass-to-pass tests do not regress.

A trajectory, `Submitted` status, zero process exit, or plausible diff alone is never success.

### Required gates

The existing v2 scorecard thresholds remain frozen:

- product success advantage at least 10 percentage points;
- paired 95% bootstrap lower bound greater than zero;
- no-source success regression no worse than 2 percentage points;
- median input tokens at least 15% lower or median completion time at least 20% lower;
- overall p95 completion time no more than 5% slower;
- retrieval, usability, compatibility, and reproduction gates also pass.

If product success is equal but efficiency passes, the allowed claim is limited to efficiency. It must not be rewritten as product superiority.

## Functional Requirements

### PG1 — Immutable candidate and inputs

The run records the Jeviphy SHA, Graphify SHA, manifest SHA-256, agent-config SHA-256, model identifier, mini-swe-agent version, SWE-bench version, Python version, Docker version, machine class, command hash, and cost ceilings. Any mismatch aborts resume or aggregation.

The Graphify and Jeviphy datasets must have identical instance IDs, repository pins, test patches, fail-to-pass tests, pass-to-pass tests, environment images, and metadata. A checked-in whitelist defines the only permitted arm difference: the Jeviphy problem statement may add bounded source-backed context. The validator rejects gold patch text, gold symbols, test patch text, or fields outside that whitelist.

The Graphify and Jeviphy datasets must have identical instance IDs, repository pins, test patches, fail-to-pass tests, pass-to-pass tests, environment images, and metadata. A checked-in whitelist defines the only permitted arm difference: the Jeviphy problem statement may add bounded source-backed context. The validator rejects gold patch text, gold symbols, test patch text, or fields outside that whitelist.

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

The runner sets mini-swe-agent global call and cost limits from the same ceilings. The frozen agent configuration sets `environment.pull_timeout: 900` so cold SWE-bench images can finish downloading before Docker startup is judged unavailable. Provider and Docker failures stop the serial run without retrying an uncertain write.

Arm and cost ceilings are cumulative across resume-safe chunks. Before each arm, the runner verifies the append-only journal, subtracts completed arms and reported spend from the single approved totals, passes the remaining cost allowance to mini-swe-agent, and applies the frozen per-arm step limit as the internal model-call ceiling. Missing, malformed, negative, or uncertain cost data blocks resume. Restarting a process never resets the user's approved budget.

The first four-arm Docker pilot is historical diagnostic evidence only: the 80-step ceiling ended both Jeviphy arms before official evaluation while Graphify completed both. The replacement protocol gives both arms the same 160-step and `$0.16` per-arm ceilings, pins the complete agent configuration by SHA-256, and uses a fresh run root. No pilot outcome is pooled into the candidate denominator.

The subsequent six-arm v5 run is also historical diagnostic evidence only. It exposed a harness defect that classified a model-generated malformed patch in SWE-bench `error_ids` as infrastructure failure. The fixed runner records `error_ids` as product failures, reserves `infra_failure_ids` or a missing report for infrastructure failures, and starts from a fresh run root and candidate SHA. No v5 record is pooled into the replacement run.

The ten-arm v6 run is historical diagnostic evidence only. It exposed that mini-swe-agent's `TimeoutExpired` status during Docker container startup was classified as a product failure with uncertain cost. The fixed runner classifies that status as `infrastructure_failed`, stops without charging the product denominator, and starts from a fresh run root and candidate SHA. No v6 record is pooled into the replacement run.

### PG5 — Remote compute

Product generation and SWE-bench evaluation run in a managed GitHub Codespace through `codespace-manager`. The run proves the remote checkout SHA and clean state before execution. The Codespace is stopped after each command. No product benchmark or full suite runs directly on the Mac.

The complete candidate run contains all 120 cases and 240 arms in the same environment class. Earlier Modal or partial runs remain historical evidence and are never pooled with the Docker candidate.

The run is split into resume-safe chunks of at most 12 new arms. Each chunk revalidates every pin, appends complete arm records, stops the Codespace afterward, and never seals the final report until all 240 expected arms exist. At a 35-minute arm timeout, one chunk has a 7-hour worst-case bound.

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

### PG9 — Beta readiness

A private beta may start when retrieval, usability, and compatibility pass, even if product superiority or reproduction does not. The beta uses 5–10 Graphify or Claude-Mem users and records only:

- successful install;
- time to first useful answer;
- whether the first task completed without assistance;
- fallback mode;
- explicit qualitative feedback.

No source code, prompts, memories, or graph contents are collected by default.

### PG10 — Claim policy

The scorecard emits exactly one allowed claim:

| Evidence | Allowed claim |
| --- | --- |
| Retrieval only | “Jeviphy improved source-backed retrieval on the frozen v2 benchmark.” |
| Retrieval + usability + compatibility | “Jeviphy is ready for a limited source-aware beta.” |
| Product + retrieval + usability + compatibility, reproduction pending | “Jeviphy passed the internal frozen v2 product gates; external reproduction is pending.” |
| Every gate passes | “Jeviphy surpassed Graphify on the frozen v2 benchmark.” |

Any failed safety or compatibility gate blocks release. A product benchmark that fails must remain published as a negative result.

No page or outreach may claim that JEV caused a measured improvement unless a separately frozen JEV-on versus JEV-off comparison passes its own gate. Until then, describe Jeviphy as source-aware Graphify orchestration with optional JEV enrichment.

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

- Product records are derived from official SWE-bench evaluation, not trajectories.
- The frozen run completes remotely with immutable pins and bounded cost.
- The unified scorecard contains no `insufficient_evidence` gate required for the selected release decision.
- Twenty clean-install attempts and the 30-case zero-config suite are attached to the candidate SHA.
- Two valid independent receipts exist before a public superiority claim.
- At least five external beta participants complete the frozen onboarding protocol before mass GTM.
- The final report publishes negative and positive outcomes with hashes and exact scope.
- One task branch, one PR, required checks, and post-merge CI are green.

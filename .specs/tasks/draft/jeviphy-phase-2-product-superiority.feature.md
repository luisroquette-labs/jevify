# Feature: Jeviphy Phase 2 — Product Superiority With Graphify Compatibility

**Status:** Draft
**Owner:** Jeviphy maintainers
**Date:** 2026-10-19
**Decision target:** Establish whether Jeviphy can outperform its Graphify base on a predeclared, reproducible product benchmark without weakening Graphify behavior.

## Problem

Jeviphy has a credible narrow result: reviewed memory with valid source paths improved retrieval and latency on one frozen cohort. It has not yet established that the complete product is better than Graphify across real coding work. Synthetic repetition, paid reranking, or a favorable subset cannot support that claim.

The next phase must turn “better” into a falsifiable contract, improve only the bottlenecks exposed by that contract, and publish negative results alongside positive ones.

## Product Position

Jeviphy is a Graphify-based extension for Claude Code and Codex. It uses reviewed memory as provenance: cited source paths may narrow the existing Graphify query, while Graphify remains the retrieval engine and exact fallback.

“Jeviphy surpasses Graphify” is permitted only when every release gate in this specification passes. Before then, the accurate claim is narrower: Jeviphy performed better in the measured source-backed cohort.

## Non-Goals

- Replacing Graphify's parser, graph format, clustering, query engine, or visualization.
- Making paid Jev calls part of the default query path.
- Training a model or adding a vector database.
- Claiming universal superiority from retrieval metrics alone.
- Tuning against the holdout repositories or changing gates after results are visible.

## Benchmark Contract

### Cohort

The frozen v2 cohort contains 120 tasks drawn from at least 6 public repositories and at least 3 programming languages:

| Stratum | Cases | Purpose |
| --- | ---: | --- |
| Valid source-backed memory | 40 | Measure the intended advantage |
| Stale or misleading source evidence | 20 | Prove safe rejection and fallback |
| No-source controls | 40 | Prove Graphify compatibility |
| Cross-file or ambiguous tasks | 20 | Measure difficult real navigation |

At least one repository, containing at least 20 tasks, is frozen as a holdout before implementation changes begin. No contributor who changes retrieval logic may view holdout outputs before the candidate release is frozen.

Every task has a public repository URL, immutable commit, question, deterministic oracle command, allowed time, gold source files, stratum, and memory evidence. Questions and memory summaries must not contain gold symbol names. Source paths may identify gold files because provenance is the product input being tested.

### Arms

- **Graphify arm:** current upstream Graphify at one immutable SHA.
- **Jeviphy arm:** Jeviphy based on that same Graphify SHA, with only the Jeviphy layer enabled.
- Both arms use the same repository commit, graph bytes, machine class, Python version, warm-up policy, task order, agent/model, context limit, and wall-clock limit.
- Paired order alternates by task and pass. Retrieval timing uses at least 5 paired passes after one unmeasured warm-up.
- A dirty checkout, mismatched SHA, changed graph, missing oracle, duplicate task ID, or incomplete arm aborts the run.

### Primary Product Outcome

A coding task succeeds only when its deterministic oracle command exits zero in a clean task worktree. Human judgment cannot override a failing oracle.

Jeviphy passes the primary gate when all conditions hold on the complete frozen cohort:

1. Task success is at least 10 percentage points higher than Graphify.
2. The 95% paired bootstrap confidence interval for the success-rate difference has a lower bound greater than 0.
3. On no-source controls, Jeviphy success is no more than 2 percentage points below Graphify.
4. Median total input tokens are at least 15% lower, or median completion time is at least 20% lower.
5. Overall p95 completion time is no more than 5% slower.

### Retrieval Outcome

Jeviphy passes the retrieval gate when all conditions hold:

1. Valid source-backed precision@5 and first-answer gold-file hits exceed Graphify.
2. The 95% paired bootstrap confidence interval for precision@5 improvement has a lower bound greater than 0.
3. Stale or misleading evidence causes zero new top-five losses relative to Graphify.
4. No-source results are byte-identical to Graphify.
5. Valid source-backed median retrieval latency is lower, and p95 latency is no more than 5% slower.

### Usability Outcome

From clean temporary homes on macOS and Ubuntu:

1. At least 90% of 20 scripted installs complete successfully.
2. Median time from clone to successful `doctor` is under 5 minutes.
3. One documented command installs the skill for Claude Code, Codex, or both.
4. Missing Graphify, graph, corpus, source commit, and permissions produce a specific non-zero diagnostic.
5. Uninstall removes only files recorded by the Jeviphy installer.

## Functional Requirements

### FR1 — Frozen Manifest

The evaluator must validate a versioned JSON manifest against a checked-in schema. It must reject duplicate IDs, mutable Git references, leaked gold symbols, missing oracle commands, invalid counts, and a cohort that does not meet the language/repository/stratum minimums.

### FR2 — Source Provenance

Each memory observation may contain `source_paths`, `source_commit`, and `reviewed_at`. A source path is usable only when it is tracked at the tested commit, maps to at least one graph node, and has not changed since `source_commit`. Changed, missing, untracked, or non-ancestor evidence is ineligible and must use the unscoped Graphify fallback.

### FR3 — Exact Fallback

When no usable source evidence remains, Jeviphy must call the existing unscoped Graphify query path with the original question. It must not append memory text, reorder results, call Jev, or mutate graph files.

### FR4 — Paired Evaluation

The runner records arm order, start/end timestamps, exit code, task success, wall time, input/output token counts when available, output hashes, repository SHA, graph SHA-256, Graphify SHA, Jeviphy SHA, Python version, and machine identifier. Interrupted runs resume only when all pinned hashes still match.

### FR5 — Gate Scoring

The scorer calculates every threshold in this specification from raw immutable run records. It emits `pass`, `fail`, or `insufficient_evidence` per gate and exits non-zero unless all required product gates pass.

### FR6 — Local-First Safety

The default evaluator performs no paid model call and no content upload. A command capable of network or paid execution requires an explicit command-line acknowledgement, a positive call limit, and a positive cost ceiling. Execution still requires the user's separate approval at run time.

### FR7 — Product Command

The existing Jeviphy skill runner gains three stable commands:

- `doctor`: validate Graphify, graph, repository, corpus, and provenance.
- `query`: run source-aware retrieval with exact Graphify fallback.
- `benchmark`: validate and execute the frozen paired retrieval benchmark.

The installed skill and repository implementation remain byte-equivalent for shared pilot modules.

### FR8 — Reproduction Package

The repository publishes the manifest schema, fixture generator, runner, scorer, command transcript template, and a report containing raw artifact hashes. At least two people outside the implementation work reproduce the result; one must use a different supported operating system.

## Safety and Integrity

- The graph is read-only throughout Jeviphy query and evaluation.
- Private memory corpora and raw paid-agent transcripts stay outside Git with mode `0600`.
- Repository and graph pins are validated before each arm, not only at run start.
- Failed, timed-out, or missing results remain failures; they are never dropped from denominators.
- Results from different SHAs, models, context limits, or hardware classes cannot be pooled.
- Existing negative paid-Jev and generic-memory findings remain in the public evidence report.

## Release Decision

| Result | Allowed decision |
| --- | --- |
| All product, retrieval, usability, compatibility, and reproduction gates pass | Publish “Jeviphy surpassed Graphify on the frozen v2 benchmark” with scope and hashes |
| Retrieval passes; product gate fails | Ship as an optional source-aware Graphify adapter; do not claim product superiority |
| No-source parity or stale-evidence safety fails | Do not release the candidate |
| External reproduction is incomplete | Keep the result labeled internal and preliminary |
| Confidence interval crosses zero | Report no demonstrated difference |

## Acceptance Scenarios

### Scenario: Valid reviewed source evidence narrows retrieval

**Given** an observation whose source commit is an ancestor of the tested commit
**And** every cited path is unchanged, tracked, and represented in the graph
**When** Jeviphy runs the query
**Then** it may seed traversal from those source nodes
**And** the graph bytes remain unchanged.

### Scenario: Stale source evidence falls back exactly

**Given** a cited file changed after the observation's source commit
**When** Jeviphy runs the query
**Then** the changed path is rejected
**And** if no usable path remains, output equals the Graphify arm byte for byte.

### Scenario: Manifest tries to leak the answer

**Given** a question or memory summary contains a gold symbol name
**When** the manifest is validated
**Then** validation fails before either arm runs.

### Scenario: Interrupted run resumes safely

**Given** a partial journal with pinned hashes
**When** the runner restarts with identical inputs
**Then** completed pairs are retained and missing pairs run
**But** any changed pin rejects the journal.

### Scenario: Superiority claim is blocked

**Given** retrieval improves but the product success confidence interval crosses zero
**When** the scorecard is generated
**Then** product superiority is `fail`
**And** the report permits only the narrower retrieval claim.

## Definition of Done

- All repository tests and new focused tests pass through `mac-gate`.
- The branch is current with the pinned upstream Graphify SHA.
- The frozen 120-task report and raw hashes are committed without private content.
- Two independent reproduction receipts are linked.
- The claim emitted by the scorecard matches the release decision table exactly.

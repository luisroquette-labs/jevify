# Feature: Jeviphy Zero-Configuration Parity

**Status:** Draft
**Owner:** Jeviphy maintainers
**Date:** 2026-10-19
**Decision target:** Make a bare `/jeviphy` invocation complete useful work with no parameter, corpus, credential, or mode-selection questions, while preserving Graphify as the exact offline fallback.

## Problem

The Jeviphy runner exposes safe retrieval and evaluation primitives, but its product path still expects users or agents to assemble `--repo`, `--graph`, `--corpus`, `--case-id`, and provider state. The skill text now tells Claude Code and Codex to infer some of these inputs, yet the executable does not enforce that behavior. Graphify feels simpler because it treats the current directory as the target, uses an existing graph immediately, and completes without requesting project-specific setup.

Jeviphy must provide the same zero-configuration path at the executable boundary. Memory and live Jev remain optional enhancements. Their absence or failure cannot prevent a source-verified Graphify answer.

## Product Contract

A user runs `/jeviphy` from a Git worktree. Without another message, the host invokes the portable runner, which:

1. resolves the repository root from the current directory;
2. uses `graphify-out/graph.json` from that root;
3. accepts the user's question or deterministically selects one graph-generated question;
4. executes an offline Graphify query;
5. applies reviewed memory only when a valid private corpus is already available;
6. attempts live Jev only inside an explicitly approved scope and with an available key; and
7. finishes with the best available source-verified answer.

The command never asks the user to prepare a corpus, choose among generated questions, replace an expired key, or select offline versus live mode.

## Non-Goals

- Replacing Graphify extraction, graph format, traversal, clustering, or visualization.
- Creating a hosted Jev proxy, billing system, OAuth flow, or shared provider credential.
- Making a paid request part of the default path.
- Reading Claude Mem storage directly or inventing memory when the supported bridge is unavailable.
- Claiming Jeviphy is better than Graphify before the frozen product benchmark passes.
- Changing the currently running frozen benchmark or pooling its results with this candidate.

## Functional Requirements

### ZC1 — Bare Invocation

`python skills/jeviphy/scripts/run.py` with no arguments resolves the top-level Git worktree containing the current directory. An explicit question remains accepted through `auto --question QUESTION`; the existing `query` subcommand remains the strict legacy evaluation interface. Explicit `--repo`, `--graph`, and `--corpus` values remain supported for evaluation and debugging.

Outside a Git worktree, the command exits non-zero with one specific diagnostic. It does not search parent home directories or guess another repository.

### ZC2 — Graph Resolution and Offline Repair

The default graph is `<repo>/graphify-out/graph.json`. A current readable graph is used immediately. When it is missing, stale, or corrupt, the auto path performs exactly one offline Graphify repair from the resolved repository: `extract . --code-only` for missing state, `extract . --force --code-only` for corrupt state, or `update .` for stale state. The child process receives no AI-provider key and uses no shell interpolation. After repair, Jeviphy reloads and revalidates the graph before querying.

Graph freshness requires the persisted top-level `built_at_commit` field. Graphify `_read_graph` must normalize it to the in-memory `_built_at_commit` attribute; missing, blank, malformed, or mismatched values are stale. A failed repair exits non-zero with the attempted command and bounded Graphify diagnostic; it never loops or asks the user to choose a repair. The graph is read-only after successful repair and during every query.

### ZC3 — Autonomous Question Selection

An explicit non-empty question always wins. Otherwise, a valid optional corpus containing exactly one case supplies that case question. Without either source, Jeviphy calls Graphify's existing `suggest_questions(...)` over the current graph and selects the first non-low-confidence question. If no such question exists, it selects the first available suggestion. If the graph yields no usable question, the command exits non-zero with a specific diagnostic instead of asking the user.

The selected question is printed before the answer so the run is auditable.

### ZC4 — Optional Memory

A corpus is optional for the default path. The host skill may create a private temporary corpus through `memory-gateway` and pass its path, but the executable never requires the user to create one. Without a valid corpus, Jeviphy calls `query_unscoped_graphify(...)` with the original selected question.

When a corpus is supplied, the auto path accepts it only when it contains exactly one valid case and one project consistent with its observations; it derives `case-id` and `project` internally. Offline auto mode reuses the existing `fast-source` path and reports `memory_offline` only when trusted cited source nodes actually seed the query; otherwise it returns the exact graph-only fallback and reports `graph_only`. Existing permission, provenance, observation-count, and source-path validation remains unchanged. Multiple-case, invalid, mismatched, or ineligible memory emits one bounded status, falls back exactly to the Graphify query, and does not mutate graph files.

### ZC5 — Optional Live Jev

The default invocation performs no provider request. Live Jev requires the existing explicit approval flag and request cap. Authorization already established in the current host conversation may be reused only within its approved provider, project, content, request, and cost scope.

A live path with no valid corpus or no eligible pairs reads no provider key and makes no request. A missing, rejected, expired, redirected, timed-out, malformed, or cost-uncertain live request performs no retry. The command emits one concise `live_enrichment=skipped` status on stderr and returns the offline/source-aware answer with exit code zero.

### ZC6 — Stable Result Envelope

The auto path emits human-readable text by default and supports `--json` with this stable envelope:

```json
{
  "schema_version": 1,
  "mode": "graph_only|memory_offline|memory_live",
  "repo": "/absolute/repository/path",
  "graph": "/absolute/repository/path/graphify-out/graph.json",
  "question": "Selected or supplied question",
  "live_enrichment": "not_requested|applied|skipped",
  "answer": "Graphify-compatible answer text"
}
```

`mode` describes applied execution: `graph_only` when memory changed no seed, `memory_offline` when trusted source seeds were used, and `memory_live` when validated live decisions were applied. Secrets, corpus content, provider error bodies, and API keys never appear in stdout, stderr, graph sidecars, or JSON output.

### ZC7 — Host Skill Integration

The installed Claude Code and Codex skills invoke the auto path for bare `/jeviphy`. They do not independently recreate target discovery, question selection, or provider-fallback logic. The portable skill copy and repository implementation remain byte-equivalent for shared modules.

### ZC8 — Doctor and Compatibility

`jeviphy doctor` defaults repository and graph from the current directory. Corpus checks appear only when `--corpus` is supplied. Existing explicit evaluation commands remain compatible.

No-source query output must equal Graphify's direct query output byte for byte after removing the Jeviphy audit header. Existing `query`, `benchmark`, installer, provenance, and exact-fallback tests remain green.

## Acceptance Scenarios

### Scenario: Bare invocation in a ready repository

**Given** the current directory is inside a Git worktree
**And** `graphify-out/graph.json` matches `HEAD`
**And** the graph can generate at least one useful question
**When** the portable runner receives no arguments
**Then** it selects a question without user input
**And** runs the offline Graphify query
**And** exits zero without reading a provider key.

### Scenario: Explicit question takes precedence

**Given** a current graph
**When** Jeviphy receives `auto --question "What calls createClient?"`
**Then** it uses that exact question
**And** does not generate or ask for alternatives.

### Scenario: Corpus is unavailable

**Given** no corpus path and no supported memory export
**When** Jeviphy runs
**Then** it returns the exact Graphify fallback answer
**And** reports `mode=graph_only`.

### Scenario: Live key is expired

**Given** live use was approved within a bounded scope
**And** the provider rejects the key
**When** Jeviphy runs
**Then** it makes no retry
**And** does not request a replacement key
**And** returns the offline answer with exit code zero
**And** reports `live_enrichment=skipped`.

### Scenario: Graph is missing, corrupt, or stale

**Given** the current directory is a Git worktree
**And** the default graph is absent, unreadable, or does not match `HEAD`
**When** Jeviphy runs
**Then** it performs exactly one offline Graphify repair without provider credentials
**And** reloads and validates the repaired graph
**And** continues the selected query without user input.

### Scenario: Automatic graph repair fails

**Given** Graphify repair exits non-zero or produces an invalid graph
**When** Jeviphy revalidates the result
**Then** it exits non-zero with one bounded diagnostic
**And** does not retry or ask the user to select a repair command.

### Scenario: Invocation occurs outside Git

**Given** the current directory is not inside a Git worktree
**When** Jeviphy runs
**Then** it exits non-zero
**And** identifies the current directory
**And** does not search for another project.

## Quality Gates

A zero-configuration release candidate passes only when:

1. all 30 frozen runner cases across at least 6 repositories complete with stdin closed and no `interaction_required` outcome;
2. no valid-repository case asks for a repository, question, corpus, mode, or credential;
3. all no-corpus outputs match direct Graphify output after removing the audit header;
4. median matched-pair zero-configuration overhead over direct Graphify is at most 10%, and p95 matched-pair overhead is at most 15%;
5. missing/stale/corrupt graph cases repair automatically, while repair failure, outside-Git, malformed corpus, and expired-key cases emit the specified bounded outcomes;
6. clean-home installs pass for Claude Code and Codex on macOS and Ubuntu, and static host-contract tests prove both skills delegate bare invocation to `auto`; and
7. the frozen product benchmark remains a separate baseline and is rerun for this candidate before any superiority claim.

## Definition of Done

- Every acceptance scenario has a focused automated test.
- The bare command completes end to end in a temporary Git worktree without network access.
- The default path reads no provider environment variable.
- Existing Graphify fallback and Jeviphy evaluation tests remain green.
- Claude Code and Codex installations contain the same zero-configuration contract.
- Local tests run through `mac-gate`; no local `next build` is run.
- One task branch, one PR, required GitHub checks, and post-merge CI are green.

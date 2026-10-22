# Jevify Graphify Amplification

Status: accepted for technical beta

## Product contract

Jevify is a Graphify-native orchestration layer. It must preserve Graphify's
structural graph, update semantics, integrity protections, reports, and
questions, then add verified freshness, prioritized questions, and optional
reviewed memory. JEV remains optional and cannot be presented as the source of
structural truth or as a demonstrated product advantage.

The user-visible invariant is:

```text
Jevify = complete Graphify workflow
       + verified freshness
       + actionable graph insights
       + reviewed memory provenance
       + optional JEV relevance decisions
```

Jevify must never report a graph as current, updated, or complete when the
matching Graphify workflow would still detect pending files, incomplete
semantic extraction, or an integrity guard.

## Primary workflow

Given a user invokes `$jevify --update` inside a Git worktree:

1. Jevify resolves the containing repository and the repository's configured
   Graphify output directory.
2. Jevify compares the live corpus with Graphify's manifest, even when
   `built_at_commit` already equals `HEAD`.
3. Jevify runs or orchestrates the same Graphify update required by the
   detected file types.
4. Jevify verifies that no changed or deleted files remain pending and runs
   the Graphify integrity diagnostic. It also verifies that Graphify produced
   `GRAPH_REPORT.md`; `graph.html` must exist without Graphify's stale marker,
   unless visualization is explicitly disabled.
5. Jevify reports graph counts, changed-file counts, integrity caveats, God
   Nodes, surprising connections, and three to five ranked questions.
6. Jevify does not automatically expand the highest-ranked question into a
   broad, truncated traversal during an update-only request.

## Scenarios

### Same commit with pending files

Given `graph.json` has `built_at_commit` equal to the repository `HEAD`
And at least one tracked or untracked supported file differs from the Graphify manifest
When Jevify inspects the graph
Then `graph_current` is false
And the response lists pending files by supported file type
And Jevify does not claim that it updated the graph before Graphify completes.

### Current graph

Given the persisted commit matches `HEAD`
And Graphify's manifest has no changed or deleted supported files
When Jevify inspects the graph
Then `graph_current` is true
And `$jevify --update` returns `already_current`
And no graph artifact is rewritten.

### Code-only update

Given every pending file is structurally extractable code
When `$jevify --update` runs
Then Jevify delegates to Graphify's local code-only update
And all paid-provider variables are removed from the child environment
And `GRAPHIFY_BACKEND=none` is set
And Jevify re-inspects the manifest before reporting success.

### Mixed code and document update

Given at least one pending document, paper, image, or video requires semantic extraction
When `$jevify --update` runs in Claude Code or Codex
Then the installed skill routes that work through the Graphify skill's host-agent extraction flow
And no paid API or ambient provider credential is used
And Jevify resumes automatically after Graphify finishes
And Jevify reports `blocked` rather than `updated` if the semantic pass is incomplete.

### Missing or corrupt graph

Given the graph is missing or cannot be parsed
When `$jevify --update` runs
Then a code-only corpus is built through Graphify locally
And a mixed corpus is routed through Graphify's full host-agent build
And a corrupt graph is preserved until its replacement passes validation
And Jevify performs no silent retry.

### Integrity protection

Given Graphify refuses an unexpected shrink or reports missing or dangling endpoints
When Jevify finalizes the update
Then Jevify returns `blocked`
And the last accepted `graph.json` remains available
And the exact Graphify diagnostic is summarized without claiming success.

### Actionable questions

Given a valid updated graph contains question signals
When Jevify builds the insight bundle
Then it returns three to five diversified questions
And repeated community labels are removed from question text
And low-confidence ambiguous-edge questions cannot outrank source-backed bridge questions
And each question records its type, rationale, and confidence class without inventing node identifiers.

### Query after update

Given the user supplied an explicit question
When the graph is current
Then Jevify runs the existing Graphify-compatible query path
And identifies truncation as incomplete evidence
And points to a narrower path, explanation, or context filter instead of treating the truncated output as a complete answer.

### Memory and JEV boundary

Given reviewed observations exist
When Jevify uses them
Then every memory suggestion retains its source reference and cited source paths
And source files are verified before a conclusion is presented
And invalid or unavailable memory falls back to the Graphify answer.

Given no current approval for paid JEV use
When Jevify runs
Then it makes zero paid calls
And does not read or reuse ambient personal provider credentials.

## Public output contract

Human output must contain, in this order:

1. Update status and pending-file receipt.
2. Graph size and integrity status.
3. God Nodes and surprising connections.
4. Three to five suggested questions.
5. Memory/JEV status and evidence boundary.

JSON output uses schema version 2 and adds `freshness`, `update`, `graph_stats`,
`health`, `god_nodes`, `connections`, and `questions`. The existing `repo`,
`graph`, `question`, `mode`, `live_enrichment`, and `answer` fields remain
available. Update-only invocations use `question: null` and `answer: null`.

## Acceptance evidence

- Unit regression for a same-HEAD manifest drift.
- Unit coverage for missing, corrupt, code-only, mixed, deleted, sensitive,
  incomplete semantic, and shrink-refusal states.
- An offline CleanMyMac reproduction showing zero pending files after update,
  graph counts matching the accepted Graphify graph, and three to five useful
  questions without duplicated labels.
- One code-only and one mixed public fixture proving the two update routes.
- Every updated case has a `GRAPH_REPORT.md` whose node/edge counts match the
  accepted graph; `graph.html` exists without `.graph.html.stale`, unless the
  frozen environment explicitly disables visualization.
- Existing zero-configuration and exact Graphify fallback tests remain green.
- Ruff, focused type checking, security checks, `mac-gate` preflight, GitHub
  checks, and Pages/Preview requirements pass on the same SHA.
- Product demand, preference, repeat use, and willingness to pay are evaluated
  separately by `.specs/tasks/draft/jevify-smoke-validation.feature.md`;
  technical acceptance alone cannot promote Jevify beyond technical beta.

## Non-goals

- Replacing or forking Graphify's structural extraction engine.
- Claiming that Jevify, memory, or JEV is generally faster or better.
- Repeating the stopped paid benchmark or making paid JEV calls.
- Adding a daemon, hosted backend, vector database, OAuth flow, or new runtime dependency.
- Publishing private memory corpora, raw questions, source paths, credentials, or payloads.

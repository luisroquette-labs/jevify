# Jevify operator smoke-test runbook

Status: prepared, not started. Luis can run it in one 15-minute session.

## Setup

- Use one real repository Luis understands, one current graph, and one bounded ungraphed change.
- Freeze the order before results: Graphify, then Jevify.
- Create two private worktrees from the same candidate commit and apply the same bounded diff.
- Confirm equal SHA-256 values for the starting graph, manifest, and diff before either condition.
- Run both commands from their explicit repository roots. A contextual guess of the target fails the smoke.
- Unset provider credentials and do not pass `--decisions`. No paid API, live JEV, source
  collection, identity, or incentive.

## One session — 15 minutes

1. **Condition A — 5 minutes:** from the first warm worktree, run `$graphify --update`, then
   identify the next architectural question worth checking.
2. **Condition B — 5 minutes:** repeat with the untouched second worktree and the other prompt.
3. **Ratings — 5 minutes:** record usefulness `1..5`, preferred next tool, correctness of
   freshness/update claims, and whether Jevify alone surfaced a useful connection verified in
   source. Record whether memory was `graph_only` or `reviewed_memory`; `graph_only` means memory
   value is `not_tested`. The facilitator cannot interpret output before ratings are locked.
4. Create `receipt.json` once with mode `0600` inside a mode-`0700` directory, then validate it:

```bash
mac-gate uv run --frozen python -m tools.jevify_user_validation validate \
  --bundle "$HOME/.local/share/jevify/operator-smoke"
```

Rating anchors: `1 = misleading`, `2 = mostly noise`, `3 = useful with manual work`,
`4 = useful and clear`, `5 = immediately actionable and source-verifiable`.

## Five answers to lock

1. Usefulness of Graphify from `1..5`.
2. Usefulness of Jevify from `1..5`.
3. Which tool you would open first on the next change.
4. Whether Jevify alone surfaced a useful connection that you verified in source.
5. If reviewed memory was connected, whether it added useful prior-session context; otherwise
   record `not_tested`.

Luis only supplies these five answers. The facilitator records route, attribution, comparative
claim status (`not_made`, `supported`, or `unsupported`), run hashes, and
creates the schema-v4 receipt; Luis does not need to edit JSON.

## Decide immediately

```bash
mac-gate uv run --frozen python -m tools.jevify_user_validation validate \
  --bundle "$HOME/.local/share/jevify/operator-smoke"

mac-gate uv run --frozen python -m tools.jevify_user_validation score \
  --bundle "$HOME/.local/share/jevify/operator-smoke" \
  --json benchmarks/jevify-user-validation/scorecard.json \
  --markdown benchmarks/jevify-user-validation/scorecard.md
```

`proceed_to_memory_smoke` means the graph-only flow passed but historical memory remains untested.
`proceed_to_external_validation` additionally requires reviewed memory to be helpful. Mixed cold/warm
runs, wrong target resolution, wrong Graphify/Jevify attribution, an `unsupported` comparative claim,
false freshness/update claims, or paid requests make the smoke invalid.

Reviewed memory tests Jevify's memory-assisted workflow. This smoke does not test whether the JEV
model improves ranking.

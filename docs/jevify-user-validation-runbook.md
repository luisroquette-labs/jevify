# Jevify operator smoke-test runbook

Status: prepared, not started. Luis can run it in one 15-minute session.

## Setup

- Use one real repository Luis understands and one bounded ungraphed change.
- Freeze the order before results: Graphify, then Jevify.
- Create two private worktrees from the same candidate commit and apply the same bounded diff.
- Confirm equal SHA-256 values for the starting graph, manifest, and diff before either condition.
- Unset provider credentials. No paid API, source collection, identity, or incentive.

## One session — 15 minutes

1. **Condition A — 5 minutes:** run the first frozen prompt, `$graphify --update` or
   `$jevify --update`, then identify the next architectural question worth checking.
2. **Condition B — 5 minutes:** repeat with the untouched second worktree and the other prompt.
3. **Ratings — 5 minutes:** record usefulness `1..5`, preferred next tool, correctness of
   freshness/update claims, and whether Jevify alone surfaced a useful connection verified in
   source. The facilitator cannot interpret output before ratings are locked.
4. Create `receipt.json` once with mode `0600` inside a mode-`0700` directory, then validate it:

```bash
mac-gate uv run --frozen python -m tools.jevify_user_validation validate \
  --bundle "$HOME/.local/share/jevify/operator-smoke"
```

Rating anchors: `1 = misleading`, `2 = mostly noise`, `3 = useful with manual work`,
`4 = useful and clear`, `5 = immediately actionable and source-verifiable`.

## Four answers to lock

1. Usefulness of Graphify from `1..5`.
2. Usefulness of Jevify from `1..5`.
3. Which tool you would open first on the next change.
4. Whether Jevify alone surfaced a useful connection that you verified in source.

Luis only supplies these four answers. The facilitator records the run hashes and creates the
schema-v3 receipt; Luis does not need to edit JSON.

## Decide immediately

```bash
mac-gate uv run --frozen python -m tools.jevify_user_validation validate \
  --bundle "$HOME/.local/share/jevify/operator-smoke"

mac-gate uv run --frozen python -m tools.jevify_user_validation score \
  --bundle "$HOME/.local/share/jevify/operator-smoke" \
  --json benchmarks/jevify-user-validation/scorecard.json \
  --markdown benchmarks/jevify-user-validation/scorecard.md
```

`proceed_to_external_validation` requires Jevify preferred, Jevify `>=4/5`, Jevify rated above
Graphify, one Jevify-only source-verified connection, zero false freshness/update claims, and zero
paid requests. A safe miss selects `revise_or_extension`; unsafe evidence selects `invalid_smoke`.

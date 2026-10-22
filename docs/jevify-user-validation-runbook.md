# Jevify five-user validation runbook

Status: prepared, not started. No invitation has been sent.

## Fixed cohort

- Exactly five people who previously used Graphify on a real repository or are actively
  evaluating it with authority to inspect that repository.
- Luis, implementers, and anyone who designed Jevify ranking are ineligible.
- Orders are fixed before results: `p01 GJ`, `p02 JG`, `p03 GJ`, `p04 JG`, `p05 GJ`.
- No payment, incentive, private-source collection, memory export, credential, or paid API.
- A false freshness/update claim, privacy failure, or unequal starting artifact ends the frozen
  round as `insufficient_evidence`.

## Before recruiting

1. Obtain approval for the five recipients and external sends.
2. Create `~/.local/share/jevify/user-validation/` with mode `0700`.
3. Create `manifest.json` once with mode `0600`; never overwrite it.
4. Store only IDs `p01`–`p05`, eligibility category, fixed order, candidate SHA, and session date.
5. Record the manifest SHA-256 publicly; keep the manifest itself outside Git.

Manifest shape:

```json
{
  "schema_version": 1,
  "candidate_commit": "40 lowercase hexadecimal characters",
  "session_date": "YYYY-MM-DD",
  "participants": [
    {"participant_id":"p01","eligibility_evidence":"prior_real_repository_use","tool_order":["graphify","jevify"]},
    {"participant_id":"p02","eligibility_evidence":"active_graphify_evaluation","tool_order":["jevify","graphify"]},
    {"participant_id":"p03","eligibility_evidence":"prior_real_repository_use","tool_order":["graphify","jevify"]},
    {"participant_id":"p04","eligibility_evidence":"prior_real_repository_use","tool_order":["jevify","graphify"]},
    {"participant_id":"p05","eligibility_evidence":"prior_real_repository_use","tool_order":["graphify","jevify"]}
  ]
}
```

Create immutable files with `os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)`.
Never use `write_text()` for private receipts because it can overwrite a locked result.

## Initial session — 25 minutes

1. **Prepare (before timer):** make two private worktrees from the candidate commit. Copy the
   same accepted `graph.json` and `manifest.json` into both, apply the same real bounded diff,
   unset provider credentials, then record separate SHA-256 hashes for each condition's graph,
   manifest, and diff. The evaluator rejects any unequal pair.
2. **Condition A (10 minutes):** run the first frozen prompt exactly: `$graphify --update` or
   `$jevify --update`. The participant identifies the next architectural question worth checking.
3. **Condition B (10 minutes):** repeat in the other untouched worktree with the other fixed
   prompt. Neither condition may consume artifacts written by the first.
4. **Ratings (5 minutes):** lock both usefulness ratings, freshness trust, preferred next tool,
   and whether Jevify alone surfaced a useful connection that was absent from Graphify and was
   then verified in source. The facilitator cannot suggest a question, interpret output, or
   troubleshoot before ratings are locked.
5. **Receipt:** record separate SHA-256 hashes for the Graphify and Jevify run receipts, create
   `pNN/initial.json` once with mode `0600`, then record its SHA-256 in a separate append-only
   event. Validate immediately with the command below. Preserve a failed round unchanged; any
   retest uses a new versioned manifest and directory instead of replacing a participant.

```bash
mac-gate uv run --frozen python -m tools.jevify_user_validation validate-initial \
  --bundle "$HOME/.local/share/jevify/user-validation/pNN"
```

Rating anchors: `1 = unusable or misleading`, `2 = mostly noise`, `3 = useful with manual work`,
`4 = useful and clear`, `5 = immediately actionable and source-verifiable`.

## Seven-day observation

- Send no reuse reminder during `(initial_at, initial_at + 7 days]`.
- Count reuse only from a Jevify run-receipt hash on a different commit inside that window.
- At day seven, create `terminal.json` once with the exact SHA-256 of `initial.json`.
- For no reuse, write `repeat_used=false` and leave repeat timestamp, commit, and hash as `null`.
- Do not contact the participant before locking the terminal record.

## Validate and decide

```bash
mac-gate uv run --frozen python -m tools.jevify_user_validation validate \
  --manifest "$HOME/.local/share/jevify/user-validation/manifest.json"

mac-gate uv run --frozen python -m tools.jevify_user_validation score \
  --manifest "$HOME/.local/share/jevify/user-validation/manifest.json" \
  --json benchmarks/jevify-user-validation/scorecard.json \
  --markdown benchmarks/jevify-user-validation/scorecard.md
```

`validate` stops on the first invalid private bundle. `score` fails closed but still writes an
aggregate `insufficient_evidence` scorecard with anonymous slot IDs and failure counts only.
The scorer selects `continue_product` only with at least 3/5 preference, 3/5 unprompted later-
commit reuse, 2/5 novel source-verified outcomes, zero false claims, and zero paid requests.
Preference or reuse below threshold selects `graphify_extension`; incomplete or unsafe evidence
selects `insufficient_evidence`.

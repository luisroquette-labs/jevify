# Jeviphy v2 benchmark

This benchmark compares Jeviphy with the exact Graphify revision on which it is based. The manifest is immutable after either arm has produced output.

## Freeze order

1. Pin six public repository commits and verify their licenses.
2. Write behavior questions and deterministic oracle commands.
3. Freeze gold files and symbols, then assign one whole repository to holdout.
4. Add reviewed memory evidence without copying gold symbol names into questions or summaries.
5. Validate the manifest, write `MANIFEST.sha256`, and commit both before running either arm.

Changing a repository, case, label, stratum, threshold, or pin creates a new benchmark version. Timed-out and failed cases stay in the denominator. Private transcripts and credentials never belong in this directory.

Run the contract tests with:

```bash
mac-gate uv run --frozen pytest tests/test_jeviphy_eval_contract.py -q
```

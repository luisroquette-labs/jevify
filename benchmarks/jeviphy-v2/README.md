# Jeviphy v2 benchmark

This benchmark compares Jeviphy with the exact Graphify revision on which it is based. The manifest is immutable after either arm has produced output.

## Freeze order

1. Pin the MIT-licensed SWE-bench Multilingual dataset revision and Graphify commit.
2. Select 120 real issue/PR tasks across at least six repositories and three languages.
3. Freeze gold files and official fail-to-pass tests, then assign 20 cases to holdout by salted hash.
4. Add reviewed source-path evidence without copying new solution details into the issue text.
5. Validate the manifest, write `MANIFEST.sha256`, and commit both before running either arm.

Changing a repository, case, label, stratum, threshold, or pin creates a new benchmark version. Timed-out and failed cases stay in the denominator. Private transcripts and credentials never belong in this directory.

## Published result

The frozen candidate completed 600 paired measurements and passed the retrieval gate. Read the [evaluation](../../docs/jeviphy-v2-evaluation.md), inspect the [raw report](results/retrieval-report.json), or follow the [independent reproduction instructions](reproductions/README.md). Product superiority remains blocked by incomplete product-task and external reproduction evidence.

Run the contract tests with:

```bash
mac-gate uv run --frozen pytest tests/test_jeviphy_eval_contract.py -q
```

The network-agent batch uses `tools/jeviphy_product_batch.py`. It requires the three live-execution guardrails from the specification, a project-scoped key in `JEVIPHY_OPENROUTER_API_KEY`, and a private run root containing the frozen arm datasets, manifest, and model configuration. The runner validates both datasets before reading the key, allows only bounded context appended to `problem_statement`, and rejects changes to every other field. Each mini-swe-agent prediction is scored by the official SWE-bench Docker evaluator; a trajectory or submitted patch alone is never success.

Use `--max-new-arms 12` or less for bounded, serial chunks. `--max-agent-calls` and `--max-cost-usd` are totals for the complete candidate run: the append-only journal subtracts prior arms and exact decimal cost before every new paid arm. A missing or malformed cost blocks resume. The runner seals `product-report.json` only after all 240 arms exist, and stops on provider or evaluator infrastructure failure. Keep the output directory private because it contains patches, trajectories, and logs.

Invoke it from the repository root as a module:

```bash
uv run --frozen python -m tools.jeviphy_product_batch \
  --root "$PRIVATE_ROOT" --cases "$PRIVATE_ROOT/isolated/remaining-cases.json" \
  --output-dir "$PRIVATE_OUTPUT" --allow-network-agent \
  --max-agent-calls 186 --max-cost-usd 14.88
```

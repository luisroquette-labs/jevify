# Independent reproduction

Run from a clean clone at candidate `99b944748350f4c341ffb3ae5320df2e38269959`. Dependencies and the six frozen repositories must already be present; the measured run is offline:

```bash
uv sync --frozen
uv run --frozen python -m tools.run_jeviphy_v2_retrieval \
  --manifest benchmarks/jeviphy-v2/manifest.json \
  --project . \
  --workspace ~/.local/share/jeviphy-v2-reproduction \
  --graphify .venv/bin/graphify \
  --passes 5

uv run --frozen python -m tools.jeviphy_product_score \
  ~/.local/share/jeviphy-v2-reproduction/retrieval-report.json \
  --output /tmp/jeviphy-scorecard.json \
  --markdown /tmp/jeviphy-scorecard.md
```

Expected manifest SHA-256: `ce54fe1c5c531d10947ea363a05cbb0ed6dcd0336324752b03276306713584ac`. Expected published result SHA-256: `d30e91c17877764c323542672502b3b93021fbdfa01865f3c767793e62fbb82e`. Confirm your reproduced report has the same hash before creating a receipt.

Generate the canonical receipt:

```bash
uv run --frozen python -m tools.jeviphy_reproduction \
  --reviewer YOUR_GITHUB_HANDLE \
  --os "Ubuntu 24.04" \
  --machine "4 vCPU, 16 GB RAM" \
  --manifest benchmarks/jeviphy-v2/manifest.json \
  --result ~/.local/share/jeviphy-v2-reproduction/retrieval-report.json \
  --output YOUR_GITHUB_HANDLE-ubuntu.json
```

Submit one JSON receipt in this directory:

```json
{
  "schema_version": 1,
  "reviewer": "github-handle",
  "independent": true,
  "os": "Ubuntu 24.04",
  "machine": "CPU and RAM",
  "manifest_sha256": "ce54fe1c5c531d10947ea363a05cbb0ed6dcd0336324752b03276306713584ac",
  "graphify_commit": "4342e67107f77db54098d7873b563ff20830dcb8",
  "jeviphy_commit": "99b944748350f4c341ffb3ae5320df2e38269959",
  "result_sha256": "SHA-256 of retrieval-report.json",
  "scorecard": {
    "retrieval": "pass"
  },
  "payload_sha256": "SHA-256 of canonical payload without this field"
}
```

Open a pull request containing only the receipt. The payload hash detects edits; the GitHub identity on the pull request establishes who submitted it. The public product claim stays blocked until two people who did not author the retrieval changes reproduce the result, including one Linux run.

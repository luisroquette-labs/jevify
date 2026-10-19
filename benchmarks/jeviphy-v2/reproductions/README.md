# Independent reproduction

Run the commands in [`docs/jeviphy-v2-evaluation.md`](../../../docs/jeviphy-v2-evaluation.md) from a clean clone. Do not change the manifest, evaluator, Graphify pin, or Jeviphy candidate before the run.

Submit one JSON receipt in this directory:

```json
{
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
  }
}
```

The public product claim stays blocked until two people who did not author the retrieval changes reproduce the result, including one Linux run.

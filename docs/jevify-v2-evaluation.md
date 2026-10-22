# Jevify v2 evaluation

> Jevify improved source-backed retrieval on the frozen v2 benchmark.

## Decision

The offline retrieval gate passed. Jevify remains an optional source-aware Graphify adapter because product-task, complete usability, and independent reproduction evidence is still incomplete. This result does not establish better coding-task success or a universal advantage over Graphify.

## Frozen result

| Measure | Graphify | Jevify |
| --- | ---: | ---: |
| Valid-source precision@5 | 4.0% | 24.5% |
| Valid-source first hits | 4/40 | 40/40 |
| Valid-source median query time | 337.85 ms | 51.98 ms |
| Valid-source p95 query time | 4,170.41 ms | 170.47 ms |
| Stale-source losses | — | 0/20 |
| No-source byte equality | — | 40/40 |

The paired precision@5 improvement was 20.5 percentage points with a 95% bootstrap interval of 16.5 to 25.5 points. The 20-case salted holdout also passed: precision@5 was 5.7% for Graphify and 25.7% for Jevify, with a 95% interval for the improvement of 11.4 to 28.6 points.

## Method and artifacts

- 120 public SWE-bench Multilingual tasks from 38 repositories and 9 languages: 40 valid-source, 20 stale-source, 40 no-source, and 20 ambiguous cases.
- One warm-up plus five measured paired passes per case, for 600 pairs. Arm order alternated by case and pass.
- Both arms used Graphify commit `4342e67107f77db54098d7873b563ff20830dcb8`; Jevify candidate `99b944748350f4c341ffb3ae5320df2e38269959`; Python 3.13.12.
- Manifest SHA-256: `ce54fe1c5c531d10947ea363a05cbb0ed6dcd0336324752b03276306713584ac`.
- Sanitized raw report SHA-256: `d30e91c17877764c323542672502b3b93021fbdfa01865f3c767793e62fbb82e`.
- The [raw report](../benchmarks/jevify-v2/results/retrieval-report.json), [mechanical scorecard](../benchmarks/jevify-v2/results/scorecard.json), frozen [manifest](../benchmarks/jevify-v2/manifest.json), and [reproduction instructions](../benchmarks/jevify-v2/reproductions/README.md) are public.

## Limits and negative findings

- Source paths are product inputs and may identify the correct file; the test measures retrieval from reviewed provenance, not discovery without provenance.
- The final stale-evidence rule was selected after four training cases with test-only paths lost to Graphify. No holdout output was inspected before that candidate was frozen, but this is still a dataset-shaped heuristic and needs external reproduction.
- This benchmark scores gold-file retrieval. It does not execute agent-written patches, compare answer quality, or prove lower end-to-end token use.
- The product, full two-OS usability, and external reproduction gates remain `insufficient_evidence`. The scorer therefore blocks the product-superiority claim.
- A separate 19-call paid Jev pilot produced no top-five gain and added network latency. Jev remains optional and outside this result.

## Reproduce

```bash
uv run --frozen python -m tools.run_jevify_v2_retrieval \
  --manifest benchmarks/jevify-v2/manifest.json \
  --project . \
  --workspace ~/.local/share/jevify-v2-benchmark \
  --graphify .venv/bin/graphify \
  --passes 5

uv run --frozen python -m tools.jevify_product_score \
  ~/.local/share/jevify-v2-benchmark/retrieval-report.json \
  --output scorecard.json \
  --markdown scorecard.md
```

The scorer exits non-zero until every product release gate passes. A retrieval-only result with the claim above is therefore expected to exit `1`.

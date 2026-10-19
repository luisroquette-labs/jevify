# Jeviphy independent complete-workflow comparison

## Claim supported

On the frozen synthetic Click code-review cohort described below, Jeviphy's local source-cited workflow retrieved more exact target nodes and completed faster than the matching unscoped Graphify workflow. The result supports this workflow and cohort class only.

## Independent confirmation

- Source: Click commit `2247b35ea1c47c727d7a06e51fa280e12a863ff6`
- Runner: Jeviphy commit `8c44768d8ea08ce641f2d7e2472f77881e7b2311`
- Frozen manifest SHA-256: `e72fe6dda95c32b7a40aa38cc42063f14918813c8116eb7b73755cc9528111d4`
- Graph SHA-256: `b28000e0ab157ce1d991cf0a600477293a97988eb62221c0301839d7b36c1154`
- Private report SHA-256: `c56ce1d0a081f2cbb6e7af573ae02bacc121d402ba48952079fc91387e4e92b3`

The manifest was frozen before candidate output. It contains 40 source-cited questions across 15 Click modules and 20 controls without source provenance. Gold function names do not occur in the questions or summaries. Both arms used the same AST graph, clean source commit, Python 3.13.12 process, Apple arm64 machine, case order, and alternating execution order. Five passes produced 300 paired complete-query timings.

| Metric | Graphify | Jeviphy |
|---|---:|---:|
| Exact source gold nodes in top five | 2/40 | 11/40 |
| First-pass source answer hits | 22/40 | 32/40 |
| Overall p50 | 183.92 ms | 79.63 ms |
| Overall p95 | 275.69 ms | 212.95 ms |
| Source p50 | 189.02 ms | 65.37 ms |
| Source p95 | 294.29 ms | 158.29 ms |

Jeviphy had zero source retrieval losses, zero first-pass answer losses, and 198/200 faster source pairs. All control answers were byte-identical. The 10,000-resample 95% interval for p95 advantage was 23.51–119.46 ms overall and 75.09–218.64 ms for source-backed cases. Both lower bounds are above zero.

## Development run disclosed

An earlier frozen cohort used Graphify's own source at `1615fca4`. Jeviphy was faster in all 200 source pairs and improved first-pass answer hits from 23/40 to 40/40, but had one top-five retrieval loss despite increasing source hits from 9/40 to 32/40. That failed the predeclared zero-loss gate and became development data. Its report SHA-256 is `fb09f6050664a4f2c9514ee559cee7e23d03a28cd599949bde6dc513a272f372`.

The observed loss showed that a path-heavy memory summary could displace the question's strongest source-scoped match. Jeviphy now reserves one slot for that question-only winner. The untouched Click cohort was frozen before running this correction and supplied the independent confirmation above.

## Limits

Questions and labels are synthetic. The timing includes graph loading, source validation, candidate scoring, and graph traversal; it excludes Claude Mem lookup and paid Jev. The paid Jev ranking pilot failed separately, so Jev is not part of the performance claim. These results do not prove faster performance for no-source questions, every repository, real-user tasks, or end-to-end agent productivity. Raw manifests, questions, answers, and timing rows remain private with mode `0600`.

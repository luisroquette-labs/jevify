# Jeviphy zero-configuration evaluation — 19 October 2026

**Result: PASS at runner commit `61af39b8`.** Bare Jeviphy met the predeclared zero-configuration parity gate. This is runner-level evidence, not a claim that Jeviphy is generally better than Graphify.

## Frozen result

| Gate | Result |
| --- | ---: |
| Frozen cases / public repositories | 30 / 6 |
| Runs requesting interaction | 0 |
| Exact Graphify-compatible outputs | 24 / 24 |
| Measured paired runs | 90 |
| Median overhead | 9.40% (limit 10%) |
| p95 overhead | 5.44% (limit 15%) |
| Failed expected outcomes | 0 |

The cohort covers ready and nested worktrees, explicit and automatically selected questions, missing live credentials, invalid corpus, missing/stale/corrupt graph repair, forced repair failure, and invocation outside Git. Every process ran with closed stdin. Default and repair cases had network sockets disabled and provider variables removed.

## Reproducibility pins

- Candidate runner: `61af39b8` (portable core: `355773375977c8339181d30a512b334cbd67ba96`).
- Manifest SHA-256: `015963128a3174186416ee124e18599908f1e048f5570d06b2b436dd4975c6db`.
- Private append-only journal SHA-256: `90900cc7051ea0a04ec3e48b001dbe7e660969ba0bc575c3eb4f0afec4b9d1b8`; raw questions, outputs, and paths remain outside Git with private permissions.
- Aggregate score SHA-256: `bc61dab909704130bb408e8cdd6101ddae27fb13047b2bac832a2154d3a35ac9`.
- Five measured pairs per timing case, one warm-up, alternating arm order, identical question in both arms.

## What this demonstrates

A bare invocation can resolve the containing Git repository, choose a question, repair the graph once, and return Graphify-compatible output without asking for setup or reading a provider key. The measured wrapper cost stayed inside the declared 10% median and 15% p95 limits. Jeviphy was still slower than direct Graphify in these aggregate ratios, so this result supports usability parity rather than a speed-superiority claim.

## Separate product benchmark

The earlier frozen product-task run remains separate: Jeviphy candidate `99b944748350f4c341ffb3ae5320df2e38269959`, 186 arm rows / 93 pairs, 184 zero-exit wrapper processes, two timeouts, and no recorded trajectories. Post-run inspection found `ImageBuildError` in all 184 zero-exit arms because Modal had reached its billing-cycle spend limit. The old wrapper misclassified those internal failures as completed. This run contains no product evidence, is not pooled with the runner result above, and must not be used for speed or quality claims.

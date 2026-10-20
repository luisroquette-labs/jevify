# Jeviphy zero-configuration evaluation — 20 October 2026

**Result: PASS at candidate `5f27a320b1768b577df456fdbb4d8ae43a3af759`.** Bare Jeviphy met the predeclared zero-configuration parity gate after the installer cache fix. This is runner-level evidence, not a claim that Jeviphy is generally better than Graphify.

## Frozen result

| Gate | Result |
| --- | ---: |
| Frozen cases / public repositories | 30 / 6 |
| Runs requesting interaction | 0 |
| Exact Graphify-compatible outputs | 24 / 24 |
| Measured paired runs | 90 |
| Median overhead | 4.58% (limit 10%) |
| p95 overhead | 6.86% (limit 15%) |
| Failed expected outcomes | 0 |

The cohort covers ready and nested worktrees, explicit and automatically selected questions, missing live credentials, invalid corpus, missing/stale/corrupt graph repair, forced repair failure, and invocation outside Git. Every process ran with closed stdin. Default and repair cases had network sockets disabled and provider variables removed.

## Reproducibility pins

- Candidate: `5f27a320b1768b577df456fdbb4d8ae43a3af759`.
- Manifest SHA-256: `015963128a3174186416ee124e18599908f1e048f5570d06b2b436dd4975c6db`.
- Private append-only journal SHA-256: `9c35773ab63e45e8ffcacd8f4398b52397f3d88e8d473ebc2a539cd28e815286`; raw questions, outputs, and paths remain outside Git with private permissions.
- Source score SHA-256: `4e44d8277840ba9140832f89eefba549013e165af223b5f515082e86f517967c`.
- Public aggregate: `benchmarks/jeviphy-zero-config/results/score.json`.
- Five measured pairs per timing case, one warm-up, alternating arm order, identical question in both arms.

## What this demonstrates

A bare invocation can resolve the containing Git repository, choose a question, repair the graph once, and return Graphify-compatible output without asking for setup or reading a provider key. The measured wrapper cost stayed inside the declared 10% median and 15% p95 limits. This result supports usability parity rather than a product speed claim.

## Separate product benchmark

The earlier frozen product-task run remains separate: Jeviphy candidate `99b944748350f4c341ffb3ae5320df2e38269959`, 186 arm rows / 93 pairs, 184 zero-exit wrapper processes, two timeouts, and no recorded trajectories. Post-run inspection found `ImageBuildError` in all 184 zero-exit arms because Modal had reached its billing-cycle spend limit. The old wrapper misclassified those internal failures as completed. This run contains no product evidence, is not pooled with the runner result above, and must not be used for speed or quality claims.

## Release-candidate install evidence

The frozen matrix is `benchmarks/jeviphy-v2/install-matrix.json`: five clean-home attempts for Claude and five for Codex on each of Ubuntu and macOS. Every attempt installs, runs `doctor`, makes one offline query, reinstalls, and performs receipt-safe uninstall with provider keys removed and stdin closed. Ubuntu runs in the task Codespace. macOS runs only for a `jeviphy-rc-*` tag through `.github/workflows/jeviphy-rc-evidence.yml`. The two journals must name the same candidate SHA before aggregation.

The aggregate above was regenerated from a fresh 30-case remote run on the named candidate. Any later change to the installed runner, portable core, installer, or Graphify query path requires another fresh run; historical numbers are never silently relabeled as current evidence.

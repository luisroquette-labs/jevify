# Jevify zero-configuration evaluation — 20 October 2026

**Result: PASS at candidate `635d30c1ab8582b005225fad62b146abca8cbebd`.** Bare Jevify met the predeclared zero-configuration parity gate after the installer cache fix. This is runner-level evidence, not a claim that Jevify is generally better than Graphify.

## Frozen result

| Gate | Result |
| --- | ---: |
| Frozen cases / public repositories | 30 / 6 |
| Runs requesting interaction | 0 |
| Exact Graphify-compatible outputs | 24 / 24 |
| Measured paired runs | 90 |
| Median matched-pair overhead | 4.56% (limit 10%) |
| p95 matched-pair overhead | 9.26% (limit 15%) |
| Failed expected outcomes | 0 |

The cohort covers ready and nested worktrees, explicit and automatically selected questions, missing live credentials, invalid corpus, missing/stale/corrupt graph repair, forced repair failure, and invocation outside Git. Every process ran with closed stdin. Default and repair cases had network sockets disabled and provider variables removed.

## Reproducibility pins

- Candidate: `635d30c1ab8582b005225fad62b146abca8cbebd`.
- Manifest SHA-256: `015963128a3174186416ee124e18599908f1e048f5570d06b2b436dd4975c6db`.
- Private append-only journal SHA-256: `cfc18976b261e6b074dd7a51a43df977c260036451386f9f5b1c77f0b5c5f086`; raw questions, outputs, and paths remain outside Git with private permissions.
- Source score SHA-256: `b9eb8e1e3ea195089d4eb1a45c32635a2bb700e837ab199401c2bbf97785e357`.
- Public aggregate: `benchmarks/jevify-zero-config/results/score.json`.
- Five measured pairs per timing case, one warm-up, alternating arm order, identical question in both arms. Median and p95 are calculated from within-pair relative overheads so repositories with different absolute runtimes cannot distort the comparison.

## What this demonstrates

A bare invocation can resolve the containing Git repository, choose a question, repair the graph once, and return Graphify-compatible output without asking for setup or reading a provider key. The measured wrapper cost stayed inside the declared 10% median and 15% p95 limits. This result supports usability parity rather than a product speed claim.

## Separate product benchmark

The earlier frozen product-task run remains separate: Jevify candidate `99b944748350f4c341ffb3ae5320df2e38269959`, 186 arm rows / 93 pairs, 184 zero-exit wrapper processes, two timeouts, and no recorded trajectories. Post-run inspection found `ImageBuildError` in all 184 zero-exit arms because Modal had reached its billing-cycle spend limit. The old wrapper misclassified those internal failures as completed. This run contains no product evidence, is not pooled with the runner result above, and must not be used for speed or quality claims.

## Release-candidate install evidence

The frozen matrix is `benchmarks/jevify-v2/install-matrix.json`: five clean-home attempts for Claude and five for Codex on each of Ubuntu and macOS. Every attempt installs, runs `doctor`, makes one offline query, reinstalls, and performs receipt-safe uninstall with provider keys removed and stdin closed. Ubuntu runs in the task Codespace. macOS runs only for a `jevify-rc-*` tag through `.github/workflows/jevify-rc-evidence.yml`. The two journals must name the same candidate SHA before aggregation.

The candidate passed all 10 Ubuntu attempts: 5/5 Claude Code and 5/5 Codex, with median end-to-end attempt time of 0.804 seconds. The private Ubuntu journal SHA-256 is `83a72f1e05fa9a509d841a5849bff71462957d151dc371e801eaea05625d58a7`. This is half of the release-candidate matrix; the macOS half remains pending and no combined install pass is claimed.

The aggregate above was regenerated from a fresh 30-case remote run on the named candidate. Any later change to the installed runner, portable core, installer, or Graphify query path requires another fresh run; historical numbers are never silently relabeled as current evidence.

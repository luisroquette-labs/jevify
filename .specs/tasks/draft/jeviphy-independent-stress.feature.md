---
title: Gate Jeviphy claims on an independent paired stress test
---

## Status

Stage 2 of the five-stage roadmap. The private SWEN cohort was frozen before either arm was measured. The offline candidate test completed and the advancement gate failed; [report](../../../docs/jeviphy-independent-stress-20261018.md). Jev reranking and answer quality remain untested.

## Question

On a repository not used to design the source-aware rule, does Jeviphy improve useful candidate retrieval **and** finish faster than Graphify question-only retrieval under the same graph, source commit, hardware, and query set?

## Frozen design

- Pin the SWEN graph and clean source checkout to the same commit. Verify graph integrity and preserve their SHA-256 hashes.
- Use 30 preselected, nonredacted claude-mem observations: 20 with cited implementation files in the graph and 10 controls without a cited implementation file. Keep case text, paths, and per-case results outside Git in a mode-0700 directory. These cases have no semantic relevance labels.
- Query each case with its observation title. Baseline is `candidate_pool(..., question)`; assisted is `candidate_pool(..., question, [summary], source_paths=reviewed_paths)`. Both call the same Graphify scorer on the same graph. No external API call.
- Compare exact top-five candidate IDs, top-ten overlap with cited implementation files, and paired wall time. Source overlap is a provenance proxy, **not** semantic relevance or answer quality. A negative control with no cited file is unscored for overlap.
- Warm up both arms, alternate order, and run at least three full 30-case passes. Report median and p95 per arm, paired ratios, process peak RSS, exceptions, and run environment. Preserve raw results privately and publish only aggregate measurements and the protocol.

## Advancement gate

Proceed to paid Jev and later sales work only if an independent, source-reviewed 30-case set shows higher held-out semantic precision@5 without new unsupported suggestions **and** the complete Jeviphy workflow has lower paired median and p95 wall time than original Graphify. The offline candidate stress test may reject advancement; source-file overlap alone cannot pass the quality gate. No performance claim follows from a synthetic or same-cohort result.

## Acceptance

1. A frozen manifest identifies the exact graph, source commit, observation IDs, and selection rule before candidate outputs are seen.
2. A repeatable local runner verifies pinning, executes both arms with balanced order, and writes raw data only to private storage.
3. Its small synthetic test catches top-five divergence, metric arithmetic errors, and invalid graph/source pinning.
4. The published report includes denominators, timing distribution, run count, failures, measurement limits, and an explicit pass/fail decision.

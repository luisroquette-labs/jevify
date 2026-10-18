---
title: Test a single scoped scoring pass for source-backed memory retrieval
---

## Status

Implemented as an opt-in experiment after the [negative SWEN stress result](../../../docs/jeviphy-independent-stress-20261018.md). The earlier 30 cases became development data. Two later frozen cohorts were tested; the [cross-repository result](../../../docs/jeviphy-fast-source-stress-20261018.md) failed the pooled p95 gate, so rollout and sales remain paused.

## Problem

Memory mode currently scores the whole graph once for the question and again for memory text, then preserves the first seven or eight question nodes. The independent SWEN test found more cited-file nodes in the top ten but identical top five on all source-backed cases and higher latency.

## Hypothesis and contract

- For an observation with reviewed, tracked source paths represented in a graph pinned to a clean source commit, score only graph nodes in those files. Use the question and bounded memory summary to order at most ten local nodes; permit source-backed nodes to enter the top five.
- Keep the existing question mode unchanged. If source paths are absent or no graph nodes score in them, skip candidate generation and run the original unseeded Graphify answer. Never treat an untracked, stale, or modified source file as trusted provenance.
- Use one scoped scoring pass for source-backed cases, then pass its top three nodes to Graphify's existing seeded traversal without a second graph load. With missing or invalid Jev decisions, keep the original unseeded fallback; in explicit `fast-source` mode with no decisions, use only validated source seeds. Preserve the exact private payload/paid-use gate.
- Record when fewer than ten source-backed nodes exist rather than inventing candidates. Avoid new dependencies, network calls, and automatic paid model use.

## SDD checkpoints

1. **Plan:** verify that scoped Graphify scoring can run without reusing whole-graph caches; estimate graph-load and scoring costs on the prior SWEN development cohort.
2. **Review:** inspect every caller, portable skill copy, tests, and disclosure points before changing code. Reject the design if the development cohort cannot plausibly beat question mode on top-five retrieval and paired p50/p95 complete-workflow latency.
3. **Execute:** implement the smallest optional source-backed path and matching portable skill behavior, leaving defaults intact.
4. **Test:** synthetic tests for source pinning, subgraph cache isolation, ten-node cap, default/fallback parity, and private payload behavior; then repeat paired stress with balanced order.
5. **Validate:** freeze at least 30 previously unused questions with source-reviewed semantic gold IDs before viewing assisted candidates. A victory requires held-out semantic precision@5 improvement without unsupported suggestions and lower paired p50/p95 **complete workflow** latency. An offline source-file proxy or reused development cases cannot pass.

## Stop rule

If the scoped path is not faster in a representative offline development test, do not ship it. If it passes offline but fails the fresh semantic/end-to-end gate, publish the negative result and keep stages 3–5 paused. Reusing a failed holdout to tune another variant requires another untouched cohort.

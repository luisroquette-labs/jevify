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
- For offline `fast-source` cases with no cited source paths and no decision or payload request, validate the corpus record and delegate the query directly to Graphify before loading the graph in Jeviphy. Preserve the exact Graphify answer and avoid writing a Jev sidecar for a query that did not use memory.
- Record when fewer than ten source-backed nodes exist rather than inventing candidates. Avoid new dependencies, network calls, and automatic paid model use.

## SDD checkpoints

1. **Plan:** verify that scoped Graphify scoring can run without reusing whole-graph caches; estimate graph-load and scoring costs on the prior SWEN development cohort.
2. **Review:** inspect every caller, portable skill copy, tests, and disclosure points before changing code. Reject the design if the development cohort cannot plausibly beat question mode on top-five retrieval and paired p50/p95 complete-workflow latency.
3. **Execute:** implement the smallest optional source-backed path and matching portable skill behavior, leaving defaults intact.
4. **Test:** synthetic tests for source pinning, subgraph cache isolation, ten-node cap, default/fallback parity, and private payload behavior; then repeat paired stress with balanced order.
5. **Validate:** freeze at least 30 previously unused questions with source-reviewed semantic gold IDs before viewing assisted candidates. A victory requires held-out semantic precision@5 improvement without unsupported suggestions and lower paired p50/p95 **complete workflow** latency. An offline source-file proxy or reused development cases cannot pass.

## Stop rule

If the scoped path is not faster in a representative offline development test, do not ship it. If it passes offline but fails the fresh semantic/end-to-end gate, publish the negative result and keep stages 3–5 paused. Reusing a failed holdout to tune another variant requires another untouched cohort.

## Conditional activation follow-up (predeclared before COESA outcomes)

The original pooled p95 gate failed and remains a recorded negative result. A no-source query now delegates directly to Graphify. The product can therefore make only a **conditional** speed claim, if this new gate passes on untouched COESA cases:

- Freeze 20 source-backed and ten no-source questions with exact gold node IDs before running either arm. Use the same pinned AST graph, checkout, and 3 balanced passes (90 pairs) for both arms.
- On source-backed cases, require higher precision@5, no first-pass gold answer loss, lower p50 and p95 complete-query wall time, and a case-level bootstrap 95% interval for the p95 advantage strictly above zero.
- On no-source controls, require byte-identical Graphify answers. Report pooled p50/p95 without treating a favorable pooled point estimate as proof of a universal speed advantage.
- This gate tests local source-aware retrieval only. It cannot validate Jev model decisions, real Claude Mem selection, or end-to-end agent work. Keep paid Jev, sales, and outreach gated separately.

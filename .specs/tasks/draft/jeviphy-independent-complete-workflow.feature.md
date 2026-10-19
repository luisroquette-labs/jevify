---
title: Independently validate the local source-cited Jeviphy workflow
status: passed
---

# Stage 4: independent complete-workflow comparison

## Plan

Use the untouched `origin/jeviphy` source commit as a fourth repository, outside the CF Gauss, SWEN, and COESA design cohorts. Build one AST-only graph from a clean detached checkout. Before running either retrieval arm, freeze 60 synthetic code-review questions: 40 with one reviewed source path and exact gold node ID, plus 20 no-source controls. Questions and summaries must describe behavior without containing the gold node label or function name. A source summary may identify the reviewed file path because source provenance is the feature under test.

Run Graphify and local `fast-source` against the same graph, checkout, Python environment, question order, and process path. Warm both arms once, alternate order per pair, and collect five passes: 300 paired complete-query timings. The local Jeviphy arm includes graph loading, source validation, candidate scoring, and graph traversal. It excludes Claude Mem retrieval and paid Jev because the product cannot claim those unmeasured costs as local retrieval performance.

## Review

- Freeze the source commit, graph hash, manifest hash, questions, summaries, paths, and gold IDs before inspecting candidate or answer output.
- Do not change the implementation or cohort after the first run. Harness defects may be fixed only with disclosure; the repaired cohort then counts as development data and requires a new independent cohort for confirmation.
- The same source file is evidence of provenance, not correctness. Success requires exact gold-node retrieval and first-pass answer inclusion.
- Keep raw questions, summaries, answers, timing rows, and graph copies private outside Git with mode 0700 directories and 0600 files.

## Execute

Use the versioned full-stress runner without paid calls. Record the source, graph, manifest, runner commit, platform, Python version, and all paired measurements. Preserve control answers byte for byte.

## Test and validation

Stage 4 passes only if all conditions hold on this first frozen run:

1. Jeviphy has higher precision@5 across all 60 cases and more source-case top-five gold hits, with zero source-case losses.
2. Jeviphy loses no first-pass gold answer hit, and all no-source controls are byte-identical to Graphify.
3. Jeviphy has lower p50 and p95 for both all cases and source-backed cases.
4. The case-level 10,000-resample 95% interval for both pooled and source-backed p95 advantage is strictly above zero.
5. At least 190/200 source-backed paired runs are faster, limiting success from a few extreme outliers.

Passing supports only local source-cited retrieval on synthetic code-review cases. It does not prove paid Jev benefit, real Claude Mem benefit, or end-to-end agent productivity.

## Result

The first frozen Graphify-repository cohort improved every speed and answer metric, but failed the zero-loss retrieval gate: 32/40 source gold nodes reached the top five versus 9/40 for Graphify, with one loss. That cohort became development data. The correction reserves one source-scoped slot for the question-only winner so path-heavy memory cannot displace it.

The next frozen cohort used the untouched Click repository at `2247b35e`, with 40 source cases across 15 modules and 20 no-source controls. It passed every declared gate on its first candidate run: 11/40 versus 2/40 source top-five hits, zero source losses, 32/40 versus 22/40 first-pass answer hits, 198/200 faster source pairs, and byte-identical controls. Overall p50/p95 were 79.63/212.95 ms versus 183.92/275.69 ms. Source p50/p95 were 65.37/158.29 ms versus 189.02/294.29 ms. The pooled p95 advantage interval was 23.51–119.46 ms and the source interval was 75.09–218.64 ms.

The result validates the narrow local source-cited claim on synthetic code-review questions. It does not validate paid Jev, Claude Mem lookup time, real-user productivity, or all repositories.

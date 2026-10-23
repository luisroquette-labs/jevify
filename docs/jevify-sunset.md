# Jevify closure record

**Status:** product shelved  
**Decision date:** 2026-10-22  
**Maintenance:** ended; repository preserved read-only after this record

Jevify was tested as an orchestration and memory-assisted layer on top of Graphify. The experiment
is complete. The project is preserved for technical reference, but it is not an active beta,
supported product, or planned launch.

## Why it was shelved

1. Graphify produced the strongest structural discoveries and remained the source of graph truth.
2. Jevify added useful safeguards and orchestration, but not enough differentiated value for a
   separate product.
3. The bounded live JEV pilot did not improve top-five retrieval and added network latency.
4. Graph-only operator tests preferred Graphify; reviewed-memory value was not established.
5. Integrity checks did not by themselves prove extractor coverage, as shown by omitted SQL files
   when the required parser extra was absent.

## Evidence boundary

- Verified historical results remain: 20/20 clean installations, 30/30 zero-configuration cases,
  compatibility receipts, bounded offline update cases, and the local test suites recorded in the
  evidence package.
- The 60-arm product benchmark ended with 0/60 valid final arms.
- Eight earlier comparison pairs remain diagnostic only.
- No claim that Jevify is better, faster, or more efficient than Graphify is supported.
- The experiment did not prove that JEV adds useful ranking or memory value to this workflow.

## Preserved artifacts

- Source, history, tests, specifications, scorecards, and evaluation documents remain in Git.
- The final repository graph is attached to the
  [`jevify-shelved-2026-10-22`](https://github.com/luisroquette-labs/jevify/releases/tag/jevify-shelved-2026-10-22)
  release as `graph.json`, `graph.html`, and `GRAPH_REPORT.md`.
- Private operator receipts remain local and are not published.

## Reactivation condition

Reconsider the project only with independent evidence that reviewed memory or JEV produces a
source-verified result that Graphify alone does not, repeatedly enough to justify the additional
complexity. Until then, use Graphify directly.

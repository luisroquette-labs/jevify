<!-- jeviphy-outreach:claude-mem-source-paths-v1 -->

We built a small experimental bridge between reviewed memory and Graphify: memory-provided source paths narrow the graph query before Claude Code or Codex receives the result.

On a frozen synthetic Click cohort with 40 source-cited questions, this workflow performed better on the measured retrieval and latency points: 11/40 exact targets in the top five versus 2/40 for the matching unscoped Graphify workflow, with overall p95 of 212.95 ms versus 275.69 ms.

We see this as a promising result for this cohort, not evidence that Jeviphy is universally better. The questions and labels were synthetic, Claude Mem lookup time was excluded, and the separate paid-Jev ranking attempt did not help.

We would value your critique of a small optional interoperability contract:

1. Can an observation expose stable `source_paths` without coupling Claude Mem to a graph implementation?
2. How should renamed or stale paths be represented?
3. What should be redacted before paths leave the local memory boundary?

The experiment and its limitations are public: https://luisroquette-labs.github.io/jeviphy/

Reproducible report: https://github.com/luisroquette-labs/jeviphy/blob/jeviphy/docs/jeviphy-independent-complete-workflow-20261018.md

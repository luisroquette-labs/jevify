<!-- jevify-outreach:graphify-evidence-v1 -->

Small evidence update, shared as an experiment rather than a general comparison.

On a frozen synthetic Click cohort with 40 source-cited questions, the Jevify source-seeded workflow performed better on the points we measured: 11/40 exact targets in the top five versus 2/40 with the matching unscoped Graphify workflow. Overall p95 was 212.95 ms versus 275.69 ms. Both arms used the same AST graph, source commit, questions, machine, and alternating execution order.

This result is limited to that cohort. It does not show that Jevify is generally better, and the separate paid-Jev ranking pilot did not improve retrieval. The promising part appears to be the bounded source citations coming from reviewed memory.

Would a small upstream query interface for bounded source-cited seeds make sense in Graphify, or would you prefer this to remain an adapter maintained by Jevify? We are happy to reshape the draft around the boundary you consider useful.

- Demo and orientation: https://luisroquette-labs.github.io/jevify/
- Reproducible report: https://github.com/luisroquette-labs/jevify/blob/jevify/docs/jevify-independent-complete-workflow-20261018.md

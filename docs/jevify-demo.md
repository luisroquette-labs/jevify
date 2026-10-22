# Jevify: 60-second offline demo

From the repository root, with dependencies installed:

```sh
uv run --frozen python -m tools.jevify_demo
```

The command creates a tiny temporary Python repository, extracts its code graph,
and runs the same question with Graphify's ranking and a complete **synthetic**
offline decision. It prints the changed rank, a node-to-observation citation,
and confirmation that the graph bytes did not change. The temporary data is
removed when the command ends. No API key or network model call is used.

Expected output:

```text
Graphify baseline: auth_validate_token at rank 3
Synthetic offline decision: auth_validate_token at rank 1
Evidence: auth_validate_token at auth.py:L3 ↔ synthetic-001
Graph unchanged; Jev API calls: 0
```

This is an integration demonstration, **not** evidence that Jev improves
retrieval on real memory. The real evaluation protocol and its current status
are in [the evaluation record](jev-memory-pilot-evaluation.md).

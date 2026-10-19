# Jeviphy participant brief

## What it is

Jeviphy is an open-source Graphify fork and skill for Claude Code and Codex. Graphify builds and queries the code graph. Jeviphy adds an optional local step: reviewed memory can name source files, and those paths can narrow where the graph query begins.

The practical idea is simple: if a reviewed observation already cites the implementation files behind a past decision, the coding agent should inspect those files early instead of searching the entire graph with equal weight.

## What changed

The measured `fast-source` mode:

1. validates the graph against the repository commit;
2. checks reviewed `source_paths` against the working tree;
3. scores nodes only inside those files;
4. uses the best three nodes as Graphify traversal seeds; and
5. delegates to the original Graphify query when the hints are missing or unusable.

Jeviphy does not add memory assertions to the structural graph. The final agent answer still needs source inspection, and runtime claims still need runtime evidence.

## What the tests showed

The strongest result comes from a frozen synthetic Click cohort: 40 source-cited questions across 15 modules, plus 20 controls. Both arms used the same AST graph, code commit, questions, hardware, case order, and alternating execution order.

| Measure | Graphify | Jeviphy `fast-source` |
| --- | ---: | ---: |
| Exact target nodes in top five | 2/40 | **11/40** |
| First-pass source answer hits | 22/40 | **32/40** |
| Overall p50 | 183.92 ms | **79.63 ms** |
| Overall p95 | 275.69 ms | **212.95 ms** |

Jeviphy had no source retrieval loss in that cohort, was faster in 198/200 paired source runs, and returned byte-identical control answers. This supports a narrow conclusion: the source-cited workflow performed better on the measured points in this experiment.

It does not establish a universal advantage. Questions and labels were synthetic, Claude Mem lookup was excluded from timing, and no end-to-end developer productivity study has run.

## What did not work

The separate paid Jev reranking pilot did not improve top-five retrieval: both arms stayed at 4/19. It also added 649.74 ms p50 and 1,083.09 ms p95 API latency. Jev therefore remains optional, off by default, and outside every performance claim.

## Try it without a key

From the repository root:

```bash
uv run --frozen python -m tools.jeviphy_demo
```

Expected core output:

```text
Graphify baseline: auth_validate_token at rank 3
Synthetic offline decision: auth_validate_token at rank 1
Evidence: auth_validate_token at auth.py:L3 ↔ synthetic-001
Graph unchanged; Jev API calls: 0
```

The demo proves the integration path and fallback behavior. The [independent comparison](jeviphy-independent-complete-workflow-20261018.md) contains the measured result and limits.

## Feedback that would help

- **Graphify:** should source-seeded traversal live upstream or remain an adapter?
- **Claude Mem:** is optional reviewed `source_paths` metadata useful and safe?
- **Agent builders:** does the source citation make the result easier to verify?
- **Independent testers:** does the same bounded workflow reproduce on another pinned repository?

Please report the repository commit, Jeviphy commit, command, environment, and outcome. A positive or negative reproduction is useful.

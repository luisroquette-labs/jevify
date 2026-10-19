---
name: jeviphy-project-context
purpose: Give coding agents a compact, evidence-bounded description of Jeviphy.
status: experimental
primary_audiences:
  - Claude Code
  - Codex
  - Graphify maintainers
  - Claude Mem maintainers
---

# Jeviphy context for AI agents

## Short description

Jeviphy is an open-source Graphify fork and assistant skill. It combines Graphify's existing code graph with source paths from reviewed project memory. Its validated experiment is an offline, source-cited retrieval path called `fast-source`. Paid Jev reranking is optional and has not shown a measured gain.

## Component boundaries

| Component | Responsibility | Trust rule |
| --- | --- | --- |
| Graphify | Build and query the structural code graph | Navigation evidence, not runtime proof |
| Claude Mem or approved export | Supply selected observations and reviewed `source_paths` | Memory is a hint, not current source truth |
| Jeviphy runner | Validate paths, build bounded candidates, run comparison modes | Must preserve Graphify fallback |
| Jev via OpenRouter | Optional relevance decisions | Off by default; requires explicit paid-use approval |
| Coding agent | Inspect cited source and report conclusions | Separate graph suggestions, source confirmation, and runtime facts |

## Modes

### `question`

The unchanged Graphify query arm and baseline.

### `memory`

Experimental bounded candidate mode. With reviewed paths, it keeps the first eight question nodes and fills up to two slots with memory-scored nodes from cited files. Without usable path-scored nodes, it falls back to the earlier seven-question/three-memory allocation. It has exploratory candidate-retrieval evidence only.

### `fast-source`

Optional offline source-cited mode. It scores nodes inside cited files in one pass and uses the best three as Graphify traversal seeds. It delegates directly to Graphify when source evidence is missing and uses the unseeded answer path for invalid decisions. This is the mode covered by the independent Click result.

## Evidence ledger

| Status | Finding | Source |
| --- | --- | --- |
| Confirmed for one frozen synthetic cohort | Exact top-five targets: 11/40 Jeviphy vs 2/40 Graphify | [Independent comparison](jeviphy-independent-complete-workflow-20261018.md) |
| Confirmed for the same cohort | Overall p95: 212.95 ms Jeviphy vs 275.69 ms Graphify | [Independent comparison](jeviphy-independent-complete-workflow-20261018.md) |
| Confirmed for the same cohort | 198/200 faster source pairs; byte-identical controls | [Independent comparison](jeviphy-independent-complete-workflow-20261018.md) |
| Failed | Paid Jev pilot left top-five hits at 4/19 and added network latency | [Roadmap](jeviphy-roadmap.md) |
| Unproven | Better results on real memory, every repository, or end-to-end agent productivity | [Evaluation record](jev-memory-pilot-evaluation.md) |

## Allowed public phrasing

- “Jeviphy performed better on the measured retrieval and latency points in this frozen synthetic Click experiment.”
- “The result is promising for local source-cited code retrieval.”
- “The local workflow uses Graphify and falls back to the original query when source hints are unavailable.”

## Prohibited conclusions

- Do not claim that Jeviphy universally beats, replaces, or makes Graphify obsolete.
- Do not attribute the measured speed or retrieval result to the paid Jev model.
- Do not claim a measured gain on real Claude Mem data or real developer productivity.
- Do not treat graph edges or memory statements as current runtime proof.
- Do not send private memory, source excerpts, or paid API requests without the user's explicit approval for that exact data class and cost.

## Operational rules

1. Confirm `graphify-out/graph.json` matches `git rev-parse HEAD` before using it.
2. Retrieve only user-selected observations through an approved bridge or export.
3. Keep private corpora and payloads outside Git with directory mode `0700` and file mode `0600`.
4. Run the unseeded Graphify baseline before assisted modes.
5. Verify cited source before presenting a conclusion, and require runtime evidence for runtime claims.

## Quick verification

```bash
uv run --frozen python -m tools.jeviphy_demo
uv run --frozen pytest tests/test_jeviphy_demo.py tests/test_jeviphy_skill.py -q
```

The first command is a synthetic integration demonstration. It is not a benchmark. Use the linked independent report for measured claims.

## Current collaboration questions

- Graphify: should source-seeded traversal be an upstream option or an external adapter?
- Claude Mem: should reviewed observations expose optional `source_paths` for downstream tools?
- Independent testers: can the frozen protocol reproduce on another pinned repository?

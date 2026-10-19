# Jeviphy presentation

Seven slides for a short maintainer or technical-team presentation. The wording is intentionally narrow: it describes the measured experiment without turning it into a universal product claim.

---

## 1. Jeviphy

### Source-aware code search from reviewed memory

Jeviphy is an open-source Graphify fork and skill for Claude Code and Codex. It lets reviewed memory point the existing graph query toward cited source files.

**One sentence:** Graphify maps the repository; Jeviphy uses trustworthy source paths from memory to choose where the graph search should start.

Speaker note: Jeviphy keeps Graphify as the graph engine. It does not replace the graph or modify its structure.

---

## 2. The problem

A code graph can contain the right answer and still rank unrelated nodes first when the question is broad.

Reviewed project memory sometimes already names the implementation files that resolved the same issue. Jeviphy treats those file references as bounded search hints.

```text
question + reviewed memory source paths
                    ↓
          smaller candidate area
                    ↓
             Graphify traversal
                    ↓
       source-cited result for the agent
```

Speaker note: memory text is not accepted as runtime truth. The agent still checks the cited source.

---

## 3. The local workflow

1. Confirm that `graphify-out/graph.json` matches the repository commit.
2. Read only the selected, reviewed observations.
3. Validate their `source_paths` against the repository.
4. Score nodes from those files and use the best three as Graphify traversal seeds.
5. Fall back to the original unseeded Graphify query when evidence is absent or invalid.

The default workflow is offline. Paid Jev calls are optional, off by default, and excluded from the performance result.

Speaker note: the `fast-source` mode is the measured path. The broader memory candidate mode remains experimental.

---

## 4. Result on the frozen Click cohort

Both arms used the same AST graph, source commit, 40 source-cited questions, machine, alternating order, and five timing passes.

| Measure | Graphify | Jeviphy `fast-source` |
| --- | ---: | ---: |
| Exact target nodes in top five | 2/40 | **11/40** |
| First-pass source answer hits | 22/40 | **32/40** |
| Overall p50 | 183.92 ms | **79.63 ms** |
| Overall p95 | 275.69 ms | **212.95 ms** |
| Source p95 | 294.29 ms | **158.29 ms** |

Jeviphy was faster in 198 of 200 paired source-backed runs. All control answers were byte-identical.

Speaker note: say “performed better on the measured points in this experiment.” Do not say “Jeviphy is universally faster or better than Graphify.”

---

## 5. The failed experiment matters

A separate paid Jev pilot completed 19 calls on identical bounded candidate pools.

- Top-five hits stayed at **4/19**.
- API latency added **649.74 ms p50** and **1,083.09 ms p95**.
- The experiment failed its advancement gate.

Jev remains optional because this result does not support a quality or speed claim for model-based reranking.

Speaker note: the positive result came from local source-cited retrieval, not from the paid Jev model.

---

## 6. What the evidence supports

**Supported**

- A promising result for synthetic source-cited code questions.
- Better measured retrieval and latency on one frozen Click cohort.
- Offline operation with an exact Graphify fallback.
- A reproducible 60-second demo with no API key.

**Still open**

- Real-user task outcomes.
- Real-memory relevance gains.
- Results across more repositories and question types.
- The right interoperability boundary with Claude Mem and upstream Graphify.

---

## 7. What we want reviewed

### Graphify maintainers

Is source-seeded traversal useful inside Graphify, or should Jeviphy remain an external adapter?

### Claude Mem maintainers

Is an optional, reviewed `source_paths` field a reasonable interoperability boundary?

### Independent testers

Can the frozen workflow be reproduced on another repository without weakening the fallback or privacy rules?

Start with the [60-second offline demo](jeviphy-demo.md), then inspect the [independent comparison](jeviphy-independent-complete-workflow-20261018.md).

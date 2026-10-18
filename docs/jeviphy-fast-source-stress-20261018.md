# Fast source retrieval: two independent stress cohorts (18 October 2026)

## Decision

**The five-stage sales gate remains closed.** The opt-in `fast-source` path improved top-five retrieval and median offline query time on both repositories. It did not reliably beat Graphify at p95 for the complete measured query: CF Gauss was 6.79 ms slower, and case-level bootstrap intervals for p95 include a regression in both repositories. No Jev request, model decision, cost, outreach, or sales claim is supported by this test.

The earlier [memory-mode result](jeviphy-independent-stress-20261018.md) remains a separate negative baseline. Its 30 SWEN cases were used only to develop the new design. A second SWEN cohort exposed duplicated fallback work and then became development data. The two cohorts below were frozen before their candidate or answer output was viewed. The CF Gauss run used the same implementation as the final SWEN run, with no tuning between them.

## Reproducible scope

- Both arms used the same pinned source commit and normalized AST graph per repository. Graphify baseline was `python -m graphify query`. Jeviphy loaded that graph once, scored at most ten nodes from cited files, and passed the top three as seeds to Graphify's existing traversal. Without a scored cited node it ran the unseeded Graphify traversal. No paid API or model was called.
- Each cohort had 30 distinct sanitized memory questions: 20 with source paths represented in the graph and ten negative controls without code-backed source paths. One agent selected exact gold node IDs from the frozen source and graph **before seeing results**. Selection was purposive, and there was no second annotator.
- The versioned [runner](../tools/jeviphy_full_stress.py) warmed both arms, alternated their order per case, and ran three passes: 90 paired query timings per repository. It records exact graph, manifest, and source hashes and refuses a dirty source checkout. Its private raw results include first-pass answers for review.
- SWEN: source `d5de37906d4d9c41154ad3cc6a412e297ff5b5b9`, graph SHA-256 `386d8c5755298fb072fb1aac1197203b01524bb19e8a7f26c4c5af1c805d6597`, final manifest SHA-256 `641756f328d0d23868aa99b9c2785b67fe153380ddc3b3a1b0e78d9bfb926a0f`. Graph: 14,229 nodes, 34,905 edges.
- CF Gauss: source `891190876402d739fc9b0d492d4ef19fe5a9081a`, graph SHA-256 `f91d5361e487cd5db0ad4aa056c7ce83a3c54f1339201686405299b657a050cd`, manifest SHA-256 `398c5bd1db38f1b5f3dc9e73369dd35c0a5be58efe071b758889b88b4206a1ef`. Graph: 26,847 nodes, 60,502 edges. Graphify's AST build found three syntax warnings and 596 code files without symbols. Twelve external-package `source_file` fields were blanked in the private copy; both arms used that same copy. A separate clean worktree at the pinned commit supplied the source.

| Cohort and measure | Graphify | Jeviphy `fast-source` |
| --- | ---: | ---: |
| SWEN semantic precision@5, all 30 cases | 0.0467 | 0.1467 |
| SWEN source-case gold nodes in top five | 7 | 22 |
| SWEN gold nodes shown in first-pass answers | 13 | 20 |
| SWEN complete query p50 / p95 | 512.38 / 566.94 ms | 249.49 / 544.77 ms |
| CF Gauss semantic precision@5, all 30 cases | 0.0067 | 0.1000 |
| CF Gauss source-case gold nodes in top five | 1 | 15 |
| CF Gauss gold nodes shown in first-pass answers | 9 | 26 |
| CF Gauss complete query p50 / p95 | 920.29 / 1055.26 ms | 490.34 / 1062.05 ms |

On SWEN, Jeviphy was faster in 72/90 pairs, with 12 source-case top-five gains and zero losses. On CF Gauss it was faster in 63/90 pairs, with 13 source-case gains and zero losses. In the 60 source-backed pairs per repository, Jeviphy was faster in all 60. CF Gauss controls had a median of 1002 ms for Jeviphy versus 912 ms for Graphify; that fallback overhead drove the pooled p95 failure.

Case-level bootstrap (10,000 resamples, three timings kept together per case) gave descriptive 95% intervals for the p50 advantage of 130–295 ms on SWEN and 182–463 ms on CF Gauss. The p95 advantage intervals were **−25 to 88 ms** and **−74 to 76 ms** respectively. These are one-machine measurements under ordinary background load, not a guarantee of future latency.

The answer-level inspection found one SWEN loss: the correct Facebook icon node was fourth in Jeviphy's candidate pool but outside its top-three seeds, and did not appear in the rendered answer. CF Gauss had no first-pass answer-hit loss. Exact node-and-file matches in rendered answers are still a limited proxy for answer usefulness; there was no blind human comparison of answer text.

## Privacy and reproduction

Raw observations, source-backed questions, labels, graph copies, first-pass answer text, and timing rows are outside Git under `~/.local/share/jev-memory-pilot/` with mode 0700 directories and 0600 files. The normalized graph hashes above identify exactly what was tested without publishing private memories. Reproduce a cohort using `mac-gate uv run --frozen python -m tools.jeviphy_full_stress --manifest <private-manifest> --graph <private-graph> --repo <clean-pinned-checkout> --output <new-private-file> --passes 3`.

This test begins after observation selection and graph construction. It does not time Claude Mem retrieval, Jev inference, paid API transport, a warmed Graphify MCP server, or agent reading time. Jev's relevance and cost remain unmeasured. The `fast-source` mode remains opt-in; question and memory modes remain the default comparison paths. Stages 3–5 remain paused until a predeclared complete-workflow test demonstrates a stable p95 advantage and answer quality without regressions.

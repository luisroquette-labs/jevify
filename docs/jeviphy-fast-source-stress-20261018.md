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

## Follow-up: no-source pass-through and conditional activation

After the pooled CF Gauss p95 failure, profiling traced the control slowdown to loading the graph and running an unseeded query inside Jeviphy even when no observation cited a source. The revised `fast-source` CLI validates the selected corpus case and delegates these offline, unscoped queries directly to Graphify. It does not create a Jev sidecar for that query. A dedicated regression test checks exact output and the absence of a Jeviphy graph load. A second test accepts Graphify's exit code 4 only for its exact `No matching nodes found.` response. Both paired arms use the same Graphify subprocess path; `PYTHONHASHSEED=0` makes its edge ordering reproducible.

Replays of the already-seen cohorts were **development checks**, not new confirmation: CF Gauss p50/p95 became 503.09/979.72 ms versus Graphify 939.33/1076.71 ms; SWEN became 262.50/554.98 ms versus 508.32/852.68 ms. A new CF Gauss cohort used 20 previously unused files and ten controls, frozen at manifest SHA-256 `be06b1f1c455bf54ef7a9940b83503d5489e038c0decabf6de70d2259b8e7848`. Its precision@5 was 0.1333 versus 0.0267, and complete-query p50/p95 was 500.09/1170.45 ms versus 1023.14/1196.55 ms. The pooled p95 advantage's case-bootstrap 95% interval was **−110 to 210 ms**, so it does not prove a general tail-latency win. Those questions were then used to choose the conditional gate below and are development data for that gate.

The conditional gate was [specified before COESA output](../.specs/tasks/draft/jeviphy-fast-source-retrieval.feature.md): require a source-backed precision@5 gain, no first-pass answer loss, lower source-backed p50/p95 with a strictly positive case-bootstrap 95% interval for the p95 advantage, and identical no-source control answers. The cohort had 20 source-backed and ten no-source questions, with 90 balanced paired timings. The questions and summaries were **synthetic code-review scenarios**, not Claude Mem observations; one agent assigned exact gold IDs from the graph before either arm ran. The pinned COESA source was `4e773bd2764ebdd85a072f53c752f3a397737ce4`; its AST-only graph had 2,455 nodes and 4,568 edges, SHA-256 `25637c03044d6ebabcd557bc22b226e3018fa8a7626baa0941a810541c41b205`. The private frozen manifest SHA-256 was `de944fe5edf316261de03a4d6f83d32ba91a874ab0c186c67da0352eb94067a3`.

| COESA measure | Graphify | Jeviphy `fast-source` |
| --- | ---: | ---: |
| Precision@5, all 30 cases | 0.0200 | 0.1333 |
| Source-case gold nodes in top five | 3 | 20 |
| Gold nodes in first-pass answers | 8 | 20 |
| Source-backed complete-query p50 / p95 | 161.88 / 200.46 ms | 43.55 / 69.87 ms |
| All-case complete-query p50 / p95 | 160.54 / 197.53 ms | 47.29 / 165.33 ms |

All 60 source-backed pairs were faster. The versioned runner's case-level 10,000-resample bootstrap gave a **119.08–152.45 ms** descriptive 95% interval for the source-backed p95 advantage. No source-backed case lost a first-pass gold answer hit. After deterministic Graphify subprocess ordering, all 30 no-source control pairs returned byte-identical answers. The first COESA run exposed Graphify's ordinary no-match exit code; a second showed edge-order variance between processes. Both harness corrections were tested, and the same frozen questions were rerun. The table reports the final run with versioned subgroup and bootstrap metrics. This is useful confirmation of the **source-cited activation path**, with that repair history disclosed; it is not a pristine single-shot trial.

The original broad pooled p95 gate remains unresolved: COESA's first deterministic run had only a 3.60 ms pooled advantage; the final run had 32.20 ms. A case-level bootstrap on the final run gave a 7.68–43.80 ms pooled advantage, but the variation across repeat runs and the earlier CF Gauss regression do not justify a universal speed claim. This test supports the narrow statement that local source-cited retrieval was faster and more precise on these synthetic cases. It does **not** prove Jev model benefit, real-memory benefit, universal speed, or end-to-end agent efficiency. Paid Jev, a sales page, and outreach remain gated on their separate evidence and approval requirements.

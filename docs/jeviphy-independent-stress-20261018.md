# Independent SWEN candidate stress test — 18 October 2026

## Decision

**Do not advance to stages 3–5 or claim that Jeviphy is faster or more effective than Graphify.** The optional memory mode found more nodes from memory-cited files in the top ten, but took longer. On all 20 source-backed questions its first five node IDs were identical to Graphify question mode, so this experiment cannot demonstrate a semantic top-five gain. No answer text, Jev ranking, paid API, or complete workflow was tested.

## Frozen setup

- Independent repository: SWEN, clean source commit `d5de37906d4d9c41154ad3cc6a412e297ff5b5b9`. The source-aware Jeviphy rule was designed on CF Gauss, not SWEN.
- Thirty nonredacted observations were selected **before any candidate output**: 20 with an implementation file cited in the graph, 10 without one. Every observation predates the graph build. Selection was purposive across subsystems, not random; no semantic gold labels or second reviewer exist. Case text and results are private.
- An earlier SWEN graph failed the pinning check because it referenced an untracked generated file. It was discarded before measurement. An AST-only graph was rebuilt from the clean checkout with the SQL grammar installed. Three external-package nodes had their nonlocal `source_file` metadata blanked; the verified source HEAD was stamped in the graph. Both arms used this **same** normalized graph. Its SHA-256 is `386d8c5755298fb072fb1aac1197203b01524bb19e8a7f26c4c5af1c805d6597`; the frozen 30-case manifest SHA-256 is `026f29e6779ab2f011682fe10f5b383af1e5a03c97f44b0bf968213ada80df13`.
- Graphify's diagnostic found 14,229 nodes and 34,905 edges, with no missing or dangling endpoints. One TSX file had a syntax warning and 268 code files yielded no symbols; both arms share this graph limitation.
- Same Python 3.13.12 process, Apple M5, 16 GiB RAM, macOS 26.1. The runner warmed both arms, alternated order, and completed three passes of all 30 cases: 90 paired questions and 180 measured candidate calls. Source and graph pinning checks stayed active. No call failed after rebuilding the graph.

## Measured result

| Measure | Graphify question mode | Jeviphy memory mode |
| --- | ---: | ---: |
| Top-ten pool contains a memory-cited implementation file, source-backed cases | 5/20 | 18/20 |
| Wall-time p50, 90 calls per arm | 445.80 ms | 542.45 ms |
| Wall-time p95, 90 calls per arm | 548.84 ms | 620.30 ms |

Fourteen source-backed cases gained a cited-file hit and one lost one; these counts were identical in each pass. This is an **exact-file provenance proxy**, not proof that a node answers the question. All 20 source-backed cases had identical first-five candidate IDs in both arms on all three passes. In one control, baseline returned only one candidate and memory mode added three; across all 30 cases, the baseline top-five **prefix** was preserved in 90/90 pairs and the complete top-five lists were identical in 87/90.

The median within-pair time ratio was 1.201 (Jeviphy / Graphify). Using one median ratio per case, the median was 1.212; a 10,000-resample, case-level bootstrap gave a descriptive 95% interval of 1.177–1.234. Jeviphy was faster in 1/90 individual pairs and in 0/30 case medians. The process peak RSS was 164,462,592 bytes. Candidate IDs were stable across the three passes for all 30 cases.

## Interpretation and limits

The implementation keeps the question's first seven or eight nodes before adding memory candidates. The observed top-five parity on source-backed cases follows that rule, so higher top-ten source overlap cannot establish higher precision@5. The additional memory scoring and graph loading made this candidate operation slower at both p50 and p95. The test gives a strong reason **not to claim** superiority; it does not measure Jev reranking, Graphify answer quality, or end-to-end latency.

The observations were selected rather than randomly sampled, file overlap is not semantic relevance, and one agent prepared the private corpus. Source-code syntax and extraction warnings limit graph coverage. The paired timing test ran on one machine under ordinary background load. These limits prevent a general product-performance claim even if one proxy improved.

## Reproduction and privacy

The versioned runner is `tools/jeviphy_stress.py`; its arithmetic and fail-closed pinning behavior are covered by `tests/test_jeviphy_stress.py`. It requires the private mode-0600 manifest and normalized graph, plus the clean pinned source checkout. Run it through `mac-gate` with `--manifest`, `--graph`, `--repo`, `--output`, and `--passes 3`. The output directory must be mode 0700. The raw per-case questions, memory summaries, candidate IDs, source paths, and timing rows remain outside Git. The hashes above identify the exact local artifacts without publishing private memories.

The stage-2 gate requires independently reviewed semantic precision@5 improvement and faster paired median **and** p95 complete-workflow latency. This offline result meets neither proof condition. The roadmap therefore stops before paid Jev requests and the sales page.

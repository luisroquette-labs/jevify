# Jeviphy: evidence before sales

Jeviphy builds on Graphify. Speed and relevance claims require a measured comparison against the same Graphify version, graph, hardware, questions, and request budget. Jev is optional and no paid call is authorized by this roadmap.

**Current gate: stopped after stage 2.** The independent [SWEN stress test](jeviphy-independent-stress-20261018.md) found more cited-source files in the top ten but slower candidate retrieval and no top-five change on source-backed cases. Stages 3–5 remain paused until a new design passes a fresh independent quality and speed gate.

1. **Candidate retrieval (current):** specify and test a bounded source-aware memory candidate pool. Keep the original question mode and unseeded answer fallback intact. Report exploratory retrieval metrics without claiming better answers.
2. **Independent relevance and stress gate:** freeze at least 30 questions from a repository outside the design cohort before inspecting results. Run a matched, repeated offline candidate stress test; review semantic labels independently where feasible. Continue only if held-out semantic precision@5 improves without unsupported suggestions and the complete workflow beats original Graphify on paired median and p95 wall time. Source-file overlap alone cannot pass this gate. If either condition fails, stop stages 3–5 and publish the negative result.
3. **Paired Jev test:** compare rankings on identical ten-node pools. Measure precision@5, recall@5, unsupported suggestions, latency, requests, and actual cost. Review exact private payloads and obtain explicit paid-use approval before any live request.
4. **Graphify comparison:** benchmark the complete Jeviphy workflow and the original Graphify workflow on the same environment and graph. Publish distributions for answer quality, time, and resource use, with the method and limits. Claim an improvement only for metrics that pass this comparison.
5. **Sales page:** design a page in the repository's visual style with a reproducible demo, install path, measured evidence, limits, and a clear call to action. Use “faster” or “more effective” only when stage 4 supports the exact claim; identify Graphify as the foundation and Jev as an optional ranking step.

The upstream Graphify draft PR remains a separate technical feasibility proposal. Outreach to Graphify and Claude Mem should link to evidence and avoid performance claims until stages 2–4 are complete.

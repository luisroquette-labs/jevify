# Jeviphy: evidence before sales

Jeviphy builds on Graphify. Speed and relevance claims require a measured comparison against the same Graphify version, graph, hardware, questions, and request budget. Jev is optional and no paid call is authorized by this roadmap.

1. **Candidate retrieval (current):** specify and test a bounded source-aware memory candidate pool. Keep the original question mode and unseeded answer fallback intact. Report exploratory retrieval metrics without claiming better answers.
2. **Independent relevance set:** freeze at least 30 source-reviewed questions, including negative and stale cases, before inspecting the new candidate results. Use 10 calibration and at least 20 held-out cases; review labels independently where feasible.
3. **Paired Jev test:** compare rankings on identical ten-node pools. Measure precision@5, recall@5, unsupported suggestions, latency, requests, and actual cost. Review exact private payloads and obtain explicit paid-use approval before any live request.
4. **Graphify comparison:** benchmark the complete Jeviphy workflow and the original Graphify workflow on the same environment and graph. Publish distributions for answer quality, time, and resource use, with the method and limits. Claim an improvement only for metrics that pass this comparison.
5. **Sales page:** design a page in the repository's visual style with a reproducible demo, install path, measured evidence, limits, and a clear call to action. Use “faster” or “more effective” only when stage 4 supports the exact claim; identify Graphify as the foundation and Jev as an optional ranking step.

The upstream Graphify draft PR remains a separate technical feasibility proposal. Outreach to Graphify and Claude Mem should link to evidence and avoid performance claims until stages 2–4 are complete.

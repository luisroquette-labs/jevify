---
title: Evaluate Jev decisions on a bounded mixed candidate pool
status: draft
---

# Stage 3: paired Jev ranking pilot

## Plan

The 20 previously observed synthetic COESA source cases are **development data**. Their original source-scoped pool already placed every reachable gold node in the top five, leaving no ranking headroom. A no-name ablation removed function names from the summaries: 13/20 gold nodes remained in the source-scoped top five, and seven were absent from its top ten. The model cannot recover an absent candidate.

Before viewing any Jev response, form each of the 20 paired pools deterministically: the first five Graphify question candidates followed by the first five no-name source-scoped candidates, deduplicated in that order. The same ten-or-fewer nodes are the baseline and Jev inputs. The frozen payloads contain 136 committed source lines; nodes without a committed excerpt are excluded. Baseline gold top-five coverage in the transmitted pools is 4/20 and pool coverage is 13/20. One case has no committed excerpt and must be reported without a paid call, leaving at most 19 model requests. Each request contains one synthetic question, one synthetic summary without a function name, and at most one committed source line per node. The private inventory SHA-256 is `8ee6f3f616480449fa5c1cd28c3dd69d3fb466a5378190c104f9e8a6dfd36681`; the 20 payloads total 92,657 bytes. Keep all payloads and responses private outside Git.

## Review

- The pool combines two already tested retrievers and was designed after inspecting the offline cohort. Any positive result is exploratory; it cannot validate an independent product or sales claim.
- A model can only reorder supplied candidates. Report candidate recall separately from top-five precision, and flag suggestions outside the exact gold labels for later review; the single gold label does not prove every other node irrelevant.
- Compare rankings on the same pool; record Jev network latency and actual `usage.cost` separately from offline Graphify query time. Do not imply that a paid model improves end-to-end speed.
- The user approved at most 20 OpenRouter Jev calls using synthetic COESA content and at most 152 committed code lines, with an operational ceiling of US$0.05. Use only a dedicated Jeviphy key with that credit limit. Never use a personal or other project's key.

## Execute

Prepare the exact private payload inventory and assert its hash, node order, model, endpoint, 20-request cap, and 152-line cap. The live runner requires explicit paid-use flags and the project key. Record an attempt privately **before** each POST; after an uncertain outcome, stop without retry. Store validated decisions, latency, model, and actual cost after each success. Stop when the request or cost cap is reached.

## Test and validation

Test malformed payloads, duplicate attempts, failed/partial responses, cost accounting, and the no-retry boundary with a local stub. Run all Python gates through `mac-gate`. Compare baseline and Jev precision@5 and recall@5, non-gold suggestions for review, success/failure counts, latency, and total actual cost. Stage 3 passes only as a technical model measurement. An independent memory cohort and complete-workflow gate remain necessary for stages 4–5.

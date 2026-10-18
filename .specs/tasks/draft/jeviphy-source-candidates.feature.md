---
title: Retrieve bounded memory candidates from source provenance
---

## Status

Phase 1 of the [five-stage roadmap](../../../docs/jeviphy-roadmap.md). This specification precedes the implementation and tests. The existing 18-case source-reviewed cohort is exploratory design data, not an independent holdout.

## Problem

The optional memory mode searches concatenated summaries and keeps seven question candidates plus three memory candidates. It found a relevant top-ten node in 9/16 positive cases, versus 8/16 for question-only search, with no top-five gain. A memory can also cite implementation files through the supported gateway, but the runner currently discards that provenance when choosing candidates.

## Contract

- Accept optional repo-relative `source_paths` on selected observation records. The field is a local retrieval hint and must not be sent to Jev or written to the decision sidecar; selected node IDs and excerpts remain subject to the existing outbound-payload review.
- When at least one valid path matches a graph node scored by the memory summary, keep the question's first eight candidates and fill at most two slots from memory-scored nodes in those files. Deduplicate and fill remaining slots from the question ranking. Keep the ten-node cap.
- With no source paths or no scored node in the cited files, retain the existing 7+3 memory behavior. The default question mode remains byte-for-byte equivalent in candidate IDs and ordering.
- Reject malformed path lists; do not follow paths or read working-tree files. Existing graph commit and tracked-source checks apply to every selected candidate.
- Preserve the original unseeded Graphify answer when no valid Jev decisions change the top three seeds. This feature makes no paid API call.

## SDD acceptance

1. A synthetic graph proves source-backed nodes can enter slots nine or ten while the first eight question nodes stay ordered.
2. Synthetic tests prove the legacy 7+3 fallback, malformed path rejection, ten-node cap, source parity in the portable skill, and no private path in the outbound Jev payload.
3. The pinned exploratory cohort is rescored offline, reporting candidate recall, top-ten hit rate, top-five precision, gains and losses, and comparison limitations. The design cohort cannot establish general effectiveness.
4. Focused tests, lint, portable-skill parity, and repository CI pass on the same PR SHA. Refresh the local code graph after code changes.

## Out of scope

Automatic memory export, new graph edges, a vector database, a live Jev call, a speed claim, and the sales page are later-stage work.

## Exploratory design result

The source-bearing cohort used to choose this rule has 18 scored cases, 16 with relevant nodes. Question mode had a relevant top-ten node in 8/16; source-aware mode had one in 10/16. Mean candidate recall changed from 0.176 to 0.314; mean precision@5 stayed 0.078. Five cases gained relevant top-ten nodes and one lost one. These numbers are not held-out evidence because this same cohort guided the design.

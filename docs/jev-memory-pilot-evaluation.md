# Jev memory pilot: evaluation record

## Current result

The offline harness is implemented. Synthetic tests prove bounded candidate selection, typed pair mapping, exact fallback to the unseeded Graphify query, and graph/learning-sidecar integrity. They do **not** establish that Jev improves retrieval on real memory.

No real claude-mem record or private source excerpt has been sent to Jev. No paid request has run. The real paired result remains pending the data and cost review described below. The existing upstream draft PR requests design feedback without asserting an outcome.

One private evaluation checkout is pinned to its source commit and has an AST-only graph. A private cohort has 30 draft questions: the original three cases plus 27 additional questions from the same project's memory index. An agent inspected the selected memory records and audited their source paths against all 30 deterministic candidate pools. This audit does not provide independently reviewed relevance labels. The original three exact local payload previews contain 16, 8, and 5 pairs. No paid request has run, and there is no measured Jev gain.

## Autonomous source-provenance audit

The audit used the memory gateway's `files_modified` field and the graph node's `source_file` field at the same pinned source commit. It excluded test files and counted a hit when at least one of the ten Graphify candidates came from a source file named by the selected memory. The 10 calibration and 20 held-out case IDs were assigned before this audit; this is a descriptive audit, not a scored experiment.

Of 30 questions, 26 had at least one memory-cited implementation file represented in the graph. Only 6 of those 26 candidate pools contained a node from such a file in the top ten; 4 did so in the top five. The other four questions concerned external configuration (two), another repository (one), or a source file absent from the pinned commit (one). Exact file overlap is a provenance proxy: it can miss semantically relevant nodes in other files and cannot establish that a matching node answers the question. The selected questions also cluster around one subsystem. These figures are **not** precision, recall, or Jev results.

This shows a practical ceiling for reranking the current ten candidates: many source-linked cases offer Jev no node from the memory's cited implementation files to promote. The next technical experiment should improve or broaden candidate retrieval, then repeat the audit and a separately labeled paired evaluation. The private questions, memory records, file paths, and per-case results remain outside Git.

## Bounded two-query candidate experiment

An optional `--candidate-mode memory` now takes the first seven candidates from the question-only Graphify ranking and up to three from a separate search over the selected memory summaries. It deduplicates the union and fills spare slots from the question ranking. The default `question` mode and the unseeded answer fallback are unchanged. No Jev request is needed to compare candidate pools.

On the exploratory 30-question cohort, exact memory-cited source-file overlap in the top ten rose from 6/26 to 10/26 without losing a previous file hit. This variant was chosen after inspecting those cases, so they cannot validate it independently. A second cohort was selected from all previously unused memories with an implementation file represented in the pinned graph and frozen before running the variant. It contains 19 memories predating the graph commit and one later memory used as a stale-code control. On the 19 primary cases, overlap moved from 7/19 to 8/19, again without losing a previous hit; neither arm hit the stale control. This selected cohort is not random or independently labeled. The result is a modest source-path proxy, not proof of better answers or a Jev gain. The private case details and results remain outside Git.

## Frozen labeling rule for the real cohort

1. Select one repository with a graph pinned to its source commit. Select observations through the supported memory gateway, review each summary for sensitive content, and keep all records and labels under a mode-0700 directory outside Git worktrees.
2. Before viewing Jev answers, label at least 30 questions: 10 calibration and at least 20 held-out. Include zero-relevant, ambiguous-label, stale-code, and unrelated-memory cases. Record gold graph node IDs and gold node–observation pairs. A node outside the ten-candidate pool remains gold; it lowers the candidate-recall ceiling.
3. Use the same ten deterministic candidates for baseline and assisted arms. Choose a relevance threshold only on calibration cases, requiring zero unsupported suggestions there. Freeze that threshold before scoring held-out cases.
4. Treat a suggestion as unsupported when its exact node–observation pair is absent from frozen gold. Compute precision@5 with denominator five; compute recall@5 only when gold is nonempty. Report zero-relevant cases separately, plus candidate recall, paired per-question differences, p50/p95 latency, actual request count, and `usage.cost`.
5. Claim a pilot gain only if held-out precision@5 rises with no unsupported suggestion displayed. These metrics concern candidate ranking; they do not prove better Graphify answer text or runtime causality.

## Synthetic metric check

The committed test fixture covers a missed gold node and a zero-relevant case. In its two-case metric example, candidate recall is 0.50, mean baseline P@5 is 0.00, mean assisted P@5 is 0.10, assisted R@5 on the nonempty case is 0.50, and one of two suggestions is unsupported. These numbers validate arithmetic only; they are not a product result.

## Live gate and contribution decision

Before a paid call, render each exact payload to mode-0600 storage, inspect every code excerpt and memory summary, show the current model price and total call/cost cap, and obtain explicit approval for that payload class and paid use. Stop on the first unexpected response; never retry an uncertain POST. Publish only aggregate held-out metrics and synthetic examples in the fork PR. An upstream PR is a separate task only if the real comparison reveals a reusable Graphify gap.

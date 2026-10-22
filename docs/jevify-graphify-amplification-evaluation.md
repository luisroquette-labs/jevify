# Jevify Graphify amplification evaluation

## Result

Candidate `1132abd00b67d25896d5a04fdd6b551866c3ff00` passed three
bounded offline update cases. Jevify orchestrated the applicable Graphify
workflow, verified manifest freshness and artifact health, and returned five
prioritized questions in each case. Graphify remained the structural engine;
JEV was not called.

The frozen private manifest has SHA-256
`134167fa1b2427cf129b880882446548264017ae06f67471789900bfde541b68`.
The private result receipt has SHA-256
`2aee7c2be157c42cb9769c140919a6bbc771ecd956c2b6f550574c906cd93ee9`.
Neither receipt contains source payloads or question text.

## Cases

| Case | Route | Before | After | Result |
| --- | --- | ---: | ---: | --- |
| CleanMyMac mixed | Graphify host | 623 nodes / 1,255 edges | 627 / 1,223 | pass |
| Axios code-only | local Graphify | 1,388 / 1,976 | 1,397 / 1,976 | pass |
| Gson mixed | Graphify host | 4,076 / 12,982 | 4,096 / 12,919 | pass |

Every case ended with zero pending files and zero blocking integrity findings.
Reports matched graph counts, HTML visualizations were current, five questions
were returned without duplicate labels, and a second update returned
`already_current` without rewriting any graph artifact. Paid request count was
zero. The accepted graphs are direct Graphify outputs; Jevify's finalization
verifies them and does not rewrite their structure.

## Feedback loops

The first output review found duplicated whitespace in a question. The second
found an unbounded bridge question in Gson. The third found two distinct node
IDs collapsing to one visible label in CleanMyMac. Each issue received a
focused regression test before the three outputs were reviewed again. The
final questions were 84–138 characters at most across the public fixtures and
120 characters at most in CleanMyMac.

An exhaustive post-integration audit found and fixed three acceptance gaps:
local and already-current routes now reject blocking Graphify health findings,
already-current results require the report and visualization, and failed
updates restore the complete verified artifact set instead of only
`graph.json`. Regression coverage pins all three behaviors. The audit suite
finished with 8,647 tests passed and 15 skipped.

## Boundaries and caveats

- Axios was intentionally restricted to a code-only corpus; two sensitive test
  certificate files were skipped by Graphify.
- Gson's semantic corpus was intentionally limited to its root `README.md`.
- Graphify 0.9.92 ran with a locally installed 0.9.93 skill. No package upgrade
  was made because it would be a separate structural change.
- Graphify reported 2, 11, and 29 non-blocking self-loops respectively. Mixed
  updates also exercised the official intentional-write path after semantic
  IDs replaced older IDs under the shrink guard.

This evidence proves bounded update compatibility, honest freshness, artifact
preservation, and actionable output for these three cases. It does not prove
product superiority, general answer quality, latency advantage, user demand,
or a JEV contribution.

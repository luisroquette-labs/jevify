# Jevify technical beta evidence

## Decision

Jevify is available as a transparent technical beta. It orchestrates the
complete applicable Graphify workflow, verifies freshness, and adds prioritized
questions and optional reviewed memory. Graphify remains the structural engine;
JEV remains optional.

## What passed

| Evidence | Result | Candidate |
| --- | ---: | --- |
| Clean installation | 20/20 across Ubuntu and macOS | `a2f7aee0` |
| Zero configuration | 30/30 with no interaction | `a2f7aee0` |
| Graphify compatibility | pass | `a2f7aee0` |
| Bounded update acceptance | 3/3 offline cases | `1132abd0` |
| Local suite | 8,647 tests passed; 15 skipped | exhaustive audit checkpoint |

GitHub CI later ran 8,602 tests per supported Python interpreter on the PR SHA.
The public [machine-readable scorecard](../benchmarks/jevify-beta/scorecard.json)
contains the evidence hashes.

The [Graphify amplification evaluation](jevify-graphify-amplification-evaluation.md)
records one code-only and two mixed cases. All produced current artifacts, five
questions, zero blocking integrity findings, and zero paid requests. It is
technical compatibility evidence, not a comparative product result.

## What stopped

- Product benchmark v13: stopped at 0/60 after the beta decision.
- Product benchmark v11: eight pairs, diagnostic only.
- Paid JEV: optional and off by default. No performance claim is attached to it.

## Review requests

- **Graphify:** review whether the adapter preserves graph semantics and fallback behavior.
- **Claude Mem:** review the bounded `source_paths` interoperability contract and privacy boundary.
- **JEV:** review the opt-in decision interface and evaluation protocol without treating diagnostic data as proof.

No current material makes a product-advantage claim over Graphify.

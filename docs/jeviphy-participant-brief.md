# Jeviphy technical beta brief

## What it is

Jeviphy is an open-source Graphify fork and assistant skill for Claude Code and
Codex. Graphify builds and queries the code graph. Jeviphy can validate source
paths from reviewed memory and use them as bounded traversal hints.

Graphify remains the engine. Memory remains a hint. The coding agent must inspect
the cited source before reporting a conclusion.

## Evidence available now

| Gate | Result |
| --- | ---: |
| Clean installation | 20/20 on Ubuntu and macOS |
| Zero configuration | 30/30 with no interaction |
| Graphify compatibility | pass |
| Local suite | 8,601 tests passed |

The [beta scorecard](../benchmarks/jeviphy-beta/scorecard.md) publishes the
evidence hashes and exact candidate.

## Evidence boundary

The v13 product benchmark stopped at 0/60 after the beta decision. The eight v11
pairs are diagnostic only. JEV remains optional, off by default, and requires
explicit approval for paid use. None of these results supports a product
advantage claim over Graphify.

## Review requested

- **Graphify:** verify graph semantics and the unchanged fallback.
- **Claude Mem:** review the optional `source_paths` contract and privacy rules.
- **JEV:** review the bounded decision interface and future evaluation protocol.

Use the [offline demo](jeviphy-demo.md) to inspect the integration path without
an API key. Report the repository commit, Jeviphy commit, command, environment,
and outcome for any independent test.

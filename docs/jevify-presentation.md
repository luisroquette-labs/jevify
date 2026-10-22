# Jevify technical beta presentation

Seven slides for Graphify, Claude Mem, and JEV maintainers. The deck uses only
the release evidence in the technical beta scorecard.

## 1. Jevify

### Graphify code graphs with reviewed memory hints

Jevify is an open-source Graphify fork and assistant skill for Claude Code and
Codex. It keeps Graphify as the graph engine and adds a bounded path from
reviewed memory to cited source files.

Speaker note: introduce this as a transparent technical beta.

## 2. Component boundary

1. Graphify builds and queries the structural graph.
2. Claude Mem or an approved export supplies reviewed source paths.
3. Jevify validates the paths and runs bounded traversal.
4. The coding agent verifies cited source before reporting a conclusion.

Memory does not become a structural graph assertion or runtime proof.

## 3. Local workflow

1. Confirm the graph and repository commit match.
2. Read only selected, reviewed observations.
3. Validate cited paths in the working tree.
4. Run bounded Graphify traversal.
5. Use the original Graphify path when evidence is absent or invalid.

The default workflow is offline. Paid JEV calls require explicit approval.

## 4. Beta evidence

| Gate | Result |
| --- | ---: |
| Clean installation | 20/20 on Ubuntu and macOS |
| Zero configuration | 30/30, no interaction |
| Graphify compatibility | pass |
| Local suite | 8,608 tests passed |

Speaker note: evidence hashes are in the machine-readable beta scorecard.

## 5. Stopped evaluation

The v13 product benchmark stopped at 0/60 after the technical beta decision.
The eight v11 pairs are diagnostic only. No long benchmark or paid API run is
part of this release decision.

## 6. Evidence boundary

**Supported:** installation on two operating systems, zero-configuration
execution, Graphify-compatible fallback, and an offline default path.

**Still open:** real-user task outcomes, independent product evaluation,
coverage across more repositories, and maintainer review of the integration
boundary.

## 7. Review requests

- **Graphify:** does the adapter preserve graph semantics and fallback behavior?
- **Claude Mem:** is reviewed `source_paths` metadata a safe interoperability boundary?
- **JEV:** is the opt-in decision interface appropriate for later independent evaluation?

Start with the [beta evidence](jevify-beta-evidence.md), then inspect the
[offline demo](jevify-demo.md) and source contracts.

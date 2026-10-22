---
name: jevify-project-context
purpose: Give coding agents a compact, evidence-bounded description of Jevify.
status: technical-beta
primary_audiences:
  - Claude Code
  - Codex
  - Graphify maintainers
  - Claude Mem maintainers
  - JEV maintainers
---

# Jevify context for AI agents

## Short description

Jevify is an open-source Graphify fork and assistant skill. It combines
Graphify's code graph with validated source paths from reviewed project memory.
The default workflow is offline. JEV relevance decisions are optional.

## Component boundaries

| Component | Responsibility | Trust rule |
| --- | --- | --- |
| Graphify | Build and query the structural code graph | Navigation evidence, not runtime proof |
| Claude Mem or approved export | Supply selected observations and reviewed `source_paths` | Memory is a hint, not current source truth |
| Jevify runner | Validate paths, build bounded candidates, preserve fallback | Must not alter the structural graph |
| JEV via OpenRouter | Optional relevance decisions | Off by default; paid use requires explicit approval |
| Coding agent | Inspect cited source and report conclusions | Separate graph suggestions, source confirmation, and runtime facts |

## Beta evidence ledger

| Finding | Result | Scope |
| --- | ---: | --- |
| Clean installation | 20/20 | Ubuntu and macOS, candidate `a2f7aee0` |
| Zero configuration | 30/30 | no interaction, candidate `a2f7aee0` |
| Graphify compatibility | pass | pinned candidate receipt |
| Local suite | 8,608 passed | release checkpoint |
| Product benchmark v13 | 0/60, stopped | no product claim |
| Product benchmark v11 | 8 pairs | diagnostic only |

## Allowed public phrasing

- “Jevify is available as a transparent technical beta.”
- “20 of 20 clean installation attempts passed on Ubuntu and macOS.”
- “30 of 30 zero-configuration cases completed without interaction.”
- “The pinned candidate passed the Graphify compatibility check.”
- “8,608 local tests passed.”

## Prohibited conclusions

- Do not claim a product advantage over Graphify.
- Do not attribute a measured gain to JEV.
- Do not treat the eight v11 pairs as public evidence.
- Do not treat graph edges or memory statements as current runtime proof.
- Do not send private memory, source excerpts, or paid API requests without explicit approval.

## Operational rules

1. Confirm `graphify-out/graph.json` matches `git rev-parse HEAD` before using it.
2. Retrieve only user-selected observations through an approved bridge or export.
3. Keep private corpora outside Git with directory mode `0700` and file mode `0600`.
4. Verify cited source before presenting a conclusion.
5. Keep paid JEV off unless the user approves the exact data and cost scope.

## Current collaboration questions

- Graphify: does the adapter preserve graph semantics and fallback behavior?
- Claude Mem: is optional reviewed `source_paths` metadata a safe boundary?
- JEV: is the opt-in decision interface appropriate for later independent evaluation?

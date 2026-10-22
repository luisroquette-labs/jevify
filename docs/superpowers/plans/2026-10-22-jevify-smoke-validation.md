# Jevify operator smoke validation plan

**Goal:** Obtain a bounded same-session signal before investing in longitudinal validation.

**Spec:** `.specs/tasks/draft/jevify-smoke-validation.feature.md`

## Plan

1. Replace the two-stage seven-day receipt with one immutable `receipt.json` using schema v3.
2. Run one 15-minute operator session: five minutes per tool and five minutes for ratings.
3. Score immediately: advance only if Jevify is preferred, scores `>=4/5`, beats Graphify, and
   provides one Jevify-only source-verified connection with zero safety or paid-call failures.
4. Run focused and full gates, review the diff, and integrate one PR.

## Validation loop

- Planning: protocol and thresholds are frozen in the spec.
- Implementation: schema, validator, scorer, tests, runbook, and invitation use the same contract.
- Test: focused tests, Ruff, Pyright, Bandit, full preflight, Graphify AST refresh, and remote CI.
- Repeat: any failure returns to the first affected stage; no follow-up window is introduced.

## Boundaries

- No paid API, long benchmark, incentive, private content, build, or Codespace.
- No invitation or external participant is needed for this smoke test.
- A smoke result is directional evidence only; public comparative claims remain prohibited.

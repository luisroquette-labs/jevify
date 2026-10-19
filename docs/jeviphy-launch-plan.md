# Jeviphy launch plan

## Positioning

Jeviphy is an open-source Graphify fork for Claude Code and Codex. It uses source paths from reviewed memory to focus Graphify before the coding agent answers.

The public claim is deliberately narrow: on the frozen synthetic Click cohort, Jeviphy `fast-source` found 11/40 exact targets in the top five versus 2/40 for unscoped Graphify, with overall p95 of 212.95 ms versus 275.69 ms. Say that Jeviphy performed better on those measured points in this experiment. Present it as a promising result and an invitation to reproduce, never as proof that Jeviphy is generally better than Graphify.

Paid Jev stays optional and off by default. Its 19-call pilot did not improve top-five hits and added latency. This negative result is part of the product story because it shows where the current value comes from.

## Audiences and message

| Audience | What they need to hear | Primary action |
| --- | --- | --- |
| Claude Code and Codex users | Start from files the team already learned matter | Try the 60-second offline demo |
| Graphify contributors | Reviewed source citations can focus the existing graph | Review the implementation and evidence |
| Memory-tool builders | Memory can preserve a verifiable path back to source | Test source-path interoperability |
| Jev and TypeSafe builders | The first typed-question design failed; the evaluation is public | Suggest a better bounded decision design |
| Curators and technical writers | Claims, failures, hashes, and limits are published together | Independently evaluate or list the project |

## Launch record

| Destination | Channel | Status | Evidence |
| --- | --- | --- | --- |
| `@luisroquette` | X, tracked in Social Machine v2.1 | Published | [Portuguese launch](https://x.com/luisroquette/status/2111992863122739227) |
| `@thedoomguy_ai` | X, queued and tracked in Social Machine v3.1 | Published | [English launch](https://x.com/thedoomguy_ai/status/2111993321954398510) |
| Moritz Kremb / ZimaSpace | X mention | Sent | [Evaluation request](https://x.com/thedoomguy_ai/status/2111993628146946250) |
| Claude Memory | X mention | Sent | [Technical critique request](https://x.com/thedoomguy_ai/status/2111993633515671953) |
| Graphify | X mention | Sent | [Upstream review request](https://x.com/thedoomguy_ai/status/2111993639853568203) |
| TypeSafe AI / Jev | X mention | Sent | [Typed-question feedback request](https://x.com/thedoomguy_ai/status/2111993645566206423) |

The v2.1 X API returned `402 credits depleted`, so the approved record was published through the authenticated X web UI and reconciled with the resulting tweet ID. The v3.1 queue accepted its approved item but did not persist a publication ID during the verification window; that item was also published through X web and reconciled with its real tweet ID. Neither fallback used a paid generation API.

## Maintainer-first outreach

The existing 18 October posts stay published. Do not repeat those mentions. From here, use one evidence-backed request per destination and move the technical conversation to the channel each project already uses.

### Graphify

1. Add one concise update to [upstream draft PR #4530](https://github.com/Graphify-Labs/graphify/pull/4530) with the independent Click result, the public demo, and one decision request: should bounded source-cited seeds become an upstream query interface or remain a Jeviphy adapter?
2. Wait for the maintainer response in PR #4530. Keep every Graphify follow-up in that PR so the technical context stays in one place.
3. If Graphify wants the boundary upstream, reduce the proposal to one concern, align its title and tests with `CONTRIBUTING.md`, and keep the Jeviphy product layer outside that PR.

### Claude Mem

1. Open one GitHub Discussion in **Show and tell** or **Ideas**, not an issue: demonstrate the offline workflow and propose an optional `source_paths` interoperability contract.
2. Ask three concrete questions: whether observations can expose stable source paths, how stale or renamed paths should be represented, and what must be redacted before export.
3. Wait 48 hours, then send one short X reply or DM to `@Claude_Memory` linking to the Discussion. Mention their earlier repost and ask for technical critique. Do not open a code PR until the contract is accepted.

### Outreach packet

Every contact uses the same compact structure: the problem in one sentence, the independently measured result in one sentence, one limitation, one suggestion or question, and no more than three links. Use "performed better on the measured points" or "showed a promising result in this cohort". Avoid "beat", "won", "replacement", or any universal comparison. Use the public page for orientation, the reproducible report for evidence, and the relevant PR or Discussion for the conversation. Never present Jeviphy as endorsed by Graphify or Claude Mem, and never attribute the measured gain to paid Jev.

## Autonomous delivery

The campaign does not depend on an open Codex session:

1. A macOS LaunchAgent checks the two maintainer tasks every 15 minutes. It posts the Graphify PR update and creates the Claude Mem Discussion through the authenticated `gh` CLI. Remote HTML markers and a local state file make both actions idempotent.
2. Social Machine v3.1 owns the two public X posts. Its Vercel cron claims one due row at a time from `scheduled_outreach`, publishes the exact approved copy, and persists the resulting post ID or retry state.
3. Conditional follow-ups stay unscheduled. A maintainer reply changes the next message, so automatically repeating a mention would violate the campaign tone.
4. The 2 November scorecard stays unscheduled because its numbers must be computed from the real replies and visits collected by then.

## Fourteen-day cadence

Allow only one outbound Jeviphy touch every 48 hours across GitHub and both X profiles. A substantive reply replaces the next scheduled post; answer the person before continuing the sequence.

| Date and time (America/Sao_Paulo) | Destination | Action | Success signal |
| --- | --- | --- | --- |
| 20 Oct, 10:30 | Graphify PR #4530 | Post the independent evidence and interface question | Maintainer answers the architecture question |
| 24 Oct, 11:00 | Claude Mem GitHub Discussions | Publish the `source_paths` interoperability proposal | Maintainer critiques or accepts the contract |
| 26 Oct, 10:30 | `@Claude_Memory`, only without a Discussion reply | Send one link to the technical Discussion | Reply or referral to the right contributor |
| 28 Oct, 13:30 | `@luisroquette` | Publish the 60-second demo in Portuguese | Demo runs and repository visits |
| 30 Oct, 10:30 | `@thedoomguy_ai` | Explain the independent result and failed paid-Jev test | Reproduction or counterexample |
| 2 Nov, 13:30 | Both audiences through one scorecard post | Report replies, runs, limitations, and next experiment | Independent reproduction or agreed integration step |

## Measurement and decisions

Track page visits, repository visitors, clones, stars, demo completions, technical replies, independent reproductions, and accepted upstream changes. Record the source post for each referral so the two profiles and each outreach message can be compared. A maintainer decision, independent reproduction, or concrete integration experiment outranks reach and impressions.

Continue the campaign after day 14 only if it produces at least one independent reproduction, substantive technical review, or qualified upstream discussion. If none occurs, publish the scorecard and pause outreach instead of increasing frequency. Revise the page if an external run contradicts the current cohort result. Do not promote paid Jev as the cause of the measured speed or retrieval gain unless a new frozen experiment demonstrates it.

## Reusable assets

- [Public evidence page](https://luisroquette-labs.github.io/jeviphy/)
- [Independent complete-workflow comparison](jeviphy-independent-complete-workflow-20261018.md)
- [60-second offline demo](jeviphy-demo.md)
- [Five-stage evidence roadmap](jeviphy-roadmap.md)
- [Upstream Graphify pilot PR](https://github.com/Graphify-Labs/graphify/pull/4530)

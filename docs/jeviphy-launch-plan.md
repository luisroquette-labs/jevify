# Jeviphy launch plan

## Positioning

Jeviphy is an open-source Graphify fork for Claude Code and Codex. It uses source paths from reviewed memory to focus Graphify before the coding agent answers.

The public claim is deliberately narrow: on the frozen synthetic Click cohort, Jeviphy `fast-source` found 11/40 exact targets in the top five versus 2/40 for unscoped Graphify, with overall p95 of 212.95 ms versus 275.69 ms. This is evidence for that local source-cited workflow, not a general benchmark of every repository or task.

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

## Fourteen-day cadence

No more than one Jeviphy publication per calendar day across both profiles. Keep at least 48 hours between planned posts, review the previous post's response before releasing the next one, and pause the sequence when a technical reply deserves an answer.

| Date and time (America/Sao_Paulo) | Profile | Publication | Success signal |
| --- | --- | --- | --- |
| 20 Oct, 10:30 | `@luisroquette` | 60-second offline demo in Portuguese | Repository visits and demo runs |
| 22 Oct, 13:30 | `@thedoomguy_ai` | Moritz Kremb evaluation request | Reply or independent review |
| 24 Oct, 11:00 | `@thedoomguy_ai` | Failed paid-Jev result and what changed | Typed-question design suggestions |
| 26 Oct, 10:30 | `@thedoomguy_ai` | Claude Memory source-path interoperability request | Technical critique or test |
| 28 Oct, 13:30 | `@thedoomguy_ai` | Graphify method thread and upstream review request | Qualified upstream discussion |
| 30 Oct, 10:30 | `@thedoomguy_ai` | TypeSafe request for a better bounded Jev design | Jev design feedback |
| 2 Nov, 13:30 | `@luisroquette` | Public scorecard and next experiment | Reproduction, review, or counterexample |

The four outreach messages in the launch record were mistakenly published together on 18 October instead of being scheduled on this cadence. Their deletion and rescheduling must preserve the correction record and the original resulting URLs.

## Measurement and decisions

Track page visits, repository visitors, clones, stars, demo completions, technical replies, independent reproductions, and accepted upstream changes. Record the source post for each referral so the two profiles and each outreach message can be compared.

Continue the campaign after day 14 only if it produces at least one independent reproduction, substantive technical review, or qualified upstream discussion. Revise the page if an external run contradicts the current cohort result. Do not promote paid Jev as the cause of the measured speed or retrieval gain unless a new frozen experiment demonstrates it.

## Reusable assets

- [Public evidence page](https://luisroquette-labs.github.io/jeviphy/)
- [Independent complete-workflow comparison](jeviphy-independent-complete-workflow-20261018.md)
- [60-second offline demo](jeviphy-demo.md)
- [Five-stage evidence roadmap](jeviphy-roadmap.md)
- [Upstream Graphify pilot PR](https://github.com/Graphify-Labs/graphify/pull/4530)

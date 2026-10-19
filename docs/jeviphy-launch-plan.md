# Jeviphy Maintainer-First Launch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Present Jeviphy to Graphify, Claude Mem, and source-aware coding-agent users with reproducible evidence, restrained claims, autonomous delivery, and no repeated outreach.

**Architecture:** GitHub is the technical conversation layer: one existing Graphify pull request and one Claude Mem Discussion. A macOS LaunchAgent publishes those two approved messages idempotently; Social Machine v3.1 publishes two approved X posts from its persisted queue. Evidence and message copy stay versioned in Jeviphy, while mutable delivery state and traffic snapshots stay outside Git.

**Tech Stack:** Python 3 standard library, `gh` CLI, macOS `launchd`, GitHub Actions, Social Machine v3.1, Supabase Postgres, Vercel Cron, X API.

**Spec:** `docs/jeviphy-roadmap.md`

## Global Constraints

- Public performance claims apply only to the frozen synthetic Click cohort: exact top-five targets were 11/40 for Jeviphy `fast-source` and 2/40 for unscoped Graphify; overall p95 was 212.95 ms and 275.69 ms, respectively.
- Describe the result as “performed better on the measured points in this experiment” or “showed a promising result in this cohort.” Never claim a universal win, replacement, endorsement, or general speed advantage.
- Paid Jev remains optional and outside every performance claim: its 19-call pilot kept top-five hits at 4/19 and added 649.74 ms p50 and 1,083.09 ms p95 API latency.
- Use GitHub and X only. Keep every Graphify follow-up in upstream PR #4530 and every Claude Mem technical proposal in one GitHub Discussion.
- Make no paid model or API call. Publish only the reviewed, versioned copy in `docs/outreach/` and the two persisted Social Machine rows.
- Maintain at least 48 hours between outbound Jeviphy messages. A substantive reply replaces the next optional follow-up; it never causes an extra message.
- Treat GitHub comments, Discussion URLs, X post IDs, persisted queue state, and terminal CI/deployment results as publication evidence. A scheduled row or local log is not publication proof.
- Keep memory corpora, raw questions, private labels, tokens, and traffic snapshots outside Git with mode `0600`.
- Use branch → PR → `jeviphy`; run local checks through `mac-gate`; require current GitHub checks before merge.

## Review Focus

1. **Duplicate delivery:** a prior remote marker or local completion record must prevent a second GitHub publication; Task 1 pins both paths with tests.
2. **Stale installed copy:** the LaunchAgent must execute byte-identical scheduler and message files from the merged Jeviphy commit; Task 2 verifies each file with `cmp` and SHA-256.
3. **Partial provider failure:** a failed GitHub or X request must remain retryable and must not be recorded as published; Tasks 1 and 4 verify failure state.
4. **Cadence collision:** every persisted timestamp must leave at least 48 hours after the previous possible outbound message; Task 2 validates the schedule in UTC.
5. **Unmeasurable success:** page visits and demo completions have no installed analytics source; Task 5 excludes them and uses only GitHub traffic, public replies, persisted post URLs, and independent reproduction evidence.

---

## File and System Map

| Responsibility | Source of truth |
| --- | --- |
| Approved Graphify message | `docs/outreach/graphify-pr-4530.md` |
| Approved Claude Mem message | `docs/outreach/claude-mem-discussion.md` |
| GitHub delivery logic | `scripts/jeviphy_outreach_scheduler.py` |
| LaunchAgent installer | `scripts/install_jeviphy_outreach_launchd.sh` |
| Scheduler regression tests | `tests/test_jeviphy_outreach_scheduler.py` |
| Independent evidence | `docs/jeviphy-independent-complete-workflow-20261018.md` |
| Public explanation | `docs/jeviphy/index.html` and `docs/jeviphy-demo.md` |
| X delivery route | Social Machine `src/app/api/cron/jeviphy-outreach/route.ts` |
| X queue schema | Social Machine `supabase/migrations/20261019113351_create_scheduled_outreach.sql` |
| Mutable GitHub delivery state | `~/.local/share/jeviphy-outreach/state.json` |
| Private measurement snapshots | `~/.local/share/jeviphy-outreach/metrics/` |

## Approved Positioning and Existing Record

Jeviphy is an open-source Graphify fork for Claude Code and Codex. Reviewed memory can supply source paths that narrow the existing Graphify query before the coding agent reads the result. The measured gain came from this bounded local source-cited workflow, not from paid Jev.

The six X messages published on 18 October remain online and must not be repeated: the Portuguese and English launch posts plus one mention each to Moritz Kremb, Claude Memory, Graphify, and TypeSafe AI / Jev. The last one was published at 22:31 BRT, derived from its public X snowflake ID; their URLs remain the historical record in Git and are not additional tasks in this plan.

## Delivery Schedule

| Due time (America/Sao_Paulo) | Destination | Delivery | State before execution |
| --- | --- | --- | --- |
| 21 Oct, 10:30 | Graphify PR #4530 | LaunchAgent, exact reviewed comment | Must move from 20 Oct |
| 24 Oct, 11:00 | Claude Mem GitHub Discussion | LaunchAgent, exact reviewed proposal | Scheduled |
| 28 Oct, 13:30 | `@luisroquette` | Social Machine persisted queue | Queued |
| 30 Oct, 13:30 | `@thedoomguy_ai` | Social Machine persisted queue | Must move from 10:30 |
| 2 Nov, 13:30 or later | Public scorecard | Publish only after evidence review | Conditional, unscheduled |

No reminder, reply, or direct message is scheduled between these rows. Silence from a maintainer is a valid outcome and does not authorize another contact.

### Task 1: Pin Idempotent GitHub Delivery

**Files:**
- Create: `tests/test_jeviphy_outreach_scheduler.py`
- Modify: `scripts/jeviphy_outreach_scheduler.py`

**Interfaces:**
- Consumes: `TASKS`, `graphify_comment()`, `claude_mem_discussion()`, and `main()` from `scripts/jeviphy_outreach_scheduler.py`.
- Produces: regression proof that early runs do nothing, remote markers suppress duplicates, and failed actions do not persist completion state.

Start this task from current `origin/jeviphy` on branch `fix/jeviphy-outreach-cadence-20261020`. This clone does not fetch `jeviphy` through its default refspec, so update it explicitly:

```bash
git fetch origin refs/heads/jeviphy:refs/remotes/origin/jeviphy
git switch -c fix/jeviphy-outreach-cadence-20261020 origin/jeviphy
```

- [ ] **Step 1: Write focused scheduler tests**

Create `tests/test_jeviphy_outreach_scheduler.py` with import-by-path and three tests:

```python
import importlib.util
import json
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parents[1] / "scripts/jeviphy_outreach_scheduler.py"
SPEC = importlib.util.spec_from_file_location("jeviphy_outreach_scheduler", SCRIPT)
assert SPEC and SPEC.loader
scheduler = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scheduler)


def test_before_due_does_not_call_action(monkeypatch, tmp_path):
    called = []
    monkeypatch.setitem(scheduler.ACTIONS, "graphify_comment", lambda: called.append(True))
    monkeypatch.setattr(
        "sys.argv",
        ["scheduler", "--now", "2026-10-21T10:29:59-03:00", "--state-file", str(tmp_path / "state.json")],
    )
    assert scheduler.main() == 0
    assert called == []


def test_graphify_remote_marker_prevents_duplicate(monkeypatch):
    calls = []

    def fake_run_gh(args):
        calls.append(args)
        return "<!-- jeviphy-outreach:graphify-evidence-v1 -->" if "api" in args else ""

    monkeypatch.setattr(scheduler, "run_gh", fake_run_gh)
    assert scheduler.graphify_comment() == "already_present"
    assert len(calls) == 1


def test_claude_mem_remote_marker_prevents_duplicate(monkeypatch):
    payload = {
        "data": {
            "repository": {
                "id": "repo-id",
                "discussionCategories": {"nodes": [{"id": "category-id", "name": "Ideas"}]},
                "discussions": {
                    "nodes": [
                        {
                            "body": "<!-- jeviphy-outreach:claude-mem-source-paths-v1 -->",
                            "url": "https://github.com/thedotmack/claude-mem/discussions/1",
                        }
                    ]
                },
            }
        }
    }
    calls = []

    def fake_run_gh(args):
        calls.append(args)
        return json.dumps(payload)

    monkeypatch.setattr(scheduler, "run_gh", fake_run_gh)
    assert scheduler.claude_mem_discussion() == "already_present"
    assert len(calls) == 1


def test_local_completion_prevents_duplicate(monkeypatch, tmp_path):
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps({"graphify-evidence-v1": {"outcome": "published"}}))
    called = []
    monkeypatch.setitem(scheduler.ACTIONS, "graphify_comment", lambda: called.append(True))
    monkeypatch.setattr(
        "sys.argv",
        ["scheduler", "--now", "2026-10-22T10:30:00-03:00", "--state-file", str(state_file)],
    )
    assert scheduler.main() == 0
    assert called == []


def test_failed_action_does_not_persist_state(monkeypatch, tmp_path):
    state_file = tmp_path / "state.json"
    monkeypatch.setitem(
        scheduler.ACTIONS,
        "graphify_comment",
        lambda: (_ for _ in ()).throw(RuntimeError("provider failed")),
    )
    monkeypatch.setattr(
        "sys.argv",
        ["scheduler", "--now", "2026-10-21T10:30:00-03:00", "--state-file", str(state_file)],
    )
    with pytest.raises(RuntimeError, match="provider failed"):
        scheduler.main()
    assert not state_file.exists() or json.loads(state_file.read_text()) == {}
```

- [ ] **Step 2: Run the new tests and verify the cadence test fails**

Run:

```bash
mac-gate uv run --frozen pytest tests/test_jeviphy_outreach_scheduler.py -q
```

Expected: `test_before_due_does_not_call_action` fails because the current scheduler still considers the Graphify task due on 20 October.

- [ ] **Step 3: Move the Graphify task to the compliant time**

In `scripts/jeviphy_outreach_scheduler.py`, change only the Graphify task timestamp:

```python
{
    "id": "graphify-evidence-v1",
    "due": "2026-10-21T10:30:00-03:00",
    "action": "graphify_comment",
},
```

Retain the 60-second subprocess timeout, file lock, atomic state replacement, and remote markers.

- [ ] **Step 4: Run the focused tests and repository gate**

Run:

```bash
mac-gate uv run --frozen pytest tests/test_jeviphy_outreach_scheduler.py -q
mac-gate uv run --frozen pre-commit run --all-files
mac-gate uv run --frozen pytest -q
```

Expected: all three commands exit `0`; the focused file reports five passing tests.

- [ ] **Step 5: Commit the cadence fix and regression coverage**

```bash
git add tests/test_jeviphy_outreach_scheduler.py scripts/jeviphy_outreach_scheduler.py
git commit -m "fix: enforce Jeviphy outreach cadence"
```

- [ ] **Step 6: Merge the publisher change before reinstalling it**

Push branch `fix/jeviphy-outreach-cadence-20261020`, open one PR to `jeviphy`, and require the full PR check matrix on its latest SHA. Merge only after every required check is green; then verify the post-merge CI and GitHub code-scanning run on the merge SHA. Task 2 must use that merged commit, not the feature-branch checkout.

### Task 2: Reconcile Schedule, Installed Copy, and Baseline

**Files:**
- Read: `scripts/install_jeviphy_outreach_launchd.sh`
- Read: `docs/outreach/graphify-pr-4530.md`
- Read: `docs/outreach/claude-mem-discussion.md`
- Create locally: `~/.local/share/jeviphy-outreach/metrics/baseline-20261020.json`
- Modify remotely: Supabase `public.scheduled_outreach` row with dedupe key `jeviphy-click-result-en-v1`

**Interfaces:**
- Consumes: merged Jeviphy commit, Supabase project `aosyonzvesotxppazugc`, and Social Machine campaign `jeviphy-launch-v1`.
- Produces: byte-identical installed publisher, valid 48-hour cadence, two queued X rows, and a private pre-outreach baseline.

- [ ] **Step 1: Move the English X post to a valid interval**

Through the authorized Supabase connection, execute exactly:

```sql
update public.scheduled_outreach
set publish_after = '2026-10-30T16:30:00Z', updated_at = now()
where campaign = 'jeviphy-launch-v1'
  and dedupe_key = 'jeviphy-click-result-en-v1'
  and status = 'queued'
  and attempts = 0;
```

Then query:

```sql
select dedupe_key, account_key, publish_after, status, attempts,
       published_id, published_url, last_error, length(content) as content_chars
from public.scheduled_outreach
where campaign = 'jeviphy-launch-v1'
order by publish_after;
```

Expected: Portuguese remains `2026-10-28T16:30:00Z`; English becomes `2026-10-30T16:30:00Z`; both have `status = 'queued'`, `attempts = 0`, and `content_chars = 275`.

- [ ] **Step 2: Install the merged GitHub publisher**

From a clean checkout of the merged `jeviphy` branch, run:

```bash
bash scripts/install_jeviphy_outreach_launchd.sh
```

Expected: exit `0`; label `com.luisroquette.jeviphy-outreach` is loaded with a 900-second interval.

- [ ] **Step 3: Verify source and installed copies are identical**

```bash
cmp scripts/jeviphy_outreach_scheduler.py ~/.local/share/jeviphy-outreach/scheduler.py
cmp docs/outreach/graphify-pr-4530.md ~/.local/share/jeviphy-outreach/docs/outreach/graphify-pr-4530.md
cmp docs/outreach/claude-mem-discussion.md ~/.local/share/jeviphy-outreach/docs/outreach/claude-mem-discussion.md
launchd_state="$(launchctl print gui/$(id -u)/com.luisroquette.jeviphy-outreach)"
rg -q 'last exit code = 0' <<< "$launchd_state"
rg -q 'run interval = 900 seconds' <<< "$launchd_state"
```

Expected: every `cmp` exits `0`; `launchctl` shows both expected values. The approved message SHA-256 values are `8d128343151917438348e5a25a4cd88e87087a6eca6ccc84d5c9951020e1ccc5` for Graphify and `8f5fc181863b68628316c173da6642e740e529295f3290b378d13eeae337c95c` for Claude Mem.

- [ ] **Step 4: Capture the private pre-outreach baseline**

```bash
install -d -m 700 ~/.local/share/jeviphy-outreach/metrics
baseline=~/.local/share/jeviphy-outreach/metrics/baseline-20261020.json
jq -n \
  --argjson repo "$(gh api repos/luisroquette-labs/jeviphy)" \
  --argjson views "$(gh api repos/luisroquette-labs/jeviphy/traffic/views)" \
  --argjson clones "$(gh api repos/luisroquette-labs/jeviphy/traffic/clones)" \
  '{captured_at: now | todate, stars: $repo.stargazers_count, forks: $repo.forks_count, views: $views, clones: $clones}' \
  > "$baseline"
chmod 600 "$baseline"
jq '{captured_at, stars, forks, view_count: .views.count, clone_count: .clones.count}' "$baseline"
```

Expected: valid JSON, mode `0600`, and numeric counts. Do not commit the snapshot.

### Task 3: Publish and Verify Maintainer Outreach

**Files:**
- Read: `docs/outreach/graphify-pr-4530.md`
- Read: `docs/outreach/claude-mem-discussion.md`
- Read locally: `~/.local/share/jeviphy-outreach/state.json`

**Interfaces:**
- Consumes: the Task 2 installed scheduler and authenticated `gh` CLI.
- Produces: one Graphify PR comment and one Claude Mem Discussion, each with a stable URL and remote marker.

- [ ] **Step 1: Verify the Graphify action is due without publishing a duplicate**

At or after 21 October 10:30 BRT, run:

```bash
/usr/bin/python3 ~/.local/share/jeviphy-outreach/scheduler.py --dry-run --now 2026-10-21T10:30:00-03:00
```

Expected before publication: `due: graphify-evidence-v1 (graphify_comment)`. Expected after publication: no due line because local state already contains the task.

- [ ] **Step 2: Verify persisted Graphify publication proof**

```bash
gh api --paginate repos/Graphify-Labs/graphify/issues/4530/comments \
  --jq '.[] | select(.body | contains("jeviphy-outreach:graphify-evidence-v1")) | {html_url, created_at, user: .user.login}'
jq '."graphify-evidence-v1"' ~/.local/share/jeviphy-outreach/state.json
```

Expected: exactly one remote comment URL and one local state record with outcome `published` or `already_present`. If the scheduler exits nonzero, read `outreach-error.log`; do not post through another channel, because the next 15-minute run is the retry path.

- [ ] **Step 3: Verify persisted Claude Mem publication proof**

At or after 24 October 11:00 BRT, query the repository Discussions and local state:

```bash
query='query($owner:String!,$name:String!){repository(owner:$owner,name:$name){discussions(first:50,orderBy:{field:CREATED_AT,direction:DESC}){nodes{body url category{name}}}}}'
gh api graphql -f query="$query" -F owner=thedotmack -F name=claude-mem \
  --jq '.data.repository.discussions.nodes[] | select(.body | contains("jeviphy-outreach:claude-mem-source-paths-v1")) | {url, category: .category.name}'
jq '."claude-mem-source-paths-v1"' ~/.local/share/jeviphy-outreach/state.json
```

Expected: exactly one Discussion URL in **Show and tell** or **Ideas** and one local state record. If neither category exists or repository permissions reject creation, leave the task retryable, record the error, and pause this destination without creating an issue or alternate message.

- [ ] **Step 4: Apply the response decision tree**

Use these mutually exclusive outcomes:

| Response | Next action |
| --- | --- |
| Graphify asks for a smaller boundary | Update PR #4530 on its existing branch with that single boundary and tests |
| Graphify prefers an external adapter | Record the decision in Jeviphy and stop upstream code changes |
| Claude Mem accepts or revises `source_paths` | Write a separate interoperability spec before any code PR |
| Maintainer identifies an evidence flaw | Correct the public evidence before further promotion |
| No substantive response | Send nothing else to that maintainer |

### Task 4: Verify X Queue Delivery Without Expanding the Campaign

**Files:**
- Read in Social Machine: `src/app/api/cron/jeviphy-outreach/route.ts`
- Test in Social Machine: `src/app/api/cron/jeviphy-outreach/route.test.ts`
- Read remotely: Supabase `public.scheduled_outreach`

**Interfaces:**
- Consumes: the two Task 2 queue rows and deployed Social Machine cron.
- Produces: at most one persisted X URL per dedupe key, with retry state on failure.

- [ ] **Step 1: Re-run the focused route test before the first due time**

From the Social Machine checkout containing merge commit `ed3183c51c9c12b915124f6094bb2f81d7f7b4c8`, run its existing focused test through `mac-gate`:

```bash
mac-gate npm test -- src/app/api/cron/jeviphy-outreach/route.test.ts
```

Expected: pass with assertions for authorization, due-row claiming, success persistence, and retryable failure.

- [ ] **Step 2: Verify the deployed cron remains protected**

```bash
curl -sS -o /dev/null -w '%{http_code}\n' https://social-machine-v31.vercel.app/api/cron/jeviphy-outreach
```

Expected without the cron secret: `401`.

- [ ] **Step 3: Verify each row after its due time**

Run the Task 2 read query after 28 October 13:30 BRT and again after 30 October 13:30 BRT.

Expected success for the due row: `status = 'published'`, non-null `published_id`, and non-null `published_at`; `published_url` may be null because the publisher treats it as optional. Expected retryable failure before attempt three: `status = 'queued'`, incremented `attempts`, null publication fields, and a bounded `last_error`. Attempt three or a stale processing claim becomes `status = 'failed'` and requires manual reconciliation. Never publish manually while a row is queued or processing, and never requeue a failed row until the account timeline has been checked for an already-created post.

- [ ] **Step 4: Validate the public records**

Open each persisted `published_url`; when it is null, construct `https://x.com/<account_key>/status/<published_id>`. Confirm that the visible account, text, and link match its row. Save only the verified URL and timestamp in the scorecard; do not infer delivery from HTTP `200` on the cron route.

### Task 5: Produce the Evidence Scorecard and Stop or Continue

**Files:**
- Create: `docs/jeviphy-launch-scorecard-20261102.md`
- Read locally: `~/.local/share/jeviphy-outreach/metrics/baseline-20261020.json`
- Modify if evidence changes: `docs/jeviphy/index.html`, `README.md`, and the relevant evaluation report

**Interfaces:**
- Consumes: publication URLs, maintainer responses, GitHub traffic snapshots, and independent reproduction reports.
- Produces: one auditable campaign decision: `continue-one-experiment` or `pause-outreach`.

- [ ] **Step 1: Capture the matching post-campaign snapshot**

Repeat Task 2 Step 4 into `~/.local/share/jeviphy-outreach/metrics/final-20261102.json` and retain mode `0600`.

- [ ] **Step 2: Write the public scorecard with only verifiable fields**

Create `docs/jeviphy-launch-scorecard-20261102.md` with this table and fill every cell from a linked public record or the two private snapshots:

```markdown
| Measure | Result | Evidence |
| --- | --- | --- |
| Graphify substantive technical responses | 0 | PR #4530 comment URLs |
| Claude Mem substantive technical responses | 0 | Discussion reply URLs |
| Independent reproductions | 0 | Public issue, PR, or report URLs |
| Accepted integration experiments | 0 | Public maintainer decision URL |
| GitHub stars delta | 0 | Private baseline/final snapshots |
| GitHub unique visitors delta | 0 | Private baseline/final snapshots |
| GitHub unique cloners delta | 0 | Private baseline/final snapshots |
| Published X records | 0/2 | Persisted X URLs |
```

Replace the initial zeroes with observed values. Report GitHub traffic as a before/after 14-day-window difference, not as traffic caused by the campaign. A substantive response must discuss the API boundary, implementation, measurement, or reproducibility. A like, repost, impression, generic compliment, or unanswered mention does not qualify. An independent reproduction must name the tested commit and command and report an outcome.

- [ ] **Step 3: Apply the predeclared decision gate**

Set `Decision: continue-one-experiment` only if at least one independent reproduction, substantive maintainer review, or accepted integration experiment exists. Otherwise set `Decision: pause-outreach`. Reach and star growth cannot open the gate by themselves.

- [ ] **Step 4: Correct contradicted claims before publishing the scorecard**

If an external run contradicts the Click result, update the report, README, and public page in the same PR as the scorecard. Keep both the original result and the contradiction visible, identify the tested commits and environments, and narrow the claim. If no contradiction exists, change only the scorecard.

- [ ] **Step 5: Validate and commit the scorecard**

```bash
mac-gate uv run --frozen pre-commit run --all-files
git add docs/jeviphy-launch-scorecard-20261102.md docs/jeviphy/index.html README.md docs/jeviphy-independent-complete-workflow-20261018.md
git commit -m "docs: report Jeviphy launch evidence"
```

Expected: pre-commit exits `0`; `git diff --cached` contains the scorecard and only evidence corrections actually required by Step 4. Open one PR to `jeviphy`, wait for all checks, merge, and verify the GitHub Pages workflow on the merge SHA.

## Completion Criteria

The launch is complete when the four fixed messages have terminal evidence, the scorecard records the real outcome, and its decision gate is applied. The four fixed deliveries do not require an open Codex session. After the second X post, the campaign pauses automatically; the next agent session evaluates replies and writes the scorecard, and no conditional follow-up is sent before that review.

The next development plan begins only from a maintainer-requested boundary, an independent reproduction, or a demonstrated evidence correction. A new audience list, additional social network, paid promotion, or broader automation is outside this plan.

## Reusable Evidence

- [Public evidence page](https://luisroquette-labs.github.io/jeviphy/)
- [Independent complete-workflow comparison](jeviphy-independent-complete-workflow-20261018.md)
- [60-second offline demo](jeviphy-demo.md)
- [Five-stage evidence roadmap](jeviphy-roadmap.md)
- [Upstream Graphify pilot PR](https://github.com/Graphify-Labs/graphify/pull/4530)

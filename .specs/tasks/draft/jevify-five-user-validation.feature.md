# Jevify Five-User Product Validation

Status: draft

## Question

After Jevify reliably orchestrates the complete Graphify workflow, do active
Graphify users receive enough additional value to prefer Jevify and use it
again on a later change?

This validation tests product pull. It does not test JEV quality, benchmark
latency, or broad market demand.

## Eligible participant

A participant must have used Graphify on a real repository before the session
or be actively evaluating Graphify with authority to inspect that repository.
The participant must be able to run Graphify and Jevify locally without sharing
private source, memory observations, credentials, or raw graph output.

Luis, the implementing agent, and anyone who designed the Jevify retrieval or
question-ranking behavior are ineligible as participants.

## Protocol

Each of five participants uses one repository they understand. Before either
condition, the facilitator creates two private isolated worktrees from the same
commit and copies the same accepted starting Graphify artifacts into each; the
same bounded repository change is then applied to both. The direct Graphify and
Jevify orders alternate across participants, but neither condition can consume
artifacts written by the other. Each participant:

1. Updates each isolated graph after the identical real repository change.
2. Identifies the next architectural question worth investigating.
3. Rates freshness trust and question usefulness on a five-point scale.
4. Selects which tool they would start with on the next change and explains why.
5. Receives no prompt to reuse either tool for seven days; repeat use is counted
   only from a timestamped invocation receipt on a later commit, created no
   more than seven days after the initial session and with no reminder sent.

The evaluator writes one immutable initial record after the session and one
immutable terminal record after the observation window. The terminal record
contains the initial record's SHA-256, so later outcomes cannot rewrite the
locked ratings. Records contain only participant ID, eligibility evidence,
tool order, structured ratings, source-verified outcome categories, timestamps,
and run-receipt hashes.

## Safety and external-action boundary

Recruitment messages and scheduling are external sends and require explicit
current approval before transmission. Drafting the message, evaluator, schema,
and candidate list is allowed without sending. No paid API, incentive,
participant credential, private repository content, or private memory corpus is
requested or stored.

## Gates

Continue treating Jevify as a standalone product hypothesis only if all are true:

- Five eligible participants complete the first session.
- At least three of five prefer to start with Jevify on the next change.
- At least three of five reuse Jevify on a later commit within seven days without a reminder.
- At least two of five report a source-verified useful question or connection they did not identify in the direct Graphify condition.
- No run falsely reports a stale graph as current or an incomplete graph as updated.
- No run makes a paid JEV or other paid provider call.

If preference or repeat use misses its threshold, position Jevify as a Graphify
extension or upstream contribution rather than a standalone product. A false
freshness or update-success claim ends the frozen round as `insufficient_evidence`.
Any retest starts a new versioned manifest and directory after the defect is fixed;
the failed round remains immutable and visible in the report.

## Outputs

- Private append-only initial and terminal participant records with mode `0600`.
- Public aggregate scorecard with no identities, private paths, prompts, code, or memory.
- One decision: `continue_product`, `graphify_extension`, or `insufficient_evidence`.

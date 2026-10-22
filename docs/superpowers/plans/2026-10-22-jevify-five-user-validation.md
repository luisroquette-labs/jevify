# Jevify Five-User Product Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Determine whether five eligible Graphify users prefer Jevify and reuse it on a later commit, without collecting private source or running paid JEV.

**Architecture:** Add a small local evaluator that combines an immutable initial record with an immutable terminal record linked by SHA-256, then scores exactly five participant bundles against predeclared gates. Keep recruitment and sessions human-facing and separate from the engineering acceptance plan; publish only aggregate outcomes and use the mechanical result to choose standalone-product, Graphify-extension, or insufficient-evidence positioning.

**Tech Stack:** Python 3.10+, standard library, pytest, JSON/Markdown, Git, existing Jevify private-evidence permissions.

**Spec:** `.specs/tasks/draft/jevify-five-user-validation.feature.md`

## Global Constraints

- Do not send recruitment messages or schedule sessions without explicit current approval for those external actions.
- Recruit exactly five eligible Graphify users; Luis and Jevify designers are ineligible.
- Collect no repository source, raw graph, private path, memory corpus, credential, provider payload, or participant identity in Git.
- Participant receipt directories use mode `0700`; each `initial.json` and `terminal.json` uses mode `0600`, is created once, and is never overwritten.
- Make zero paid JEV or other paid provider calls.
- Freeze participant eligibility, tool order, questions, gates, and scoring code before reading outcomes.
- Give both conditions byte-identical starting graph/manifest artifacts and the same commit/diff in separate private worktrees; never run both against one mutable checkout.
- A false freshness or false update-success claim pauses the affected slot and remains visible in the report.
- Do not offer payment, incentives, discounts, or product access without separate approval.
- Use one task branch and one PR to `jevify`; run tests and lint only through `mac-gate`; never run a local build.

## Review Focus

1. **Ineligible or conflicted participant:** reject designers, duplicate people, and users without prior Graphify experience; Task 1 pins eligibility validation.
2. **Reminder-contaminated reuse:** count repeat use only from a later-commit receipt created without a reminder during the seven-day window; Tasks 1 and 3 enforce it.
3. **Private-data leakage:** reject any receipt containing paths, prompts, source text, memory text, emails, or names; Task 1 tests every forbidden key.
4. **Missing or contradictory receipts:** return `insufficient_evidence`, never infer success from partial sessions; Task 2 tests all denominator failures.
5. **Commercial overclaim:** automatically select `graphify_extension` when preference or repeat-use thresholds fail; Task 4 binds public copy to the mechanical decision.

The runbook also pins isolation as an acceptance condition: compare the SHA-256 of both starting `graph.json` and manifest files before timing either condition, then reject the slot if either hash differs.

---

## File and Interface Map

| Responsibility | File |
| --- | --- |
| Validation behavior contract | `.specs/tasks/draft/jevify-five-user-validation.feature.md` |
| Private event schema | `benchmarks/jevify-user-validation/receipt.schema.json` |
| Aggregate scorecard schema | `benchmarks/jevify-user-validation/scorecard.schema.json` |
| Validator and scorer | `tools/jevify_user_validation.py` |
| Unit tests | `tests/test_jevify_user_validation.py` |
| Participant runbook | `docs/jevify-user-validation-runbook.md` |
| Recruitment draft | `docs/outreach/jevify-user-validation-invite.md` |
| Aggregate result | `benchmarks/jevify-user-validation/scorecard.json`, `scorecard.md` |
| Public interpretation | `docs/jevify-user-validation-report.md`, `docs/jevify-roadmap.md` |

### Task 1: Freeze a Privacy-Safe Receipt Contract

**Files:**
- Create: `benchmarks/jevify-user-validation/receipt.schema.json`
- Create: `tools/jevify_user_validation.py`
- Create: `tests/test_jevify_user_validation.py`

**Interfaces:**
- Consumes: one private participant directory containing `initial.json` and `terminal.json`.
- Produces: `InitialRecord`, `TerminalRecord`, combined `ParticipantReceipt`, `load_receipt_bundle(path) -> ParticipantReceipt`, and a specific validation error for unsafe or incomplete input.

- [ ] **Step 1: Write failing valid-receipt and privacy tests**

```python
INITIAL = {
    "schema_version": 1,
    "stage": "initial",
    "participant_id": "p01",
    "eligible": True,
    "conflicted": False,
    "tool_order": ["graphify", "jevify"],
    "initial_at": "2026-10-22T15:00:00Z",
    "initial_commit": "a" * 40,
    "freshness_correct": True,
    "update_correct": True,
    "graphify_usefulness": 3,
    "jevify_usefulness": 5,
    "freshness_trust": 5,
    "preferred_next": "jevify",
    "novel_source_verified_outcome": True,
    "paid_request_count": 0,
    "initial_run_sha256": "c" * 64,
}

TERMINAL = {
    "schema_version": 1,
    "stage": "terminal",
    "participant_id": "p01",
    "observed_at": "2026-10-29T15:00:00Z",
    "repeat_at": "2026-10-25T15:00:00Z",
    "later_commit": "b" * 40,
    "repeat_used": True,
    "repeat_without_reminder": True,
    "reminder_sent": False,
    "paid_request_count": 0,
    "repeat_run_sha256": "d" * 64,
    # private_bundle replaces this sentinel with SHA-256(initial.json bytes).
    "initial_record_sha256": "AUTO",
}


def test_valid_receipt_bundle_loads(private_bundle):
    assert load_receipt_bundle(private_bundle(INITIAL, TERMINAL)).participant_id == "p01"


@pytest.mark.parametrize("forbidden", [
    "name", "email", "repo_path", "question", "prompt", "source", "memory", "credential",
])
def test_private_content_keys_are_rejected(private_bundle, forbidden):
    with pytest.raises(ValueError, match="forbidden private field"):
        load_receipt_bundle(private_bundle({**INITIAL, forbidden: "secret"}, TERMINAL))
```

- [ ] **Step 2: Run tests and verify the module is absent**

```bash
mac-gate uv run --frozen pytest tests/test_jevify_user_validation.py -q
```

Expected: FAIL during collection because `tools.jevify_user_validation` does not exist.

- [ ] **Step 3: Implement strict dataclass parsing**

```python
@dataclass(frozen=True)
class InitialRecord:
    participant_id: str
    eligible: bool
    conflicted: bool
    tool_order: tuple[Literal["graphify", "jevify"], Literal["graphify", "jevify"]]
    initial_at: datetime
    initial_commit: str
    freshness_correct: bool
    update_correct: bool
    graphify_usefulness: int
    jevify_usefulness: int
    freshness_trust: int
    preferred_next: Literal["graphify", "jevify", "neither"]
    novel_source_verified_outcome: bool
    paid_request_count: int
    initial_run_sha256: str


@dataclass(frozen=True)
class TerminalRecord:
    participant_id: str
    observed_at: datetime
    repeat_at: datetime | None
    later_commit: str | None
    repeat_used: bool
    repeat_without_reminder: bool
    reminder_sent: bool
    paid_request_count: int
    repeat_run_sha256: str | None
    initial_record_sha256: str
```

Define `ParticipantReceipt` as the combined immutable view used by the scorer. The `private_bundle` fixture writes canonical JSON for the initial record, hashes those exact bytes, and replaces the `AUTO` test sentinel before writing the terminal record. Parse timestamps as timezone-aware UTC. Verify `terminal.initial_record_sha256 == sha256(initial.json bytes)`. Reject unknown keys, mismatched participant IDs, duplicate participant IDs at aggregation time, non-40-character lowercase hexadecimal commits, non-64-character lowercase hexadecimal hashes, ratings outside `1..5`, repeated tool names, repeat use on the same commit, repeat use without a run hash, a reminder-contaminated repeat, a repeat timestamp outside `(initial_at, initial_at + 7 days]`, an observation before the seventh-day boundary, or files whose mode exposes group/other permissions.

- [ ] **Step 4: Add exact invalid-state tests**

```python
@pytest.mark.parametrize("stage, change, message", [
    ("initial", {"eligible": False}, "participant is not eligible"),
    ("initial", {"conflicted": True}, "participant is conflicted"),
    ("initial", {"tool_order": ["jevify", "jevify"]}, "tool order"),
    ("initial", {"graphify_usefulness": 6}, "rating"),
    ("terminal", {"later_commit": "a" * 40}, "later commit"),
    ("terminal", {"repeat_run_sha256": None}, "repeat run"),
    ("terminal", {"reminder_sent": True}, "reminder"),
    ("terminal", {"repeat_at": "2026-10-30T15:00:01Z"}, "seven-day window"),
    ("terminal", {"paid_request_count": 1}, "paid request"),
])
def test_invalid_receipt_is_rejected(private_bundle, stage, change, message):
    initial, terminal = dict(INITIAL), dict(TERMINAL)
    (initial if stage == "initial" else terminal).update(change)
    with pytest.raises(ValueError, match=message):
        load_receipt_bundle(private_bundle(initial, terminal))
```

- [ ] **Step 5: Run focused tests and commit**

```bash
mac-gate uv run --frozen pytest tests/test_jevify_user_validation.py -q
mac-gate uv run --frozen ruff check tools/jevify_user_validation.py tests/test_jevify_user_validation.py
```

```bash
git add .specs/tasks/draft/jevify-five-user-validation.feature.md \
  benchmarks/jevify-user-validation/receipt.schema.json \
  tools/jevify_user_validation.py tests/test_jevify_user_validation.py
git commit -m "feat: define private Jevify user-validation receipts"
```

### Task 2: Implement the Mechanical Product Decision

**Files:**
- Create: `benchmarks/jevify-user-validation/scorecard.schema.json`
- Modify: `tools/jevify_user_validation.py`
- Modify: `tests/test_jevify_user_validation.py`

**Interfaces:**
- Consumes: exactly five unique `ParticipantReceipt` values.
- Produces: `ValidationScore`, `score(receipts) -> ValidationScore`, and `continue_product | graphify_extension | insufficient_evidence`.

- [ ] **Step 1: Write failing threshold tests**

```python
def test_all_gates_pass_returns_continue_product(valid_receipts):
    result = score(valid_receipts(prefer=3, repeat=3, novel=2))
    assert result.decision == "continue_product"


@pytest.mark.parametrize(("prefer", "repeat"), [(2, 3), (3, 2), (2, 2)])
def test_preference_or_repeat_failure_returns_extension(valid_receipts, prefer, repeat):
    assert score(valid_receipts(prefer=prefer, repeat=repeat, novel=2)).decision == (
        "graphify_extension"
    )


def test_less_than_five_unique_receipts_is_insufficient(valid_receipts):
    assert score(valid_receipts(count=4)).decision == "insufficient_evidence"


def test_false_freshness_is_insufficient_and_pauses_slot(valid_receipts):
    receipts = valid_receipts()
    receipts[0] = replace(receipts[0], freshness_correct=False)
    result = score(receipts)
    assert result.decision == "insufficient_evidence"
    assert result.paused_participant_ids == ("p01",)
```

- [ ] **Step 2: Run tests and confirm the scorer is absent**

Run `mac-gate uv run --frozen pytest tests/test_jevify_user_validation.py -q`.

Expected: FAIL because `score` and `ValidationScore` do not exist.

- [ ] **Step 3: Implement the frozen arithmetic**

```python
@dataclass(frozen=True)
class ValidationScore:
    completed: int
    prefer_jevify: int
    repeated_jevify: int
    novel_source_verified: int
    false_freshness: int
    false_update: int
    paid_requests: int
    paused_participant_ids: tuple[str, ...]
    decision: Literal["continue_product", "graphify_extension", "insufficient_evidence"]
```

Return `insufficient_evidence` before commercial scoring when there are not exactly five unique eligible receipts, any slot is paused, or paid requests are nonzero. Otherwise return `continue_product` only for preference `>=3`, reminder-free later-commit repeat `>=3`, and novel source-verified outcomes `>=2`; return `graphify_extension` for every other complete cohort.

- [ ] **Step 4: Add deterministic serialization and schema tests**

Serialize with `json.dumps(asdict(score), sort_keys=True, separators=(",", ":"))`. Parse `scorecard.schema.json` with the standard library and assert its `required` names and declared primitive types match `ValidationScore`; do not add a schema library for this bounded object. Shuffle receipt order 50 times and assert byte-identical output.

- [ ] **Step 5: Run focused tests and commit**

```bash
mac-gate uv run --frozen pytest tests/test_jevify_user_validation.py -q
mac-gate uv run --frozen ruff check tools/jevify_user_validation.py tests/test_jevify_user_validation.py
```

```bash
git add benchmarks/jevify-user-validation/scorecard.schema.json \
  tools/jevify_user_validation.py tests/test_jevify_user_validation.py
git commit -m "feat: score Jevify product pull mechanically"
```

### Task 3: Prepare and Run the Five Participant Slots

**Files:**
- Create: `docs/jevify-user-validation-runbook.md`
- Create: `docs/outreach/jevify-user-validation-invite.md`
- Create after approved sessions: private receipts outside Git only

**Interfaces:**
- Consumes: merged amplification release SHA and explicit approval before external sends.
- Produces: five valid private receipts without source or identity data.

- [ ] **Step 1: Write the participant runbook**

Include eligibility check, alternating order `GJ/JG/GJ/JG/GJ`, one real repository change duplicated into two private worktrees, the two fixed prompts `$graphify --update` and `$jevify --update`, ten minutes per condition, five minutes for locked ratings, five-point rating anchors, source-verification instruction, receipt hashing, and the no-reminder seven-day rule. Before either prompt, require equal starting commit plus equal SHA-256 for `graph.json` and `manifest.json`; reject the slot on mismatch. State that facilitators cannot help choose a question or interpret either tool before ratings are locked.

- [ ] **Step 2: Draft but do not send the invitation**

Use this bounded copy:

```text
Estou validando uma camada local e experimental sobre o Graphify. A sessão leva
25 minutos e usa um repositório que você já pode inspecionar; nenhum código,
grafo, memória ou credencial será enviado. Depois, durante sete dias, não haverá
lembrete de reutilização. Não há pagamento nem API paga. Você já usou Graphify
em um projeto real e aceitaria comparar os dois fluxos localmente?
```

Stop here until Luis explicitly approves the recipient list and external sends.

- [ ] **Step 3: Freeze five participant IDs and tool order before sessions**

Write a private mode-`0600` manifest containing only `p01` through `p05`, eligibility evidence category, alternating order, merged candidate SHA, and session date. Create the manifest and every event with `os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)` so an existing record cannot be overwritten. Hash the manifest and record only its SHA-256 publicly.

- [ ] **Step 4: Conduct each 25-minute initial session after approval**

Create two isolated private worktrees at the frozen commit, seed both from the same accepted Graphify artifacts, apply the same diff, and verify the starting hashes. Run the conditions in the frozen order, removing provider credentials in both. Create `pNN/initial.json` immediately after ratings lock. Do not mutate the frozen manifest; write the initial-record hash to a separate append-only `events/pNN-initial.json`. Stop an affected slot on isolation mismatch, false freshness, false update success, paid request, or privacy-schema failure; preserve the failed record and do not substitute a sixth participant silently.

- [ ] **Step 5: Observe seven days without a reuse reminder**

Count repeat use only when the participant supplies a Jevify run-receipt hash from a different commit within seven days. At day seven, create `pNN/terminal.json` exactly once, referencing the byte hash of `initial.json`. For a slot without reuse, write `repeat_used=false`, `repeat_at=null`, `later_commit=null`, `repeat_run_sha256=null`, and `repeat_without_reminder=false`; do not contact the participant first.

- [ ] **Step 6: Validate the five receipts and commit only the runbook/draft**

```bash
mac-gate uv run --frozen python -m tools.jevify_user_validation validate \
  --manifest "$HOME/.local/share/jevify/user-validation/manifest.json"
```

Expected: `5 valid receipts; 0 private-field violations; 0 paid requests`, or a nonzero exit naming the affected participant IDs.

```bash
git add docs/jevify-user-validation-runbook.md docs/outreach/jevify-user-validation-invite.md
git commit -m "docs: define the Jevify five-user validation"
```

### Task 4: Apply the Product Decision Without Interpretation Drift

**Files:**
- Create: `benchmarks/jevify-user-validation/scorecard.json`
- Create: `benchmarks/jevify-user-validation/scorecard.md`
- Create: `docs/jevify-user-validation-report.md`
- Modify: `docs/jevify-roadmap.md`
- Modify only after a supported decision: `README.md`, `docs/jevify/index.html`

**Interfaces:**
- Consumes: five validated private receipts and frozen manifest hash.
- Produces: aggregate scorecard, report, and one mechanically selected product position.

- [ ] **Step 1: Generate the aggregate scorecard**

```bash
mac-gate uv run --frozen python -m tools.jevify_user_validation score \
  --manifest "$HOME/.local/share/jevify/user-validation/manifest.json" \
  --json benchmarks/jevify-user-validation/scorecard.json \
  --markdown benchmarks/jevify-user-validation/scorecard.md
```

Expected: exit `0` with one of `continue_product`, `graphify_extension`, or `insufficient_evidence`; outputs contain counts only.

- [ ] **Step 2: Write the public report from the scorecard**

Report eligibility, cohort size, tool order, preference, repeat use, novel verified outcomes, failures, manifest hash, candidate SHA, and the mechanical decision. Do not include quotes, identities, repositories, paths, questions, prompts, code, or receipt hashes.

- [ ] **Step 3: Apply the exact positioning selected by the scorer**

- `continue_product`: keep Jevify as a technical-beta product hypothesis and state only the five-user aggregate result.
- `graphify_extension`: describe Jevify as a Graphify extension/experimental workflow and remove standalone-product language.
- `insufficient_evidence`: retain the current technical-beta wording and state which denominator or safety gate remains open.

- [ ] **Step 4: Run gates, review, and integrate one PR**

```bash
mac-gate uv run --frozen pytest tests/test_jevify_user_validation.py -q
mac-gate uv run --frozen ruff check tools/jevify_user_validation.py tests/test_jevify_user_validation.py
mac-gate uv run --frozen pyright tools/jevify_user_validation.py
git diff --check
```

Commit the schemas, scorer, aggregate scorecard, report, roadmap, and supported copy. Push one task branch, open one PR to `jevify`, review it autonomously, require all current checks green on the latest SHA, merge, and verify post-merge CI and Pages.

## Completion Gate

This validation is complete only when five eligible initial sessions and the seven-day observation window have terminal receipts, the scorer has selected one decision, private-data checks pass, the aggregate report is merged, and public positioning matches the mechanical decision. Until then, Jevify remains a technical beta and JEV remains optional and unproven.

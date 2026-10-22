# Jevify operator smoke validation implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a short, fair operator smoke test that separates Graphify's structural work, Jevify's orchestration, and reviewed-memory value.

**Architecture:** Keep one private schema-v4 receipt as the trust boundary. The validator rejects unequal or cold starting conditions, unsafe target resolution, incorrect attribution, and an unsupported comparative claim before the scorer can advance the product. Graph-only success advances only to a reviewed-memory smoke.

**Tech Stack:** Python 3.12, dataclasses, JSON Schema, pytest, Ruff, Pyright, Bandit.

**Spec:** `.specs/tasks/draft/jevify-smoke-validation.feature.md`

## Global Constraints

- No paid API, live or precomputed JEV decisions, long benchmark, build, Codespace, private source, prompt, memory, or credential in Git.
- Run typecheck, lint, and tests only through `mac-gate`.
- Compare Graphify and Jevify from identical warm graph, manifest, commit, and diff hashes.
- Graphify is the structural engine; Jevify routes, verifies, and queries it.
- Two consecutive self-review passes must find no substantial executable improvement before push.

## Review Focus

- A cold Jevify bootstrap followed by a warm Graphify no-op must be rejected.
- A graph-only Jevify run must report memory value as `not_tested`.
- A reviewed-memory run must rate memory as `helpful` or `not_helpful`.
- Wrong target resolution or attribution must invalidate the smoke.
- A token or latency claim without equal-work evidence must be `unsupported` and invalidate the smoke; no claim is `not_made`.

---

### Task 1: Freeze the schema-v4 evidence contract

**Files:**
- Modify: `benchmarks/jevify-user-validation/receipt.schema.json`
- Modify: `benchmarks/jevify-user-validation/scorecard.schema.json`
- Test: `tests/test_jevify_user_validation.py`

**Interfaces:**
- Consumes: one mode-`0600` `receipt.json` inside a mode-`0700` directory.
- Produces: a bounded public scorecard with no private content.

- [x] **Step 1: Write failing tests for warm starts, attribution, route, and memory modes**
- [x] **Step 2: Confirm the schema-v3 implementation cannot construct the schema-v4 receipt; the queued red run was canceled before execution**
- [x] **Step 3: Add the schema-v4 fields and decision enum**
- [x] **Step 4: Run the focused test and confirm 49 tests pass**

### Task 2: Enforce scoring semantics

**Files:**
- Modify: `tools/jevify_user_validation.py`
- Test: `tests/test_jevify_user_validation.py`

**Interfaces:**
- Consumes: `SmokeReceipt` with `memory_mode`, `memory_value`, and evidence booleans.
- Produces: `proceed_to_memory_smoke`, `proceed_to_external_validation`, `revise_or_extension`, or `invalid_smoke`.

- [x] **Step 1: Reject cold starts and inconsistent memory-mode values during parsing**
- [x] **Step 2: Invalidate wrong target, attribution, comparative claim, freshness, update, paid-use evidence**
- [x] **Step 3: Limit graph-only success to `proceed_to_memory_smoke`**
- [x] **Step 4: Require helpful reviewed memory before external validation**

### Task 3: Align the operator protocol

**Files:**
- Modify: `docs/jevify-user-validation-runbook.md`
- Modify: `.specs/tasks/draft/jevify-smoke-validation.feature.md`

**Interfaces:**
- Consumes: two isolated warm worktrees with identical starting hashes and diff.
- Produces: five locked operator answers plus machine-recorded route and evidence hashes.

- [x] **Step 1: State that cold-versus-warm comparisons are invalid**
- [x] **Step 2: State that Graphify builds the structure and Jevify orchestrates it**
- [x] **Step 3: Mark graph-only memory value as `not_tested`**
- [x] **Step 4: Document the next decision for each valid result**

### Task 4: Validate and integrate

**Files:**
- Modify: `graphify-out/*` through AST-only `graphify update .`

**Interfaces:**
- Consumes: the completed diff.
- Produces: one reviewed PR merged into `jevify` with green checks.

- [x] **Step 1: Run focused tests, Ruff, and Pyright through `mac-gate`**
- [x] **Step 2: Run AST-only `graphify update .` with provider keys unset**
- [x] **Step 3: Run the full repository gate through `mac-gate`**
- [x] **Step 4: Complete two consecutive self-review passes with no substantial findings**
- [ ] **Step 5: Commit, push, open one PR, wait for green checks, merge, and verify post-merge CI**

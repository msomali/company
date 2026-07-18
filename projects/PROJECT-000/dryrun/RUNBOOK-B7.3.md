---
artifact_id: projects/PROJECT-000/dryrun/RUNBOOK-B7.3.md
title: B7.3 dry-run runbook — §88 checks 6, 8, 9 (owner-solo legs + agent support)
type: runbook
project: PROJECT-000
owner: human owner (B7.3 is plan-row (H)); drafted by bootstrap agent
version: "1.0"
status: READY_FOR_REVIEW
sensitivity: internal
created: "2026-07-18"
updated: "2026-07-18"
---

# B7.3 Dry-Run Runbook — §88 checks 6, 8, 9

Authored 2026-07-18 after the owner caught the gap: plan row B7.3 existed
with no written procedure anywhere (B7.4 finding, RUNBOOK-B7.2 friction
list). Check texts below are verbatim v2 §88; procedures are derived from
the mechanisms as implemented (`approvals.py`, `dispatcher.py`, the §51
register), not improvised.

## Check 6 — separation of duties (COMPLETED 2026-07-18)

> A GitHub approval attempted from `agenticfoundrybot` on its own PR is
> rejected (author-review block), and a merge attempted without the human
> owner's review is blocked by required reviews.

Executed on owner instruction (12:23 PDT) against episode PR #58: leg A
self-approval → HTTP 422 author-review block; leg B faithful merge attempt
(after read-only `reviewDecision: REVIEW_REQUIRED` verification, BA-2
interlock) → HTTP 405 required-review block, nothing merged. Evidence:
`episodes/TASK-001/evidence/check6-separation-of-duties.md`.

## Check 8 — SSE/DPC approvals captured into gate records

> SSE/DPC human-held approvals are issued in `#approvals` and captured into
> gate records by the dispatcher.

**Channel of record:** no `#approvals` channel exists. Per the §51 register
(`control/registers/section-51-owner-and-section-86-signature.md`), the
designated equivalent is a **GitHub PR review by @msomali**; the textual
format is parsed by `approvals.py` (`APPROVE|REJECT TASK-### <GATE>`,
line-start; malformed lines ignored, never inferred; approver must be the
§51 owner — bot reviews refused).

**State prerequisites (machine-enforced, §82.5):** SSE requires
`SECURITY_REVIEW`; DPC requires `PRIVACY_COMPLIANCE_REVIEW`.

Procedure:

1. **[A]** Dispatcher walks TASK-001 `INTAKE → DISCOVERY → REQUIREMENTS →
   DESIGN → DELIVERY_PLAN → IMPLEMENTATION → QUALITY_REVIEW` via
   `dispatcher.transition()` (host, dispatcher-user pattern of check 1).
   Each edge's evidence string cites real artifacts: check-3 dispatch
   capture, task.yaml criteria, implementation note, PR #53 commits,
   521/521 tests + SAT cycle 1. Commits land on `dispatch/TASK-001`
   (state.yaml + log.jsonl per transition — §82.4/§82.6).
2. **[H]** Owner issues one PR review on episode PR #58 whose body carries,
   each on its own line (reference = the review URL):
   `APPROVE TASK-001 SAT` (unlocks SECURITY_REVIEW; reference the SAT
   cycle-2 recommendation), then `APPROVE TASK-001 SSE`, then
   `APPROVE TASK-001 DPC`. One review with three lines is valid
   (`parse_decisions` returns all; applied in order).
3. **[A]** Capture run on the host: `ApprovalsCapture(dispatcher)` with
   approver `msomali` + review URL. Expected: immutable records
   `projects/PROJECT-000/gates/GATE-TASK-001-SAT-1.yaml`, `-SSE-1.yaml`,
   `-DPC-1.yaml`; state advances to `PRODUCTION_READINESS`; every decision
   logged (`gate_decision` events).
4. Evidence: capture stdout, record files, state history — committed to the
   episode.

**Pass =** SSE and DPC records exist with `approval_message_ref` = the
owner's review, and state history shows the two gate transitions.

## Check 9 — release-branch merge blocked without human APPROVE

> A merge attempted to the release branch without the human `APPROVE` is
> blocked; with it, it succeeds.

**Setup that does not yet exist (owner-only):** the repo has no `release`
branch and no protection rule for one; branch protection is invisible to
and unconfigurable by the bot token.

Procedure:

1. **[H]** Owner creates branch `release` from current `main` and adds
   protection: require ≥1 approving review (code owners), required status
   checks as on `main`.
2. **[H]** Prerequisite gates to reach the HUMAN gate state:
   `APPROVE TASK-001 DCE` (→ `PRODUCT_ACCEPTANCE`), `APPROVE TASK-001 PJM`
   (→ `HUMAN_RELEASE_AUTHORIZATION`) — same channel + capture as check 8.
3. **[A]** Bot opens the release PR (base `release`, head `main`).
4. **[A] Blocked leg:** with zero reviews, read-only probe
   (`reviewDecision` must read `REVIEW_REQUIRED`), then faithful merge
   attempt via API with true head sha (BA-2 interlock per check 6).
   Expected: HTTP 405, nothing merged, no `GATE-TASK-001-HUMAN-*` record
   exists.
5. **[H] Succeeds leg:** owner issues `APPROVE TASK-001 HUMAN` on the
   release PR (capture emits `GATE-TASK-001-HUMAN-1.yaml`, state →
   `DEPLOYMENT`), submits the approving review, and **merges** (merge is
   always the owner's act — BA-2).
6. Evidence: both attempt outputs, the HUMAN gate record, state history,
   merge SHA — committed to the episode.

**Pass =** the same merge that failed without the APPROVE succeeds after
it, and the HUMAN gate record binds the two.

## Rules in force

Identical to RUNBOOK-B7.2: raw output to the episode, friction recorded as
it appears, two failed remediation attempts → ESC + stop.

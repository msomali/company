# §88 check 9 — release-branch merge vs human APPROVE (raw evidence)

- Date: 2026-07-18 (PDT); RUNBOOK-B7.3 check 9
- Release protection (owner-attested 15:03 PDT, bot cannot read config):
  required review, enforce_admins on, no status checks

## Prerequisite gates (step 2, captured this session)

| Gate | Review of record (COMMENTED, @msomali API-verified) | Record | Transition |
|---|---|---|---|
| DCE | 4729371783 | `GATE-TASK-001-DCE-1.yaml` | PRODUCTION_READINESS → PRODUCT_ACCEPTANCE |
| PJM | 4729376823 | `GATE-TASK-001-PJM-1.yaml` | PRODUCT_ACCEPTANCE → HUMAN_RELEASE_AUTHORIZATION |

Drivers: `check9_capture_dce.py`, `check9_capture_pjm.py`; both records'
`approval_message_ref` verified against their review URLs (`ref_ok=True`).

## Step 3 — release PR (deviation noted)

- Owner cut `release` at the head of `main` (both `9b5aa3b`), so the
  runbook's "head `main`" PR was impossible (GitHub: "No commits between
  release and main"). Promotion instead rides `rc/TASK-001` carrying the
  release-notes artifact only. Recorded as B7.4 procedure friction.
- Release PR: #61 (base `release`, head `rc/TASK-001`).

## Step 4 — blocked leg (without the human APPROVE)

- Pre-attempt probe (read-only): `reviewDecision=REVIEW_REQUIRED`,
  base=release, state=OPEN — protection live for this PR.
- No HUMAN gate record exists at attempt time (verified: no
  `GATE-TASK-001-HUMAN-*` under `projects/PROJECT-000/gates/`).
- Faithful attempt: `PUT /repos/msomali/company/pulls/61/merge` with the
  true head sha of `rc/TASK-001` (BA-2 interlock per check 6).
- Response (verbatim): HTTP **405** — `"At least 1 approving review is
  required by reviewers with write access."`
- Post-attempt: `state=OPEN mergedAt=null` — nothing merged.
- Result (blocked leg): **PASS** — merge to the release branch without the
  human APPROVE is blocked by required reviews.

## Step 5 — succeeds leg (COMPLETE)

1. Owner issued `APPROVE TASK-001 HUMAN` as COMMENTED review 4729388103
   on PR #61 (@msomali, API-verified).
2. Captured pre-merge (driver `check9_capture_human.py`):
   `GATE-TASK-001-HUMAN-1.yaml` emitted (`ref_ok=True`,
   decided_at 2026-07-18T22:17:13Z); state → `DEPLOYMENT` (commit
   `39392b4`) — the authorization record precedes the release act.
3. Owner formal Approve + merge: PR #61 merged by @msomali —
   **merge SHA `f9bb463ba06539e40da180b52402da0b64d3d089`** (API:
   merged=true, merged_by=msomali).

- Result (succeeds leg): **PASS** — the same merge that returned 405
  without the human APPROVE succeeded after it; `GATE-TASK-001-HUMAN-1`
  binds the two legs.
- **Check 9 overall: PASS.**

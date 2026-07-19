# §88 check 8 — SSE/DPC approvals captured into gate records (raw evidence)

- Date: 2026-07-18 (PDT); actors: H (decisions) + A (capture);
  RUNBOOK-B7.3 check-8 steps 2–3
- Driver: `evidence/check8_capture.py` (committed pre-run); exit 0

## Channel of record (owner-settled review state)

- Decisions review: **COMMENTED** review `PRR_kwDOTZyvsc8AAAABGePYIg`
  (id 4729329698, user `msomali` verified via API, submitted
  2026-07-18T21:29:07Z) — body is exactly the three lines
  `APPROVE TASK-001 SAT` / `APPROVE TASK-001 SSE` / `APPROVE TASK-001 DPC`.
- Ignored per owner instruction (never passed to the parser): the
  accidental APPROVED review 4729320370 (superseded) and the
  CHANGES_REQUESTED review 4729344902 (cancellation-only, no decision
  lines). PR #58 `reviewDecision` = CHANGES_REQUESTED → merge stays
  blocked; its `MERGEABLE` flag is only the no-git-conflict bit.

## Capture run (verbatim output)

    §51 owner of record: @msomali
    parsed decisions: [('APPROVE', 'TASK-001', 'SAT'), ('APPROVE', 'TASK-001', 'SSE'), ('APPROVE', 'TASK-001', 'DPC')]
    APPLIED SAT: GATE-TASK-001-SAT-1.yaml decision=APPROVED ref_ok=True state_now=SECURITY_REVIEW
    APPLIED SSE: GATE-TASK-001-SSE-1.yaml decision=APPROVED ref_ok=True state_now=PRIVACY_COMPLIANCE_REVIEW
    APPLIED DPC: GATE-TASK-001-DPC-1.yaml decision=APPROVED ref_ok=True state_now=PRODUCTION_READINESS
    final state: PRODUCTION_READINESS

- Authorization: approver bound to the §51 owner parsed from the register
  (`owner_identity()`), not hardcoded.
- State-order enforcement exercised implicitly: SAT applied at
  QUALITY_REVIEW, SSE at SECURITY_REVIEW, DPC at
  PRIVACY_COMPLIANCE_REVIEW — any reordering would have raised.

## Emitted records (all reference the COMMENTED review URL)

| Record | gate_owner | decision | approval_message_ref confirmed |
|---|---|---|---|
| `gates/GATE-TASK-001-SAT-1.yaml` | SAT | APPROVED | ✓ …#pullrequestreview-4729329698 |
| `gates/GATE-TASK-001-SSE-1.yaml` | SSE | APPROVED | ✓ same |
| `gates/GATE-TASK-001-DPC-1.yaml` | DPC | APPROVED | ✓ same |

State history gained three gate transitions (each committed with the
review URL as evidence); `log.jsonl` gained three `gate_decision` events.

## Mechanism observation (minor)

`ApprovalsCapture.apply()` writes the gate record file but does not include
it in any commit — `transition()` commits only state.yaml + log.jsonl. The
records were committed manually after the run. Not friction-blocking for
§88.8 (the records exist and validate); flagged for the B4.3 dispatcher
runtime, which should own committing records it emits.

- Result: **PASS** — SSE and DPC human-held approvals issued in the §51
  interim channel and captured into schema-valid, immutable gate records
  by the dispatcher-side capture, with correct state advancement.

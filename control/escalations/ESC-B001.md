---
artifact_id: control/escalations/ESC-B001.md
title: ESC-B001 — Bootstrap blocked at B1.1; B0.1 precondition not met
type: escalation
project: control
owner: bootstrap
contributors: [bootstrap]
reviewers: [human-owner]
version: "1.1"
status: RESOLVED
sensitivity: internal
created: 2026-07-15
updated: 2026-07-16
approval: granted
---

# ESC-B001 — Bootstrap blocked: B0.x human preconditions incomplete

Filed under BA-2.7 / BA-7 and v1.1 §54. The bootstrap actor stops here; no
B-task work proceeds until the human owner resolves this record.

## Issue

`BOOTSTRAP-PLAN.md` task **B1.1** (initialize repo with seed kit; extract
digest) is the first agent-actor task. Its declared dependencies are
**B0.1–B0.2**, both HUMAN tasks. Verification on 2026-07-15 found:

| Task | Plan state | Observed evidence |
|---|---|---|
| B0.1 hardening evidence | unchecked | `handoff/control/sops/hardening-evidence.md` is an empty skeleton: all nine §85 evidence rows blank, none checked. **FAILING** |
| B0.2 forge + machine account + token | unchecked | Functionally satisfied: repo `msomali/company` exists; `agenticfoundrybot` PAT authenticates and pushed a branch (2026-07-15 22:00 PDT); `.secrets/` gitignored before token creation; file mode 600. Actions-secret copy not verifiable from the sandbox. **Needs human confirmation + checkbox** |
| B0.3 provider OAuth + policies/prices | unchecked | `control/models/policies.yaml` and `prices.yaml` REQUIRED-INPUTs unfilled. Not a B1.1 dependency but blocks B2.1+ |
| B0.4 §51 owner + §86 register signed | unchecked | §51 named-owner field blank; §86 register unsigned. Not a B1.1 dependency but blocks B7.1 |

Per v2.1 §85: "No Phase 1 activation may occur before every item below is
completed and the evidence checklist is committed." Per BA-2.7 the bootstrap
actor must not continue past a failing precondition.

## Positions

- **Bootstrap actor:** cannot start B1.1. Proceeding would violate BA-2.7 and
  the §85 normative precondition. Stopped; no seed-kit files committed to any
  mainline path.
- **Human owner:** RESOLVED 2026-07-16 per option 1 — B0.1 evidence completed and committed (`control/sops/hardening-evidence.md`, PR #2, owner-attested; rows 4/9 remain open by the annex's progressive design and close before §87), B0.2 confirmed (evidence row 6). ADR-B004 records the companion repo-visibility decision. Branch protection live. Bootstrap resumed at B1.1.

## Evidence links

- `handoff/BOOTSTRAP-PLAN.md` — all checkboxes unchecked (commit 114d9c4).
- `handoff/control/sops/hardening-evidence.md` — empty evidence table.
- `handoff/control/models/policies.yaml`, `prices.yaml` — REQUIRED-INPUT
  placeholders present.
- Successful authenticated push of `test-probe` by `agenticfoundrybot`
  (B0.2 functional evidence).

## Options considered

1. **(Recommended)** Human completes B0.1 on the host, fills and commits the
   evidence checklist, ticks B0.1/B0.2 in `BOOTSTRAP-PLAN.md` (or approves a
   bootstrap PR doing so with human-supplied evidence), then bootstrap starts
   B1.1. B0.3/B0.4 can follow in parallel before B2.1/B7.1.
2. Human grants a recorded §45-style exception deferring specific §85 rows
   with dates — requires an ADR; not recommended for security rows.
3. Proceed anyway — prohibited (BA-2.7); not an option.

## Requested decision

Complete/confirm B0.1 and B0.2 (and schedule B0.3, B0.4), or record an
explicit exception. Reply per §51 approval format or merge this PR with
direction in review comments.

## Decision deadline

Per v1.1 §51 SLA: acknowledgement ≤ 24 business hours; decision ≤ 72 business
hours. Until then bootstrap remains BLOCKED and idle.

## Note on filing location

No `control/escalations/` path exists in the §79 layout and no task episode
directory exists yet (no task envelope has been issued). This location was
chosen as the minimal non-destructive home for pre-B1.1 escalations; the human
owner may relocate it during B1.1 layout review if preferred.

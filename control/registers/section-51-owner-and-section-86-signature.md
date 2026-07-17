# Owner Record (v1 §51) and Compensating-Controls Register Signature (v2 §86) — B0.4

This record fills the v1 §51 Human Owner Specification by reference and constitutes
the human-owner signature required by v2 §86 ("each entry MUST carry human-owner
approval and a quarterly review date"). Committed per BOOTSTRAP-PLAN B0.4.

## v1 §51 — Human Owner Specification (filled)

| Field | Value |
|---|---|
| Named owner | msomali (GitHub: @msomali) |
| Roles held in v1.1 | SSE approval, DPC approval, Release Authority, Governance, change-management approver |
| Approvals channel | GitHub Pull Request review on `msomali/company` (designated equivalent per §51). Gate approvals of record = PR review + merge by @msomali under branch protection (required review, code owners, enforce_admins). The textual `APPROVE <task-id> <gate> …` format activates when the dispatcher and a dedicated `#approvals` channel exist (B4.x); adding that channel amends this record and requires setting the OpenClaw command owner (hardening evidence row 6). |
| Approval format | Interim: PR review Approve / Request changes, reasons in review comments; captured in gate records by the B5.x gate-writer on merge. |
| Acknowledgement SLA | ≤ 24 business hours (in force — exercised on ESC-B001) |
| Decision SLA | ≤ 72 business hours or an explicit recorded extension |
| Overdue behavior | Task remains BLOCKED. Agents MUST NOT proceed, infer approval, or route around the human. PJM MAY re-prioritize the queue. |
| Unavailability | Work queues. No delegation of human-mandatory approvals exists in v1.1; adding a delegate is a §44 change with its own identity and audit trail. |

## v2 §86 — Register signature (C1–C7)

I have read the full register text of v2.6 §86. For each entry I acknowledge the
stated *why unenforceable*, mitigations, residual risk, and backstop, and I approve
the entry as a deliberately accepted, registered risk — not an enforced control.

| Entry | Subject | Owner (per register) | Owner approval | Next review |
|---|---|---|---|---|
| C1 | In-model context precedence (§18) | SSE (human-held) | APPROVED | 2026-10-16 |
| C2 | Mid-generation budget interruption (§15) | DCE | APPROVED | 2026-10-16 |
| C3 | Cryptographically attested per-execution identity (§42) | SSE (human-held) | APPROVED | 2026-10-16 |
| C4 | Prompt-injection immunity (§39, §32) | SSE (human-held) | APPROVED | 2026-10-16 |
| C5 | Shared provider identity + subscription-policy volatility (§81 Mode S — ACTIVE, ADR-B003) | Human owner | APPROVED | 2026-10-16, and immediately on any provider terms change |
| C6 | Per-gate identity separation within bot output (ADR-B000) | Human owner | APPROVED | 2026-10-16, or when review volume exceeds careful single-person attribution |
| C7 | Bot PAT resident in agent-readable workspace (ADR-B002) | Human owner | APPROVED | 2026-10-16, and when a host-side credential-broker becomes available in OpenClaw |

Amendment note (accuracy over template): C7's mitigation text in v2.6 says
"fine-grained PAT (Contents + Pull requests RW)". Per the B1.2-era finding —
fine-grained PATs cannot access collaborator repos — the live token is a classic
PAT, `repo` + `workflow` scopes, 90-day expiry, blast radius bounded by
single-collaborator account hygiene. Signed as such; v2 wording correction queued
for the next doc revision.

Signed: msomali (human owner) — 2026-07-16.
Scope: constitutes B0.4 completion. Quarterly review of this register is a
standing owner duty; C5 additionally reviews on any provider policy movement.

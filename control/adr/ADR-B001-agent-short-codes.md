---
artifact_id: control/adr/ADR-B001-agent-short-codes.md
title: ADR-B001 — Uniform ≤3-Letter Agent Short Codes (ALE, LIN)
type: adr
project: control
owner: human-owner
version: "1.0"
status: APPROVED
sensitivity: internal
created: <fill on merge>
updated: <fill on merge>
approval: human-owner
---

# ADR-B001 — Agent Short Codes

**Context.** Eleven of the thirteen role IDs were already ≤3-letter codes (PJM, SAA,
UUD, SDE, SAT, SSE, DPC, DCE, DE, AIE, TW). Two agents carried persona names —
Alex (Customer Success) and Lina (Growth, Sales & Marketing) — which leaked persona
naming into the task-envelope enum, the model-policy agent map, and templates, and
broke the code convention.

**Decision.** Owner-directed rule: every agent name is a code of up to 3 letters
taken from the first letters of its name. Applied: **Alex → ALE** (OpenClaw id
`ale`), **Lina → LIN** (OpenClaw id `lin`).

The eleven existing codes already satisfy the ≤3-letter rule and are **unchanged**.
Re-deriving them from current role titles (SAT, SSE, DPC, PJM do not match their
titles' initials) was considered and rejected: those codes are load-bearing across
the Constitution Digest, task.json enum, eval directories, gate names, and the
§48.3 table, and changing them buys nothing but churn.

**Known trade-off.** ALE is visually one middle letter away from AIE. Accepted; if
it causes mis-addressing in practice, **ALX** is the reserved alternative (one-line
change here plus the same mechanical substitution set).

**Affected files.** v1.3 (§6, §7, §8.6, stage contributor lists, §18, §33–§34
headers, §48.3 table, §50, §55, §47 checklist); v3.0.1 (opportunity-sources list);
PROJECT-001 charter (`non_goals`); seed kit: `control/schemas/task.json`
(`assigned_role` enum), `control/models/policies.yaml` (agents map),
`control/templates/onboarding-assessment.md`. The Constitution Digest v1.1 is
unaffected — it contains no persona names. v2 is unaffected.

**Upgrade path.** A future rename is the same mechanical substitution set plus an
Appendix D change-record entry in each affected document.

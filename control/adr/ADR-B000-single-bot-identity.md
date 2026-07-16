---
artifact_id: control/adr/ADR-B000-single-bot-identity.md
title: ADR-B000 — Single Machine-Account Identity Replaces Three-Bot Design
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

# ADR-B000 — Single Bot Identity

**Context.** v2 §80.1 specifies three GitHub machine identities (`sat-bot`, `dce-bot`,
`pjm-bot`) so no single account can both author and approve the same artifact —
GitHub's required-review setting blocks a PR's author from approving their own PR,
and per-gate identities make that block map cleanly to SAT/DCE/PJM gate ownership.

**Decision.** For solo-operator scale, one machine account — `agenticfoundrybot` —
replaces all three. It authors commits and opens PRs for every agent (pjm, sde, sat,
dce). The human owner is the sole reviewer/merger.

**What is preserved.** Self-approval is still structurally blocked: the author
identity (`agenticfoundrybot`) is never the same as the approver identity (the human
owner's account), so GitHub's required-review rule still functions as a real gate.

**What is lost.** Per-gate identity separation *within* the bot's own output is no
longer GitHub-structural — e.g. GitHub cannot distinguish "SAT approved this" from
"DCE approved this" by account, because both post as the same bot. Gate attribution
(which role approved what) is recorded instead in the PR body / gate record content,
enforced by PR-template convention and human review, not by a second identity.

**Compensating control (register as v2 §86-C6).** *Mitigation:* every PR states its
role and gate explicitly in the handoff template; the human owner reviews gate
attribution as part of merge, not just code correctness. *Residual risk:* a
mis-attributed gate (bot claims SAT reviewed when it was actually SDE output) is
only caught by human read, not by GitHub structure. *Owner:* human owner. *Review:*
revisit if/when review volume exceeds what one person can carefully attribute.

**Affected files.** CODEOWNERS (single owner for all gated paths); v1 §48.3 agent
table (all four active agents push via `agenticfoundrybot`); BA-6 tasks B0.2, B4.3.

**Upgrade path.** Splitting back into per-gate identities is a later ADR: create the
additional accounts, split CODEOWNERS paths across them, no other structural change
needed — the PR-template gate-attribution convention already in place transfers
directly.

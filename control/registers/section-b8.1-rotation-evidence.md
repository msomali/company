---
artifact_id: control/registers/section-b8.1-rotation-evidence.md
title: B8.1 — Bootstrap Identity Token Rotation Evidence
type: register
project: company
owner: msomali
version: "1.0"
status: APPROVED
sensitivity: internal
created: "2026-07-20"
updated: "2026-07-20"
approval: "msomali 2026-07-20"
---

# B8.1 — Bootstrap Identity Rotation (BA-6; post-§87 owner act)

Per BOOTSTRAP-PLAN B8.1 / Bootstrap Annex BA-6: "Revoke bootstrap identity and
tokens; archive this annex's working branch." Executed 2026-07-20, post Phase-1
declaration (PR #78). **This is credential hygiene only — no agent was activated
(BA-2.4); agent activation remains a separate future human act.**

## What rotated

| Credential | Action | Note |
|---|---|---|
| Bot PAT (bootstrap, ~2026-07-15, classic `repo`+`workflow`) | **REVOKED** 2026-07-20 from the `agenticfoundrybot` session | Not owner-executable — revoked from the bot account per incident-SOP custody rule |
| Bot PAT (operational) | **MINTED** 2026-07-20, classic `repo`+`workflow`, 90-day | Classic PAT retained per v2.7 §80.4 / ADR-B002 / §86-C7 — fine-grained is structurally unavailable to a collaborator account (BA-6 B0.2's "fine-grained" wording superseded) |
| Actions secret `GH_TOKEN_AGENTICFOUNDRYBOT` | **UPDATED** to operational token | gate-writer home; verified by this PR's merge (gate record emits on new secret) |
| Workspace file `<repo>/.secrets/gh-token` | **UPDATED** to operational token, mode 600 | agent git/gh home |

## What did NOT rotate (deliberately)
- **Bot identity** (`agenticfoundrybot`) — retained; ADR-B000 single-bot identity persists into operations. Only its token rotated.
- **Dispatcher deploy key** (`dispatcher@company-vm`, id 157623533) — already current (minted 2026-07-17 during the kill-switch drill), not a bootstrap-stale credential; untouched.
- **Collaborator access** — retained (the identity we keep).

## Verification (rotate-then-verify-then-revoke; machine never lost its credential)
1. New token minted; **old token left live as fallback**.
2. Both homes updated atomically (Actions secret + workspace file 600).
3. New token verified BEFORE revoking old: `gh api user` → `agenticfoundrybot`; `X-Oauth-Scopes: repo, workflow`.
4. Old bootstrap token revoked only after (3) passed.
5. Post-revoke re-verify: `gh api user` (new token) → `agenticfoundrybot` — old token's death stranded nothing.
6. Dispatcher healthy throughout (`systemctl is-active` → active).

## Honest process note (rotation evidence, not a clean-room record)
The first replacement token attempt was discarded before use: it was minted
`repo`-only (missing `workflow`, caught by the pre-revoke scope check — which is
exactly why verify precedes revoke) AND was accidentally echoed to the terminal
(exposed in shell history). It was deleted from the bot account and history was
scrubbed; a correctly-scoped token was re-minted via silent entry (`read -rs`).
No exposed or mis-scoped token was ever the operative credential; the old
bootstrap token remained the fallback until the correct new token passed
verification.

## Lessons (for the credential-handling SOP)
- Secret-to-file entry MUST use silent read (`read -rs`), never a literal on the command line — prevents history exposure.
- Token minting MUST verify BOTH scopes (`repo`, `workflow`) before the old credential is revoked — missing `workflow` fails gate-writer silently later.

Attested by: msomali (human owner) — 2026-07-20. B8.1 rotation complete.

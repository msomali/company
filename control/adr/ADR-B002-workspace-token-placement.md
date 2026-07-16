---
artifact_id: control/adr/ADR-B002-workspace-token-placement.md
title: ADR-B002 — Bot PAT Lives in the Agent Workspace (Registered Exception to BA-3)
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

# ADR-B002 — Workspace Token Placement

**Context.** BA-3 prohibits placing any secret where the bootstrap actor can read
it — the rationale being that anything an agent reads enters model context and
transcripts. Phase-0 testing established two hard substrate facts: OpenClaw blocks
bind-mounting any system path (`/etc/*`, credential stores, docker.sock) into a
sandbox container, and the JSON config does not expand `~`. Agents must
authenticate `git push` / `gh` from **inside** the sandbox to satisfy
one-task-one-branch-one-PR; the workspace tree is the only mountable location.
The first bootstrap attempt failed on exactly this contradiction.

**Decision.** The bot PAT (`GH_TOKEN_AGENTICFOUNDRYBOT`) is stored at
`<repo>/.secrets/gh-token` — inside the workspace, gitignored **before** the file
is created, mode 600 — and additionally as a GitHub Actions secret for CI use.
This is the **sole** exception to BA-3. Every other secret keeps its BA-3
destination (dispatcher host env file, Actions secrets, proxy `env_file`); provider
API keys in particular never enter any workspace.

**What is accepted.** The token value can enter agent context. Registered as
**v2 §86-C7** with mitigations: fine-grained PAT scoped to the single company repo
(Contents + Pull requests RW only, nothing else); gitleaks CI (POL-009) on every
PR; 60–90-day expiry and rotation; handling rule in BA-2.2 as amended (read only
into `GH_TOKEN`, never print/echo/log/commit/transmit); revocation at B8.1 and on
any incident. Protected branches plus human-only merge mean a leaked token cannot
merge or release anything — the blast radius is unreviewed branch/PR noise until
revocation.

**Rejected alternatives.**
(a) `/etc/company/...` bind mount — hard-blocked by OpenClaw (the original failure).
(b) Host-side git credential helper injected from outside the sandbox — no OpenClaw
mechanism exposes one into sandboxed `exec` today; the C7 review clause revisits
this whenever a credential-broker capability appears.
(c) No agent token; the human pushes on the agent's behalf — defeats A2 autonomy
and makes the human the bottleneck on every commit, not just every merge.

**Affected files.** Bootstrap Annex rev 1.1 (BA-2.2, BA-3 table, B0.2); v2.5
(§80.4, §86-C7); `control/secrets/SECRETS-MANIFEST.md` (governance line);
PHASE-0-RUNBOOK v3 (Steps 5–7 token handling and AGENTS.md text).

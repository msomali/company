---
artifact_id: control/adr/ADR-B006-delivery-path.md
title: ADR-B006 — Work-Product Delivery Path (Dispatcher Harvest, CI-Opened PRs, Credential-Free Role Workspaces)
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

# ADR-B006 — Work-Product Delivery Path

**Context.** The first live spawn (TASK-003, 2026-07-22, 58s SDE turn) proved
execution but exposed the missing organ: the deliverable sits in the role
workspace (`~/company-agents/sde` — no git, no credentials, by design), the
dispatch commit landed on whatever branch the dispatcher clone had checked out
(local `main`, unpushable; owner relocated it to `dispatch/TASK-003` by hand),
and nothing connects workspace product → task branch → PR → gate review.
Delivery mechanics were left to the §82 build items; this ADR fills that gap.

What the constitution actually binds (researched 2026-07-22):

- v1 Part IX §17: **every handoff of a material artifact is a pull request**;
  the §15 ten-item package is the PR template; CI blocks merge while any item
  is absent. The PR is the handoff — not an implementation detail.
- v2 §80.1 (ADR-B000): `agenticfoundrybot` **authors all agent commits and
  PRs**; the human owner is sole reviewer/merger. Role attribution rides the
  handoff template and gate record (§86-C6), not separate accounts.
- v2 §80.5 (ADR-B002 amendment, owner rider 2026-07-17): the dispatcher is
  **infrastructure identity** — own deploy key, independently revocable,
  never pushes `main`, authors state/episode commits as
  `dispatcher <dispatcher@company.local>`; three-way provenance ledger
  (owner / agent-roles / infrastructure).
- v2 §6/§82.1: the envelope's `required_outputs` is mandatory and validated
  before any model call — the declared shape of what a task may deliver.
- v2 §85.4/§85.6 + §86-C7: containment posture; credentials never in agent
  context except registered exceptions. C7 registers exactly ONE
  workspace-resident PAT (bootstrap's), with review triggers on any surface
  change. ADR-B002's context is bootstrap-specific necessity ("the first
  bootstrap attempt failed on exactly this contradiction"), and its
  rejected-alternative (c) rejected the *human* as pusher, not infrastructure.
- §88 archaeology: the dry-run minted the branch pattern —
  `sde/TASK-001-slugify` (work), `dispatch/TASK-001` (state/episode),
  `rc/TASK-001` (release) — but bootstrap's PAT played every role; the
  pattern, not the credential path, is the precedent.
- B5.2 precedent: `gate-writer.yml` already opens PRs **from CI as the bot**
  using the existing Actions secret `GH_TOKEN_AGENTICFOUNDRYBOT`
  (`persist-credentials: false` lesson recorded in-file).

**Decision.**

1. **Dispatcher-side harvest.** On a successful turn, the dispatcher collects
   **exactly the envelope's `required_outputs`** (workspace-relative paths;
   traversal rejected; size-capped) from the role workspace into its clone on
   branch **`<role_lc>/TASK-###[-slug]`** and pushes with its deploy key.
   Nothing outside `required_outputs` ships — structural output containment:
   a prompt-injected agent cannot attach undeclared files to a delivery.
2. **Provenance via author/committer split.** Harvest commits carry
   author `agenticfoundrybot <agenticfoundrybot@users.noreply.github.com>`
   (agent-roles lane, §80.1) and committer `dispatcher
   <dispatcher@company.local>` (the ferry stays visible), plus
   `Task: TASK-### / Role: <ROLE>` trailers (§86-C6 attribution). §80.5's
   enumeration is extended by this ADR: dispatcher-*authored* = state/episode;
   bot-authored-dispatcher-*committed* = harvested work product. Authorship
   metadata is provenance, not authentication — GitHub attributes the push to
   the deploy key; the gate reviewer verifies attribution per §86-C6.
3. **PR opened by CI as the bot.** A `delivery` workflow triggers on pushes to
   the thirteen role-branch globs, validates the harvested handoff through
   `handoff_check` (the pr_open.py refusal gate: any failure → loud red run,
   **no PR opened**, finding recorded), then opens the PR as
   `agenticfoundrybot` via the **existing** `GH_TOKEN_AGENTICFOUNDRYBOT`
   Actions secret. No second Actions secret is introduced (no §86-C7 review
   trigger). §80.1 holds: the bot authors the PR. v1 Part IX holds: the PR is
   the handoff, ten sections enforced at creation and at merge.
4. **The handoff body is agent work.** Every envelope carries `handoff.md`
   (the §15 ten sections) as a standing required output — the role agent
   writes its own handoff in the workspace; harvest ships it; CI validates
   it and uses it as the PR body. Role-claim line (`role: <GATE>`) included
   per §86-C6 for role-prefixed branches.
5. **Role workspaces stay credential-free.** ADR-B002's PAT placement does
   NOT extend to role workspaces. C7's surface stays ×1 (bootstrap) and
   retires on schedule at B8.1; role sandboxes keep zero git credentials and
   no GitHub egress requirement.
6. **Lane separation.** `dispatch/TASK-###` remains state/episode only. The
   live-dispatch defect (committing to the clone's checked-out branch) is
   root-caused as an implicit-branch assumption; the implementation item
   makes the dispatcher create-or-target `dispatch/TASK-###` explicitly in
   live mode, matching the dry-run pattern (owner finding 2, 2026-07-22).

**Custody implications, stated both ways (owner brief 2026-07-22).**

- *Chosen (harvest):* zero new credential homes — PAT stays in its two
  (bootstrap workspace + Actions secret), deploy key scope unchanged, role
  sandboxes stay clean. The kill switch remains one lever: severing the
  deploy key halts state AND delivery pushes; disabling the delivery workflow
  halts PR creation. New trust: the dispatcher handles work-product bytes —
  it already writes episodes and is non-model infrastructure (§80.5); its
  compromise = forged commits on unprotected branches until key revocation,
  bounded by protected `main`, human-only merge, gitleaks (POL-009), and the
  handoff gate.
- *Rejected (agent-side push — §80.4's letter generalized to the fleet):*
  replicating the classic `repo`+`workflow` PAT into thirteen
  injection-exposed sandboxes multiplies C7's registered residual risk by
  fleet size and by task-content exposure; every single-agent incident forces
  fleet-wide rotation (two homes become fifteen); the sandbox egress
  allowlist must open github.com in every role container (new exfiltration
  channel, §85.4); and the B8.1 PAT retirement would break the delivery path
  the day bootstrap dissolves. C7 was signed for surface ×1; ×13 is a
  different control regime. The governed route back to agent-side push is
  ADR-B000's preserved three-identity upgrade (per-role bots, org-owned
  fine-grained tokens) — an explicit future ADR, not a silent extension.
- *Rejected (bootstrap ferries deliveries):* entangles the dissolving
  bootstrap actor in the Phase-1 runtime loop (BA lifecycle; B8.1).
- *Rejected (human ferries deliveries):* ADR-B002 rejected-alternative (c)
  reasoning — per-commit human bottleneck defeats A2 autonomy; the human's
  constitutional seat is the gate, not the transport.

**What is accepted.** (a) The dispatcher can technically write files the
envelope did not declare only by code defect, not by agent action — harvest
code is CI-tested infrastructure under `control/scripts/`. (b) Author-field
provenance is metadata; the §86-C6 gate-review verification is the check.
(c) Harvest fidelity depends on `required_outputs` naming concrete
workspace-relative paths — `task-create` validation tightens accordingly
(implementation item). (d) A failed handoff validation strands the product on
the role branch until the next dispatch cycle or owner action — deliberate:
nothing handoff-invalid reaches review.

**Rejected alternatives.** Folded into custody implications above.

**Decision record (ADR lifecycle).** Decision: **ACCEPTED**, decided-by:
msomali, 2026-07-22 (webchat; the approving review on this PR's head is the
acceptance act). Front-matter `status` uses the artifact schema's vocabulary
(`APPROVED`); this block carries the ADR-lifecycle state, matching ADR-B000–
B005. Acceptance binds three implementation requirements:

1. **Delivery refusal is loud and episodic.** A handoff-validation refusal (or
   any delivery-path refusal) is recorded as an episode log event AND surfaces
   as a red delivery-workflow run — never a silent no-op. The stranded-on-
   branch state in "What is accepted" (d) is always accompanied by both
   signals.
2. **Harvest-side secret scan, pre-push.** The dispatcher scans the collected
   `required_outputs` set before committing/pushing and refuses the harvest on
   any hit — PR-CI (POL-009) catching it at merge is too late; pushed branch
   history is already the exposure. The refusal follows requirement 1's
   loud-and-episodic rule.
3. **Envelope-author rule (SOP).** `required_outputs` is the COMPLETE delivery
   manifest: anything not listed does not ship. The SOP's envelope-authoring
   guidance states this explicitly so task authors treat the field as the
   delivery contract, not a hint.

TASK-003 waits for the implementation — no one-off manual harvest (supersedes
the interim option floated in the proposal discussion).

**Affected files.** `control/scripts/dispatcher_runtime.py` +
`session_backend.py` (harvest, explicit `dispatch/TASK-###` targeting,
`durationMs` parse — owner findings 2–3 ride the implementation PR);
`.github/workflows/delivery.yml` (new); `control/schemas/task.json`
(`required_outputs` path convention + `handoff.md`); `control/sops/
dispatcher-install.md` (delivery section; plus owner findings 4a — temporary-
main-entry container cleanup — and 4b — in-sandbox test verification);
`handoff/` v2 §80.5 wording rider (recorded by this ADR, applied at the next
constitution revision); `SECRETS-MANIFEST.md` unchanged (no new rows — that
is the point). First execution: TASK-003 harvest from `~/company-agents/sde`
→ `sde/TASK-003-titlecase` → delivery PR → gate → episode close.

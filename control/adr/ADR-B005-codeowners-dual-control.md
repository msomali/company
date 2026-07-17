# ADR-B005 — CODEOWNERS dual-control co-ownership on owner-input paths
Decision: `/control/**`, `/company/**`, `/memory/org/**`, `/memory/roles/**` are
co-owned by @msomali and @agenticfoundrybot. Sole human ownership made
owner-authored PRs on those paths unmergeable once code-owner review is required
(B1.2 Phase 1): authors cannot self-approve and no other code owner existed
(B0.4 signature, model inputs, evidence pastes are all owner-authored).
Invariant preserved: with exactly two registered identities (ADR-B000), GitHub's
author-cannot-self-approve rule guarantees every gate-path merge carries two
distinct identities — bot-authored PRs still require the human owner;
owner-authored PRs are satisfied by bot review (interim owner-PR rule, in
practice since PR #2). If `require_last_push_approval` is ever enabled, revisit:
it would block approvals from a co-pushing reviewer.
Rejected: (b) per-occasion enforce_admins toggles — manual, easy to forget to
re-enable, and creates protection-off windows that leave no structural trace.
Status: APPROVED, owner (merge of PR #7); proposed by bootstrap.

---
memory_id: MEM-ORG-0004
namespace: org
type: observed
subject: "ADR-B000 kills the review-body claim channel: bot-role PRs must claim their gate role in the PR body"
scope: every bot-role PR and every gate-record emitter, permanently (not a dry-run quirk)
source: "§88 check-7 hold 2026-07-18: gate-writer emitted GATE-HUMAN-PR53 for a SAT-gated PR; owner analysis + bootstrap assessment; PR #53 comments 5012331464/5012336995"
creator: bootstrap agent (agenticfoundrybot), from owner check-7 hold decision
confidence: verified
sensitivity: internal
created: "2026-07-18"
updated: "2026-07-18"
expires: null
retention: permanent while ADR-B000 single-bot identity stands; revisit only on per-gate identities upgrade
supersedes: null
superseded_by: null
related: ["control/adr/ADR-B000-single-bot-identity.md", "projects/PROJECT-000/dryrun/RUNBOOK-B7.2.md", "control/scripts/gate_writer.py", "control/scripts/handoff_check.py"]
---

# ADR-B000 kills the review-body claim channel — claim the gate role in the PR body

## The constraint

gate-writer derives `gate_owner` from §86-C6 claim markers (a line-start
`role: <ROLE>` or a `GATE-<ROLE>` token) found in **approving review bodies
or the PR body** — never from reviewer identity. Under ADR-B000 the single
bot account authors every bot PR, and GitHub structurally forbids an author
reviewing its own PR. Consequence, permanent and structural:

**For every bot-role PR, the approving-review-body claim channel is dead.
The PR body (handoff template) is the only live claim channel.** A bot-role
PR whose body lacks the machine-readable claim will be recorded as a HUMAN
gate no matter how thorough the role review was — the attribution §86-C6
carries simply never reaches the emitted artifact.

## How it bit (first §88 check-7 run, 2026-07-18)

PR #53 carried a full SAT two-cycle review in gate-record-format comments
(runbook check-5 form). Comments are invisible to gate-writer; the PR body
had SAT only in prose, not in claim form; the owner's approving review body
was empty. The emitter — behaving exactly to spec — emitted
`GATE-HUMAN-PR53`, and the C6 attribution under test in §88.7 was absent
from the artifact. Corrected via PR-body claim + workflow_dispatch replay.

## The rule (enforced)

Bot-role PRs (head branch prefixed with a role short-code, ADR-B001) MUST
carry a line-start `role: <ROLE>` claim in the PR body, naming the
gate-owner role (SAT/SSE/DPC/DCE/PJM, or HUMAN for a conscious no-bot-gate
claim). Mandatory, not advisory: a doctrine rule with no gate silently
regresses (same failure class as plan ticks without artifacts, L-001/
MEM-ORG-0001). handoff-check fails role-prefixed PRs without the claim.
The human owner verifies claimed attribution at merge — the C6 backstop.

## Deferred hardening

Extending `claimed_role()` to scan issue comments (where review evidence
lives) would let the check-5 and check-7 mechanisms compose directly.
Deferred to activation era; recorded as B7.4 friction.

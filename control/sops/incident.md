# Incident SOP — v2 §63 / v2 §78 row 28 (finalized B6.2)

Applies to AI incidents per §63: harmful output, data exposure, unauthorized
action, tool misuse, memory poisoning, prompt injection, regressions, cost
runaway, workflow failure, audit loss, material hallucination. The human
owner is incident commander for every incident; agents only assist inside
their sandboxes and never communicate externally (v1.1 §55).

## 1. Detect / report

Open `control/escalations/INC-###.md` (artifact front matter, `type:
escalation`) with: timestamp, reporter (human or agent + session), incident
class from the §63 list, affected systems/artifacts, and the observation
that triggered it. An agent that suspects an incident stops its task and
files the record (or reports in-channel if the repo is unreachable) — BA-2.7
spirit: no self-directed remediation.

## 2. Contain

Severity call by the owner:

- **Full stop** (default for data exposure, unauthorized action, memory
  poisoning, prompt injection with side effects, cost runaway):
  `sudo bash control/scripts/kill_switch.sh pause` on the host — stops
  dispatcher + containers, revokes model access (gateway stop, Mode S),
  revokes the dispatcher deploy key, freezes `main`, archives evidence
  (drilled per `control/sops/killswitch-drill.md`; hardening row 9).
- **Scoped stop** (single-surface regressions/workflow failures): stop the
  offending unit only (`systemctl stop company-dispatcher.service`, or close
  the agent session) and record why full pause was unnecessary.

## 3. Preserve evidence

Before ANY cleanup: kill-switch pause already archives episodes + dispatcher
journal to `/var/company/incident-<stamp>/`; additionally capture `git
status`/`git stash list` of touched worktrees, relevant session transcripts,
and gateway logs. Nothing is deleted, rewritten, or force-pushed during an
incident — audit loss is itself a §63 incident class.

## 4. Secret exposure (POL-009)

If any secret VALUE was exposed (even masked or partial), rotate now —
custody and rotation procedures per row in
`control/secrets/SECRETS-MANIFEST.md`:

| Credential | Rotation |
|---|---|
| Bot PAT (GH_TOKEN_AGENTICFOUNDRYBOT) | **FAST, owner-side (C7):** remove the bot as collaborator — `gh api -X DELETE repos/msomali/company/collaborators/agenticfoundrybot` — severs repo access instantly regardless of token state (an exfiltrated token works off-host; host containment does not touch it). Revocation itself is **not owner-executable**: a PAT belongs to its account and is revoked only from the `agenticfoundrybot` session. Then: revoke + mint replacement from the bot session; update Actions secret + workspace file (600); owner re-invites (`-X PUT …/collaborators/agenticfoundrybot -f permission=push`), bot accepts, verify 204. While removed, ADR-B005 dual-control CODEOWNERS cannot be satisfied — expected under freeze. |
| Gateway token | Regenerate file (`openssl rand -hex 32`) + `openclaw gateway restart` |
| Dispatcher deploy key | Delete key on repo (kill-switch step 4 does this); new keygen + re-register per dispatcher-install §3b |
| Provider auth (Mode S) | Re-mint setup-token / re-run OAuth sign-in per agent auth store |
| Actions-only secrets | Rotate at source, update repository secret |

Record rotation evidence (timestamps, old-key revocation confirmation) in
the INC record. Values never appear in evidence — existence checks only.

## 5. Rollback

Bad merges revert via `git revert` PRs into `main` — branch protection stays
in force during incidents (unfreeze first if paused; that act is deliberate
and logged in the INC record). Released artifacts roll back to the prior
release tag through the DCE human-gated path. Verify rollback with the same
checks that gated the original merge (CI + evals).

## 6. Communicate

The human owner sends all external and stakeholder communications (v1.1
§55). Agents draft only if asked, and drafts stay in the repo.

## 7. Remediate, review, prevent recurrence

Close the INC record with: root cause, actions taken, rotation evidence,
and the recurrence-prevention set —

1. **Lesson** → organizational memory record under `memory/org/` via
   reviewed PR (B6.1; pattern: MEM-ORG-0001).
2. **Eval case** → every failure that reached a gate becomes a golden/seeded
   case under `control/evals/` (§84.4; B5.1).
3. **Register review** → if a §86 C-item was involved, review its entry and
   mitigations; amend by PR with owner approval.
4. **Resume** → `kill_switch.sh resume` + the deliberate manual acts
   (unfreeze `main`, re-register deploy key), verified per
   killswitch-drill.md step 5.

INC records use the escalation numbering space (`INC-###` alongside
`ESC-###`) and the same front-matter discipline; both live in
`control/escalations/` under dual-control CODEOWNERS.

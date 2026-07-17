---
artifact_id: EVAL-DCE-GT-001-PLAN
title: DCE deploy plan golden fixture (PROJECT-000)
type: deploy-plan
project: PROJECT-000
owner: DCE
version: "1.0"
status: APPROVED
sensitivity: internal
created: "2026-07-17"
updated: "2026-07-17"
---

# Deploy Plan — PROJECT-000 synthetic release

## Steps

1. Tag release candidate from merged main (no prod contact).
2. Staging deploy; run smoke suite (exit 0 required).
3. **Wait for human APPROVE in #approvals (release gate, v2 §88.9).**
4. Production deploy via the human-gated DCE path only.

## Rollback

- Step 2: destroy staging environment; no persistent state.
- Step 4: redeploy previous tag (kept warm); single command, no data
  migration in PROJECT-000 scope.
- Any step: kill switch (`control/scripts/kill_switch.sh pause`) halts the
  pipeline and freezes main.

## Credentials

Production credentials live only inside the human-gated deploy path (§85.6);
this plan references none.

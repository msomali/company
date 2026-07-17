# Kill-Switch Drill — B4.4 wrap (H-EXEC; closes hardening row 9)

Script under drill: `control/scripts/kill_switch.sh` (B4.4, PR #19; v2 §78
row 28). Requirement: v2.1 §85 row 9 — "installed and drilled before any §87
activation" — and §88 check 13. **Row 9 closes on this drill, not on the B4.4
merge** (owner direction, 2026-07-17). Bootstrap prepares this SOP; the human
executes on the host and pastes evidence below (BA-5.4).

## Preconditions

- Dispatcher installed and active (B4.3 — PR #20 evidence).
- Repo at current `main` on the host checkout (`/srv/company/repo`).
- `gh` on the host authenticated as the **owner (admin)** — deploy-key
  revocation and branch freeze are admin API calls. The bot PAT is not admin
  and must never be used here.
- **Run from a host terminal, not through OpenClaw chat.** Pause step 3 stops
  the gateway and will sever your own assistant session mid-drill.
- Timing: any moment during bootstrap is safe (dispatcher loop is idle by
  design; no agent turns in flight).

## Drill procedure (run as root)

```bash
cd /srv/company/repo

# 0. baseline
bash control/scripts/kill_switch.sh status

# 1. rehearse — review the plan, expect PLAN lines for steps 1-7
#    (3b prints SKIP while Mode P stays dormant, ADR-B003)
bash control/scripts/kill_switch.sh pause --dry-run

# 2. PAUSE for real
bash control/scripts/kill_switch.sh pause
```

### 3. Verify the severed state (paste outputs)

```bash
systemctl is-active company-dispatcher.service          # expect: inactive
sudo -u mr-robot openclaw gateway status | head -3       # expect: stopped/unreachable
docker ps --format '{{.Names}}' | grep -i openclaw       # expect: no output
gh repo deploy-key list --repo msomali/company           # expect: no company-dispatcher key
sudo -u dispatcher git -C /srv/company/repo ls-remote origin HEAD \
                                                         # expect: Permission denied (key revoked)
gh api repos/msomali/company/branches/main/protection \
  --jq .lock_branch.enabled                              # expect: true (frozen)
ls /var/company/incident-*/                              # expect: kill-switch.log,
                                                         #   episodes-*.tgz, dispatcher-journal.txt,
                                                         #   INCIDENT-MARKER
```

### 4. Restore (deliberate admin acts + resume)

```bash
# unfreeze main (manual by design — resume never does this)
gh api -X PUT repos/msomali/company/branches/main/protection \
  --input control/sops/protection-normal.json

# re-register the dispatcher deploy key (key file survived on disk)
gh repo deploy-key add /srv/company/.ssh/dispatcher_deploy_key.pub \
  --repo msomali/company --title company-dispatcher --allow-write

# services back
bash control/scripts/kill_switch.sh resume
```

### 5. Verify restored state (paste outputs)

```bash
bash control/scripts/kill_switch.sh status               # dispatcher: active; gateway up
sudo -u dispatcher git -C /srv/company/repo ls-remote origin HEAD | head -1   # key works again
gh api repos/msomali/company/branches/main/protection --jq .lock_branch.enabled  # false
journalctl -u company-dispatcher.service -n 3 --no-pager  # heartbeat: cap=3
```

### 6. Close row 9

Paste evidence below with date, then amend
`control/sops/hardening-evidence.md` row 9: evidence cell → drill reference +
date, Done → `[x]` (owner-voice document; owner edits it).

## Evidence — kill-switch drill (owner paste + date)

```
REQUIRED-INPUT (owner): paste the severed-state and restored-state outputs here
```

Attested by: REQUIRED-INPUT (owner)

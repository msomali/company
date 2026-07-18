# Kill-Switch Drill — B4.4 wrap (H-EXEC; closes hardening row 9)

Script under drill: `control/scripts/kill_switch.sh` (B4.4, PR #19; v2 §78
row 28). Requirement: v2.1 §85 row 9 — "installed and drilled before any §87
activation" — and §88 check 13. **Row 9 closes on this drill, not on the B4.4
merge** (owner direction, 2026-07-17). Bootstrap prepares this SOP; the human
executes on the host and pastes evidence below (BA-5.4).

## Preconditions

- Dispatcher installed and active (B4.3 — PR #20 evidence).
- Host checkout at current `main` — run it, don't assume it:

  ```bash
  sudo -u dispatcher git -C /srv/company/repo pull --ff-only
  ```

  **Stale-checkout warning:** a stale checkout drills yesterday's script.
  The 2026-07-17 drill surfaced defects against live state (key title/path
  drift, user-context gateway) for exactly this class of reason — verify
  `git -C /srv/company/repo log --oneline -1` matches origin/main before
  starting.
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

Pause executes steps 1–3 and 6–7 itself. Steps 4 (deploy-key revoke) and 5
(freeze) are **printed OWNER commands** — root's `gh` is unauthenticated by
design (drill defect 4) — run them in your own window as printed. **Evidence
requirement:** the `lock_branch.enabled → true` read-back must be captured
immediately after the freeze PUT, at freeze time, not later.

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

## Targeted re-drill — row 9 closure (after PR: drill-defect fixes)

The 2026-07-17 full drill validated containment structure but three legs
were never demonstrated (defects 1–5, fixed in the follow-up PR). Row 9
closes on evidence of exactly these:

1. **Gateway sever + restore (user context):**
   `bash control/scripts/kill_switch.sh pause` step 3 shows DONE; verify
   `sudo -u mr-robot -i openclaw gateway status` → stopped; then resume
   step 1 DONE and status → running.
2. **Freeze/unfreeze cycle with read-backs:** freeze PUT →
   `.lock_branch.enabled` → `true` (captured at freeze time) → unfreeze PUT
   with protection-normal.json → read-back `false`.
3. **Scripted resume end-to-end:** `kill_switch.sh resume` with both service
   legs DONE and `kill-switch.log` present in the (pre-existing or created)
   evidence dir; dispatcher heartbeat `cap=3` after.

Paste the three legs' outputs below; then amend hardening-evidence row 9 to
`[x]` with this SOP + date as the evidence cell (owner-voice document; owner
edits it).

## Evidence — kill-switch drill (owner paste + date)

Full drill 2026-07-17: executed — five defects found and fixed forward
(see PR); containment verified except gateway sever + freeze, hence row 9
remains open pending the targeted re-drill above.

Drill 1 — full pause, 2026-07-17 19:32 PDT (evidence: /var/company/incident-20260718T023226Z/):
DONE: dispatcher stopped (journal: 8h16m uptime, clean stop); container 2dfe52bba53f stopped; evidence bundle written (kill-switch.log, episodes tgz, dispatcher-journal, INCIDENT-MARKER). Owner-side: deploy key revoked (ID 157550550; re-registration minted 157623533; ls-remote Permission denied while revoked). FAILED legs = script defects 1–5, documented and fixed in PR #35; restore completed manually, protection read-back clean.

Drill 2 — targeted re-drill on fixed script (HEAD a2b17ae), 2026-07-17 ~20:15 PDT:
Gateway severed: sudo -u mr-robot -i openclaw gateway stop → "Connectivity probe: failed / ECONNREFUSED 127.0.0.1:18789" (§78 row 28 Mode-S revocation demonstrated). Freeze/unfreeze: lock_branch read-backs captured true → false, all protections intact throughout. Scripted resume: evidence dir reused (defect-1 fix), owner commands printed with live-derived key path/title (defect-4/5 fix), DONE on both starts; status: dispatcher active, gateway up, bootstrap container up. Dispatcher start was a no-op (already active since 19:53 recovery — journal). Post-resume gateway probe ok; dashboard re-authed.

Row 9 closes on this evidence. MEM-ORG-0002 records the generalized lesson.

Attested by: msomali, 2026-07-17

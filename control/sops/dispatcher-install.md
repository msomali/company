# Dispatcher Install Spec — B4.3 (H-EXEC)

Bootstrap prepares (this file + the unit + the runtime); the human executes on
the host and pastes evidence below (BA-5.4). Runtime = BA-1.4: systemd service,
OS user `dispatcher`, outside OpenClaw.

## What gets installed

| Piece | Source | Destination |
|---|---|---|
| Repo checkout | `msomali/company` | `/srv/company/repo` (owned `dispatcher:dispatcher`) |
| Python venv | python3 + pyyaml + jsonschema | `/srv/company/venv` |
| Unit file | `control/sops/systemd-company-dispatcher.service` | `/etc/systemd/system/company-dispatcher.service` |
| Env file | created by you, from the names below | `/etc/company/dispatcher.env` (root:dispatcher, 640) |

Env file variable NAMES (values never in the repo — SECRETS-MANIFEST):
`GH_TOKEN_DISPATCHER` (reserved; not required for the idle loop),
`APPROVALS_CHANNEL_TOKEN` (reserved until the dedicated channel exists — §51
register pre-notes that adding it amends the register + sets the OpenClaw
command owner).

## Design decisions needing your sign-off at install (both pre-wired, neither irreversible)

1. **State-commit identity.** Episode/state commits made by the dispatcher are
   authored as `dispatcher <dispatcher@company.local>` — NOT the bot PAT
   identity. Rationale: ADR-B000 binds *agent* commits to `agenticfoundrybot`;
   the dispatcher is infrastructure (BA-1.4), and v2 §80.4 keeps its
   credentials out of agent reach. Distinct authorship makes state-machine
   writes auditable separately from agent work.
2. **Push path.** The dispatcher never pushes to `main` (protection applies to
   everyone). It commits state/episode changes locally and pushes to
   `dispatch/TASK-###` branches; episode artifacts enter `main` via the task's
   PR like everything else. This satisfies §79 ("episodes/ writable only by
   CI" on main) without weakening protection. If you prefer episodes to land
   exclusively via CI automation later, the gate-writer (B5.2) absorbs it.

## Install (run as root; each command idempotent)

```bash
# 1. user + directories
useradd --system --create-home --home-dir /srv/company --shell /usr/sbin/nologin dispatcher || true
install -d -o dispatcher -g dispatcher /srv/company

# 2. checkout + venv (as dispatcher)
sudo -u dispatcher git clone https://github.com/msomali/company /srv/company/repo || \
  sudo -u dispatcher git -C /srv/company/repo pull --ff-only
sudo -u dispatcher python3 -m venv /srv/company/venv
sudo -u dispatcher /srv/company/venv/bin/pip install pyyaml jsonschema

# 3. dispatcher git identity (design decision 1)
sudo -u dispatcher git -C /srv/company/repo config user.name  "dispatcher"
sudo -u dispatcher git -C /srv/company/repo config user.email "dispatcher@company.local"

# 4. env file (names only here; you supply values if/when needed)
install -d -m 755 /etc/company
touch /etc/company/dispatcher.env
chown root:dispatcher /etc/company/dispatcher.env && chmod 640 /etc/company/dispatcher.env

# 5. unit
cp /srv/company/repo/control/sops/systemd-company-dispatcher.service \
   /etc/systemd/system/company-dispatcher.service
systemctl daemon-reload
systemctl enable --now company-dispatcher.service
```

## Verify (paste output into Evidence below)

```bash
systemctl status company-dispatcher.service --no-pager | head -12
journalctl -u company-dispatcher.service -n 5 --no-pager
sudo -u dispatcher /srv/company/venv/bin/python \
  /srv/company/repo/control/scripts/dispatcher_runtime.py --once
```

Expected: service `active (running)`; journal shows the idle heartbeat
(`dispatcher: 0 task(s); concurrency cap=3`); `--once` exits 0. The loop is
deliberately idle during bootstrap — every manifest is contract-only, so
dispatch structurally refuses (BA-2.4); the service existing and surviving
restart is the B4.3 acceptance, not task throughput.

## Manual smoke (optional, no side effects)

```bash
echo "APPROVE TASK-999 SAT" | sudo -u dispatcher /srv/company/venv/bin/python \
  /srv/company/repo/control/scripts/dispatcher_runtime.py \
  --process-review --project PROJECT-000 --approver msomali --reference manual-smoke
# expected: "refused: ... unknown task TASK-999" — proves parse+authorize
# work and that nothing is invented for nonexistent tasks.
```

## Evidence — B4.3 (owner paste + date)

● company-dispatcher.service - Company dispatcher (v2 §82) — task state, approvals, metering
     Loaded: loaded (/etc/systemd/system/company-dispatcher.service; enabled; preset: enabled)
     Active: active (running) since Fri 2026-07-17 01:24:44 PDT; 7h ago
 Invocation: 7d629884fde64f74833fee931792b391
       Docs: file:///srv/company/repo/control/sops/dispatcher-install.md
   Main PID: 69993 (python)
      Tasks: 1 (limit: 4484)
     Memory: 18.8M (max: 1G, available: 1005.1M, peak: 23.1M)
        CPU: 657ms
     CGroup: /system.slice/company-dispatcher.service
             └─69993 /srv/company/venv/bin/python control/scripts/dispatcher_runtime.py --daemon --interval 60

Jul 17 01:24:44 mr-robot-VMware20-1 systemd[1]: Started company-dispatcher.service - Company dispatcher (v2 §82) — task state, approvals, metering.

dispatcher: 0 task(s); concurrency cap=3

Deploy-key rider executed per PR #17 review: key "dispatcher@company-vm" registered read-write <date>; GH_TOKEN_DISPATCHER retired — dispatcher authenticates by key only
Identity verification: ssh -T as dispatcher greets "Hi msomali/company!" — deploy-key scoped identity confirmed, 2026-07-17.

Attested by: msomali, 2026-07-17

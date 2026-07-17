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

## Design decisions — APPROVED by owner (PR #17 review, 2026-07-17) with the deploy-key rider

1. **State-commit identity (APPROVED).** Episode/state commits made by the
   dispatcher are authored as `dispatcher <dispatcher@company.local>` — NOT
   the bot PAT identity. ADR-B000 binds *agent* commits to `agenticfoundrybot`;
   the dispatcher is infrastructure (BA-1.4). The provenance ledger is
   three-way: owner / agent-roles / infrastructure.

   **Owner rider — authentication separation (binding):** the dispatcher
   pushes with its **own dedicated read-write deploy key** (ed25519, generated
   at install, key file mode 600 under the `dispatcher` user, registered on
   `msomali/company`) — **NEVER a third copy of the bot PAT.** Rationale
   (owner): independent revocation — the B4.4 kill switch cuts dispatcher
   access without touching agent pushes; no PAT custody proliferation; GitHub
   attributes pushes to the key. Custody row added to SECRETS-MANIFEST.
2. **Push path (APPROVED).** The dispatcher never pushes to `main` (protection
   applies to everyone). It commits state/episode changes locally and pushes
   to `dispatch/TASK-###` branches; episode artifacts enter `main` via the
   task's PR like everything else. This satisfies §79 ("episodes/ writable
   only by CI" on main) without weakening protection. If you prefer episodes
   to land exclusively via CI automation later, the gate-writer (B5.2)
   absorbs it.

**Read-path note (owner):** review-polling and fetches can run
unauthenticated while the repo is public (ADR-B004). **TODO at the private
flip:** provision a read credential for the dispatcher (the deploy key
already covers it — verify, then delete this line).

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

# 3b. dedicated deploy key (owner rider, PR #17) — never the bot PAT
sudo -u dispatcher install -d -m 700 /srv/company/.ssh
sudo -u dispatcher ssh-keygen -t ed25519 -N "" -C "company-dispatcher-deploy" \
  -f /srv/company/.ssh/dispatcher_deploy_key      # creates key 600 by default
# Register the PUBLIC key as a read-write deploy key (admin, one-time):
#   gh repo deploy-key add /srv/company/.ssh/dispatcher_deploy_key.pub \
#     --repo msomali/company --title company-dispatcher --allow-write
# (or Settings → Deploy keys → Add; check "Allow write access")
sudo -u dispatcher git -C /srv/company/repo remote set-url origin \
  git@github.com:msomali/company.git
sudo -u dispatcher git -C /srv/company/repo config core.sshCommand \
  "ssh -i /srv/company/.ssh/dispatcher_deploy_key -o IdentitiesOnly=yes"
# Revocation drill target (B4.4 kill switch): deleting the deploy key on the
# repo severs dispatcher push access without touching agent credentials.

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

Additional rider verification (paste with the rest):

```bash
sudo -u dispatcher git -C /srv/company/repo ls-remote origin HEAD | head -1   # deploy key works (read)
stat -c '%a %U' /srv/company/.ssh/dispatcher_deploy_key                        # expect: 600 dispatcher
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

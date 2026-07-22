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
`GH_TOKEN_DISPATCHER` — **RETIRED** by the deploy-key rider (PR #17 review,
executed PR #20): the dispatcher authenticates by its dedicated deploy key
only, never a PAT. Do not provision this variable.
`APPROVALS_CHANNEL_TOKEN` (reserved until the dedicated channel exists — §51
register pre-notes that adding it amends the register + sets the OpenClaw
command owner). The env file remains empty until then (evidence, PR #20).

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

## Addendum — session-spawn activation pre-flight (activation item 1, 2026-07-21)

The dispatcher spawns real agent turns via the `openclaw` CLI against the
loopback gateway (`control/scripts/session_backend.py`; one spawn = one agent
turn, `openclaw agent --json`). Model credentials never leave the gateway
user (Mode S, ADR-B003) — the dispatcher carries ONLY the gateway connection
token. Everything below is OWNER-executed on activation day, in order,
BEFORE the first one-shot.

### PREREQUISITE 1 — system-wide openclaw CLI (hard requirement)

The systemd unit runs `ProtectHome=yes`, and the `dispatcher` user gets **no
traverse rights into `/home/mr-robot`** — the home boundary stays intact
(owner ruling 2026-07-21; do NOT solve this with permissions). The CLI must
resolve from a system path:

```bash
npm install -g --prefix /usr/local openclaw
```

Resolution after install: the daemon resolves `/usr/local/bin/openclaw` via
the systemd default PATH; interactive `sudo -u dispatcher` shells resolve the
same binary. Nothing under `/home` is read by either path.

Verify (paste with pre-flight evidence — the one-shot is NOT run until this
passes):

```bash
sudo -u dispatcher which openclaw     # expect: /usr/local/bin/openclaw
sudo -u dispatcher openclaw --version # version prints, no error
```

### PREREQUISITE 2 — gateway token in the env file

Append to `/etc/company/dispatcher.env` (root:dispatcher 640; names in
SECRETS-MANIFEST — same secret as gateway auth, second destination):

```
OPENCLAW_GATEWAY_TOKEN=<gateway token value>
# seat config — REQUIRED for agent-id resolution (see PREREQUISITE 3):
OPENCLAW_CONFIG_PATH=/etc/company/openclaw-dispatcher.json
# optional — defaults to ws://127.0.0.1:18789 in session_backend.py
# OPENCLAW_GATEWAY_URL=ws://127.0.0.1:18789
```

Coupling (deliberate, owner ruling 2026-07-21): rotating the gateway token
severs dispatcher spawn access and dashboard login together — see the
killswitch-drill SOP note. Spawn pre-flight refuses when the variable is
absent; nothing is spawned on a refusal.

### PREREQUISITE 3 — the 13 role agents, applied to BOTH seats

**Why two seats (corrected 2026-07-21 after the first live-spawn failure):**
the `openclaw` CLI validates `--agent` against the **invoking user's own
config** before it ever contacts the gateway
(`src/commands/agent-via-gateway.ts`: unknown ids throw
`Unknown agent id "…"` client-side). The dispatcher's fresh default config
knew only `main`, so both live one-shots refused while the dry-run (no
gateway contact) stayed green. "Configured in gateway agents.list" is
necessary but NOT sufficient: the gateway seat executes; the dispatcher
seat resolves.

Generate ONE artifact, apply it twice:

```bash
python3 control/scripts/agents_config_gen.py --out /tmp/company-agents.json5

# Seat 1 — gateway (execution): merge agents.list into the gateway user's
# ~/.openclaw/openclaw.json (workspaces, models, containment; validate
# config, restart gateway — your standing pre-restart validator step).

# Seat 2 — dispatcher (id resolution): install the SAME file VERBATIM — it
# is a complete, valid JSON5 config document — then point the CLI at it
# via OPENCLAW_CONFIG_PATH (PREREQUISITE 2 env block):
install -o root -g dispatcher -m 640 /tmp/company-agents.json5 \
  /etc/company/openclaw-dispatcher.json
```

On the dispatcher seat the `workspace`/`model` fields are inert — only the
ids resolve; execution state stays with the gateway. No traverse into
`/home/mr-robot` is needed or permitted (standing ruling); device/pairing
state still lives in the dispatcher's own `~/.openclaw` (`/srv/company`).

The header carries provenance (source policies.yaml commit + date +
DO-NOT-HAND-EDIT): host config has no CI lint, so **regenerate after any
policies.yaml change and re-apply to BOTH seats; never hand-edit either
applied copy**. Each agent's gateway-side `workspace` must contain that
role's AGENTS.md from `control/manifests/_generated/<ROLE>/` (paths
adjustable; ids are not — the dispatcher spawns `agent_id = role.lower()`).
Fallbacks are explicit per entry: `agents.list[].model` without `fallbacks`
is STRICT (no fallback at all — docs concepts/model-failover); the explicit
pair is what makes a rate-limited primary fail over inside the runtime per
MODEL-002.

**Seat-check (verify BOTH, paste with pre-flight evidence — this check
would have caught the 2026-07-21 failure before any live attempt):**

```bash
# dispatcher seat — must list sde (and the other 12 ids),
# NOT just "main (default)":
sudo -u dispatcher bash -c 'set -a; . /etc/company/dispatcher.env; set +a; \
  openclaw agents list'

# gateway seat — same ids visible to the gateway user:
sudo -u mr-robot -i openclaw agents list
```

### PREREQUISITE 4 — first-connect device pairing

The dispatcher's first CLI connect may raise a one-time device-pairing
approval (gateway clients doc). Approve it (dashboard or `openclaw pairing`)
before the first one-shot, or the one-shot stalls on it.

### First live spawn — one-shot only; the daemon stays scan-only

`--daemon` NEVER dispatches: it constructs no session backend, by code. The
only spawning entrypoint is the owner-invoked one-shot:

```bash
# dry-run (default): prints role/model policy/caps/prompt hash/argv plus
# WOULD-REFUSE reasons; spawns nothing; exit 2 if anything would refuse
sudo -u dispatcher bash -c 'set -a; . /etc/company/dispatcher.env; set +a; \
  /srv/company/venv/bin/python control/scripts/dispatcher_runtime.py \
  --dispatch-once --project PROJECT-000 --task TASK-00X'

# live — same command + --live, human watching
```

Interlocks that must ALL hold before `--live` spawns: role manifest
`status: active` (owner flip, separate PR — BA-2.4), token present,
separation of duties, task not BLOCKED, concurrency slot free. Every refusal
is loud and spawns nothing.

### Live-observation list — first one-shot (observe, do not assume)

Owner requirement B (2026-07-21): run the first live one-shot under
deliberately tight caps (small `wall_clock_minutes` in the envelope) and
record:

1. **`--timeout` semantics under fallback:** total wall-time vs per-attempt
   across OpenClaw's up-to-10× overload retries and the model-fallback chain
   (docs state the retry loop, not its interaction with the CLI deadline).
   Compare actual wall time against the passed `--timeout`.
2. **Fallback visibility on a headless turn:** where the "↪️ Model
   Fallback" notice lands and whether `--json` meta reflects the
   fallback-vs-selected model.
3. **`in_flight` dedup:** a second one-shot against the same session key
   while a turn runs must surface `status: in_flight` (backend raises; no
   double spawn).
4. **Pairing friction:** whether PREREQUISITE 4 actually triggered, and
   where the approval surfaced.

Paste observations under Evidence below; they close requirement B.

## Evidence — session-spawn pre-flight + first one-shot (owner paste + date)

_(pending activation day)_
